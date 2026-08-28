from __future__ import annotations

import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "upload-fortify-fprs.py"
spec = importlib.util.spec_from_file_location("upload_fortify_fprs", MODULE_PATH)
fortify = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fortify)


class UploadFortifyFprsTests(unittest.TestCase):
    def test_validate_base_url_requires_explicit_http_exception(self) -> None:
        with self.assertRaisesRegex(ValueError, "평문 전송"):
            fortify.validate_base_url("http://ssc.example/ssc", False)

        self.assertEqual(
            fortify.validate_base_url("http://ssc.example/ssc/", True),
            "http://ssc.example/ssc",
        )

    def test_validate_base_url_rejects_embedded_credentials(self) -> None:
        embedded_credentials = (
            "https://" + ":".join(("user", "credential-placeholder"))
            + "@ssc.example/ssc"
        )
        with self.assertRaisesRegex(ValueError, "사용자명이나 비밀번호"):
            fortify.validate_base_url(embedded_credentials, False)

    def test_validate_base_url_rejects_invalid_scheme_or_host(self) -> None:
        for value in ("ftp://ssc.example/ssc", "https:///ssc"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "형식"):
                fortify.validate_base_url(value, False)

    def test_month_argument_derives_directory_and_version(self) -> None:
        argv = [
            str(MODULE_PATH),
            "--month",
            "202609",
            "--base-url",
            "https://ssc.example/ssc",
        ]
        with patch.object(fortify.sys, "argv", argv):
            options = fortify.args()

        self.assertEqual(options.directory, Path("~/Documents/Work/fortify/202609"))
        self.assertEqual(options.version, "26.09")

    def test_month_argument_rejects_invalid_month(self) -> None:
        argv = [
            str(MODULE_PATH),
            "--month",
            "202613",
            "--base-url",
            "https://ssc.example/ssc",
        ]
        with (
            patch.object(fortify.sys, "argv", argv),
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            fortify.args()

    def test_month_argument_uses_configured_default_url(self) -> None:
        argv = [str(MODULE_PATH), "--month", "202609"]
        with (
            patch.object(fortify.sys, "argv", argv),
            patch.object(fortify, "DEFAULT_BASE_URL", "https://ssc.example/ssc"),
        ):
            options = fortify.args()

        self.assertEqual(options.base_url, "https://ssc.example/ssc")

    def test_month_argument_rejects_explicit_directory_conflict(self) -> None:
        argv = [
            str(MODULE_PATH),
            "--month",
            "202609",
            "--directory",
            "/tmp/fprs",
            "--base-url",
            "https://ssc.example/ssc",
        ]
        with (
            patch.object(fortify.sys, "argv", argv),
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            fortify.args()

    def test_application_matching_covers_alias_suffix_and_typo(self) -> None:
        applications = ["B2B Batch", "Blog", "Bazaar-Admin-Front", "Naru"]

        self.assertEqual(
            fortify.match_application("partner-integration-batch", applications),
            "B2B Batch",
        )
        self.assertEqual(fortify.match_application("blog-web", applications), "Blog")
        self.assertEqual(
            fortify.match_application("Bazzar-Admin-Front", applications),
            "Bazaar-Admin-Front",
        )
        self.assertEqual(fortify.match_application("naru-server", applications), "Naru")

    def test_explicit_alias_requires_application_to_exist(self) -> None:
        with self.assertRaisesRegex(fortify.SscError, "명시 매핑 대상"):
            fortify.match_application("partner-integration-batch", ["Blog"])

    def test_ambiguous_application_match_fails_closed(self) -> None:
        with self.assertRaisesRegex(fortify.SscError, "매핑 불가"):
            fortify.match_application("unknown", ["Alpha", "Beta", "Gamma"])

    def test_build_mapping_rejects_two_files_for_one_application(self) -> None:
        versions = [{"project": {"name": "Blog"}}]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "blog.fpr").touch()
            (directory / "blog-web.fpr").touch()
            with self.assertRaisesRegex(fortify.SscError, "여러 FPR"):
                fortify.build_mapping(directory, versions)

    def test_build_mapping_rejects_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(
            fortify.SscError, "FPR 파일이 없습니다"
        ):
            fortify.build_mapping(Path(tmp), [{"project": {"name": "Blog"}}])

    def test_source_version_uses_latest_creation_date(self) -> None:
        versions = [
            {
                "id": 1,
                "name": "26.06",
                "creationDate": "2026-06-01T00:00:00Z",
                "project": {"name": "Blog"},
            },
            {
                "id": 2,
                "name": "26.07",
                "creationDate": "2026-07-01T00:00:00Z",
                "project": {"name": "Blog"},
            },
        ]

        self.assertEqual(fortify.source_version_for("Blog", versions, "26.08")["id"], 2)

    def test_source_version_requires_previous_version(self) -> None:
        with self.assertRaisesRegex(fortify.SscError, "복사 기준 버전"):
            fortify.source_version_for("Blog", [], "26.08")

    def test_parse_date_handles_missing_and_utc_values(self) -> None:
        self.assertEqual(fortify.parse_date(None), fortify.datetime.min)
        self.assertEqual(fortify.parse_date("2026-08-01T12:30:00Z").year, 2026)

    def test_existing_target_skips_only_committed_version(self) -> None:
        committed = {
            "id": 7,
            "name": "26.08",
            "committed": True,
            "project": {"name": "Blog"},
        }
        self.assertEqual(
            fortify.existing_target("Blog", [committed], "26.08"), committed
        )

        incomplete = {**committed, "id": 8, "committed": False}
        with self.assertRaisesRegex(fortify.SscError, "미완성 대상 버전"):
            fortify.existing_target("Blog", [incomplete], "26.08")

    def test_existing_target_rejects_duplicate_version_names(self) -> None:
        versions = [
            {
                "id": version_id,
                "name": "26.08",
                "committed": True,
                "project": {"name": "Blog"},
            }
            for version_id in (1, 2)
        ]
        with self.assertRaisesRegex(fortify.SscError, "여러 개"):
            fortify.existing_target("Blog", versions, "26.08")

    def test_existing_target_returns_none_when_version_is_missing(self) -> None:
        self.assertIsNone(fortify.existing_target("Blog", [], "26.08"))

    def test_writable_attributes_keeps_only_api_write_shape(self) -> None:
        raw = [
            {
                "attributeDefinitionId": 3,
                "value": "High",
                "values": [{"guid": "one", "name": "ignored"}],
                "extra": "ignored",
            }
        ]
        self.assertEqual(
            fortify.writable_attributes(raw),
            [
                {
                    "attributeDefinitionId": 3,
                    "value": "High",
                    "values": [{"guid": "one"}],
                }
            ],
        )

    def test_poll_artifact_treats_require_auth_as_terminal(self) -> None:
        class Client:
            def get(self, path: str) -> dict:
                self.path = path
                return {"data": {"status": "REQUIRE_AUTH"}}

        client = Client()
        with patch.object(fortify.time, "sleep"), redirect_stdout(io.StringIO()):
            status = fortify.poll_artifact(client, 42, 1, 0)

        self.assertEqual(status, "REQUIRE_AUTH")
        self.assertEqual(client.path, "/artifacts/42")

    def test_poll_artifact_returns_failure_status(self) -> None:
        class Client:
            def get(self, path: str) -> dict:
                return {"data": {"status": "ERROR_PROCESSING"}}

        with patch.object(fortify.time, "sleep"), redirect_stdout(io.StringIO()):
            status = fortify.poll_artifact(Client(), 42, 1, 0)

        self.assertEqual(status, "ERROR_PROCESSING")

    def test_poll_artifact_reports_timeout_before_first_poll(self) -> None:
        class Client:
            def get(self, path: str) -> dict:
                raise AssertionError("deadline 경과 후에는 조회하지 않아야 함")

        with patch.object(fortify.time, "monotonic", side_effect=(0.0, 2.0)):
            status = fortify.poll_artifact(Client(), 42, 1, 0)

        self.assertEqual(status, "TIMEOUT(UNKNOWN)")

    def test_upload_builds_multipart_request_with_upload_token(self) -> None:
        client = fortify.SscClient("https://ssc.example/ssc", None, "upload-token")
        with tempfile.TemporaryDirectory() as tmp:
            fpr = Path(tmp) / "blog.fpr"
            fpr.write_bytes(b"fpr-content")
            with patch.object(
                client,
                "_request",
                return_value={"data": {"id": 99}},
            ) as request:
                result = client.upload(7, fpr)

        self.assertEqual(result["data"]["id"], 99)
        method, path = request.call_args.args
        kwargs = request.call_args.kwargs
        self.assertEqual((method, path), ("POST", "/projectVersions/7/artifacts"))
        self.assertEqual(kwargs["token"], "upload-token")
        self.assertEqual(kwargs["expected"], (201,))
        self.assertIn(b'name="file"; filename="blog.fpr"', kwargs["body"])
        self.assertIn(b"fpr-content", kwargs["body"])

    def test_credential_rejects_empty_secret(self) -> None:
        empty = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n", stderr="")
        with patch.object(fortify.subprocess, "run", return_value=empty), self.assertRaisesRegex(
            fortify.SscError, "빈 자격증명"
        ):
            fortify.credential("fortify-test-token")

    def test_credential_reports_helper_failure(self) -> None:
        failed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Keychain item missing\n"
        )
        with patch.object(fortify.subprocess, "run", return_value=failed), self.assertRaisesRegex(
            fortify.SscError, "Keychain item missing"
        ):
            fortify.credential("fortify-test-token")

    def test_client_requires_admin_token_for_admin_calls(self) -> None:
        client = fortify.SscClient("https://ssc.example/ssc", None, "upload-token")
        with self.assertRaisesRegex(
            fortify.SscError, "fortify-ssc-unified-login-token"
        ):
            client.require_admin_token()

    def test_create_version_copies_configuration_and_commits(self) -> None:
        attributes = [
            {
                "attributeDefinitionId": 3,
                "value": "High",
                "values": [{"guid": "one"}],
            }
        ]

        class Client:
            def __init__(self) -> None:
                self.posts = []
                self.puts = []

            def get(self, path: str) -> dict:
                responses = {
                    "/projectVersions/4": {
                        "data": {
                            "description": "source",
                            "issueTemplateId": "template",
                            "masterAttrGuid": "master",
                        }
                    },
                    "/projectVersions/4/attributes": {"data": attributes},
                    "/projectVersions/9": {
                        "data": {"id": 9, "name": "26.08", "committed": True}
                    },
                    "/projectVersions/9/attributes": {"data": attributes},
                }
                return responses[path]

            def post(self, path: str, payload: object, **kwargs: object) -> dict:
                self.posts.append((path, payload, kwargs))
                if path == "/projects/2/versions":
                    return {"data": {"id": 9}}
                return {"data": {}}

            def put(self, path: str, payload: object) -> dict:
                self.puts.append((path, payload))
                return {"data": {}}

        source = {"id": 4, "project": {"id": 2}}
        client = Client()
        with redirect_stdout(io.StringIO()):
            version_id = fortify.create_version(client, "Blog", "26.08", source)

        self.assertEqual(version_id, 9)
        self.assertEqual(client.posts[0][0], "/projects/2/versions")
        self.assertEqual(client.posts[0][2]["expected"], (201,))
        self.assertEqual(client.posts[1][0], "/projectVersions/action/copyFromPartial")
        self.assertIn(("/projectVersions/9?hideProgress=true", {"committed": True}), client.puts)


if __name__ == "__main__":
    unittest.main()
