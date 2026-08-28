#!/usr/bin/env python3
"""Create missing SSC application versions and upload a directory of FPR files.

Defaults are deliberately conservative:

- dry-run unless ``--apply`` is provided;
- skip an application entirely when the target version already exists;
- use a short-lived UnifiedLoginToken only for version administration;
- use an AnalysisUploadToken for FPR upload;
- never print either token.
"""

from __future__ import annotations

import argparse
import difflib
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


REPO = Path(__file__).resolve().parents[1]
CRED = REPO / "tools" / "cred.py"
DEFAULT_BASE_URL = os.environ.get("FORTIFY_SSC_URL")
DEFAULT_FPR_ROOT = Path("~/Documents/Work/fortify")
UPLOAD_CREDENTIAL = "fortify-ssc-analysis-upload-token"
ADMIN_CREDENTIAL = "fortify-ssc-unified-login-token"
TERMINAL_ARTIFACT_STATUSES = {
    "PROCESS_COMPLETE",
    "REQUIRE_AUTH",
    "ERROR_PROCESSING",
    "ERROR_ANALYZING",
    "ERROR_DISPATCH",
    "AUDIT_FAILED",
    "AUTH_DENIED",
}
FAILURE_ARTIFACT_STATUSES = TERMINAL_ARTIFACT_STATUSES - {
    "PROCESS_COMPLETE",
    "REQUIRE_AUTH",
}
EXPLICIT_ALIASES = {
    "partnerintegrationbatch": "B2B Batch",
}


class SscError(RuntimeError):
    pass


def credential(name: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CRED), "get", name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SscError(result.stderr.strip() or f"자격증명 조회 실패: {name}")
    value = result.stdout.rstrip("\n")
    if not value:
        raise SscError(f"빈 자격증명: {name}")
    return value


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalized_without_role_suffix(value: str) -> str:
    result = normalized(value)
    for suffix in ("server", "web"):
        if result.endswith(suffix) and len(result) > len(suffix):
            return result[: -len(suffix)]
    return result


def validate_base_url(value: str, allow_insecure_http: bool) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("SSC URL은 http(s)://host/path 형식이어야 합니다")
    if parsed.username or parsed.password:
        raise ValueError("SSC URL에 사용자명이나 비밀번호를 포함할 수 없습니다")
    if parsed.scheme == "http" and not allow_insecure_http:
        raise ValueError(
            "HTTP는 Fortify 토큰을 평문 전송합니다. HTTPS를 사용하거나, "
            "격리된 신뢰 경로임을 확인한 경우에만 --allow-insecure-http를 지정하세요"
        )
    return value.rstrip("/")


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


class SscClient:
    def __init__(self, base_url: str, admin_token: str | None, upload_token: str):
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self.upload_token = upload_token

    def require_admin_token(self) -> str:
        if not self.admin_token:
            raise SscError(
                f"버전 생성/처리 조회에는 Keychain의 {ADMIN_CREDENTIAL}이 필요합니다"
            )
        return self.admin_token

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str,
        payload: object | None = None,
        body: bytes | None = None,
        content_type: str | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> dict:
        if payload is not None and body is not None:
            raise ValueError("payload와 body는 동시에 지정할 수 없습니다")
        headers = {
            "Accept": "application/json",
            "Authorization": f"FortifyToken {token}",
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json;charset=UTF-8"
        elif content_type:
            headers["Content-Type"] = content_type
        request = Request(
            f"{self.base_url}/api/v1{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=120) as response:
                status = response.status
                raw = response.read()
        except HTTPError as error:
            raw = error.read()
            detail = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(detail)
                detail = parsed.get("message") or detail
            except json.JSONDecodeError:
                pass
            raise SscError(f"{method} {path}: HTTP {error.code}: {detail}") from None
        except URLError as error:
            raise SscError(f"{method} {path}: {error}") from None
        if status not in expected:
            raise SscError(f"{method} {path}: 예상하지 못한 HTTP {status}")
        if not raw:
            return {"responseCode": status}
        result = json.loads(raw.decode("utf-8"))
        response_code = result.get("responseCode")
        if response_code is not None and response_code >= 400:
            raise SscError(f"{method} {path}: {response_code}: {result.get('message')}")
        return result

    def get(self, path: str, *, upload_token: bool = False) -> dict:
        token = self.upload_token if upload_token else self.require_admin_token()
        return self._request("GET", path, token=token)

    def post(self, path: str, payload: object, *, expected=(200,)) -> dict:
        return self._request(
            "POST",
            path,
            token=self.require_admin_token(),
            payload=payload,
            expected=expected,
        )

    def put(self, path: str, payload: object) -> dict:
        return self._request(
            "PUT", path, token=self.require_admin_token(), payload=payload
        )

    def upload(self, version_id: int, fpr: Path) -> dict:
        boundary = f"----team2-fortify-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(fpr.name)[0] or "application/octet-stream"
        prefix = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{fpr.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
        body = prefix + fpr.read_bytes() + suffix
        return self._request(
            "POST",
            f"/projectVersions/{version_id}/artifacts",
            token=self.upload_token,
            body=body,
            content_type=f"multipart/form-data; boundary={boundary}",
            expected=(201,),
        )


def application_names(versions: list[dict]) -> list[str]:
    return sorted({item["project"]["name"] for item in versions})


def match_application(stem: str, applications: list[str]) -> str:
    stem_normalized = normalized(stem)
    alias = EXPLICIT_ALIASES.get(stem_normalized)
    if alias:
        if alias not in applications:
            raise SscError(f"명시 매핑 대상이 SSC에 없습니다: {stem} -> {alias}")
        return alias

    exact = [app for app in applications if normalized(app) == stem_normalized]
    if len(exact) == 1:
        return exact[0]

    stem_without_suffix = normalized_without_role_suffix(stem)
    suffix_matches = [
        app
        for app in applications
        if normalized_without_role_suffix(app) == stem_without_suffix
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    ranked = sorted(
        (
            difflib.SequenceMatcher(None, stem_normalized, normalized(app)).ratio(),
            app,
        )
        for app in applications
    )
    best_score, best_app = ranked[-1]
    second_score = ranked[-2][0] if len(ranked) > 1 else 0.0
    if best_score >= 0.90 and best_score - second_score >= 0.10:
        return best_app
    candidates = ", ".join(f"{app}({score:.2f})" for score, app in ranked[-3:])
    raise SscError(f"애플리케이션 매핑 불가: {stem}; 후보: {candidates}")


def build_mapping(directory: Path, versions: list[dict]) -> list[tuple[Path, str]]:
    files = sorted(directory.glob("*.fpr"), key=lambda path: path.name.lower())
    if not files:
        raise SscError(f"FPR 파일이 없습니다: {directory}")
    applications = application_names(versions)
    mapping = [(fpr, match_application(fpr.stem, applications)) for fpr in files]
    mapped_apps = [app for _, app in mapping]
    duplicates = sorted({app for app in mapped_apps if mapped_apps.count(app) > 1})
    if duplicates:
        raise SscError(f"여러 FPR이 같은 애플리케이션에 매핑됨: {', '.join(duplicates)}")
    return mapping


def source_version_for(application: str, versions: list[dict], target: str) -> dict:
    candidates = [
        item
        for item in versions
        if item["project"]["name"] == application and item["name"] != target
    ]
    if not candidates:
        raise SscError(f"복사 기준 버전이 없습니다: {application}")
    return max(candidates, key=lambda item: parse_date(item.get("creationDate")))


def existing_target(application: str, versions: list[dict], target: str) -> dict | None:
    matches = [
        item
        for item in versions
        if item["project"]["name"] == application and item["name"] == target
    ]
    if len(matches) > 1:
        raise SscError(f"동일한 대상 버전이 여러 개입니다: {application}/{target}")
    if not matches:
        return None
    existing = matches[0]
    if not existing.get("committed"):
        raise SscError(
            f"미완성 대상 버전이 존재합니다: {application}/{target} "
            f"id={existing.get('id')}. SSC에서 상태를 확인한 뒤 수동 복구하세요"
        )
    return existing


def writable_attributes(raw: list[dict]) -> list[dict]:
    return [
        {
            "attributeDefinitionId": item["attributeDefinitionId"],
            "value": item.get("value"),
            "values": [{"guid": option["guid"]} for option in item.get("values", [])],
        }
        for item in raw
    ]


def create_version(client: SscClient, application: str, target: str, source: dict) -> int:
    source_id = source["id"]
    project_id = source["project"]["id"]
    details = client.get(f"/projectVersions/{source_id}")["data"]
    attributes = client.get(f"/projectVersions/{source_id}/attributes").get("data", [])
    issue_template = details.get("issueTemplateId")
    payload = {
        "name": target,
        "description": details.get("description") or "",
        "active": True,
        "committed": False,
        "issueTemplateId": issue_template,
        "masterAttrGuid": details.get("masterAttrGuid"),
    }
    created = client.post(
        f"/projects/{project_id}/versions", payload, expected=(201,)
    )["data"]
    version_id = created["id"]
    print(f"  생성됨: id={version_id}; 속성 복사 중", flush=True)
    client.put(
        f"/projectVersions/{version_id}/attributes",
        writable_attributes(attributes),
    )
    client.post(
        "/projectVersions/action/copyFromPartial",
        {
            "projectVersionId": version_id,
            "previousProjectVersionId": source_id,
            "copyAnalysisProcessingRules": True,
            "copyBugTrackerConfiguration": True,
            "copyCustomTags": True,
        },
    )
    client.put(f"/projectVersions/{version_id}?hideProgress=true", {"committed": True})
    verified = client.get(f"/projectVersions/{version_id}")["data"]
    if not verified.get("committed") or verified.get("name") != target:
        raise SscError(f"생성 검증 실패: {application}/{target} id={version_id}")
    copied_attributes = client.get(
        f"/projectVersions/{version_id}/attributes"
    ).get("data", [])
    if writable_attributes(copied_attributes) != writable_attributes(attributes):
        raise SscError(f"속성 복사 검증 실패: {application}/{target} id={version_id}")
    return version_id


def poll_artifact(
    client: SscClient, artifact_id: int, timeout_seconds: int, interval_seconds: int
) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_status = "UNKNOWN"
    while time.monotonic() < deadline:
        artifact = client.get(f"/artifacts/{artifact_id}")["data"]
        status = artifact.get("status") or "UNKNOWN"
        if status != last_status:
            print(f"    처리 상태: {status}", flush=True)
            last_status = status
        if status in TERMINAL_ARTIFACT_STATUSES:
            return status
        time.sleep(interval_seconds)
    return f"TIMEOUT({last_status})"


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--month",
        help="월간 실행값(YYYYMM). 디렉터리는 <root>/YYYYMM, 버전은 YY.MM으로 계산",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_FPR_ROOT,
        help="--month 사용 시 FPR 월별 디렉터리의 상위 경로",
    )
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--version")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="SSC base URL. 기본값은 FORTIFY_SSC_URL 환경변수",
    )
    parser.add_argument(
        "--allow-insecure-http",
        action="store_true",
        help="격리된 신뢰 경로에서만 HTTP 토큰 전송을 명시적으로 허용",
    )
    parser.add_argument("--apply", action="store_true", help="실제 생성·업로드 수행")
    parser.add_argument("--poll-timeout", type=int, default=900)
    parser.add_argument("--poll-interval", type=int, default=5)
    options = parser.parse_args()
    if options.month:
        if not re.fullmatch(r"\d{6}", options.month):
            parser.error("--month는 YYYYMM 형식이어야 합니다")
        if options.directory or options.version:
            parser.error("--month는 --directory/--version과 함께 사용할 수 없습니다")
        year = options.month[:4]
        month = options.month[4:]
        if not 1 <= int(month) <= 12:
            parser.error("--month의 월은 01~12여야 합니다")
        options.directory = options.root / options.month
        options.version = f"{year[2:]}.{month}"
    elif options.directory is None or options.version is None:
        parser.error("--month 또는 --directory와 --version을 지정해야 합니다")
    if not options.base_url:
        parser.error("--base-url 또는 FORTIFY_SSC_URL 환경변수를 지정해야 합니다")
    try:
        options.base_url = validate_base_url(
            options.base_url, options.allow_insecure_http
        )
    except ValueError as error:
        parser.error(str(error))
    return options


def main() -> int:
    options = args()
    directory = options.directory.expanduser().resolve()
    if not directory.is_dir():
        raise SscError(f"디렉터리가 없습니다: {directory}")

    upload_token = credential(UPLOAD_CREDENTIAL)
    client = SscClient(options.base_url, None, upload_token)
    versions = client.get(
        "/projectVersions?" + urlencode(
            {"limit": -1, "includeInactive": "true", "orderby": "project.name,name"}
        ),
        upload_token=True,
    ).get("data", [])
    mapping = build_mapping(directory, versions)

    print(f"SSC: {options.base_url}; target version: {options.version}")
    print(f"FPR: {len(mapping)}개")
    plan: list[tuple[Path, str, dict | None, dict | None]] = []
    for fpr, application in mapping:
        existing = existing_target(application, versions, options.version)
        source = None if existing else source_version_for(application, versions, options.version)
        if existing:
            print(f"  SKIP   {fpr.name} -> {application}/{options.version} (id={existing['id']})")
        else:
            print(
                f"  CREATE {fpr.name} -> {application}/{options.version} "
                f"(source={source['name']}, id={source['id']})"
            )
        plan.append((fpr, application, existing, source))

    if not options.apply:
        print("DRY-RUN: 변경 없음. 실제 수행은 --apply")
        return 0

    if any(existing is None for _, _, existing, _ in plan):
        client.admin_token = credential(ADMIN_CREDENTIAL)

    results: list[dict] = []
    for fpr, application, existing, source in plan:
        if existing:
            results.append(
                {"application": application, "versionId": existing["id"], "result": "SKIPPED"}
            )
            continue
        assert source is not None
        print(f"\n[{application}] {options.version} 생성", flush=True)
        version_id = create_version(client, application, options.version, source)
        print(f"  업로드: {fpr.name} ({fpr.stat().st_size} bytes)", flush=True)
        uploaded = client.upload(version_id, fpr)["data"]
        artifact_id = uploaded["id"]
        print(f"  업로드 접수: artifact id={artifact_id}", flush=True)
        status = poll_artifact(
            client,
            artifact_id,
            options.poll_timeout,
            options.poll_interval,
        )
        results.append(
            {
                "application": application,
                "versionId": version_id,
                "artifactId": artifact_id,
                "status": status,
                "result": (
                    "FAILED"
                    if status in FAILURE_ARTIFACT_STATUSES
                    else "PENDING_APPROVAL"
                    if status == "REQUIRE_AUTH"
                    else status
                ),
            }
        )
        if status in FAILURE_ARTIFACT_STATUSES or status.startswith("TIMEOUT"):
            print(json.dumps(results, ensure_ascii=False, indent=2))
            raise SscError(f"업로드 처리 실패/지연: {application}/{options.version}: {status}")

    print("\n완료 요약")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SscError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
