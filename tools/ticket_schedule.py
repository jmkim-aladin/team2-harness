#!/usr/bin/env python3
"""계획 항목 일정 점검(scan)·일정 코멘트 일괄 작성(apply) — `/ad:ticket-schedule` 스킬의 결정적 층.

팀장의 KB 주간업무 자동 취합은 티켓 코멘트의 날짜를 읽는다. 계획 항목에 날짜 코멘트가 없으면 일정 칸이 빈다.
이 도구는 대상 분류와 쓰기만 맡고, 날짜 제안·사용자 확인은 스킬(LLM)이 맡는다.

scan — `tag: {YYMM}-planned Type: Feature State: Open, {In Progress}` Feature와
       진행중 Feature의 미해결 하위 Task를 모아 필요한 계획 일정(kind)과 상태(status)를 JSON으로 낸다.
  - kind: Open → start(시작예정일), In Progress → due(완료목표일). 하위 Task는 자기 상태로 정한다
  - status: ok(날짜 ≥ 기준일) / overdue(날짜 < 기준일) / unparsed(라벨 날짜는 없지만 날짜처럼 보이는 코멘트 있음)
            / unscheduled(그 밖) — 추정값(월말·생성일)으로 채우지 않는다
  - 라벨: 코멘트 어느 줄이든 `^\\s*{라벨}\\s*[:：]\\s*{날짜}`. 같은 kind는 가장 최근 코멘트가 이긴다
    날짜는 YYYY-MM-DD 또는 `M월 D일`(연도 = 대상 월 연도, 6개월 넘게 떨어지면 ±1년)
apply — 계획 JSON의 각 항목을 검증하고 상태를 다시 조회해 kind가 그대로면 표준 코멘트 한 줄을 POST한다.
  상태가 바뀌었으면 skipped(state_changed), 같은 날짜가 이미 최신 라벨이면 skipped(already_set).

사용법:
    python3 tools/ticket_schedule.py scan --month 2610
    python3 tools/ticket_schedule.py scan --month 2610 --assignee jmkim --today 2026-10-19 --out /tmp/scan.json
    python3 tools/ticket_schedule.py apply --plan /tmp/plan.json --dry-run
    python3 tools/ticket_schedule.py apply --plan /tmp/plan.json

계획 JSON: {"entries": [{"id": "DEV2-9143", "kind": "start", "date": "2026-10-22"}]}

토큰: env YOUTRACK_TOKEN 우선, 없으면 `python3 tools/cred.py get youtrack-token`.
base URL: env YOUTRACK_BASE_URL (기본 https://aladincommunication.youtrack.cloud).
토큰 값은 헤더에만 쓰고 어디에도 출력하지 않는다.
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
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

REPO = Path(__file__).resolve().parents[1]
KST = dt.timezone(dt.timedelta(hours=9))
DEFAULT_BASE_URL = "https://aladincommunication.youtrack.cloud"
TOKEN_CRED_NAME = "youtrack-token"

OPEN = "Open"
IN_PROGRESS = "In Progress"
KIND_START = "start"
KIND_DUE = "due"
KIND_LABEL = {KIND_START: "시작예정일", KIND_DUE: "완료목표일"}  # apply가 쓰는 표준 라벨
LABELS = {
    KIND_START: ("시작예정일", "예상 시작일", "예상 시작 일자", "예상시작일"),
    KIND_DUE: ("완료목표일", "예상 종료일", "예상 완료일"),
}
STATUSES = ("ok", "overdue", "unparsed", "unscheduled")
PARENT_TYPES = {"Feature", "Epic"}  # 하위 확장에서 빼는 유형 — 자기 planned 태그로 따로 잡히는 계획 단위

SNIPPET = 300
WHEN_LIMIT = 400
HINT_LIMIT = 3
PAGE = 200
ISSUE_BATCH = 40
RETRIES = 2

ISSUE_FIELDS = (
    "idReadable,summary,description,resolved,"
    "customFields(name,value(name,login,fullName)),"
    "links(direction,linkType(name),issues(idReadable,resolved)),"
    "comments(text,created,deleted)"
)
STATE_FIELDS = "idReadable,resolved,customFields(name,value(name)),comments(text,created,deleted)"

_DATE = r"(?P<iso>\d{4}-\d{2}-\d{2})|(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일"
LABEL_RES = {
    kind: re.compile(r"^\s*(?:" + "|".join(re.escape(lb) for lb in labels) + r")\s*[:：]\s*(?:" + _DATE + ")",
                     re.MULTILINE)
    for kind, labels in LABELS.items()
}
# 날짜처럼 보이는 표현 — M월 D일 / M월 N주차 / M/D / YYYY-MM-DD / D일~
DATE_LIKE_RE = re.compile(
    r"\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}\s*월\s*\d{1,2}\s*일"
    r"|\d{1,2}\s*월\s*\d\s*주\s*차"
    r"|(?<![\w/.])(?:1[0-2]|0?[1-9])/(?:3[01]|[12]\d|0?[1-9])(?![\w/])"
    r"|\d{1,2}\s*일\s*~"
)
MONTH_RE = re.compile(r"^\d{2}(0[1-9]|1[0-2])$")
ISSUE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 설명 본문 5W1H의 When 절 — `## When (…)`, `### When`, `**When(언제)**`, `* **When** — …` 실측 형식
_W_PREFIX = r"^\s*(?:#{1,6}\s*|[-*]\s+)?\**\s*"
WHEN_START_RE = re.compile(_W_PREFIX + r"When\b")
WHEN_MARKER_RE = re.compile(_W_PREFIX + r"When\s*(?:\([^)]*\))?\s*\**\s*[:：—–-]?\s*")
SECTION_END_RE = re.compile(r"^\s*#{1,6}\s|" + _W_PREFIX + r"(?:Who|What|Where|Why|How)\b")


# ---------------------------------------------------------------------------
# 정규화


def id_key(issue_id: str) -> Tuple[str, int, str]:
    proj, _, num = issue_id.rpartition("-")
    return (proj, int(num) if num.isdigit() else 0, issue_id)


def ms_to_iso(ms: Optional[int]) -> Optional[str]:
    if not ms:
        return None
    return dt.datetime.fromtimestamp(ms / 1000, KST).isoformat(timespec="minutes")


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _name(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        return value.get("name") or value.get("fullName") or value.get("login")
    return None if value is None else str(value)


def normalize_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """API 이슈 JSON → 내부 레코드. 삭제된 코멘트는 빼고 created 오름차순으로 둔다."""
    fields = {cf.get("name"): cf.get("value") for cf in raw.get("customFields") or []}
    assignee = fields.get("Assignee")
    children: List[str] = []
    for link in raw.get("links") or []:
        if (link.get("linkType") or {}).get("name") == "Subtask" and link.get("direction") == "OUTWARD":
            children.extend(i["idReadable"] for i in link.get("issues") or []
                            if i.get("idReadable") and not i.get("resolved"))
    comments = [c for c in raw.get("comments") or [] if not c.get("deleted") and c.get("text")]
    comments.sort(key=lambda c: c.get("created") or 0)
    return {
        "id": raw.get("idReadable") or "",
        "summary": raw.get("summary") or "",
        "description": raw.get("description") or "",
        "resolved": bool(raw.get("resolved")),
        "type": _name(fields.get("Type")),
        "state": _name(fields.get("State")),
        "assignee": {
            "login": assignee.get("login"),
            "name": assignee.get("fullName") or assignee.get("name") or assignee.get("login"),
        } if isinstance(assignee, dict) else None,
        "children": children,
        "comments": comments,
    }


def kind_for(rec: Dict[str, Any]) -> Optional[str]:
    """현재 상태에서 나오는 계획 일정 kind. 해결됐거나 Open/In Progress가 아니면 None."""
    if rec.get("resolved"):
        return None
    return {OPEN: KIND_START, IN_PROGRESS: KIND_DUE}.get(rec.get("state") or "")


# ---------------------------------------------------------------------------
# 라벨 파싱·판정


def month_year(month: str) -> Tuple[int, int]:
    """'2610' → (2026, 10)."""
    return 2000 + int(month[:2]), int(month[2:])


def resolve_md(m: int, d: int, ref: Tuple[int, int]) -> Optional[dt.date]:
    """`M월 D일` → 날짜. 연도는 대상 월 연도, 대상 월과 6개월 넘게 떨어지면 ±1년(12월↔1월 경계)."""
    year, ref_month = ref
    if m - ref_month > 6:
        year -= 1
    elif ref_month - m > 6:
        year += 1
    try:
        return dt.date(year, m, d)
    except ValueError:
        return None


def label_dates(text: str, kind: str, ref: Tuple[int, int]) -> List[dt.date]:
    """코멘트 한 건에서 kind 라벨 날짜를 등장 순서대로. 달력에 없는 날짜는 버린다."""
    out: List[dt.date] = []
    for m in LABEL_RES[kind].finditer(text):
        if m.group("iso"):
            try:
                out.append(dt.date.fromisoformat(m.group("iso")))
            except ValueError:
                continue
        else:
            date = resolve_md(int(m.group("m")), int(m.group("d")), ref)
            if date:
                out.append(date)
    return out


def latest_label(comments: List[Dict[str, Any]], kind: str,
                 ref: Tuple[int, int]) -> Tuple[Optional[dt.date], Optional[Dict[str, Any]]]:
    """가장 최근 코멘트(created 기준)의 kind 라벨 날짜. 한 코멘트에 여럿이면 마지막 것."""
    for comment in sorted(comments, key=lambda c: c.get("created") or 0, reverse=True):
        dates = label_dates(comment.get("text") or "", kind, ref)
        if dates:
            return dates[-1], comment
    return None, None


def looks_like_date(text: str) -> bool:
    return bool(DATE_LIKE_RE.search(text or ""))


def snippet(comment: Dict[str, Any]) -> Dict[str, Any]:
    return {"created": ms_to_iso(comment.get("created")), "text": clip((comment.get("text") or "").strip(), SNIPPET)}


def extract_when(description: str) -> Optional[str]:
    """설명 본문 5W1H의 When 절 발췌(400자). 다음 제목이나 다른 W/H 표지 앞에서 끊는다."""
    lines = (description or "").splitlines()
    for i, line in enumerate(lines):
        if not WHEN_START_RE.match(line):
            continue
        body = [WHEN_MARKER_RE.sub("", line, count=1).strip(" *")]
        for nxt in lines[i + 1:]:
            if SECTION_END_RE.match(nxt):
                break
            body.append(nxt.rstrip())
        text = "\n".join(s for s in body if s.strip()).strip()
        return clip(text, WHEN_LIMIT) if text else None
    return None


def classify(rec: Dict[str, Any], kind: str, ref: Tuple[int, int], today: dt.date) -> Dict[str, Any]:
    """필요 kind 기준 status·근거 코멘트·힌트. 추정값으로 채우지 않는다."""
    comments = rec.get("comments") or []
    date, source = latest_label(comments, kind, ref)
    recent = sorted(comments, key=lambda c: c.get("created") or 0, reverse=True)
    date_like = [c for c in recent if looks_like_date(c.get("text") or "")]
    if date:
        status = "ok" if date >= today else "overdue"
    elif date_like:
        status = "unparsed"  # 반대 kind 라벨만 있는 경우도 날짜 표현이라 여기로 온다
    else:
        status = "unscheduled"
    return {
        "date": date.isoformat() if date else None,
        "status": status,
        "source": snippet(source) if source else None,
        "hints": [snippet(c) for c in date_like[:HINT_LIMIT]],
    }


# ---------------------------------------------------------------------------
# YouTrack 클라이언트 — scan·apply는 get/post만 기대한다(테스트는 가짜 클라이언트 주입)


class Client(Protocol):
    def get(self, path: str, params: Dict[str, str]) -> Any: ...

    def post(self, path: str, params: Dict[str, str], body: Dict[str, Any]) -> Any: ...


class YouTrackError(RuntimeError):
    pass


class YouTrackClient:
    def __init__(self, base_url: str, token: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout
        self.calls = 0

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    def get(self, path: str, params: Dict[str, str]) -> Any:
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, method="GET", headers=self._headers())
        for attempt in range(RETRIES + 1):  # GET은 멱등이라 일시 오류(타임아웃·429·5xx)는 재시도한다
            self.calls += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == RETRIES:
                    raise YouTrackError(f"GET {path} → HTTP {exc.code}") from None
            except (urllib.error.URLError, OSError) as exc:
                if attempt == RETRIES:
                    raise YouTrackError(f"GET {path} → {getattr(exc, 'reason', exc)}") from None
            time.sleep(1 + attempt)
        raise YouTrackError(f"GET {path} → 재시도 초과")

    def post(self, path: str, params: Dict[str, str], body: Dict[str, Any]) -> Any:
        """코멘트 작성은 멱등이 아니라 재시도하지 않는다 — 중복 코멘트보다 오류 보고가 낫다."""
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        headers = {**self._headers(), "Content-Type": "application/json"}
        req = urllib.request.Request(url, method="POST", headers=headers,
                                     data=json.dumps(body, ensure_ascii=False).encode("utf-8"))
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            raise YouTrackError(f"POST {path} → HTTP {exc.code}") from None
        except (urllib.error.URLError, OSError) as exc:
            raise YouTrackError(f"POST {path} → {getattr(exc, 'reason', exc)}") from None


def resolve_token() -> str:
    token = os.environ.get("YOUTRACK_TOKEN")
    if token:
        return token
    proc = subprocess.run([sys.executable, str(REPO / "tools" / "cred.py"), "get", TOKEN_CRED_NAME],
                          capture_output=True, text=True)
    token = proc.stdout.strip()
    if proc.returncode != 0 or not token:
        raise YouTrackError(f"YouTrack 토큰 없음 — python3 tools/cred.py set {TOKEN_CRED_NAME}")
    return token


def query_all(client: Client, query: str, fields: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    while True:
        page = client.get("/api/issues", {"query": query, "fields": fields,
                                          "$top": str(PAGE), "$skip": str(len(out))})
        out.extend(page)
        if len(page) < PAGE:
            return out


def fetch_issues(client: Client, ids: List[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(ids), ISSUE_BATCH):
        chunk = ids[i:i + ISSUE_BATCH]
        items = client.get("/api/issues", {"query": "issue id: " + ", ".join(chunk),
                                           "fields": ISSUE_FIELDS, "$top": str(len(chunk) + 10)})
        for item in items:
            if item.get("idReadable") in chunk:
                out[item["idReadable"]] = item
    return out


# ---------------------------------------------------------------------------
# scan


def planned_tag(month: str) -> str:
    return f"{month}-planned"


def collect_targets(client: Client, month: str) -> List[Tuple[Dict[str, Any], Optional[str]]]:
    """(레코드, 부모 Feature id). Open Feature는 자신만, 진행중 Feature는 자신 + 미해결 하위 Task(Open·진행중)."""
    query = f"tag: {planned_tag(month)} Type: Feature State: {OPEN}, {{{IN_PROGRESS}}}"
    features = [normalize_issue(raw) for raw in query_all(client, query, ISSUE_FIELDS)]
    features = [f for f in features if kind_for(f)]
    feature_ids = {f["id"] for f in features}
    child_ids: List[str] = []
    for feature in features:
        if feature["state"] == IN_PROGRESS:
            child_ids.extend(c for c in feature["children"] if c not in feature_ids and c not in child_ids)
    children = {iid: normalize_issue(raw) for iid, raw in fetch_issues(client, child_ids).items()}

    out: List[Tuple[Dict[str, Any], Optional[str]]] = []
    seen = set(feature_ids)
    for feature in features:
        out.append((feature, None))
        if feature["state"] != IN_PROGRESS:
            continue
        for cid in feature["children"]:
            child = children.get(cid)
            if not child or cid in seen or child.get("type") in PARENT_TYPES or not kind_for(child):
                continue  # Backlog 등 그 밖의 상태, 다른 부모에서 이미 담은 Task는 뺀다
            seen.add(cid)
            out.append((child, feature["id"]))
    return out


def build_item(rec: Dict[str, Any], parent: Optional[str], ref: Tuple[int, int], today: dt.date) -> Dict[str, Any]:
    kind = kind_for(rec) or KIND_START
    return {
        "id": rec["id"],
        "summary": rec["summary"],
        "type": rec["type"],
        "state": rec["state"],
        "assignee": rec["assignee"] or {"login": None, "name": None},
        "parent": parent,
        "kind": kind,
        "label": KIND_LABEL[kind],
        **classify(rec, kind, ref, today),
        "when": extract_when(rec["description"]),
    }


def sort_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
    """담당자 → Feature → 그 하위 Task. 미지정 담당자는 맨 뒤."""
    who = item["assignee"]
    name = who.get("name") or who.get("login")
    feature = item["parent"] or item["id"]
    return (name is None, name or "", id_key(feature), item["parent"] is not None, id_key(item["id"]))


def scan(client: Client, month: str, today: dt.date, assignees: Iterable[str] = ()) -> Dict[str, Any]:
    ref = month_year(month)
    wanted = {a.lower() for a in assignees}
    items = [build_item(rec, parent, ref, today) for rec, parent in collect_targets(client, month)]
    if wanted:  # 확장한 뒤 항목 단위(Feature·Task 모두)로 거른다
        items = [it for it in items if (it["assignee"]["login"] or "").lower() in wanted]
    items.sort(key=sort_key)
    counts = {s: sum(1 for it in items if it["status"] == s) for s in STATUSES}
    return {"month": month, "tag": planned_tag(month), "today": today.isoformat(), "counts": counts, "items": items}


# ---------------------------------------------------------------------------
# apply


def comment_body(kind: str, date: str) -> str:
    return f"{KIND_LABEL[kind]}: {date}"


def validate_entry(entry: Any) -> Optional[str]:
    if not isinstance(entry, dict):
        return "invalid_entry"
    if not isinstance(entry.get("id"), str) or not ISSUE_ID_RE.match(entry["id"]):
        return "invalid_id"
    if entry.get("kind") not in KIND_LABEL:
        return "invalid_kind"
    date = entry.get("date")
    if not isinstance(date, str) or not ISO_RE.match(date):
        return "invalid_date"
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        return "invalid_date"
    return None


def apply_entry(client: Client, entry: Any, dry_run: bool) -> Dict[str, Any]:
    raw = entry if isinstance(entry, dict) else {}
    result: Dict[str, Any] = {"id": raw.get("id"), "kind": raw.get("kind"), "date": raw.get("date"),
                              "result": "error", "reason": None}
    problem = validate_entry(entry)
    if problem:
        result["reason"] = problem
        return result
    iid, kind, date = entry["id"], entry["kind"], entry["date"]
    try:
        current = normalize_issue(client.get(f"/api/issues/{urllib.parse.quote(iid)}", {"fields": STATE_FIELDS}))
    except YouTrackError as exc:
        result["reason"] = str(exc)
        return result
    result["state"] = current["state"]
    if kind_for(current) != kind:
        result.update(result="skipped", reason="state_changed")
        return result
    target = dt.date.fromisoformat(date)
    existing, _ = latest_label(current["comments"], kind, (target.year, target.month))
    if existing == target:  # 재실행 시 같은 코멘트를 또 달지 않는다
        result.update(result="skipped", reason="already_set")
        return result
    body = comment_body(kind, date)
    result["body"] = body
    if dry_run:
        result.update(result="dry_run")
        return result
    try:
        client.post(f"/api/issues/{urllib.parse.quote(iid)}/comments", {"fields": "id"}, {"text": body})
    except YouTrackError as exc:
        result["reason"] = str(exc)
        return result
    result.update(result="posted")
    return result


def apply_plan(client: Client, plan: Dict[str, Any], dry_run: bool = False) -> List[Dict[str, Any]]:
    """항목 순서대로 검증 → 상태 재조회 → 코멘트 POST. 한 항목 실패가 나머지를 막지 않는다."""
    return [apply_entry(client, entry, dry_run) for entry in plan.get("entries") or []]


# ---------------------------------------------------------------------------
# CLI


def ensure_outside_repo(out: Path) -> Path:
    """scan 결과는 티켓 코멘트를 담은 업무 데이터라 repo 안에 쓰지 않는다."""
    resolved = out.expanduser().resolve()
    if resolved == REPO or REPO in resolved.parents:
        raise ValueError(f"출력 경로는 repo 밖이어야 한다: {resolved}")
    return resolved


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="계획 항목 일정 점검(scan)·일정 코멘트 일괄 작성(apply)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_scan = sub.add_parser("scan", help="planned 태그 Feature·진행중 하위 Task의 계획 일정 분류 → JSON")
    p_scan.add_argument("--month", required=True, help="대상 월 YYMM (예: 2610 → 2610-planned)")
    p_scan.add_argument("--assignee", nargs="+", default=[], help="담당자 login 필터 (여러 개 가능)")
    p_scan.add_argument("--today", help="기준일 YYYY-MM-DD (기본: 오늘, KST)")
    p_scan.add_argument("--out", help="JSON 출력 경로 (repo 밖, 기본 stdout)")
    p_apply = sub.add_parser("apply", help="계획 JSON대로 표준 일정 코멘트 작성")
    p_apply.add_argument("--plan", required=True, help='계획 JSON 경로 ({"entries":[{"id","kind","date"}]})')
    p_apply.add_argument("--dry-run", action="store_true", help="POST 없이 쓸 본문만 출력")
    return parser.parse_args(argv)


def make_client() -> YouTrackClient:
    base_url = os.environ.get("YOUTRACK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return YouTrackClient(base_url, resolve_token())


def run_scan(args: argparse.Namespace, client: Optional[Client] = None) -> int:
    if not MONTH_RE.match(args.month):
        print(f"오류: --month는 YYMM이어야 한다: {args.month}", file=sys.stderr)
        return 2
    try:
        today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(KST).date()
        out = ensure_outside_repo(Path(args.out)) if args.out else None
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    try:
        result = scan(client or make_client(), args.month, today, args.assignee)
    except YouTrackError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"{result['tag']} 기준일 {result['today']}: {len(result['items'])}건 {result['counts']} → {out}",
              file=sys.stderr)
    else:
        print(text)
    return 0


def run_apply(args: argparse.Namespace, client: Optional[Client] = None) -> int:
    try:
        plan = json.loads(Path(args.plan).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"오류: 계획 JSON을 읽을 수 없다 — {exc}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict) or not isinstance(plan.get("entries"), list):
        print('오류: 계획 JSON은 {"entries": [...]} 형식이어야 한다', file=sys.stderr)
        return 2
    try:
        results = apply_plan(client or make_client(), plan, args.dry_run)
    except YouTrackError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if any(r["result"] == "error" for r in results) else 0


def main(argv: Optional[List[str]] = None, client: Optional[Client] = None) -> int:
    args = parse_args(argv)
    return run_scan(args, client) if args.command == "scan" else run_apply(args, client)


if __name__ == "__main__":
    sys.exit(main())
