#!/usr/bin/env python3
"""YouTrack DEV2 티켓 → 로컬 Paperclip 이슈 등록·분류 — `/ad:paperclip-dispatch` 스킬의 결정적 층.

Paperclip 파일럿(templates/paperclip/README.md)은 쇼핑 데이터 추출 요청의 SQL 작성과 티켓 분석(work-prep)을 에이전트에 맡긴다.
업무 원천은 YouTrack이고 방향은 YouTrack → Paperclip 하나다. 이 도구는 YouTrack을 읽기만 하고 Paperclip에만 쓴다.
판정·등록은 여기 두고 스킬은 실행·보고만 한다 — cron·routine이 `--inbox`·`--query`로 같은 도구를 부르게 하기 위해서다.

흐름(2026-10-22 사용자 결정): 내 티켓 → Inbox(프로젝트 없음) → 사람이 분석 프로젝트(설정 analysisProject)로 분류
  → 분석 에이전트 → 사람 승인(done) → 그 뒤의 일(데이터 추출·개발)은 분석 이슈의 하위 이슈(`--from`).
  프로젝트만 바꾸면 그 단계의 승인 기록이 초기화되고 일감을 하나로만 이어 가서, 단계마다 이슈를 따로 둔다.
자동 분석(설정 autoAnalyze {agent, wakeMax}, 없거나 enabled:false면 꺼짐): 등록(ID·--inbox·--query)으로 새로 만드는
  이슈는 analysisProject 정책 + 그 에이전트 담당 + todo로 만든다 — 서버가 생성 직후 할당 깨움을 보낸다
  (server issue-assignment-wakeup.ts). 요청자(reporter login)가 토큰 사용자이거나 비어 있으면 자동 분석하지 않고
  Board backlog로 만든다 — query가 바뀌어도 내가 만든 티켓은 자동 실행되지 않게 한다. 기존 이슈(skipped)는 그대로 둔다.
깨움 보정(--inbox, 자동 분석 켜짐): analysisProject에서 그 에이전트 담당 todo 이슈 중 진행·대기 실행
  (GET /api/issues/{id}/runs의 queued·scheduled_retry·running)이 없는 것에 POST /api/agents/{id}/wakeup을 보낸다.
  서버 할당 깨움이 빠진 일이 있었다(ALA-2 리뷰 단계). 한 번에 wakeMax건(기본 3) — 이번 실행에서 깨우는 수의 상한이고
  동시 실행 상한이 아니다. 에이전트가 paused·terminated·pending_approval이면 깨우지 않는다(사람이 멈춘 상태 존중).
  방금 만든 이슈와, 그 에이전트의 최근 실행이 failed·timed_out·cancelled·interrupted인 이슈도 건너뛴다 —
  같은 실패를 주기마다 되풀이하지 않게 사람이 확인한다.
담당자 검사(항상): YouTrack 담당자(Assignee login)가 토큰 사용자(/api/users/me login)가 아니거나 비어 있으면
  그 티켓은 error(담당자 불일치)로 거부하고 Paperclip에 아무것도 쓰지 않는다 — 파일럿은 내 티켓만 처리한다.
등록(기본):
  - 제목 `DEV2-#### {summary}`, 본문은 YouTrack 링크·summary·등록 경위 한 줄. 요청 원문(description)은 옮기지 않는다
    — 개인정보가 있을 수 있고, 작성 에이전트가 YouTrack REST로 직접 읽는다
  - 상태 backlog, 담당 Board 사용자(설정 approverUserId) — 사람 Inbox "Mine"에 모이고 에이전트는 깨어나지 않는다.
    에이전트 할당(실행 시작)은 사람이 화면에서 한다
  - 프로젝트 배분: 설정 rules를 순서대로 보고 첫 일치 규칙만 쓴다. 일치하면 projectId + 설정 projects의 그 프로젝트 정책
    (isolatedWorkspace면 이슈별 격리 workspace, stages 순서의 executionPolicy), 불일치하면 프로젝트·정책 없이 만든다
    규칙 일치 = summary에 summaryAny 중 하나가 들어 있음(대소문자 무시) 또는 태그가 tagsAny 중 하나.
    pilot.json의 rules는 비어 있다 — 모든 티켓이 Inbox로 들어가 분석부터 거친다. rules의 project는
    analysisProject만 받는다(다른 값은 설정 오류)
  - 라벨 `요청자:{fullName}`·`태그:{tag}`(48자 절단, 회사에 없으면 만든다). 요청자 login은 넣지 않는다
  - work product(artifact, provider youtrack)로 원본 티켓 링크 — 이슈 옆 Artifacts 탭에서 원본으로 간다
프로젝트 정책(설정 projects, 이름 → {isolatedWorkspace, stages}): stages는 `review:{에이전트 이름}`·`approval:{Board userId}`
  문자열 목록이고 적은 순서가 단계 순서다. 규칙의 project와 `--project`는 이 맵에 있어야 한다 — 없으면 그 티켓은 error.
분류(`--project 이름 DEV2-####`): 분석 먼저 — `--from` 없는 `--project`는 analysisProject만 받는다. 다른 프로젝트
  이름이면 YouTrack·Paperclip을 보지 않고 error. 기존 이슈면 projectId·격리 workspace·executionPolicy 중 정책과 다른 것만 PATCH한다
  (같으면 unchanged). 격리 없는 프로젝트로 옮기면 격리 설정을 지운다(null). 화면에서 프로젝트만 바꾸면 정책과 격리가
  붙지 않아서다. 이미 done이거나 다른 프로젝트 소속이면 옮기지 않고 error로 `--from`을 안내한다. 진행 중 실행·검토
  단계가 있으면 건드리지 않고 error — 정책을 바꾸면 서버가 검토 주기를 초기화한다(server issue-execution-policy.ts).
  기존 이슈가 없으면 그 프로젝트로 만든다.
하위 이슈(`--project 이름 --from ALA-n [DEV2-####]`): 부모는 분석 프로젝트 소속이고 done이어야 한다(아니면 error
  `분석 승인 전: 현재 <status>`). 부모 제목의 DEV2 번호를 읽는다. 하위 이슈는 parentId·그 프로젝트 정책·Board 담당·
  backlog로 만든다. POST /api/companies/{id}/issues에 parentId를 싣고 부모를 막는 옵션(blockParentUntilDone)은 쓰지 않는다
  — 부모는 이미 done이다. 대상 프로젝트가 부모와 다르면 서버는 부모 workspace를 물려주지 않는다(server issues.ts create).
  - DEV2를 주면(사람이 YouTrack에 새 Task를 만든 경우) 그 티켓을 읽어 담당자 검사를 하고, 제목·라벨·원본 링크는 그 티켓 기준
  - 안 주면 부모 DEV2 티켓으로 담당자 검사를 하고, 제목 `{부모 DEV2} {부모 summary} · {프로젝트}`, 부모 라벨 복사, 원본 링크는 부모 티켓
  - 멱등: 같은 부모·같은 프로젝트·같은 DEV2의 cancelled 아닌 하위 이슈가 있으면 skipped.
    DEV2를 줬는데 그 DEV2 이슈가 다른 곳에 이미 있으면 error — 같은 티켓이 두 갈래로 진행되지 않게 한다
멱등: 회사 안에 제목이 `DEV2-#### `로 시작하고 cancelled가 아닌 이슈가 있으면 skipped(하위 이슈 포함, 최상위 이슈 우선).
  skipped여도 그 이슈에 같은 provider·externalId work product가 없으면 붙인다. 라벨은 이름이 같으면 재사용한다.
대상 이름(회사·프로젝트·단계 에이전트·분석 프로젝트)·Board userId·프로젝트 정책·라벨 접두사와 색·Inbox 검색식은
  templates/paperclip/pilot.json에서 읽고, ID는 이름으로 조회한다 — 환경을 다시 만들면 ID가 바뀐다.

사용법:
    python3 tools/paperclip_import_ticket.py DEV2-8499 [DEV2-8500 ...]
    python3 tools/paperclip_import_ticket.py --inbox                      # 설정 inboxQuery (자동화용)
    python3 tools/paperclip_import_ticket.py --query "project: DEV2 tag: paperclip #Unresolved"
    python3 tools/paperclip_import_ticket.py --project "티켓 분석" DEV2-12779
    python3 tools/paperclip_import_ticket.py --project "쇼핑 데이터 추출" --from ALA-5            # 분석 승인 후 하위 이슈
    python3 tools/paperclip_import_ticket.py --project "쇼핑 데이터 추출" --from ALA-5 DEV2-12800  # 새 YouTrack Task
    python3 tools/paperclip_import_ticket.py --inbox --dry-run --json

결과: 티켓마다 created | skipped(기존 ALA-n) | updated | unchanged | dry_run(쓰지 않음) | error(사유).
  error가 하나라도 있으면 exit 1.
토큰: env YOUTRACK_TOKEN 우선, 없으면 `python3 tools/cred.py get youtrack-token` (tools/ticket_schedule.py와 같은 방식).
base URL: env YOUTRACK_BASE_URL (기본 https://aladincommunication.youtrack.cloud). 토큰 값은 헤더에만 쓰고 출력하지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "templates" / "paperclip" / "pilot.json"
DEFAULT_YT_BASE = "https://aladincommunication.youtrack.cloud"
# YouTrack `for: me`는 Assignee 기준이 아니다(2026-10-22 실측: 남의 담당 티켓 6건이 걸림) — Assignee로 명시.
# Reporter: -me — 자동 등록·분석은 "내가 만들지 않은, 나에게 할당된" 티켓만 (2026-10-22 사용자 결정)
DEFAULT_INBOX_QUERY = ("Assignee: me Reporter: -me #Unresolved project: DEV2 Type: Task, Bug"
                       " created: {minus 14d} .. Today")
TOKEN_CRED_NAME = "youtrack-token"
KST = dt.timezone(dt.timedelta(hours=9))

TICKET_RE = re.compile(r"^DEV2-\d+$")
ISSUE_REF_RE = re.compile(r"^[A-Z]+-\d+$")  # Paperclip 이슈 번호 (ALA-n)
TITLE_TICKET_RE = re.compile(r"^(DEV2-\d+)(?:\s+(.*))?$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
YT_FIELDS = "idReadable,summary,reporter(login,fullName),tags(name),customFields(name,value(login))"
ASSIGNEE_FIELD = "Assignee"
LABEL_MAX = 48  # Paperclip createIssueLabelSchema name max(48) — JS 문자열 길이(UTF-16 code unit) 기준
CANCELLED = "cancelled"
DONE = "done"
STATUS_NEW = "backlog"
STATUS_AUTO = "todo"  # 에이전트 할당 + todo면 서버가 생성 직후 할당 깨움을 보낸다(server issue-assignment-wakeup.ts)
LIVE_RUN = ("queued", "scheduled_retry", "running")  # HEARTBEAT_RUN_STATUSES 중 진행·대기
STOPPED_RUN = ("failed", "timed_out", "cancelled", "interrupted")
NO_WAKE_AGENT = ("paused", "terminated", "pending_approval")  # 사람이 멈췄거나 아직 쓸 수 없는 에이전트
DEFAULT_WAKE_MAX = 3
WAKE_REASON = "paperclip-inbox self-heal"
WORKSPACE = {"mode": "isolated_workspace"}
LIVE_REVIEW = ("pending", "changes_requested")  # executionState.status — 정책을 바꾸면 이 주기가 초기화된다
WP_PROVIDER = "youtrack"
PC_PAGE = 500  # Paperclip 이슈 목록 기본 한도(ISSUE_LIST_DEFAULT_LIMIT)
YT_PAGE = 100
DEFAULT_MAX = 20
RETRIES = 2
DETAIL_LIMIT = 200
SERVICE_HINT = "launchctl print gui/$(id -u)/com.team2.paperclip"
CONFIG_KEYS = ("baseUrl", "company", "approverUserId", "projects", "analysisProject", "labels")
LABEL_KINDS = ("reporter", "tag")
STAGE_TYPES = ("review", "approval")  # review → 에이전트 이름, approval → Board userId

# 루프백은 시스템 프록시를 타지 않게 한다 — 로컬 Paperclip 호출이 프록시로 새면 연결 실패로 보인다
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


# ---------------------------------------------------------------------------
# HTTP


class HttpError(RuntimeError):
    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(exc.read().decode("utf-8") or "null")
    except (ValueError, OSError):
        return ""
    detail = body.get("error") if isinstance(body, dict) else None
    return f": {str(detail)[:DETAIL_LIMIT]}" if detail else ""


def http_json(method: str, url: str, *, headers: Optional[Dict[str, str]] = None,
              body: Any = None, timeout: float = 30.0, detail: bool = False) -> Any:
    """JSON 요청 1회. 실패는 HttpError(status=None이면 연결 실패). detail=True면 응답 본문의 error 필드를 덧붙인다."""
    hdrs = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    host = urllib.parse.urlsplit(url).hostname or ""
    opener = _DIRECT.open if host in _LOOPBACK else urllib.request.urlopen
    try:
        with opener(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(f"HTTP {exc.code}{_error_detail(exc) if detail else ''}", exc.code) from None
    except (urllib.error.URLError, OSError) as exc:
        raise HttpError(f"연결 실패 ({getattr(exc, 'reason', exc)})") from None
    try:
        return json.loads(raw.decode("utf-8")) if raw.strip() else None
    except ValueError:
        raise HttpError("응답이 JSON이 아님") from None


class YouTrack:
    """읽기 전용 — GET만 둔다. 파일럿은 YouTrack → Paperclip 단방향이다."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout
        self.sleep = time.sleep

    def get(self, path: str, params: Dict[str, str]) -> Any:
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        headers = {"Authorization": f"Bearer {self._token}"}
        for attempt in range(RETRIES + 1):  # GET은 멱등이라 일시 오류(연결·429·5xx)는 재시도한다
            try:
                return http_json("GET", url, headers=headers, timeout=self.timeout)
            except HttpError as exc:
                if exc.status not in (None, 429, 500, 502, 503, 504) or attempt == RETRIES:
                    raise
            self.sleep(1 + attempt)
        raise HttpError("재시도 초과")

    def issue(self, ticket_id: str) -> Dict[str, Any]:
        return self.get(f"/api/issues/{urllib.parse.quote(ticket_id)}", {"fields": YT_FIELDS})

    def me(self) -> str:
        """토큰 사용자 login. 비어 있으면 HttpError — 담당자 검사를 열어 둔 채 진행하지 않는다."""
        login = ((self.get("/api/users/me", {"fields": "login"}) or {}).get("login") or "").strip()
        if not login:
            raise HttpError("응답에 login 없음")
        return login

    def search(self, query: str, cap: int) -> List[Dict[str, Any]]:
        """검색 결과를 cap+1건까지만 모은다 — 상한 초과 판정에는 그것으로 충분하다."""
        out: List[Dict[str, Any]] = []
        while len(out) <= cap:
            page = self.get("/api/issues", {"query": query, "fields": YT_FIELDS,
                                            "$top": str(YT_PAGE), "$skip": str(len(out))}) or []
            out.extend(page)
            if len(page) < YT_PAGE:
                break
        return out


class Paperclip:
    """local_trusted 모드라 인증 헤더가 없다."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        return http_json("GET", f"{self.base_url}{path}{query}", timeout=self.timeout, detail=True)

    def post(self, path: str, body: Dict[str, Any]) -> Any:
        """생성은 멱등이 아니라 재시도하지 않는다 — 중복 이슈보다 오류 보고가 낫다."""
        return http_json("POST", f"{self.base_url}{path}", body=body, timeout=self.timeout, detail=True)

    def patch(self, path: str, body: Dict[str, Any]) -> Any:
        return http_json("PATCH", f"{self.base_url}{path}", body=body, timeout=self.timeout, detail=True)


def resolve_token() -> str:
    token = os.environ.get("YOUTRACK_TOKEN")
    if token:
        return token
    proc = subprocess.run([sys.executable, str(REPO / "tools" / "cred.py"), "get", TOKEN_CRED_NAME],
                          capture_output=True, text=True)
    token = proc.stdout.strip()
    if proc.returncode != 0 or not token:
        raise HttpError(f"YouTrack 토큰 없음 — python3 tools/cred.py set {TOKEN_CRED_NAME}")
    return token


# ---------------------------------------------------------------------------
# 설정·대상 해소


class ConfigError(ValueError):
    pass


class ResolveError(RuntimeError):
    pass


def load_config(path: Path) -> Dict[str, Any]:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"설정을 읽을 수 없다 ({path}) — {exc}") from None
    missing = [k for k in CONFIG_KEYS if not cfg.get(k)] if isinstance(cfg, dict) else list(CONFIG_KEYS)
    if missing:
        raise ConfigError(f"설정 {path}에 값 없음: {', '.join(missing)}")
    for kind in LABEL_KINDS:
        spec = cfg["labels"].get(kind) if isinstance(cfg["labels"], dict) else None
        if not isinstance(spec, dict) or not spec.get("prefix") or not COLOR_RE.match(str(spec.get("color") or "")):
            raise ConfigError(f"설정 {path}의 labels.{kind}에는 prefix와 #RRGGBB color가 있어야 한다")
    if not isinstance(cfg["projects"], dict):
        raise ConfigError(f"설정 {path}의 projects는 {{프로젝트 이름: {{isolatedWorkspace, stages}}}} 맵이어야 한다")
    cfg["policies"] = {name: parse_policy(path, name, spec) for name, spec in cfg["projects"].items()}
    if cfg["analysisProject"] not in cfg["policies"]:
        raise ConfigError(f"설정 {path}의 analysisProject '{cfg['analysisProject']}'가 projects에 없다"
                          " — 하위 이슈의 부모가 될 분석 프로젝트 이름이다")
    rules = cfg.setdefault("rules", [])
    if not isinstance(rules, list) or not all(
            isinstance(r, dict) and isinstance(r.get("project"), str) and r["project"]
            and isinstance(r.get("when"), dict) for r in rules):
        raise ConfigError(f"설정 {path}의 rules는 [{{project, when:{{summaryAny, tagsAny}}}}] 목록이어야 한다")
    stray = sorted({r["project"] for r in rules} - {cfg["analysisProject"]})
    if stray:
        raise ConfigError(f"설정 {path}의 rules가 analysisProject 밖의 프로젝트를 가리킨다({', '.join(stray)})"
                          " — 분석 먼저, 다른 프로젝트는 --from 하위 이슈로만 들어간다")
    cfg.setdefault("inboxQuery", DEFAULT_INBOX_QUERY)
    cfg["auto"] = parse_auto(path, cfg.get("autoAnalyze"))
    return cfg


def parse_auto(path: Path, spec: Any) -> Optional[Dict[str, Any]]:
    """autoAnalyze: {agent, wakeMax?, enabled?} — 없거나 enabled:false면 None(꺼짐)."""
    if spec is None or (isinstance(spec, dict) and spec.get("enabled", True) is False):
        return None
    wake_max = spec.get("wakeMax", DEFAULT_WAKE_MAX) if isinstance(spec, dict) else None
    if (not isinstance(spec, dict) or not isinstance(spec.get("agent"), str) or not spec["agent"].strip()
            or not isinstance(wake_max, int) or isinstance(wake_max, bool) or wake_max < 0):
        raise ConfigError(f"설정 {path}의 autoAnalyze는 {{agent: 에이전트 이름, wakeMax: 0 이상 정수, enabled}}여야 한다")
    return {"agent": spec["agent"].strip(), "wakeMax": wake_max}


def parse_policy(path: Path, name: str, spec: Any) -> Dict[str, Any]:
    """`review:SQL Reviewer` → ("review", "SQL Reviewer"). 단계가 없으면 사람 승인 없이 done이 되므로 받지 않는다."""
    where = f"설정 {path}의 projects.{name}"
    if not isinstance(spec, dict) or not isinstance(spec.get("isolatedWorkspace"), bool):
        raise ConfigError(f"{where}에는 isolatedWorkspace(true/false)가 있어야 한다")
    stages = spec.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ConfigError(f"{where}.stages는 비지 않은 목록이어야 한다 — 단계가 없으면 사람 승인 없이 done이 된다")
    parsed: List[Tuple[str, str]] = []
    for stage in stages:
        kind, _, target = str(stage).partition(":")
        if not isinstance(stage, str) or kind.strip() not in STAGE_TYPES or not target.strip():
            raise ConfigError(f"{where}.stages의 '{stage}' — `review:{{에이전트 이름}}` 또는 "
                              "`approval:{Board userId}` 형식이어야 한다")
        parsed.append((kind.strip(), target.strip()))
    return {"isolatedWorkspace": spec["isolatedWorkspace"], "stages": parsed}


def _one(items: Any, name: str, kind: str) -> Dict[str, Any]:
    matches = [it for it in items or [] if isinstance(it, dict) and it.get("name") == name]
    if not matches:
        raise ResolveError(f"Paperclip {kind} '{name}' 없음 — Paperclip에 만들거나 templates/paperclip/pilot.json의 이름을 고친다")
    if len(matches) > 1:
        raise ResolveError(f"Paperclip {kind} '{name}'이 {len(matches)}개 — 이름을 하나로 정리")
    return matches[0]


def list_company_issues(pc: Paperclip, company_id: str) -> List[Dict[str, Any]]:
    """프로젝트 없는 이슈도 멱등 판정에 들어가야 해서 회사 전체를 본다."""
    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        page = pc.get(f"/api/companies/{company_id}/issues", {"limit": str(PC_PAGE), "offset": str(offset)}) or []
        out.extend(page)
        offset += len(page)
        if len(page) < PC_PAGE:
            return out


def resolve_context(pc: Paperclip, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """회사, 이름→프로젝트·에이전트, 회사 라벨, 회사 이슈 목록. 연결 실패·회사 해소 실패는 ResolveError.
    프로젝트·단계 에이전트는 그것이 필요한 티켓에서만 해소한다 — 규칙 불일치 티켓은 정책이 없다."""
    try:
        company = _one(pc.get("/api/companies"), cfg["company"], "회사")
        cid = company["id"]
        projects = pc.get(f"/api/companies/{cid}/projects") or []
        agents = pc.get(f"/api/companies/{cid}/agents") or []
        labels = {lb["name"]: lb for lb in pc.get(f"/api/companies/{cid}/labels") or [] if lb.get("name")}
        issues = list_company_issues(pc, cid)
    except HttpError as exc:
        if exc.status is None:
            raise ResolveError(f"Paperclip 서버 응답 없음 ({pc.base_url}) — {SERVICE_HINT}로 확인") from None
        raise ResolveError(f"Paperclip 조회 실패 — {exc}") from None
    return {"company": company, "projects": projects, "agents": agents, "labels": labels, "issues": issues}


# ---------------------------------------------------------------------------
# 판정·요청 본문


def normalize_ticket(raw: Dict[str, Any]) -> Dict[str, Any]:
    reporter = raw.get("reporter") if isinstance(raw.get("reporter"), dict) else None
    fields = {cf.get("name"): cf.get("value") for cf in raw.get("customFields") or [] if isinstance(cf, dict)}
    assignee = fields.get(ASSIGNEE_FIELD)
    return {
        "id": raw.get("idReadable") or "",
        "summary": " ".join((raw.get("summary") or "").split()),
        "reporter": {"fullName": reporter.get("fullName"), "login": reporter.get("login")} if reporter else None,
        "tags": [t["name"] for t in raw.get("tags") or [] if isinstance(t, dict) and t.get("name")],
        "assignee": ((assignee.get("login") or "").strip() or None) if isinstance(assignee, dict) else None,
    }


def assignee_reason(ticket: Dict[str, Any], me: str) -> Optional[str]:
    """내 티켓이 아니면 거부 사유. 담당자가 비어 있어도 거부한다 — 파일럿은 내 티켓만 처리한다."""
    if ticket.get("assignee") == me:
        return None
    return f"담당자 불일치: {ticket.get('assignee') or '(없음)'} — 토큰 사용자 {me}의 티켓만 처리한다"


def find_existing(issues: List[Dict[str, Any]], ticket_id: str) -> List[Dict[str, Any]]:
    """제목이 `{ticket_id} `로 시작하고 cancelled가 아닌 이슈. 최상위 이슈 먼저, 그 안에서 이슈 번호 오름차순 —
    부모 DEV2를 제목에 단 하위 이슈가 있어도 분류·skipped 대상은 최상위 이슈다."""
    found = [i for i in issues
             if ((i.get("title") or "") == ticket_id or (i.get("title") or "").startswith(ticket_id + " "))
             and i.get("status") != CANCELLED]
    return sorted(found, key=lambda i: (bool(i.get("parentId")), i.get("issueNumber") or 0))


def project_name(ctx: Dict[str, Any], project_id: Optional[str]) -> str:
    return next((p.get("name") for p in ctx["projects"] if p.get("id") == project_id), None) or f"프로젝트 {project_id}"


def find_parent(pc: Paperclip, ctx: Dict[str, Any], cfg: Dict[str, Any], ref: str) -> Dict[str, Any]:
    """`--from` 부모 — 분석 프로젝트 소속 done 이슈. 쓰기 직전 상태를 다시 읽는다. 조건 미달은 ResolveError.
    분석 프로젝트로 묶는 이유: 다른 프로젝트의 done은 분석 승인이 아니라 그 단계의 승인이라, 분석을 건너뛴 사슬이 생긴다."""
    matches = [i for i in ctx["issues"] if (i.get("identifier") or "").upper() == ref]
    if not matches:
        raise ResolveError(f"부모 {ref} 없음 — Paperclip 이슈 번호(ALA-n)를 확인")
    try:
        parent = pc.get(f"/api/issues/{matches[0]['id']}") or {}
    except HttpError as exc:
        raise ResolveError(f"Paperclip 이슈 조회 실패 — {exc}") from None
    if parent.get("status") != DONE:
        raise ResolveError(f"분석 승인 전: 현재 {parent.get('status')} — {ref}가 승인(done)된 뒤 하위 이슈를 만든다")
    analysis = _one(ctx["projects"], cfg["analysisProject"], "프로젝트")
    if parent.get("projectId") != analysis["id"]:
        where = project_name(ctx, parent["projectId"]) if parent.get("projectId") else "프로젝트 없음"
        raise ResolveError(f"부모 {ref} 이슈는 「{where}」 소속 — 하위 이슈는 「{cfg['analysisProject']}」에서"
                           " 승인된 분석 이슈에만 단다. 다른 프로젝트의 done은 분석 승인이 아니다")
    m = TITLE_TICKET_RE.match(" ".join((parent.get("title") or "").split()))
    if not m:
        raise ResolveError(f"부모 {ref} 제목이 `DEV2-#### `로 시작하지 않는다 — 원본 티켓을 알 수 없다")
    return {**parent, "ticket": m.group(1), "ticketSummary": m.group(2) or ""}


def move_reason(current: Dict[str, Any], place: Dict[str, Any], ctx: Dict[str, Any], project: str,
                analysis_project: str) -> Optional[str]:
    """`--project`가 이미 끝났거나 다른 프로젝트에 있는 이슈를 옮기려 하면 사유. 옮기면 그 단계의 승인 기록이 초기화된다."""
    identifier = current.get("identifier") or ""
    analysis = next((p.get("id") for p in ctx["projects"] if p.get("name") == analysis_project), None)
    parent = identifier if analysis and current.get("projectId") == analysis else "<승인된 분석 이슈 ALA-n>"
    hint = f'이어지는 일은 `--project "<프로젝트>" --from {parent}`로 하위 이슈를 만든다'
    if current.get("status") == DONE:
        return f"{identifier} 이슈는 이미 done — 승인 기록을 지키려고 옮기지 않는다. {hint}"
    if current.get("projectId") and current["projectId"] != place["projectId"]:
        return (f"{identifier} 이슈는 「{project_name(ctx, current['projectId'])}」 소속 — 옮기면 그 단계의 승인 기록이"
                f" 초기화된다. {hint}")
    return None


def match_rule(ticket: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """첫 일치 규칙. 판정 근거(hit)를 남겨 dry-run·JSON에서 왜 그 프로젝트인지 보이게 한다."""
    summary = ticket.get("summary", "").casefold()
    tags = {t.casefold(): t for t in ticket.get("tags") or []}
    for index, rule in enumerate(rules):
        when = rule.get("when") or {}
        for word in when.get("summaryAny") or []:
            if word and word.casefold() in summary:
                return {"matched": True, "index": index, "project": rule["project"], "hit": f"summary:{word}"}
        for tag in when.get("tagsAny") or []:
            if tag and tag.casefold() in tags:
                return {"matched": True, "index": index, "project": rule["project"], "hit": f"tag:{tags[tag.casefold()]}"}
    return {"matched": False}


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def clip_label(text: str, limit: int = LABEL_MAX) -> str:
    """Paperclip은 trim 후 48(UTF-16) 이하를 받는다. 저장 이름과 같아야 이름 일치 재사용이 되므로 자른 뒤 다시 trim한다."""
    out = " ".join(text.split())
    while _utf16_len(out) > limit:
        out = out[:-1]
    return out.rstrip()


def label_specs(ticket: Dict[str, Any], cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(이름, 색) — 요청자 fullName 1개 + 태그별 1개. fullName이 없으면 요청자 라벨을 만들지 않는다."""
    labels = cfg["labels"]
    specs: List[Tuple[str, str]] = []
    full_name = ((ticket.get("reporter") or {}).get("fullName") or "").strip()
    if full_name:
        specs.append((clip_label(labels["reporter"]["prefix"] + full_name), labels["reporter"]["color"]))
    for tag in ticket.get("tags") or []:
        specs.append((clip_label(labels["tag"]["prefix"] + tag), labels["tag"]["color"]))
    seen: set = set()
    return [s for s in specs if not (s[0] in seen or seen.add(s[0]))]


def ticket_url(yt_base: str, ticket_id: str) -> str:
    return f"{yt_base.rstrip('/')}/issue/{ticket_id}"


def issue_url(cfg: Dict[str, Any], ctx: Dict[str, Any], identifier: str) -> str:
    return f"{cfg['baseUrl'].rstrip('/')}/{ctx['company'].get('issuePrefix')}/issues/{identifier}"


def description(ticket: Dict[str, Any], yt_base: str, origin: str, today: dt.date) -> str:
    return "\n".join([
        f"- YouTrack: [{ticket['id']}]({ticket_url(yt_base, ticket['id'])})",
        f"- 요청: {ticket['summary']}",
        f"- 등록: {today.isoformat()} {origin} — paperclip_import_ticket.py, YouTrack → Paperclip 단방향."
        " 요청 원문은 YouTrack에서 직접 읽는다",
    ])


def execution_policy(participants: List[Tuple[str, Dict[str, str]]]) -> Dict[str, Any]:
    """(단계 종류, 참여자) 순서대로 단계 하나씩. 참여자는 {"type":"agent","agentId"} 또는 {"type":"user","userId"}."""
    return {"mode": "normal", "commentRequired": True, "stages": [
        {"type": kind, "approvalsNeeded": 1, "participants": [person]} for kind, person in participants
    ]}


def policy_signature(policy: Any) -> Any:
    """서버가 붙이는 stage·participant id를 뺀 비교 키 — 같은 정책인지 판정해 불필요한 PATCH를 막는다."""
    if not isinstance(policy, dict):
        return None
    stages = []
    for stage in policy.get("stages") or []:
        people = sorted((p.get("type"), p.get("agentId") if p.get("type") == "agent" else p.get("userId"))
                        for p in stage.get("participants") or [])
        stages.append((stage.get("type"), stage.get("approvalsNeeded"), tuple(people)))
    return (policy.get("mode"), bool(policy.get("commentRequired")), tuple(stages))


def placement(ctx: Dict[str, Any], cfg: Dict[str, Any], project_name: str) -> Dict[str, Any]:
    """프로젝트에 붙일 필드 — projectId, (격리 정책이면) executionWorkspaceSettings, executionPolicy.
    설정 projects에 없는 이름·Paperclip 이름 해소 실패는 ResolveError."""
    policy = cfg["policies"].get(project_name)
    if policy is None:
        raise ResolveError(f"설정 projects에 프로젝트 '{project_name}' 없음 — "
                           "templates/paperclip/pilot.json projects에 정책을 둔다")
    project = _one(ctx["projects"], project_name, "프로젝트")
    participants = [(kind, {"type": "agent", "agentId": _one(ctx["agents"], target, "에이전트")["id"]}
                     if kind == "review" else {"type": "user", "userId": target})
                    for kind, target in policy["stages"]]
    place: Dict[str, Any] = {"projectId": project["id"]}
    if policy["isolatedWorkspace"]:
        place["executionWorkspaceSettings"] = dict(WORKSPACE)
    place["executionPolicy"] = execution_policy(participants)
    return place


def issue_body(ticket: Dict[str, Any], cfg: Dict[str, Any], label_ids: List[str], place: Optional[Dict[str, Any]],
               yt_base: str, origin: str, today: dt.date, title: Optional[str] = None,
               agent_id: Optional[str] = None) -> Dict[str, Any]:
    """기본은 backlog + Board 담당 — Inbox에 모이고 에이전트는 깨어나지 않는다. 에이전트 할당은 사람이 한다.
    agent_id(자동 분석)면 todo + 그 에이전트 담당 — 서버가 생성 직후 할당 깨움을 보낸다."""
    body = {
        "title": title or f"{ticket['id']} {ticket['summary']}".strip(),
        "description": description(ticket, yt_base, origin, today),
        "status": STATUS_AUTO if agent_id else STATUS_NEW,
        "priority": "medium",
        **({"assigneeAgentId": agent_id} if agent_id else {"assigneeUserId": cfg["approverUserId"]}),
        "labelIds": label_ids,
    }
    body.update(place or {})
    return body


def work_product_body(ticket_id: str, yt_base: str) -> Dict[str, Any]:
    return {"type": "artifact", "provider": WP_PROVIDER, "externalId": ticket_id,
            "title": f"YouTrack {ticket_id}", "url": ticket_url(yt_base, ticket_id), "status": "active"}


def active_reason(issue: Dict[str, Any]) -> Optional[str]:
    run = issue.get("activeRun")
    run_id = (run.get("id") if isinstance(run, dict) else None) or issue.get("executionRunId") or issue.get("checkoutRunId")
    if run or run_id:
        return f"진행 중 실행 있음 ({run_id or 'activeRun'}) — 실행이 끝난 뒤 다시"
    state = issue.get("executionState") if isinstance(issue.get("executionState"), dict) else {}
    if state.get("status") in LIVE_REVIEW:
        return f"검토 단계 진행 중 ({state['status']}) — 정책을 바꾸면 검토 주기가 초기화된다"
    return None


def placement_patch(current: Dict[str, Any], place: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if current.get("projectId") != place["projectId"]:
        patch["projectId"] = place["projectId"]
    settings = current.get("executionWorkspaceSettings")
    isolated = isinstance(settings, dict) and settings.get("mode") == WORKSPACE["mode"]
    if "executionWorkspaceSettings" in place:
        if not isolated:
            patch["executionWorkspaceSettings"] = place["executionWorkspaceSettings"]
    elif isolated:  # 격리 없는 프로젝트로 옮기면 격리를 푼다 — 실행 위치를 그 프로젝트 정책(에이전트 cwd)에 맞춘다
        patch["executionWorkspaceSettings"] = None
    if policy_signature(current.get("executionPolicy")) != policy_signature(place["executionPolicy"]):
        patch["executionPolicy"] = place["executionPolicy"]
    return patch


# ---------------------------------------------------------------------------
# 쓰기


def ensure_labels(pc: Paperclip, ctx: Dict[str, Any], specs: List[Tuple[str, str]],
                  dry_run: bool) -> Tuple[List[str], List[Dict[str, Any]]]:
    """이름이 같은 회사 라벨은 재사용하고 없으면 만든다. dry_run이면 만들 라벨을 자리표시자로 둔다."""
    cid = ctx["company"]["id"]
    ids: List[str] = []
    plan: List[Dict[str, Any]] = []
    for name, color in specs:
        label = ctx["labels"].get(name)
        if label:
            ids.append(label["id"])
            plan.append({"name": name, "id": label["id"], "action": "existing"})
            continue
        if dry_run:
            ids.append(f"<새 라벨: {name}>")
            plan.append({"name": name, "color": color, "action": "would_create"})
            continue
        try:
            label = pc.post(f"/api/companies/{cid}/labels", {"name": name, "color": color})
        except HttpError:
            # 같은 이름이 그 사이 생겼으면(회사 안 이름 유일) 다시 읽어 쓴다
            refreshed = {lb["name"]: lb for lb in pc.get(f"/api/companies/{cid}/labels") or [] if lb.get("name")}
            if name not in refreshed:
                raise
            label = refreshed[name]
        ctx["labels"][name] = label
        ids.append(label["id"])
        plan.append({"name": name, "id": label["id"], "action": "created"})
    return ids, plan


def attach_work_product(pc: Paperclip, issue_id: str, body: Dict[str, Any], dry_run: bool,
                        check_existing: bool) -> Dict[str, Any]:
    if check_existing:
        try:
            items = pc.get(f"/api/issues/{issue_id}/work-products") or []
        except HttpError as exc:
            return {"action": "error", "reason": f"work product 조회 실패 — {exc}"}
        if any(wp.get("provider") == body["provider"] and wp.get("externalId") == body["externalId"]
               for wp in items if isinstance(wp, dict)):
            return {"action": "exists"}
    if dry_run:
        return {"action": "would_attach", "body": body}
    try:
        pc.post(f"/api/issues/{issue_id}/work-products", body)
    except HttpError as exc:
        return {"action": "error", "reason": f"work product 부착 실패 — {exc}. 다시 실행하면 기존 이슈에 붙인다"}
    return {"action": "attached", "body": body}


def wake_body(issue_id: str) -> Dict[str, Any]:
    return {"source": "assignment", "triggerDetail": "system", "reason": WAKE_REASON,
            "payload": {"issueId": issue_id, "taskId": issue_id}}


class Dispatcher:
    def __init__(self, pc: Paperclip, ctx: Dict[str, Any], cfg: Dict[str, Any], yt_base: str,
                 origin: str, today: dt.date, dry_run: bool, me: Optional[str] = None) -> None:
        self.pc, self.ctx, self.cfg = pc, ctx, cfg
        self.yt_base, self.origin, self.today, self.dry_run = yt_base, origin, today, dry_run
        self.me = me
        self.created_ids: set = set()  # 이번 실행에서 만든 이슈 — 서버가 할당 깨움을 이미 보냈다

    def auto_decision(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """자동 분석 여부. 요청자가 토큰 사용자면(또는 알 수 없으면) 하지 않는다 — query가 바뀌어도
        내가 만든 티켓은 자동 실행되지 않게 한다."""
        agent = self.cfg["auto"]["agent"]
        reporter = (((ticket.get("reporter") or {}).get("login")) or "").strip()
        if not reporter:
            return {"on": False, "agent": agent, "reason": "요청자 login 없음 — 내가 만든 티켓인지 몰라 Board backlog로"}
        if reporter == self.me:
            return {"on": False, "agent": agent,
                    "reason": f"요청자가 토큰 사용자({reporter}) — 내가 만든 티켓은 자동 분석하지 않고 Board backlog로"}
        return {"on": True, "agent": agent}

    def url(self, identifier: str) -> str:
        return issue_url(self.cfg, self.ctx, identifier)

    def run(self, ticket: Dict[str, Any], project: Optional[str]) -> Dict[str, Any]:
        """project가 있으면 분류(기존 이슈 PATCH 또는 그 프로젝트로 생성), 없으면 규칙 배분 등록."""
        tid = ticket["id"]
        result: Dict[str, Any] = {"ticket": tid, "result": "error", "reason": None, "summary": ticket["summary"]}
        existing = find_existing(self.ctx["issues"], tid)
        rule = ({"matched": True, "project": project, "hit": "--project"} if project
                else match_rule(ticket, self.cfg["rules"]))
        if existing and not project:
            issue = existing[0]
            result.update(result="skipped", reason=f"기존 {issue.get('identifier')}", issue=issue.get("identifier"),
                          url=self.url(issue.get("identifier") or ""),
                          existing=[i.get("identifier") for i in existing])
            result["workProduct"] = self.work_product(issue["id"], tid, check_existing=True)
            return result
        auto = self.auto_decision(ticket) if self.cfg["auto"] and not project and not existing else None
        if auto and auto["on"]:
            rule = {"matched": True, "project": self.cfg["analysisProject"], "hit": "autoAnalyze"}
        result["rule"] = rule
        if auto:
            result["autoAnalyze"] = auto
        agent_id = None
        try:
            place = placement(self.ctx, self.cfg, rule["project"]) if rule["matched"] else None
            if auto and auto["on"]:
                agent = _one(self.ctx["agents"], auto["agent"], "에이전트")
                agent_id, auto["agentStatus"] = agent["id"], agent.get("status")
        except ResolveError as exc:
            result["reason"] = str(exc)
            return result
        if existing:
            return self.classify(result, existing[0], place, rule["project"])
        return self.create(result, ticket, place, agent_id)

    def work_product(self, issue_id: str, tid: str, check_existing: bool) -> Dict[str, Any]:
        return attach_work_product(self.pc, issue_id, work_product_body(tid, self.yt_base), self.dry_run,
                                   check_existing)

    def classify(self, result: Dict[str, Any], issue: Dict[str, Any], place: Dict[str, Any],
                 project: str) -> Dict[str, Any]:
        identifier = issue.get("identifier") or ""
        result.update(issue=identifier, url=self.url(identifier))
        try:  # 목록은 실행 시작 시점 값이라, 쓰기 직전 상태를 다시 읽는다
            current = self.pc.get(f"/api/issues/{issue['id']}") or {}
        except HttpError as exc:
            result["reason"] = f"Paperclip 이슈 조회 실패 — {exc}"
            return result
        patch = placement_patch(current, place)
        moved = (move_reason({"identifier": identifier, **current}, place, self.ctx, project, self.cfg["analysisProject"])
                 if patch else None)
        if not patch:
            result.update(result="unchanged", reason="이미 같은 프로젝트·정책")
        elif moved:
            result["reason"] = moved
            return result
        elif active_reason(current):
            result["reason"] = f"{identifier} {active_reason(current)}"
            return result
        elif self.dry_run:
            result.update(result="dry_run", reason="쓰지 않음", request={"patch": patch})
        else:
            try:
                self.pc.patch(f"/api/issues/{issue['id']}", patch)
            except HttpError as exc:
                result["reason"] = f"Paperclip 이슈 갱신 실패 — {exc}"
                return result
            result.update(result="updated", reason=f"변경: {', '.join(patch)}", request={"patch": patch})
        result["workProduct"] = self.work_product(issue["id"], result["ticket"], check_existing=True)
        return result

    def create(self, result: Dict[str, Any], ticket: Dict[str, Any], place: Optional[Dict[str, Any]],
               agent_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            label_ids, plan = ensure_labels(self.pc, self.ctx, label_specs(ticket, self.cfg), self.dry_run)
        except HttpError as exc:
            result["reason"] = f"Paperclip 라벨 생성 실패 — {exc}"
            return result
        result["labels"] = plan
        origin = f"{self.origin} · 자동 분석 {self.cfg['auto']['agent']}" if agent_id else self.origin
        body = issue_body(ticket, self.cfg, label_ids, place, self.yt_base, origin, self.today, agent_id=agent_id)
        return self.post_issue(result, body, ticket["id"])

    def wake_pending(self) -> Dict[str, Any]:
        """깨움 보정 — 분석 프로젝트에서 자동 분석 에이전트 담당 todo인데 진행·대기 실행이 없는 이슈를 깨운다.
        서버의 할당 깨움이 빠지는 일이 있었다(ALA-2 리뷰 단계). 한 번에 wakeMax건까지 — 동시 실행 상한이 아니라
        이번 실행에서 깨우는 수의 상한이다. 방금 만든 이슈는 서버가 이미 깨웠으므로 건너뛴다."""
        auto = self.cfg["auto"]
        out: Dict[str, Any] = {"agent": auto["agent"], "max": auto["wakeMax"], "items": []}
        try:
            agent = _one(self.ctx["agents"], auto["agent"], "에이전트")
            project = _one(self.ctx["projects"], self.cfg["analysisProject"], "프로젝트")
        except ResolveError as exc:
            out["error"] = str(exc)
            return out
        out["agentStatus"] = status = agent.get("status")
        todo = sorted((i for i in self.ctx["issues"] if i.get("projectId") == project["id"]
                       and i.get("assigneeAgentId") == agent["id"] and i.get("status") == STATUS_AUTO),
                      key=lambda i: i.get("issueNumber") or 0)
        woken = 0
        for issue in todo:
            item: Dict[str, Any] = {"issue": issue.get("identifier")}
            out["items"].append(item)
            if issue["id"] in self.created_ids:
                item.update(action="just_created", reason="방금 만든 이슈 — 서버가 할당 깨움을 보냈다")
                continue
            if status in NO_WAKE_AGENT:
                item.update(action="agent_stopped", reason=f"에이전트 {status} — 사람이 멈춘 상태라 깨우지 않는다")
                continue
            if woken >= auto["wakeMax"]:
                item.update(action="deferred", reason=f"이번 실행 상한 {auto['wakeMax']}건 — 다음 실행에서")
                continue
            try:
                runs = [r for r in self.pc.get(f"/api/issues/{issue['id']}/runs") or [] if isinstance(r, dict)]
            except HttpError as exc:
                item.update(action="error", reason=f"실행 조회 실패 — {exc}")
                continue
            live = [r for r in runs if r.get("status") in LIVE_RUN]
            if live:
                item.update(action="running", reason=f"실행 {live[0].get('status')} ({live[0].get('runId')})")
                continue
            last = max((r for r in runs if r.get("agentId") == agent["id"]),
                       key=lambda r: str(r.get("createdAt") or ""), default=None)
            if last and last.get("status") in STOPPED_RUN:
                item.update(action="stopped_run", reason=f"최근 실행 {last['status']} — 같은 실패를 5분마다 되풀이하지"
                                                          " 않게 사람이 확인한 뒤 깨운다")
                continue
            body = wake_body(issue["id"])
            woken += 1
            if self.dry_run:
                item.update(action="would_wake", request={"path": f"/api/agents/{agent['id']}/wakeup", "body": body})
                continue
            try:
                resp = self.pc.post(f"/api/agents/{agent['id']}/wakeup", body) or {}
            except HttpError as exc:
                item.update(action="error", reason=f"깨움 실패 — {exc}")
                continue
            item.update(action="server_skipped" if resp.get("status") == "skipped" else "woken")
        return out

    def child(self, parent: Dict[str, Any], ticket: Dict[str, Any], given: bool, project: str) -> Dict[str, Any]:
        """분석 이슈(parent)의 하위 이슈. given=False면 ticket은 부모 DEV2 티켓(담당자 검사용)이고 제목·라벨은 부모에서 온다."""
        tid, ref = ticket["id"], parent.get("identifier") or ""
        summary = ticket["summary"] if given else parent["ticketSummary"]
        result: Dict[str, Any] = {"ticket": tid, "result": "error", "reason": None, "summary": summary, "parent": ref,
                                  "rule": {"matched": True, "project": project, "hit": f"--from {ref}"}}
        try:
            place = placement(self.ctx, self.cfg, project)
        except ResolveError as exc:
            result["reason"] = str(exc)
            return result
        existing = find_existing(self.ctx["issues"], tid)
        same = [i for i in existing if i.get("parentId") == parent["id"] and i.get("projectId") == place["projectId"]]
        if same:
            issue = same[0]
            result.update(result="skipped", reason=f"기존 하위 {issue.get('identifier')}", issue=issue.get("identifier"),
                          url=self.url(issue.get("identifier") or ""))
            result["workProduct"] = self.work_product(issue["id"], tid, check_existing=True)
            return result
        if given and existing:
            result["reason"] = (f"{tid} 이슈가 이미 {existing[0].get('identifier')}로 있다 — 같은 티켓이 두 갈래로"
                                " 진행되지 않게 만들지 않는다. 그 이슈를 cancelled로 정리한 뒤 다시")
            return result
        if given:
            try:
                label_ids, plan = ensure_labels(self.pc, self.ctx, label_specs(ticket, self.cfg), self.dry_run)
            except HttpError as exc:
                result["reason"] = f"Paperclip 라벨 생성 실패 — {exc}"
                return result
            body = issue_body(ticket, self.cfg, label_ids, place, self.yt_base, self.origin, self.today)
        else:
            names = {lb.get("id"): name for name, lb in self.ctx["labels"].items()}
            label_ids = [lid for lid in parent.get("labelIds") or [] if isinstance(lid, str)]
            plan = [{"name": names.get(lid), "id": lid, "action": "parent"} for lid in label_ids]
            base = {"id": tid, "summary": summary}
            body = issue_body(base, self.cfg, label_ids, place, self.yt_base, self.origin, self.today,
                              title=" ".join(p for p in (tid, summary, f"· {project}") if p))
        result["labels"] = plan
        body["parentId"] = parent["id"]
        return self.post_issue(result, body, tid)

    def post_issue(self, result: Dict[str, Any], body: Dict[str, Any], tid: str) -> Dict[str, Any]:
        wp = work_product_body(tid, self.yt_base)
        if self.dry_run:
            result.update(result="dry_run", reason="쓰지 않음", request={"issue": body, "workProduct": wp})
            result["workProduct"] = {"action": "would_attach", "body": wp}
            return result
        try:
            created = self.pc.post(f"/api/companies/{self.ctx['company']['id']}/issues", body) or {}
        except HttpError as exc:
            result["reason"] = f"Paperclip 이슈 생성 실패 — {exc}"
            return result
        self.ctx["issues"].append({**body, **created})  # 같은 실행 안의 중복 입력 방어
        if created.get("id"):
            self.created_ids.add(created["id"])
        identifier = created.get("identifier") or ""
        result.update(result="created", reason=None, issue=identifier, url=self.url(identifier))
        result["workProduct"] = (self.work_product(created["id"], tid, check_existing=False)
                                 if created.get("id") else {"action": "error", "reason": "생성 응답에 id 없음"})
        return result


# ---------------------------------------------------------------------------
# 실행


def _error(ticket_id: str, reason: str) -> Dict[str, Any]:
    return {"ticket": ticket_id, "result": "error", "reason": reason}


def _yt_reason(exc: HttpError) -> str:
    if exc.status == 404:
        return "YouTrack에 없음 (HTTP 404)"
    return f"YouTrack 조회 실패 — {exc}"


def run(args: argparse.Namespace, cfg: Dict[str, Any], today: Optional[dt.date] = None) -> Dict[str, Any]:
    today = today or dt.datetime.now(KST).date()
    yt_base = os.environ.get("YOUTRACK_BASE_URL", DEFAULT_YT_BASE).rstrip("/")
    query = cfg["inboxQuery"] if args.inbox else args.query
    report: Dict[str, Any] = {"dryRun": bool(args.dry_run), "project": args.project, "query": query,
                              "error": None, "results": []}
    if args.parent:
        report["from"] = args.parent
        return run_child(args, cfg, report, yt_base, today)

    # 입력 순서를 지킨다. 값: None = YouTrack에서 읽을 티켓, dict = 검색 결과 레코드, str = 이미 정해진 오류
    tickets: Dict[str, Any] = {}
    for raw in args.tickets:
        tid = raw.strip().upper()
        tickets.setdefault(tid, None if TICKET_RE.match(tid) else "DEV2-#### 형식이 아니다")
    analysis = cfg["analysisProject"]
    if args.project and args.project in cfg["policies"] and args.project != analysis:
        reason = (f"분석 먼저 — Inbox 이슈는 「{analysis}」으로만 분류한다. 분석 승인 후 --from ALA-n으로"
                  " 하위 이슈를 만든다")
        report["results"] = [_error(tid, rec or reason) for tid, rec in tickets.items()]
        return report
    try:
        yt = YouTrack(yt_base, resolve_token())
    except HttpError as exc:
        report["error"] = str(exc)
        report["results"] = [_error(tid, str(exc)) for tid in tickets]
        return report

    if query:
        try:
            found = yt.search(query, args.max)
        except HttpError as exc:
            report["error"] = f"YouTrack 검색 실패 — {exc}"
            return report
        if len(found) > args.max:
            report["error"] = (f"검색 결과가 상한 {args.max}건을 넘는다 — 검색식을 좁히거나 --max를 올린다."
                               " 아무것도 쓰지 않았다")
            return report
        for raw in found:
            rec = normalize_ticket(raw)
            if rec["id"] and tickets.get(rec["id"]) is None:
                tickets[rec["id"]] = rec if TICKET_RE.match(rec["id"]) else "DEV2 티켓이 아니다"
    if args.project:
        origin = f"--project `{args.project}` 분류"
    elif query:
        origin = f"{'Inbox ' if args.inbox else ''}검색식 `{query}`"
    else:
        origin = "티켓 지정"

    # YouTrack을 먼저 다 읽고 담당자 검사로 거른 뒤에 Paperclip을 본다 — 거부된 티켓은 Paperclip에 닿지 않는다
    for tid in [tid for tid, rec in tickets.items() if rec is None]:
        try:
            tickets[tid] = normalize_ticket(yt.issue(tid))
        except HttpError as exc:
            tickets[tid] = _yt_reason(exc)
    me: Optional[str] = None
    if any(isinstance(rec, dict) for rec in tickets.values()):
        try:
            me = yt.me()
        except HttpError as exc:
            me, reason = None, f"YouTrack 토큰 사용자 조회 실패 — {exc}. 담당자 검사를 못 해 쓰지 않았다"
            tickets.update({tid: reason for tid, rec in tickets.items() if isinstance(rec, dict)})
        for tid, rec in tickets.items():
            if me and isinstance(rec, dict):
                tickets[tid] = assignee_reason(rec, me) or rec

    pending = [tid for tid, rec in tickets.items() if isinstance(rec, dict)]
    pc = Paperclip(cfg["baseUrl"])
    dispatcher: Optional[Dispatcher] = None
    if pending:
        try:
            dispatcher = Dispatcher(pc, resolve_context(pc, cfg), cfg, yt_base, origin, today, args.dry_run, me)
        except ResolveError as exc:
            tickets.update({tid: str(exc) for tid in pending})

    for tid, rec in tickets.items():
        if isinstance(rec, str) or dispatcher is None:
            report["results"].append(_error(tid, rec if isinstance(rec, str) else "처리 안 됨"))
            continue
        report["results"].append(dispatcher.run(rec, args.project))

    # 깨움 보정은 --inbox(주기 실행)에서만 — 등록할 티켓이 없어도 돈다
    if args.inbox and cfg["auto"]:
        if dispatcher is None:
            try:
                dispatcher = Dispatcher(pc, resolve_context(pc, cfg), cfg, yt_base, origin, today, args.dry_run, me)
            except ResolveError as exc:
                report["wake"] = {"agent": cfg["auto"]["agent"], "max": cfg["auto"]["wakeMax"], "items": [],
                                  "error": str(exc)}
                return report
        report["wake"] = dispatcher.wake_pending()
    return report


def run_child(args: argparse.Namespace, cfg: Dict[str, Any], report: Dict[str, Any], yt_base: str,
              today: dt.date) -> Dict[str, Any]:
    """`--from ALA-n [DEV2-####]` — 부모는 Paperclip에서 먼저 읽고(읽기만), 담당자 검사를 통과해야 쓴다."""
    ref = args.parent
    given = args.tickets[0].strip().upper() if args.tickets else None

    def fail(reason: str, ticket: Optional[str] = None) -> Dict[str, Any]:
        report["results"].append({**_error(ticket or given or ref, reason), "parent": ref})
        return report

    if given and not TICKET_RE.match(given):
        return fail("DEV2-#### 형식이 아니다")
    try:
        yt = YouTrack(yt_base, resolve_token())
    except HttpError as exc:
        report["error"] = str(exc)
        return fail(str(exc))
    pc = Paperclip(cfg["baseUrl"])
    try:
        ctx = resolve_context(pc, cfg)
        parent = find_parent(pc, ctx, cfg, ref)
    except ResolveError as exc:
        return fail(str(exc))
    tid = given or parent["ticket"]
    try:
        ticket = normalize_ticket(yt.issue(tid))
        me = yt.me()
    except HttpError as exc:
        return fail(_yt_reason(exc) if exc.status == 404 else f"YouTrack 조회 실패 — {exc}. 담당자 검사를 못 해 쓰지 않았다",
                    tid)
    reason = assignee_reason(ticket, me)
    if reason:
        return fail(reason, tid)
    origin = f"--from `{ref}` 하위 이슈 · --project `{args.project}`"
    dispatcher = Dispatcher(pc, ctx, cfg, yt_base, origin, today, args.dry_run)
    report["results"].append(dispatcher.child(parent, ticket, given is not None, args.project))
    return report


def failed(report: Dict[str, Any]) -> bool:
    wake = report.get("wake") or {}
    return bool(report["error"]) or bool(wake.get("error")) or any(
        i.get("action") == "error" for i in wake.get("items") or []) or any(
        r["result"] == "error" or (r.get("workProduct") or {}).get("action") == "error" for r in report["results"])


WP_TEXT = {"attached": "원본 링크 부착", "exists": "원본 링크 있음", "would_attach": "원본 링크 부착 예정"}
WAKE_TEXT = {"woken": "깨움", "would_wake": "깨움 예정", "server_skipped": "서버가 깨움 건너뜀", "running": "실행 중",
             "stopped_run": "최근 실행 멈춤", "agent_stopped": "에이전트 멈춤", "deferred": "다음 실행",
             "just_created": "방금 생성", "error": "오류"}


def _auto_text(auto: Optional[Dict[str, Any]]) -> str:
    if not auto:
        return ""
    if not auto["on"]:
        return f"자동 분석 안 함: {auto['reason']}"
    status = auto.get("agentStatus")
    waiting = f" (에이전트 {status} — 재개되면 분석)" if status in NO_WAKE_AGENT else ""
    return f"자동 분석 → {auto['agent']}{waiting}"


def _wake_lines(wake: Dict[str, Any]) -> List[str]:
    lines = [f"{i['issue']}  {WAKE_TEXT.get(i['action'], i['action'])}  {i.get('reason') or ''}".rstrip()
             for i in wake.get("items") or [] if i.get("action") != "would_wake"]
    planned = [i for i in wake.get("items") or [] if i.get("action") == "would_wake"]
    if planned:
        lines.append(f"--- 깨움 보낼 요청 (쓰지 않음) {len(planned)}건")
        lines.append(json.dumps([{"issue": i["issue"], **i["request"]} for i in planned], ensure_ascii=False, indent=2))
    counts: Dict[str, int] = {}
    for i in wake.get("items") or []:
        counts[i["action"]] = counts.get(i["action"], 0) + 1
    summary = " · ".join(f"{WAKE_TEXT.get(k, k)} {v}" for k, v in counts.items()) or "대상 0건"
    head = f"깨움 보정({wake['agent']}, 상한 {wake['max']}"
    head += f", 에이전트 {wake['agentStatus']})" if wake.get("agentStatus") else ")"
    lines.append(f"{head}: {summary}")
    if wake.get("error"):
        lines.append(f"깨움 보정 오류: {wake['error']}")
    return lines
ORDER = ("created", "skipped", "updated", "unchanged", "dry_run", "error")


def _rule_text(rule: Optional[Dict[str, Any]]) -> str:
    if not rule:
        return ""
    return f"→ {rule['project']} ({rule['hit']})" if rule.get("matched") else "→ Inbox(프로젝트 없음)"


def render(report: Dict[str, Any]) -> str:
    """dry-run이면 티켓마다 보낼 요청(규칙·라벨·이슈·PATCH·work product)을 먼저 보이고, 끝에 티켓당 한 줄 결과를 낸다."""
    lines: List[str] = []
    for r in report["results"]:
        wp = r.get("workProduct") or {}
        if r["result"] == "dry_run":
            planned = {"rule": r.get("rule"), "labels": r.get("labels"), **r["request"]}
            if "workProduct" not in planned and wp.get("action") == "would_attach":
                planned["workProduct"] = wp["body"]
        elif wp.get("action") == "would_attach":
            planned = {"workProduct": wp["body"]}
        else:
            continue
        lines.append(f"--- {r['ticket']} 보낼 요청 (쓰지 않음)")
        lines.append(json.dumps({k: v for k, v in planned.items() if v is not None}, ensure_ascii=False, indent=2))
    counts: Dict[str, int] = {}
    for r in report["results"]:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
        parts = [r["ticket"], r["result"]]
        if r["result"] == "error":
            parts.append(r["reason"] or "")
        else:
            parts += [r.get("issue") or "", r["reason"] if r["result"] in ("skipped", "updated", "unchanged") else "",
                      r.get("url") or "", _rule_text(r.get("rule"))]
            if r.get("labels") is not None:
                parts.append(f"라벨 {len(r['labels'])}")
            parts.append(_auto_text(r.get("autoAnalyze")))
        wp = r.get("workProduct") or {}
        if wp.get("action") == "error":
            parts.append(wp.get("reason") or "")
        elif wp.get("action") in WP_TEXT:
            parts.append(WP_TEXT[wp["action"]])
        lines.append("  ".join(p for p in parts if p))
    if report.get("wake") is not None:
        lines.extend(_wake_lines(report["wake"]))
    if report["error"]:
        lines.append(f"오류: {report['error']}")
    lines.append("결과: " + " · ".join(f"{k} {counts.get(k, 0)}" for k in ORDER if counts.get(k) or k in ORDER[:2]))
    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YouTrack DEV2 티켓을 로컬 Paperclip 이슈로 등록·분류 (YouTrack 읽기 전용)")
    parser.add_argument("tickets", nargs="*", help="DEV2-#### (여러 개 가능)")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--inbox", action="store_true", help="설정 inboxQuery 결과를 등록 (자동화용)")
    source.add_argument("--query", help="YouTrack 검색식 결과를 등록")
    parser.add_argument("--project", help="분류: 기존 이슈에 이 프로젝트와 설정 projects의 정책(격리·단계)을 붙이고,"
                                          " 없으면 이 프로젝트로 만든다")
    parser.add_argument("--from", dest="parent", metavar="ALA-n",
                        help="하위 이슈: 승인(done)된 분석 이슈 아래에 --project 프로젝트의 하위 이슈를 만든다."
                             " DEV2-####을 하나 주면 그 티켓 기준, 안 주면 부모 티켓 기준")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX,
                        help=f"--inbox·--query 결과 상한, 넘으면 아무것도 쓰지 않는다 (기본 {DEFAULT_MAX})")
    parser.add_argument("--dry-run", action="store_true", help="보낼 요청만 출력하고 쓰지 않음")
    parser.add_argument("--json", action="store_true", help="기계 판독 JSON 출력")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="파일럿 설정 (기본 templates/paperclip/pilot.json)")
    args = parser.parse_args(argv)
    if args.parent is not None:
        args.parent = args.parent.strip().upper()
        if not ISSUE_REF_RE.match(args.parent):
            parser.error("--from은 Paperclip 이슈 번호(ALA-n)다")
        if not (args.project or "").strip() or args.inbox or args.query or len(args.tickets) > 1:
            parser.error('--from은 --project "<이름>"과 함께, DEV2-####은 없거나 하나만 쓴다')
        return args
    if not args.tickets and not (args.inbox or args.query):
        parser.error("DEV2-####, --inbox, --query 중 하나는 있어야 한다")
    if args.project is not None and (not args.project.strip() or args.inbox or args.query or not args.tickets):
        parser.error("--project는 DEV2-#### 티켓과 함께만 쓴다 — 분류는 사람이 티켓 단위로 한다")
    if args.max < 1:
        parser.error("--max는 1 이상이어야 한다")
    return args


def main(argv: Optional[List[str]] = None, today: Optional[dt.date] = None) -> int:
    args = parse_args(argv)
    try:
        cfg = load_config(Path(args.config).expanduser())
    except ConfigError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    report = run(args, cfg, today)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    return 1 if failed(report) else 0


if __name__ == "__main__":
    sys.exit(main())
