"""gate_loosening_scan — 다섯 범주를 잡고, 기준 강화·무해한 변경은 조용히 넘긴다."""
from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import gate_loosening_scan as scanner  # noqa: E402


def file_diff(path: str, removed: list[str], added: list[str], start: int = 10, context: str = "    // ctx") -> str:
    """한 hunk짜리 git diff — 문맥 줄 1개(start) + 삭제 + 추가. 첫 추가 줄은 start+1."""
    old_n, new_n = 1 + len(removed), 1 + len(added)
    body = [f" {context}"] + [f"-{r}" for r in removed] + [f"+{a}" for a in added]
    return "\n".join([
        f"diff --git a/{path} b/{path}",
        "index 1111111..2222222 100644",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -{start},{old_n} +{start},{new_n} @@",
        *body,
    ]) + "\n"


def deleted_diff(path: str, lines: list[str]) -> str:
    return "\n".join([
        f"diff --git a/{path} b/{path}",
        "deleted file mode 100644",
        "index 1111111..0000000",
        f"--- a/{path}",
        "+++ /dev/null",
        f"@@ -1,{len(lines)} +0,0 @@",
        *[f"-{ln}" for ln in lines],
    ]) + "\n"


def hits(diff: str) -> list[scanner.Hit]:
    return scanner.scan(scanner.parse_diff(diff))


def categories(diff: str) -> list[str]:
    return [h.category for h in hits(diff)]


def run_main(argv: list[str], stdin_text: str | None = None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    old_stdin = sys.stdin
    if stdin_text is not None:
        sys.stdin = io.TextIOWrapper(io.BytesIO(stdin_text.encode()), encoding="utf-8")
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scanner.main(argv)
    finally:
        sys.stdin = old_stdin
    return code, out.getvalue(), err.getvalue()


class ThresholdTests(unittest.TestCase):
    def test_loosened_thresholds_are_reported(self) -> None:
        cases = {
            "jacoco 커버리지 하한": file_diff("build.gradle.kts",
                                         ['                minimum = "0.80".toBigDecimal()'],
                                         ['                minimum = "0.70".toBigDecimal()']),
            "detekt threshold 상향": file_diff("config/detekt/detekt.yml", ["    threshold: 60"], ["    threshold: 80"]),
            "editorconfig 심각도": file_diff(".editorconfig",
                                         ["dotnet_diagnostic.CA2000.severity = error"],
                                         ["dotnet_diagnostic.CA2000.severity = none"]),
            "경고=오류 해제": file_diff("src/Api/Api.csproj",
                                   ["    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>"],
                                   ["    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>"]),
            "eslint 레벨": file_diff(".eslintrc.json", ['    "no-console": "error",'], ['    "no-console": "warn",']),
            "max-warnings 상향": file_diff("package.json",
                                          ['    "lint": "eslint . --max-warnings 0",'],
                                          ['    "lint": "eslint . --max-warnings 25",']),
            "CI 실패 무시 추가": file_diff(".github/workflows/ci.yml", [], ["        continue-on-error: true"]),
        }
        for name, diff in cases.items():
            with self.subTest(name):
                self.assertEqual(categories(diff), ["threshold"])

    def test_note_shows_old_and_new_value(self) -> None:
        found = hits(file_diff("build.gradle.kts", ['minimum = "0.80".toBigDecimal()'], ['minimum = "0.70".toBigDecimal()'],
                               start=42))
        self.assertEqual((found[0].line, found[0].note), (43, "0.80 → 0.70"))

    def test_tightening_is_silent(self) -> None:
        for diff in (
            file_diff("build.gradle.kts", ['minimum = "0.70".toBigDecimal()'], ['minimum = "0.80".toBigDecimal()']),
            file_diff("config/detekt/detekt.yml", ["    threshold: 80"], ["    threshold: 60"]),
            file_diff(".eslintrc.json", ['"no-console": "warn",'], ['"no-console": "error",']),
            file_diff("src/Api/Api.csproj", ["<TreatWarningsAsErrors>false</TreatWarningsAsErrors>"],
                      ["<TreatWarningsAsErrors>true</TreatWarningsAsErrors>"]),
        ):
            with self.subTest(diff=diff.splitlines()[-1]):
                self.assertEqual(hits(diff), [])

    def test_kover_min_value_lowered(self) -> None:
        loosened = file_diff("build.gradle.kts", ["                minValue = 80"], ["                minValue = 70"])
        tightened = file_diff("build.gradle.kts", ["                minValue = 70"], ["                minValue = 80"])
        self.assertEqual([(h.category, h.note) for h in hits(loosened)], [("threshold", "80 → 70")])
        self.assertEqual(hits(tightened), [])

    def test_eslint_numeric_severity_lowered(self) -> None:
        for removed, added in (
            ('    "no-console": 2,', '    "no-console": 1,'),
            ("    'no-unused-vars': [2, { args: 'none' }],", "    'no-unused-vars': [0, { args: 'none' }],"),
        ):
            with self.subTest(added=added):
                found = hits(file_diff(".eslintrc.js", [removed], [added]))
                self.assertEqual([h.category for h in found], ["threshold"])
        # 규칙 옵션 숫자(max-len 120→100)는 심각도 자리가 아니다 — 강화도 조용히
        self.assertEqual(hits(file_diff("eslint.config.mjs", ["  'no-console': 1,"], ["  'no-console': 2,"])), [])
        self.assertEqual(hits(file_diff(".eslintrc.json", ['  "max-len": [2, 120],'], ['  "max-len": [2, 100],'])), [])

    def test_deleted_check_config_file_is_reported(self) -> None:
        for path in (".github/workflows/ci.yml", "config/detekt/detekt.yml", ".editorconfig", ".eslintrc.json",
                     "jest.config.ts", "gradle/jacoco.gradle", "gradle/kover.gradle.kts", ".ktlint"):
            with self.subTest(path=path):
                found = hits(deleted_diff(path, ["key: value"]))
                self.assertEqual([(h.category, h.line, h.note) for h in found], [("threshold", None, "검사 설정 파일 삭제")])

    def test_deleted_module_build_file_is_not_a_check_removal(self) -> None:
        for path in ("legacy-module/build.gradle.kts", "web/legacy/package.json"):
            with self.subTest(path=path):
                self.assertEqual(hits(deleted_diff(path, ["plugins {}"])), [])

    def test_runtime_config_is_not_a_gate(self) -> None:
        # application.yml 풀 크기·재시도 상한은 검사 기준이 아니다
        diff = file_diff("src/main/resources/application.yml", ["    maximum-pool-size: 10"], ["    maximum-pool-size: 30"])
        self.assertEqual(hits(diff), [])


class TestWeakeningTests(unittest.TestCase):
    def test_skip_markers_are_reported(self) -> None:
        cases = {
            "JUnit5": ("src/test/kotlin/OrderServiceTest.kt", '    @Disabled("flaky")'),
            "JUnit4": ("src/test/java/OrderTest.java", "    @Ignore"),
            "MSTest/NUnit": ("Order.Tests/OrderTests.cs", "    [Ignore]"),
            "xUnit": ("Order.Tests/OrderTests.cs", '    [Fact(Skip = "외부 API 불안정")]'),
            "jest skip": ("web/order.test.ts", "  it.skip('places order', () => {"),
            "jasmine xit": ("web/order.spec.ts", "  xit('places order', () => {"),
            "CI 테스트 제외": (".github/workflows/ci.yml", "      - run: ./gradlew build -x test"),
            "JUnit5 FQN": ("src/test/kotlin/OrderServiceTest.kt", "    @org.junit.jupiter.api.Disabled"),
            "JUnit4 FQN": ("src/test/java/OrderTest.java", "    @org.junit.Ignore"),
            "TestNG": ("src/test/java/OrderTest.java", '    @Test(groups = "slow", enabled = false)'),
            "NUnit Explicit": ("Order.Tests/OrderTests.cs", '    [Test, Explicit("수동 실행")]'),
            "NUnit Explicit 단독": ("Order.Tests/OrderTests.cs", "    [Explicit]"),
        }
        for name, (path, line) in cases.items():
            with self.subTest(name):
                self.assertEqual(categories(file_diff(path, [], [line])), ["test"])

    def test_deleted_test_file_is_reported(self) -> None:
        found = hits(deleted_diff("src/test/kotlin/RefundServiceTest.kt", ["class RefundServiceTest {", "}"]))
        self.assertEqual([(h.category, h.line, h.note) for h in found], [("test", None, "테스트 파일 삭제")])

    def test_deleted_production_file_is_not_test_weakening(self) -> None:
        self.assertEqual(hits(deleted_diff("src/main/kotlin/Unit.kt", ["object Unit"])), [])

    def test_assertion_removed_from_remaining_test(self) -> None:
        diff = file_diff("src/test/kotlin/RefundServiceTest.kt",
                         ["        assertThat(result.amount).isEqualTo(1000)",
                          "        verify(exactly = 1) { pointClient.refund(any()) }"],
                         ["        assertThat(result.amount).isEqualTo(1000)"], start=30)
        found = hits(diff)
        self.assertEqual([h.category for h in found], ["test"])
        self.assertIn("순감 1줄", found[0].note)

    def test_generic_assertion_removed(self) -> None:
        for removed in ("        Assert.Throws<ArgumentException>(() => sut.Refund(-1));",
                        "        Assert.ThrowsAsync<InvalidOperationException>(async () => await sut.Pay());",
                        "        assertThrows<IllegalStateException> { service.refund(-1) }"):
            with self.subTest(removed=removed):
                found = hits(file_diff("Order.Tests/RefundTests.cs" if "Assert." in removed
                                       else "src/test/kotlin/RefundServiceTest.kt", [removed], []))
                self.assertEqual([h.category for h in found], ["test"])
                self.assertIn("순감 1줄", found[0].note)

    def test_conditional_disable_and_enabled_test_are_silent(self) -> None:
        for line in ("    @DisabledOnOs(OS.WINDOWS)", "    @Test(enabled = true)", "    [IgnoreDataMember]"):
            with self.subTest(line=line):
                self.assertEqual(hits(file_diff("src/test/java/OrderTest.java", [], [line])), [])

    def test_reenabling_and_rewriting_asserts_are_silent(self) -> None:
        diff = file_diff("src/test/kotlin/RefundServiceTest.kt",
                         ['    @Disabled("flaky")', "        assertThat(result.amount).isEqualTo(1000)"],
                         ["        assertThat(result.amount).isEqualTo(1200)"])
        self.assertEqual(hits(diff), [])


class LineSplitTests(unittest.TestCase):
    """diff 줄 경계는 \\n뿐이다 — 내용 속 제어 문자에서 끊으면 hunk 줄 수가 어긋나 뒤 줄을 놓친다."""

    def test_control_chars_in_content_keep_hunk_counts(self) -> None:
        for name, ctx in (("form feed", "    val a = 1\x0c// page"), ("NEL", "    // a\x85b"),
                          ("line separator", "    // a\u2028b"), ("lone CR", "    // a\rb")):
            with self.subTest(name):
                found = hits(file_diff("src/test/kotlin/OrderTest.kt", [], ['    @Disabled("flaky")'], start=20, context=ctx))
                self.assertEqual([(h.category, h.line) for h in found], [("test", 21)])

    def test_crlf_diff_is_parsed(self) -> None:
        diff = file_diff("src/test/kotlin/OrderTest.kt", [], ['    @Disabled("flaky")'], start=5).replace("\n", "\r\n")
        found = hits(diff)
        self.assertEqual([(h.category, h.line, h.text) for h in found], [("test", 6, '    @Disabled("flaky")')])


class SilenceTests(unittest.TestCase):
    def test_checker_suppressions_are_reported(self) -> None:
        for path, line in (
            ("src/main/kotlin/Mapper.kt", '@Suppress("UNCHECKED_CAST")'),
            ("src/main/kotlin/Mapper.kt", "import foo.* // ktlint-disable no-wildcard-imports"),
            ("Legacy/OrderDao.cs", "#pragma warning disable CS0618"),
            ("web/order.ts", "// eslint-disable-next-line @typescript-eslint/no-explicit-any"),
            ("web/order.ts", "// @ts-ignore"),
            ("scripts/deploy.py", "subprocess.call(cmd, shell=True)  # nosemgrep"),
            ("src/main/resources/test.properties", "api.key=sample-key # gitleaks:allow"),
        ):
            with self.subTest(line=line):
                self.assertEqual(categories(file_diff(path, [], [line])), ["silence"])

    def test_docs_mentioning_checkers_are_ignored(self) -> None:
        self.assertEqual(hits(file_diff("README.md", [], ["`@ts-ignore`를 쓰지 않는다"])), [])


class UnfinishedTests(unittest.TestCase):
    def test_stubs_and_empty_catch_are_reported(self) -> None:
        for path, added in (
            ("src/main/kotlin/Refund.kt", ['    override fun refund(id: Long): Result = TODO("Not yet implemented")']),
            ("Legacy/Refund.cs", ["        throw new NotImplementedException();"]),
            ("src/main/kotlin/Refund.kt", ["        } catch (e: Exception) {}"]),
            ("src/main/kotlin/Refund.kt", ["        } catch (e: IOException) {", "            // ignore", "        }"]),
            ("scripts/sync.py", ["    except ValueError:", "        pass"]),
        ):
            with self.subTest(added=added[0]):
                self.assertEqual(categories(file_diff(path, [], added)), ["unfinished"])

    def test_catch_with_body_is_silent(self) -> None:
        diff = file_diff("src/main/kotlin/Refund.kt", [],
                         ["        } catch (e: IOException) {", "            log.warn(e) { \"환불 실패\" }", "            throw e",
                          "        }"])
        self.assertEqual(hits(diff), [])


class ExceptionFileTests(unittest.TestCase):
    def test_entries_added_to_exception_lists(self) -> None:
        for path, added in (
            ("config/detekt/detekt-baseline.xml", ["    <ID>LongMethod:RefundService.kt$RefundService$fun refund()</ID>"]),
            (".gitleaksignore", ["a1b2c3d:src/main/resources/application-dev.yml:generic-api-key:12"]),
            ("Order.Api/GlobalSuppressions.cs",
             ['[assembly: SuppressMessage("Design", "CA1031", Justification = "legacy")]']),
        ):
            with self.subTest(path=path):
                self.assertEqual(categories(file_diff(path, [], added)), ["exception"])

    def test_domain_source_named_baseline_is_not_an_exception_list(self) -> None:
        self.assertEqual(hits(file_diff("src/main/kotlin/BaselineCalculator.kt", [], ["    val base = 10"])), [])


class HarmlessDiffTests(unittest.TestCase):
    HARMLESS = (
        file_diff("src/main/kotlin/OrderService.kt",
                  ["        val total = items.sumOf { it.price }"],
                  ["        val total = items.sumOf { it.price * it.quantity }",
                   "        val first = stream.skip(1).findFirst()",
                   "        image.fit(width, height)"])
        + file_diff("src/main/kotlin/OrderDto.kt", [], ["    @JsonIgnore", "    val internalCode: String,"])
        + file_diff("build.gradle.kts", ['version = "1.2.3"'], ['version = "1.2.4"'])
        + file_diff("docs/guide.md", [], ["테스트는 it.skip 대신 고친다. TODO(정리)"])
    )

    def test_scan_finds_nothing(self) -> None:
        self.assertEqual(hits(self.HARMLESS), [])

    def test_render_reports_zero_in_one_line(self) -> None:
        code, out, _ = run_main([], stdin_text=self.HARMLESS)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().count("\n"), 0)
        self.assertIn("0건", out)


class CliTests(unittest.TestCase):
    def test_markdown_groups_by_category_with_location(self) -> None:
        diff = (file_diff("build.gradle.kts", ['minimum = "0.80".toBigDecimal()'], ['minimum = "0.70".toBigDecimal()'], start=42)
                + deleted_diff("src/test/kotlin/RefundServiceTest.kt", ["class RefundServiceTest"]))
        code, out, _ = run_main([], stdin_text=diff)
        self.assertEqual(code, 0)
        self.assertIn("**완화 신호 2건**", out)
        self.assertIn("- 임계값 하향 1", out)
        self.assertIn('  - `build.gradle.kts:43` `minimum = "0.70".toBigDecimal()` — 0.80 → 0.70', out)
        self.assertIn("  - `src/test/kotlin/RefundServiceTest.kt` — 테스트 파일 삭제", out)

    def test_empty_input_is_an_input_error(self) -> None:
        code, out, err = run_main([], stdin_text="")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("비어 있다", err)

    def test_diff_file_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr.diff"
            path.write_text(file_diff("web/order.ts", [], ["// @ts-ignore"]))
            code, out, _ = run_main(["--diff", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("체커 침묵 1", out)

    def test_git_revision_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args: str) -> None:
                subprocess.run(["git", "-C", tmp, *args], check=True, capture_output=True)

            git("init", "-q")
            git("config", "user.email", "t@example.com")
            git("config", "user.name", "t")
            test_file = Path(tmp) / "src/test/kotlin/OrderTest.kt"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("class OrderTest {\n    @Test\n    fun places() {}\n}\n")
            git("add", ".")
            git("commit", "-qm", "base")
            test_file.write_text('class OrderTest {\n    @Disabled("flaky")\n    @Test\n    fun places() {}\n}\n')
            git("commit", "-qam", "head")
            code, out, _ = run_main(["HEAD~1..HEAD", "-C", tmp])
        self.assertEqual(code, 0)
        self.assertIn('`src/test/kotlin/OrderTest.kt:2` `@Disabled("flaky")`', out)

    def test_bad_revision_range_is_an_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            code, _, err = run_main(["nope..HEAD", "-C", tmp])
        self.assertEqual(code, 2)
        self.assertIn("git diff 실패", err)


if __name__ == "__main__":
    unittest.main()
