from pathlib import Path
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from typing import Optional

try:
    import yaml
except ImportError:  # pragma: no cover - the harness test environment provides PyYAML
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
STANDARD = ROOT / "docs/kotlin-backend-structure-standard.md"
ENFORCEMENT = ROOT / "docs/kotlin-backend-structure-standard-enforcement.md"
FIXTURES = ROOT / "tests/fixtures/standalone-app"
GRADLE_CONTRACT_FIXTURE = FIXTURES / "gradle-contract"

ENV_CALL = re.compile(r"System\.getenv\s*\(([^)]*)\)")
DIRECT_FILE_READ = re.compile(
    r"(?:\bFiles\s*\.\s*[A-Za-z_][A-Za-z0-9_]*\s*\(|"
    r"\b(?:FileInputStream|FileOutputStream|FileReader|FileWriter|RandomAccessFile|"
    r"FileChannel|AsynchronousFileChannel|InputStreamReader)\s*\(|"
    r"\b(?:java\.io\.)?File\s*\(|"
    r"\b(?:Path|Paths)\s*\.\s*(?:of|get)\s*\(|"
    r"\.(?:inputStream|outputStream|reader|bufferedReader|readBytes|writeBytes)\s*\(|"
    r"\b(?:FileChannel|AsynchronousFileChannel)\s*\.\s*open\s*\(|"
    r"\b(?:FileSystems\s*\.\s*getDefault|Channels\s*\.\s*new(?:Input|Output)Stream)\s*\(|"
    r"\bURL\s*\(|\.(?:openStream|openConnection|getInputStream)\s*\()"
)
PROJECT_DEPENDENCY = re.compile(r'implementation\s*\(\s*project\s*\(\s*"([^"]+)"\s*\)\s*\)')
RUNTIME_DEPENDENCY = re.compile(r'implementation\s*\(\s*"([^"]+)"\s*\)')
PLUGIN_ID = re.compile(r'id\s*\(\s*"([^"]+)"\s*\)')
REQUIRED_DENIED_FAMILIES = {
    "org.springframework",
    "org.hibernate",
    "jakarta.persistence",
    "org.postgresql",
    "software.amazon.awssdk:secretsmanager",
    "org.springframework.ai",
    "com.anthropic",
    "com.openai",
}


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise AssertionError("PyYAML is required to execute standalone-app YAML fixtures")
    with path.open(encoding="utf-8") as source:
        value = yaml.safe_load(source)
    if not isinstance(value, dict):
        raise AssertionError(f"fixture YAML root must be a mapping: {path}")
    return value


def file_sources(config: dict) -> list[dict]:
    return [
        entry
        for entry in config["environment"]["allowlist"]
        if entry.get("source") == "file"
    ]


def validate_file_backed_path(path: Path, root: Path, max_bytes: int) -> None:
    """The security shape required by C-2 for an allowlisted file setting."""
    if not path.is_absolute():
        raise ValueError("file setting must be an absolute, non-symlink path")
    root = Path(os.path.abspath(root))
    if root.is_symlink():
        raise ValueError("file setting root must not be a symlink")
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("file setting escapes its configured root") from exc
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError("file setting path must not contain symlinks")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("file setting must exist") from exc
    resolved_root = root.resolve(strict=True)
    if os.path.commonpath((str(resolved), str(resolved_root))) != str(resolved_root):
        raise ValueError("file setting escapes its configured root")
    metadata = candidate.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("file setting must be a regular file")
    if metadata.st_size > max_bytes:
        raise ValueError("file setting exceeds its configured size")
    if metadata.st_mode & 0o022:
        raise ValueError("file setting must not be group/world writable")


def normalized_file_mode(value: object) -> Optional[str]:
    if isinstance(value, int):
        return format(value, "04o")
    if isinstance(value, str):
        candidate = value.strip().lower()
        try:
            return format(int(candidate, 8), "04o")
        except ValueError:
            return None
    return None


def validate_kubernetes_file_mapping(
    entry: dict,
    root: Path,
    add_error,
) -> None:
    """Compare declared file policy with the actual PodSpec that mounts it."""
    kubernetes = entry.get("kubernetes", {})
    if not isinstance(kubernetes, dict):
        add_error("FILE_READ_PERMISSION_MAPPING")
        return
    manifest_paths = kubernetes.get("manifests")
    if not isinstance(manifest_paths, list) or not manifest_paths:
        add_error("FILE_READ_PERMISSION_MAPPING")
        return
    security_context = kubernetes.get("security_context", {})
    volume = kubernetes.get("volume", {})
    expected_service_account = security_context.get("service_account")
    expected_fs_group = security_context.get("fs_group")
    expected_volume_name = volume.get("name")
    expected_read_only = volume.get("read_only")
    expected_mode = normalized_file_mode(volume.get("default_mode"))
    expected_subjects = set(entry.get("read_permission", {}).get("subjects", ()))

    for relative_path in manifest_paths:
        if not isinstance(relative_path, str):
            add_error("FILE_READ_PERMISSION_MAPPING")
            continue
        manifest_path = (root / relative_path).resolve()
        try:
            inside_root = os.path.commonpath((str(manifest_path), str(root.resolve()))) == str(root.resolve())
        except ValueError:
            inside_root = False
        if not inside_root or not manifest_path.is_file():
            add_error("FILE_READ_PERMISSION_MAPPING")
            continue
        try:
            manifest = load_yaml(manifest_path)
        except (AssertionError, OSError, ValueError):
            add_error("FILE_READ_PERMISSION_MAPPING")
            continue
        kind = manifest.get("kind") if isinstance(manifest, dict) else None
        if kind == "Deployment":
            pod_spec = manifest.get("spec", {}).get("template", {}).get("spec", {})
        elif kind == "Pod":
            pod_spec = manifest.get("spec", {})
        else:
            add_error("FILE_READ_PERMISSION_MAPPING")
            continue
        if not isinstance(pod_spec, dict):
            add_error("FILE_READ_PERMISSION_MAPPING")
            continue
        actual_security_context = pod_spec.get("securityContext", {})
        actual_service_account = pod_spec.get("serviceAccountName")
        actual_fs_group = actual_security_context.get("fsGroup") if isinstance(actual_security_context, dict) else None
        mount = next(
            (
                item
                for item in pod_spec.get("containers", [])[0].get("volumeMounts", [])
                if isinstance(item, dict) and item.get("name") == expected_volume_name
            ),
            None,
        ) if pod_spec.get("containers") and isinstance(pod_spec["containers"][0], dict) else None
        actual_read_only = mount.get("readOnly") if isinstance(mount, dict) else None
        actual_volume = next(
            (
                item for item in pod_spec.get("volumes", [])
                if isinstance(item, dict) and item.get("name") == expected_volume_name
            ),
            None,
        )
        actual_mode = None
        if isinstance(actual_volume, dict):
            for source_name in ("configMap", "secret"):
                source = actual_volume.get(source_name)
                if isinstance(source, dict) and "defaultMode" in source:
                    actual_mode = normalized_file_mode(source["defaultMode"])
                    break
        if (
            actual_service_account != expected_service_account
            or actual_fs_group != expected_fs_group
            or actual_read_only is not expected_read_only
            or actual_mode != expected_mode
            or not isinstance(actual_volume, dict)
            or not expected_service_account
            or expected_fs_group is None
            or not expected_volume_name
            or expected_mode != "0444"
            or not {f"serviceAccount:{expected_service_account}", f"fsGroup:{expected_fs_group}"}.issubset(expected_subjects)
        ):
            add_error("FILE_READ_PERMISSION_MAPPING")


def is_denied_coordinate(coordinate: str, denied_families: set[str]) -> bool:
    return any(coordinate.startswith(family) for family in denied_families)


def gradle_executable() -> Optional[str]:
    configured = os.environ.get("GRADLE_BIN")
    if configured and Path(configured).is_file():
        return configured
    discovered = shutil.which("gradle")
    if discovered:
        return discovered
    candidates = list(Path.home().glob(".gradle/wrapper/dists/gradle-*/**/bin/gradle"))
    candidates.sort(
        key=lambda path: tuple(
            int(part)
            for part in re.search(r"gradle-(\d+(?:\.\d+)*)", str(path)).group(1).split(".")
        ),
        reverse=True,
    )
    return str(candidates[0]) if candidates else None


def fixture_errors(root: Path) -> list[str]:
    config = load_yaml(root / "settings.yaml")
    build = (root / "build.gradle.kts").read_text(encoding="utf-8")
    errors: list[str] = []

    def add(code: str) -> None:
        if code not in errors:
            errors.append(code)

    if config.get("mode") not in {"general", "strict"}:
        add("STANDALONE_MODE_INVALID")

    plugins = PLUGIN_ID.findall(build)
    if plugins.count("lamp.standalone-app") != 1:
        add("PLUGIN_NOT_EXCLUSIVE")
    if "org.springframework.boot" in build or "spring-boot" in build:
        add("SPRING_BOOT_DEPENDENCY")
    mode_match = re.search(r'isolation\.set\(\s*"([a-z]+)"\s*\)', build)
    if mode_match is None or mode_match.group(1) != config.get("mode"):
        add("GRADLE_MODE_MISMATCH")
    for declaration in ("allowedProjectDependencies", "allowedRuntimeCoordinates", "mainClass"):
        if declaration not in build:
            add("FIXED_DECLARATION_MISSING")

    classpath = config.get("classpath", {})
    if not isinstance(classpath, dict):
        add("CLASSPATH_ALLOWLIST_SHAPE")
        classpath = {}
    if not isinstance(classpath.get("projects"), list) or not isinstance(classpath.get("runtime"), list):
        add("CLASSPATH_ALLOWLIST_SHAPE")
    allowed_projects = set(classpath.get("projects", []))
    allowed_runtime = set(classpath.get("runtime", []))
    denied_families = set(classpath.get("denied_families", ()))
    missing_denied_families = REQUIRED_DENIED_FAMILIES - denied_families
    if missing_denied_families:
        add("DENIED_FAMILY_MISSING")
    projects = set(PROJECT_DEPENDENCY.findall(build))
    runtime = set(RUNTIME_DEPENDENCY.findall(build))
    if projects - allowed_projects:
        add("PROJECT_NOT_ALLOWLISTED")
    if runtime - allowed_runtime:
        add("RUNTIME_NOT_ALLOWLISTED")
    if any(is_denied_coordinate(coordinate, denied_families) for coordinate in runtime):
        add("CLASSPATH_DENIED_FAMILY")

    evidence = config.get("evidence", {})
    if not isinstance(evidence, dict):
        add("EVIDENCE_PATH_INVALID")
    else:
        for name in ("build", "source", "settings"):
            relative_path = evidence.get(name)
            if not isinstance(relative_path, str):
                add("EVIDENCE_PATH_INVALID")
                continue
            candidate = (root / relative_path).resolve()
            try:
                inside_root = os.path.commonpath((str(candidate), str(root.resolve()))) == str(root.resolve())
            except ValueError:
                inside_root = False
            if not inside_root or not candidate.is_file():
                add("EVIDENCE_PATH_INVALID")
        manifest_paths = evidence.get("manifests", [])
        if not isinstance(manifest_paths, list):
            add("EVIDENCE_PATH_INVALID")
        else:
            for relative_path in manifest_paths:
                if not isinstance(relative_path, str):
                    add("EVIDENCE_PATH_INVALID")
                    continue
                candidate = (root / relative_path).resolve()
                try:
                    inside_root = os.path.commonpath((str(candidate), str(root.resolve()))) == str(root.resolve())
                except ValueError:
                    inside_root = False
                if not inside_root or not candidate.is_file():
                    add("EVIDENCE_PATH_INVALID")

    allowlisted_names = {
        entry["name"] for entry in config["environment"]["allowlist"]
    }
    source_files = sorted((root / "src/main/kotlin").rglob("*.kt"))
    environment_sources = [path for path in source_files if path.name.endswith("Environment.kt")]
    app_root_environment = [
        path for path in environment_sources
        if path.parent == root / "src/main/kotlin"
    ]
    if len(app_root_environment) != 1:
        add("ENVIRONMENT_DECODER_COUNT")
    allowed_environment = app_root_environment[0] if len(app_root_environment) == 1 else None
    for source_path in source_files:
        source = source_path.read_text(encoding="utf-8")
        is_allowed_environment = source_path == allowed_environment
        if not is_allowed_environment and ENV_CALL.search(source):
            add("ENVIRONMENT_OUTSIDE_ROOT")
        if not is_allowed_environment and DIRECT_FILE_READ.search(source):
            add("FILE_READ_OUTSIDE_ROOT")
        if not is_allowed_environment:
            continue
        for argument in ENV_CALL.findall(source):
            argument = argument.strip()
            if not argument:
                add("ENVIRONMENT_WHOLE_MAP")
                continue
            literal = re.fullmatch(r'"([A-Z0-9_]+)"', argument)
            if literal is None:
                add("ENVIRONMENT_DYNAMIC_NAME")
            elif literal.group(1) not in allowlisted_names:
                add("ENVIRONMENT_NOT_ALLOWLISTED")

    for entry in file_sources(config):
        if allowed_environment is None or "readValidatedFile" not in allowed_environment.read_text(encoding="utf-8"):
            add("FILE_READER_UNVALIDATED")
        for required in ("root", "max_bytes", "no_symlink", "no_group_world_write", "read_permission"):
            if required not in entry:
                add("FILE_VALIDATION_FIELD_MISSING")
            elif required in {"no_symlink", "no_group_world_write"} and entry[required] is not True:
                add("FILE_VALIDATION_FIELD_DISABLED")
        read_permission = entry.get("read_permission")
        if (
            not isinstance(read_permission, dict)
            or read_permission.get("mode") != "deployment-identity-allowlist"
            or not read_permission.get("subjects")
        ):
            add("FILE_READ_PERMISSION_MAPPING")
            continue
        if entry.get("material") != "public-ca":
            add("FILE_MATERIAL_CLASSIFICATION")
        kubernetes = entry.get("kubernetes", {})
        security_context = kubernetes.get("security_context", {}) if isinstance(kubernetes, dict) else {}
        volume = kubernetes.get("volume", {}) if isinstance(kubernetes, dict) else {}
        expected_subjects = {
            f"serviceAccount:{security_context.get('service_account')}",
            f"fsGroup:{security_context.get('fs_group')}",
        }
        if (
            not security_context.get("service_account")
            or security_context.get("fs_group") is None
            or not expected_subjects.issubset(set(read_permission["subjects"]))
            or volume.get("read_only") is not True
            or volume.get("default_mode") != "0444"
        ):
            add("FILE_READ_PERMISSION_MAPPING")
        validate_kubernetes_file_mapping(entry, root, add)

    return errors


class KotlinBackendStructureStandardTests(unittest.TestCase):
    def test_standard_registers_allowlisted_standalone_contract(self) -> None:
        text = STANDARD.read_text(encoding="utf-8")

        for phrase in (
            "Spring-free 실행 앱",
            "`standalone-app`",
            "M-1 (필수)",
            "M-4 (필수)",
            "C-2 (필수)",
            "per-app classpath allowlist",
            "Secrets Manager",
            "LAMP_BROKER_CA_FILE",
            "symlink",
            "runtime-boundary",
            "public-ca",
            "fsGroup",
        ):
            self.assertIn(phrase, text)

    def test_enforcement_specifies_executed_fixture_contract(self) -> None:
        text = ENFORCEMENT.read_text(encoding="utf-8")

        for phrase in (
            "standalone-app",
            "정상 fixture",
            "위반 fixture",
            "System.getenv()",
            "spring-boot-app",
            "classpath allowlist",
            "LAMP_BROKER_CA_FILE",
            "YAML",
            "evidence",
            "resolutionResult",
            "runtimeOnly",
            "public-ca",
            "fsGroup",
        ):
            self.assertIn(phrase, text)

    def test_normal_fixture_passes_semantic_standalone_rules(self) -> None:
        errors = fixture_errors(FIXTURES / "normal")
        self.assertEqual([], errors)

    def test_each_violation_fixture_fails_one_exact_semantic_rule(self) -> None:
        violations = sorted(path for path in (FIXTURES / "violations").iterdir() if path.is_dir())
        self.assertGreaterEqual(len(violations), 6)
        for fixture in violations:
            with self.subTest(fixture=fixture.name):
                config = load_yaml(fixture / "settings.yaml")
                self.assertEqual([config["expected_error"]], fixture_errors(fixture), fixture)

    def test_gradle_contract_scans_resolved_runtime_classpath(self) -> None:
        executable = gradle_executable()
        if executable is None:
            self.skipTest("Gradle executable is unavailable")
        plugin_source = (
            GRADLE_CONTRACT_FIXTURE
            / "buildSrc/src/main/groovy/StandaloneAppContractPlugin.groovy"
        ).read_text(encoding="utf-8")
        self.assertIn("runtimeClasspath", plugin_source)
        self.assertIn("resolutionResult", plugin_source)
        expected_errors = {
            "normal": None,
            "runtime-only": "CLASSPATH_DENIED_FAMILY",
            "transitive-runtime": "CLASSPATH_DENIED_FAMILY",
            "project-transitive-app": "PROJECT_NOT_ALLOWLISTED",
            "version-catalog": "CLASSPATH_DENIED_FAMILY",
            "plugin-injection": "CLASSPATH_DENIED_FAMILY",
            "file-origin": "ARTIFACT_ORIGIN_UNKNOWN",
            "flatdir-origin": "ARTIFACT_ORIGIN_UNKNOWN",
            "included-build-app": "PROJECT_ORIGIN_UNKNOWN",
        }
        file_setting = file_sources(load_yaml(FIXTURES / "normal/settings.yaml"))[0]
        compiled_environment = (
            GRADLE_CONTRACT_FIXTURE
            / "normal/src/main/kotlin/ExampleEnvironment.kt"
        ).read_text(encoding="utf-8")
        max_bytes_match = re.search(r"MAX_CA_BYTES\s*=\s*([0-9_]+)L", compiled_environment)
        self.assertIsNotNone(max_bytes_match)
        self.assertEqual(file_setting["max_bytes"], int(max_bytes_match.group(1).replace("_", "")))
        self.assertIn(file_setting["root_env"], compiled_environment)
        with tempfile.TemporaryDirectory(prefix="standalone-gradle-contract-") as directory:
            fixture = Path(directory) / "gradle-contract"
            shutil.copytree(GRADLE_CONTRACT_FIXTURE, fixture)
            publish = subprocess.run(
                [
                    executable,
                    "--no-daemon",
                    "--offline",
                    "-p",
                    str(fixture),
                    ":fixture-allowed-runtime:publish",
                    ":fixture-denied-runtime:publish",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, publish.returncode, publish.stdout + publish.stderr)
            transitive_publish = subprocess.run(
                [
                    executable,
                    "--no-daemon",
                    "--offline",
                    "-p",
                    str(fixture),
                    ":fixture-transitive-runtime:publish",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                0,
                transitive_publish.returncode,
                transitive_publish.stdout + transitive_publish.stderr,
            )
            result = subprocess.run(
                [
                    executable,
                    "--no-daemon",
                    "--offline",
                    "--continue",
                    "-p",
                    str(fixture),
                    ":allowed-project:jar",
                    ":project-transitive:jar",
                    ":project-denied:jar",
                    ":normal:compileKotlin",
                    *(f":{name}:verifyStandaloneContract" for name in expected_errors),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            output = result.stdout + result.stderr
            self.assertNotEqual(0, result.returncode, output)
            self.assertTrue(
                list((fixture / "normal/build/classes/kotlin/main").rglob("ExampleSettings.class")),
                output,
            )
            for name, expected_error in expected_errors.items():
                report = fixture / name / "build/standalone-contract-report.txt"
                self.assertTrue(report.is_file(), report)
                lines = report.read_text(encoding="utf-8").splitlines()
                errors = [
                    line
                    for line in lines
                    if line.startswith(("CLASSPATH_", "PROJECT_", "ARTIFACT_"))
                ]
                if expected_error is None:
                    self.assertEqual([], errors, report.read_text())
                    self.assertIn("CONTRACT_PASS", lines)
                    self.assertIn("module:com.example:fixture-allowed-runtime:1.0", lines)
                else:
                    self.assertEqual(1, len(errors), report.read_text())
                    self.assertTrue(errors[0].startswith(expected_error), report.read_text())

            with tempfile.TemporaryDirectory(prefix="standalone-ca-probe-") as probe_directory:
                probe_root = Path(probe_directory) / "allowed-root"
                probe_root.mkdir()
                good = probe_root / "good.pem"
                good.write_bytes(b"public-ca")
                good.chmod(0o600)

                final_link = probe_root / "final-link.pem"
                final_link.symlink_to(good)

                outside = Path(probe_directory) / "outside.pem"
                outside.write_bytes(b"outside-root")
                outside.chmod(0o600)

                intermediate_target = Path(probe_directory) / "outside-directory"
                intermediate_target.mkdir()
                (intermediate_target / "nested.pem").write_bytes(b"outside-root")
                intermediate_link = probe_root / "intermediate-link"
                intermediate_link.symlink_to(intermediate_target, target_is_directory=True)

                oversized = probe_root / "oversized.pem"
                oversized.write_bytes(b"x" * (file_setting["max_bytes"] + 1))
                oversized.chmod(0o600)

                writable = probe_root / "writable.pem"
                writable.write_bytes(b"public-ca")
                writable.chmod(0o666)

                cases = {
                    "good": good,
                    "final-symlink": final_link,
                    "intermediate-symlink": intermediate_link / "nested.pem",
                    "outside-root": outside,
                    "oversized": oversized,
                    "group-world-writable": writable,
                }
                probe = subprocess.run(
                    [
                        executable,
                        "--no-daemon",
                        "--offline",
                        "-p",
                        str(fixture),
                        ":normal:runSecurityProbe",
                    ],
                    text=True,
                    capture_output=True,
                    env={
                        **os.environ,
                        "LAMP_BROKER_CA_ROOT": str(probe_root),
                        "LAMP_BROKER_CA_CASES": ",".join(
                            f"{name}={path}" for name, path in cases.items()
                        ),
                    },
                    check=False,
                )
                self.assertEqual(0, probe.returncode, probe.stdout + probe.stderr)
                probe_output = probe.stdout + probe.stderr
                self.assertIn("CASE:good:READ_OK:9", probe_output)
                for name in (
                    "final-symlink",
                    "intermediate-symlink",
                    "outside-root",
                    "oversized",
                    "group-world-writable",
                ):
                    self.assertRegex(
                        probe_output,
                        rf"CASE:{re.escape(name)}:SECURE_FILE_REJECTED:",
                    )

    def test_file_backed_setting_checks_size_permissions_and_symlink(self) -> None:
        config = load_yaml(FIXTURES / "normal/settings.yaml")
        setting = file_sources(config)[0]
        self.assertEqual("public-ca", setting["material"])
        self.assertEqual(
            {"serviceAccount:lamp-worker", "fsGroup:2000"},
            set(setting["read_permission"]["subjects"]),
        )
        self.assertTrue(setting["kubernetes"]["volume"]["read_only"])
        self.assertEqual("0444", setting["kubernetes"]["volume"]["default_mode"])
        max_bytes = setting["max_bytes"]
        compiled_environment = (
            GRADLE_CONTRACT_FIXTURE
            / "normal/src/main/kotlin/ExampleEnvironment.kt"
        ).read_text(encoding="utf-8")
        max_bytes_match = re.search(r"MAX_CA_BYTES\s*=\s*([0-9_]+)L", compiled_environment)
        self.assertIsNotNone(max_bytes_match)
        self.assertEqual(max_bytes, int(max_bytes_match.group(1).replace("_", "")))
        self.assertIn(setting["root_env"], compiled_environment)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "allowed-root"
            root.mkdir()
            good = root / "ca.pem"
            good.write_bytes(b"public-ca")
            good.chmod(0o600)
            validate_file_backed_path(good, root, max_bytes)

            shared_readable = root / "secret-configmap-ca.pem"
            shared_readable.write_bytes(b"public-ca")
            shared_readable.chmod(0o444)
            validate_file_backed_path(shared_readable, root, max_bytes)

            symlink = root / "ca-link.pem"
            symlink.symlink_to(good)
            with self.assertRaises(ValueError):
                validate_file_backed_path(symlink, root, max_bytes)

            with tempfile.TemporaryDirectory(prefix="ca-target-", dir=str(root.parent)) as target_directory:
                nested_target = Path(target_directory)
                (nested_target / "ca.pem").write_bytes(b"public-ca")
                intermediate = root / "nested-link"
                intermediate.symlink_to(nested_target, target_is_directory=True)
                with self.assertRaises(ValueError):
                    validate_file_backed_path(intermediate / "ca.pem", root, max_bytes)

            outside = workspace / "outside.pem"
            outside.write_bytes(b"outside-root")
            outside.chmod(0o600)
            with self.assertRaises(ValueError):
                validate_file_backed_path(outside, root, max_bytes)

            oversized = root / "large.pem"
            oversized.write_bytes(b"x" * (max_bytes + 1))
            oversized.chmod(0o600)
            with self.assertRaises(ValueError):
                validate_file_backed_path(oversized, root, max_bytes)

            writable = root / "writable.pem"
            writable.write_bytes(b"public-ca")
            writable.chmod(0o666)
            with self.assertRaises(ValueError):
                validate_file_backed_path(writable, root, max_bytes)

    def test_kubernetes_manifest_mapping_is_executed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="standalone-k8s-fixture-") as directory:
            fixture = Path(directory) / "normal"
            shutil.copytree(FIXTURES / "normal", fixture)
            deployment = fixture / "k8s/deployment.yaml"
            deployment.write_text(
                deployment.read_text(encoding="utf-8").replace(
                    "serviceAccountName: lamp-worker",
                    "serviceAccountName: wrong-worker",
                ),
                encoding="utf-8",
            )
            self.assertEqual(["FILE_READ_PERMISSION_MAPPING"], fixture_errors(fixture))

    def test_direct_file_read_scanner_is_fail_closed_for_known_kotlin_apis(self) -> None:
        snippets = (
            "Files.newInputStream(path)",
            "Files.newByteChannel(path)",
            "FileInputStream(path)",
            "File(path).readBytes()",
            "Paths.get(path)",
            "FileChannel.open(path)",
            "Channels.newInputStream(channel)",
            "URL(url).openStream()",
        )
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                self.assertRegex(snippet, DIRECT_FILE_READ)


if __name__ == "__main__":
    unittest.main()
