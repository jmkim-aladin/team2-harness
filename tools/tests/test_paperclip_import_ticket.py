"""paperclip_import_ticket 회귀 — YouTrack·Paperclip 모두 로컬 가짜 서버(http.server)로 대체한다. 실제 서버에는 닿지 않는다."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import threading
import unittest
import urllib.parse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("paperclip_import_ticket", ROOT / "tools/paperclip_import_ticket.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)

TOKEN = "test-token-not-real-7f3a9c"
TODAY = date(2026, 10, 22)
CID = "3ea0f9e5-0000-4000-8000-000000000001"
PID = "8db40eb8-0000-4000-8000-000000000002"
PID_OTHER = "8db40eb8-0000-4000-8000-000000000003"
PID_PREP = "8db40eb8-0000-4000-8000-000000000006"
WRITER = "c0707c1d-0000-4000-8000-000000000004"
REVIEWER = "e6301f4b-0000-4000-8000-000000000005"
SECRET_DESCRIPTION = "요청 원문 — 고객 연락처 010-0000-0000"
ME = "jmkim"
SHOP = {"isolatedWorkspace": True, "stages": ["review:SQL Reviewer", "approval:local-board"]}
PREP = {"isolatedWorkspace": False, "stages": ["approval:local-board"]}
POLICIES = {"쇼핑 데이터 추출": SHOP, "기타 요청": SHOP, "티켓 분석": PREP}
SHOP_POLICY = {"mode": "normal", "commentRequired": True, "stages": [
    {"type": "review", "approvalsNeeded": 1, "participants": [{"type": "agent", "agentId": REVIEWER}]},
    {"type": "approval", "approvalsNeeded": 1, "participants": [{"type": "user", "userId": "local-board"}]},
]}
PREP_POLICY = {"mode": "normal", "commentRequired": True, "stages": [
    {"type": "approval", "approvalsNeeded": 1, "participants": [{"type": "user", "userId": "local-board"}]},
]}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def serve(fake):
    class Handler(BaseHTTPRequestHandler):
        def _dispatch(self, method):
            parts = urllib.parse.urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else None
            try:
                status, payload = fake.handle(method, parts.path, urllib.parse.parse_qs(parts.query), body,
                                              dict(self.headers))
            except Exception as exc:  # 가짜 서버 버그는 500으로 드러낸다 — 연결 끊김이면 도구의 연결 실패와 섞인다
                status, payload = 500, {"error": f"fake: {exc!r}"}
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PATCH(self):
            self._dispatch("PATCH")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class FakeYouTrack:
    def __init__(self):
        self.issues = {}
        self.queries = {}
        self.seen_auth = []
        self.seen_queries = []
        self.writes = []
        self.me = {"login": ME}  # /api/users/me 응답 — None이면 401

    def add(self, iid, summary, *, reporter=("김정민", "jmkim"), tags=(), assignee=ME):
        self.issues[iid] = {
            "idReadable": iid, "summary": summary, "description": SECRET_DESCRIPTION,
            "reporter": {"fullName": reporter[0], "login": reporter[1]} if reporter else None,
            "tags": [{"name": t} for t in tags],
            "customFields": [{"name": "Priority", "value": {"name": "Normal"}},
                             {"name": "Assignee", "value": {"login": assignee} if assignee else None}],
        }

    def handle(self, method, path, query, body, headers):
        self.seen_auth.append(headers.get("Authorization"))
        if method != "GET":
            self.writes.append((method, path, body))
            return 405, {"error": "read only"}
        if path == "/api/users/me":
            return (200, self.me) if self.me is not None else (401, {"error": "Unauthorized"})
        if path == "/api/issues":
            q = query.get("query", [""])[0]
            self.seen_queries.append(q)
            ids = self.queries.get(q, [])
            skip, top = int(query.get("$skip", ["0"])[0]), int(query.get("$top", ["100"])[0])
            return 200, [self.issues[i] for i in ids[skip:skip + top]]
        m = re.match(r"^/api/issues/([^/]+)$", path)
        if m and m.group(1) in self.issues:
            return 200, self.issues[m.group(1)]
        return 404, {"error": "Not Found", "error_description": "Entity not found"}


class FakePaperclip:
    def __init__(self):
        self.companies = [{"id": CID, "name": "aladin-dev2", "issuePrefix": "ALA"}]
        self.projects = [{"id": PID, "name": "쇼핑 데이터 추출"}, {"id": PID_OTHER, "name": "기타 요청"},
                         {"id": PID_PREP, "name": "티켓 분석"}]
        self.agents = [{"id": WRITER, "name": "SQL Writer"}, {"id": REVIEWER, "name": "SQL Reviewer"}]
        self.labels = []
        self.issues = []
        self.work_products = {}
        self.requests = []
        self.seq = 0

    def next_id(self):
        self.seq += 1
        return f"00000000-0000-4000-8000-{self.seq:012d}"

    def add_issue(self, title, status="todo", **extra):
        issue = {"id": self.next_id(), "identifier": f"ALA-{len(self.issues) + 1}", "issueNumber": len(self.issues) + 1,
                 "title": title, "status": status, "projectId": None, "executionPolicy": None,
                 "executionWorkspaceSettings": None, "executionState": None, "activeRun": None,
                 "executionRunId": None, "checkoutRunId": None, "labelIds": []}
        issue.update(extra)
        self.issues.append(issue)
        return issue

    def add_label(self, name, color="#6B7280"):
        label = {"id": self.next_id(), "name": name, "color": color}
        self.labels.append(label)
        return label

    def writes(self, method=None, suffix=""):
        return [(m, p, b) for m, p, b in self.requests
                if m != "GET" and (method is None or m == method) and p.endswith(suffix)]

    @staticmethod
    def normalized(policy):
        """서버처럼 stage·participant에 id를 붙여 저장한다 — 클라이언트 비교가 id를 무시하는지 확인용."""
        out = json.loads(json.dumps(policy))
        for n, stage in enumerate(out.get("stages") or []):
            stage["id"] = f"stage-{n}"
            for k, person in enumerate(stage.get("participants") or []):
                person.update(id=f"p-{n}-{k}", agentId=person.get("agentId"), userId=person.get("userId"))
        return out

    def handle(self, method, path, query, body, headers):
        self.requests.append((method, path, body))
        base = f"/api/companies/{CID}"
        if method == "GET" and path == "/api/companies":
            return 200, self.companies
        if method == "GET" and path == f"{base}/projects":
            return 200, self.projects
        if method == "GET" and path == f"{base}/agents":
            return 200, self.agents
        if path == f"{base}/labels":
            if method == "GET":
                return 200, self.labels
            name = body["name"].strip()
            if len(name.encode("utf-16-le")) // 2 > 48 or not re.match(r"^#[0-9a-fA-F]{6}$", body["color"]):
                return 400, {"error": "Validation error"}
            if any(lb["name"] == name for lb in self.labels):
                return 409, {"error": "duplicate"}
            return 201, self.add_label(name, body["color"])
        if path == f"{base}/issues":
            if method == "GET":
                offset, limit = int(query.get("offset", ["0"])[0]), int(query.get("limit", ["500"])[0])
                return 200, self.issues[offset:offset + limit]
            fields = {k: v for k, v in body.items() if k not in ("executionPolicy", "title", "status")}
            issue = self.add_issue(body["title"], body["status"], **fields)
            if body.get("executionPolicy"):
                issue["executionPolicy"] = self.normalized(body["executionPolicy"])
            return 201, issue
        m = re.match(r"^/api/issues/([^/]+)(/work-products)?$", path)
        issue = next((i for i in self.issues if m and i["id"] == m.group(1)), None)
        if not issue:
            return 404, {"error": "Issue not found"}
        if m.group(2):
            items = self.work_products.setdefault(issue["id"], [])
            if method == "GET":
                return 200, items
            items.append(dict(body, id=self.next_id()))
            return 201, items[-1]
        if method == "GET":
            return 200, issue
        if method == "PATCH":
            for key, value in body.items():
                issue[key] = self.normalized(value) if key == "executionPolicy" else value
            return 200, issue
        return 405, {"error": "method"}


class Base(unittest.TestCase):
    def setUp(self):
        self.yt, self.pc = FakeYouTrack(), FakePaperclip()
        self.yt_server, self.yt_url = serve(self.yt)
        self.pc_server, self.pc_url = serve(self.pc)
        self.tmp = tempfile.TemporaryDirectory()
        self.config = self.write_config()

    def tearDown(self):
        for server in (self.yt_server, self.pc_server):
            server.shutdown()
            server.server_close()
        self.tmp.cleanup()

    def write_config(self, **overrides):
        cfg = {
            "baseUrl": self.pc_url, "company": "aladin-dev2", "projects": POLICIES,
            "approverUserId": "local-board", "inboxQuery": "for: me #Unresolved project: DEV2",
            "rules": [{"project": "쇼핑 데이터 추출",
                       "when": {"summaryAny": ["추출", "엑셀", "리스트", "데이터 요청"], "tagsAny": []}}],
            "labels": {"reporter": {"prefix": "요청자:", "color": "#6B7280"},
                       "tag": {"prefix": "태그:", "color": "#2563EB"}},
        }
        cfg.update(overrides)
        path = Path(self.tmp.name) / f"pilot-{len(list(Path(self.tmp.name).iterdir()))}.json"
        path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def run_tool(self, *argv, config=None, env=None):
        out, err = io.StringIO(), io.StringIO()
        environ = {"YOUTRACK_TOKEN": TOKEN, "YOUTRACK_BASE_URL": self.yt_url, **(env or {})}
        with mock.patch.dict(os.environ, environ), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = tool.main([*argv, "--config", config or self.config], today=TODAY)
        return code, out.getvalue(), err.getvalue()

    def run_json(self, *argv, **kwargs):
        code, out, err = self.run_tool(*argv, "--json", **kwargs)
        return code, json.loads(out), err

    def issue_posts(self):
        return [b for _, _, b in self.pc.writes("POST", f"/api/companies/{CID}/issues")]

    def label_posts(self):
        return [b for _, _, b in self.pc.writes("POST", f"/api/companies/{CID}/labels")]

    def wp_posts(self):
        return [b for _, _, b in self.pc.writes("POST", "/work-products")]


class CreateTests(Base):
    def test_single_ticket_lands_in_board_backlog_with_rule_project_and_policy(self):
        self.yt.add("DEV2-1", "회원 리스트 추출 요청")
        code, report, _ = self.run_json("DEV2-1")

        self.assertEqual(code, 0)
        result = report["results"][0]
        self.assertEqual((result["result"], result["issue"]), ("created", "ALA-1"))
        self.assertEqual(result["url"], f"{self.pc_url}/ALA/issues/ALA-1")
        self.assertEqual(result["rule"], {"matched": True, "index": 0, "project": "쇼핑 데이터 추출",
                                          "hit": "summary:추출"})
        [body] = self.issue_posts()
        self.assertEqual(body["title"], "DEV2-1 회원 리스트 추출 요청")
        self.assertEqual((body["status"], body["priority"], body["assigneeUserId"]),
                         ("backlog", "medium", "local-board"))
        self.assertNotIn("assigneeAgentId", body)
        self.assertEqual(body["projectId"], PID)
        self.assertEqual(body["executionWorkspaceSettings"], {"mode": "isolated_workspace"})
        self.assertEqual(body["executionPolicy"], {"mode": "normal", "commentRequired": True, "stages": [
            {"type": "review", "approvalsNeeded": 1, "participants": [{"type": "agent", "agentId": REVIEWER}]},
            {"type": "approval", "approvalsNeeded": 1, "participants": [{"type": "user", "userId": "local-board"}]},
        ]})
        self.assertIn(f"{self.yt_url}/issue/DEV2-1", body["description"])
        self.assertIn("회원 리스트 추출 요청", body["description"])
        self.assertIn("등록: 2026-10-22 티켓 지정", body["description"])
        self.assertNotIn(SECRET_DESCRIPTION, json.dumps(self.pc.requests, ensure_ascii=False))
        self.assertEqual(len(body["description"].splitlines()), 3)

    def test_rule_miss_creates_without_project_or_policy(self):
        self.yt.add("DEV2-2", "로그인 오류 문의")
        code, report, _ = self.run_json("DEV2-2")

        self.assertEqual(code, 0)
        self.assertEqual(report["results"][0]["rule"], {"matched": False})
        [body] = self.issue_posts()
        for key in ("projectId", "executionPolicy", "executionWorkspaceSettings"):
            self.assertNotIn(key, body)
        self.assertEqual((body["status"], body["assigneeUserId"]), ("backlog", "local-board"))

    def test_rule_by_tag_and_first_match_only(self):
        config = self.write_config(rules=[
            {"project": "기타 요청", "when": {"summaryAny": [], "tagsAny": ["데이터요청"]}},
            {"project": "쇼핑 데이터 추출", "when": {"summaryAny": ["추출"], "tagsAny": []}},
        ])
        self.yt.add("DEV2-3", "주문 추출", tags=("데이터요청",))
        code, report, _ = self.run_json("DEV2-3", config=config)

        self.assertEqual(code, 0)
        self.assertEqual(report["results"][0]["rule"]["hit"], "tag:데이터요청")
        self.assertEqual(self.issue_posts()[0]["projectId"], PID_OTHER)

    def test_multiple_tickets_dedupe_input(self):
        self.yt.add("DEV2-1", "엑셀 추출")
        self.yt.add("DEV2-2", "리스트 요청")
        code, report, _ = self.run_json("DEV2-1", "dev2-2", "DEV2-1")

        self.assertEqual(code, 0)
        self.assertEqual([(r["ticket"], r["result"], r["issue"]) for r in report["results"]],
                         [("DEV2-1", "created", "ALA-1"), ("DEV2-2", "created", "ALA-2")])
        self.assertEqual([b["title"] for b in self.issue_posts()], ["DEV2-1 엑셀 추출", "DEV2-2 리스트 요청"])


class IdempotencyTests(Base):
    def test_existing_non_cancelled_is_skipped_cancelled_is_not(self):
        self.pc.add_issue("DEV2-1 예전 제목", status="done")
        self.pc.add_issue("DEV2-2 취소된 시도", status="cancelled")
        self.pc.add_issue("DEV2-10 다른 티켓", status="todo")
        for iid in ("DEV2-1", "DEV2-2"):
            self.yt.add(iid, "추출 요청")
        code, report, _ = self.run_json("DEV2-1", "DEV2-2")

        self.assertEqual(code, 0)
        skipped, created = report["results"]
        self.assertEqual((skipped["result"], skipped["reason"]), ("skipped", "기존 ALA-1"))
        self.assertEqual((created["result"], created["issue"]), ("created", "ALA-4"))
        self.assertEqual([b["title"] for b in self.issue_posts()], ["DEV2-2 추출 요청"])

        code, report, _ = self.run_json("DEV2-1", "DEV2-2")  # 재실행 — 새로 만들지 않는다
        self.assertEqual([r["result"] for r in report["results"]], ["skipped", "skipped"])
        self.assertEqual(len(self.issue_posts()), 1)

    def test_prefix_needs_space_boundary(self):
        self.pc.add_issue("DEV2-10 다른 티켓")
        self.yt.add("DEV2-1", "추출")
        _, report, _ = self.run_json("DEV2-1")
        self.assertEqual(report["results"][0]["result"], "created")

    def test_existing_found_across_pages(self):
        for n in range(4):
            self.pc.add_issue(f"DEV2-{100 + n} 채움")
        self.pc.add_issue("DEV2-1 기존")
        self.yt.add("DEV2-1", "추출")
        with mock.patch.object(tool, "PC_PAGE", 2):
            _, report, _ = self.run_json("DEV2-1")
        self.assertEqual(report["results"][0]["result"], "skipped")


class DryRunTests(Base):
    def test_dry_run_shows_requests_and_writes_nothing(self):
        self.yt.add("DEV2-1", "엑셀 추출", tags=("쇼핑",))
        self.pc.add_issue("DEV2-5 기존")
        self.yt.add("DEV2-5", "추출")
        code, out, _ = self.run_tool("DEV2-1", "DEV2-5", "--dry-run")

        self.assertEqual(code, 0)
        self.assertEqual(self.pc.writes(), [])
        self.assertIn(PID, out)
        self.assertIn(REVIEWER, out)
        self.assertIn('"action": "would_create"', out)
        self.assertIn("요청자:김정민", out)
        self.assertIn("태그:쇼핑", out)
        self.assertIn('"hit": "summary:추출"', out)
        self.assertIn(f"{self.yt_url}/issue/DEV2-1", out)
        self.assertIn("--- DEV2-5 보낼 요청", out)  # skipped 이슈에 붙일 work product도 보인다
        self.assertIn("DEV2-5  skipped  ALA-1  기존 ALA-1", out)

    def test_dry_run_json_carries_rule_labels_and_work_product(self):
        self.yt.add("DEV2-1", "로그인 오류")
        _, report, _ = self.run_json("DEV2-1", "--dry-run")
        result = report["results"][0]
        self.assertEqual(result["result"], "dry_run")
        self.assertEqual(result["rule"], {"matched": False})
        self.assertEqual(result["request"]["workProduct"]["externalId"], "DEV2-1")
        self.assertEqual(self.pc.writes(), [])


class QueryTests(Base):
    def test_query_results_are_registered(self):
        self.yt.add("DEV2-1", "추출 A")
        self.yt.add("DEV2-2", "추출 B")
        self.yt.queries["tag: paperclip"] = ["DEV2-1", "DEV2-2"]
        code, report, _ = self.run_json("--query", "tag: paperclip")

        self.assertEqual(code, 0)
        self.assertEqual([r["result"] for r in report["results"]], ["created", "created"])
        self.assertIn("검색식 `tag: paperclip`", self.issue_posts()[0]["description"])

    def test_inbox_uses_config_query(self):
        config = self.write_config(inboxQuery="for: me #Unresolved project: DEV2 #테스트")
        self.yt.add("DEV2-7", "리스트")
        self.yt.queries["for: me #Unresolved project: DEV2 #테스트"] = ["DEV2-7"]
        code, report, _ = self.run_json("--inbox", config=config)

        self.assertEqual(code, 0)
        self.assertEqual(self.yt.seen_queries, ["for: me #Unresolved project: DEV2 #테스트"])
        self.assertEqual(report["query"], "for: me #Unresolved project: DEV2 #테스트")
        self.assertEqual(report["results"][0]["result"], "created")

    def test_query_over_cap_writes_nothing(self):
        for n in range(3):
            self.yt.add(f"DEV2-{n}", "추출")
        self.yt.queries["broad"] = ["DEV2-0", "DEV2-1", "DEV2-2"]
        code, report, _ = self.run_json("--query", "broad", "--max", "2")

        self.assertEqual(code, 1)
        self.assertIn("상한 2건", report["error"])
        self.assertEqual(self.pc.requests, [])

    def test_youtrack_is_only_read(self):
        self.yt.add("DEV2-1", "추출")
        self.run_tool("DEV2-1")
        self.assertEqual(self.yt.writes, [])


class ErrorTests(Base):
    def test_youtrack_404_is_per_ticket(self):
        self.yt.add("DEV2-1", "추출")
        code, report, _ = self.run_json("DEV2-404", "DEV2-1")

        self.assertEqual(code, 1)
        missing, created = report["results"]
        self.assertEqual((missing["result"], missing["reason"]), ("error", "YouTrack에 없음 (HTTP 404)"))
        self.assertEqual(created["result"], "created")

    def test_paperclip_connection_failure(self):
        self.yt.add("DEV2-1", "추출")
        config = self.write_config(baseUrl=f"http://127.0.0.1:{free_port()}")
        code, report, _ = self.run_json("DEV2-1", config=config)

        self.assertEqual(code, 1)
        self.assertEqual(report["results"][0]["result"], "error")
        self.assertIn("Paperclip 서버 응답 없음", report["results"][0]["reason"])
        self.assertIn("launchctl print gui/$(id -u)/com.team2.paperclip", report["results"][0]["reason"])

    def test_company_resolution_failure(self):
        self.yt.add("DEV2-1", "추출")
        code, report, _ = self.run_json("DEV2-1", config=self.write_config(company="없는 회사"))
        self.assertEqual(code, 1)
        self.assertIn("회사 '없는 회사' 없음", report["results"][0]["reason"])

    def test_rule_project_or_reviewer_missing_fails_only_that_ticket(self):
        config = self.write_config(rules=[{"project": "없는 프로젝트", "when": {"summaryAny": ["추출"]}}])
        self.yt.add("DEV2-1", "추출")
        self.yt.add("DEV2-2", "로그인 오류")
        code, report, _ = self.run_json("DEV2-1", "DEV2-2", config=config)

        self.assertEqual(code, 1)
        self.assertIn("프로젝트 '없는 프로젝트' 없음", report["results"][0]["reason"])
        self.assertEqual(report["results"][1]["result"], "created")

        self.yt.add("DEV2-3", "추출")
        missing_reviewer = {**POLICIES, "쇼핑 데이터 추출": {**SHOP, "stages": ["review:없는 리뷰어", "approval:local-board"]}}
        _, report, _ = self.run_json("DEV2-3", config=self.write_config(projects=missing_reviewer))
        self.assertIn("에이전트 '없는 리뷰어' 없음", report["results"][0]["reason"])

    def test_invalid_ticket_id(self):
        code, report, _ = self.run_json("DEV3-1")
        self.assertEqual(code, 1)
        self.assertEqual(report["results"][0]["reason"], "DEV2-#### 형식이 아니다")

    def test_project_flag_needs_tickets(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            tool.parse_args(["--inbox", "--project", "쇼핑 데이터 추출"])
        self.assertEqual(ctx.exception.code, 2)


class TokenTests(Base):
    def test_token_never_in_output(self):
        self.yt.add("DEV2-1", "추출")
        outputs = [
            self.run_tool("DEV2-1", "--dry-run"),
            self.run_tool("DEV2-1", "--dry-run", "--json"),
            self.run_tool("DEV2-404"),
            self.run_tool("DEV2-1", config=self.write_config(baseUrl=f"http://127.0.0.1:{free_port()}")),
            self.run_tool("DEV2-1"),
        ]
        for code, out, err in outputs:
            self.assertNotIn(TOKEN, out + err)
        self.assertIn(f"Bearer {TOKEN}", self.yt.seen_auth)
        for _, _, body in self.pc.requests:
            self.assertNotIn(TOKEN, json.dumps(body or {}))


class LabelTests(Base):
    def test_labels_created_once_and_reused(self):
        existing = self.pc.add_label("요청자:김정민")
        self.yt.add("DEV2-1", "추출", tags=("쇼핑",))
        self.yt.add("DEV2-2", "추출", tags=("쇼핑",))
        code, report, _ = self.run_json("DEV2-1", "DEV2-2")

        self.assertEqual(code, 0)
        self.assertEqual(self.label_posts(), [{"name": "태그:쇼핑", "color": "#2563EB"}])
        tag = next(lb for lb in self.pc.labels if lb["name"] == "태그:쇼핑")
        for body in self.issue_posts():
            self.assertEqual(body["labelIds"], [existing["id"], tag["id"]])
        self.assertEqual([lb["action"] for lb in report["results"][0]["labels"]], ["existing", "created"])
        self.assertEqual([lb["action"] for lb in report["results"][1]["labels"]], ["existing", "existing"])
        self.assertNotIn("jmkim", json.dumps(self.label_posts(), ensure_ascii=False))

    def test_long_names_are_clipped_to_48(self):
        long_tag = "가" * 60
        self.yt.add("DEV2-1", "추출", tags=(long_tag,))
        self.run_tool("DEV2-1")
        names = [b["name"] for b in self.label_posts()]
        self.assertEqual(names[1], "태그:" + "가" * 45)
        for name in names:
            self.assertLessEqual(len(name.encode("utf-16-le")) // 2, 48)

    def test_clip_label_counts_utf16_and_trims(self):
        self.assertEqual(tool.clip_label("태그:" + "😀" * 30), "태그:" + "😀" * 22)
        self.assertEqual(tool.clip_label("태그:" + "a" * 44 + " b"), "태그:" + "a" * 44)
        self.assertEqual(tool.clip_label("  요청자:  김 정민 "), "요청자: 김 정민")

    def test_no_tags_and_no_reporter(self):
        self.yt.add("DEV2-1", "추출", reporter=None)
        self.yt.add("DEV2-2", "추출", reporter=(None, "loginonly"))
        code, _, _ = self.run_tool("DEV2-1", "DEV2-2")
        self.assertEqual(code, 0)
        self.assertEqual(self.label_posts(), [])
        self.assertEqual([b["labelIds"] for b in self.issue_posts()], [[], []])


class WorkProductTests(Base):
    def test_created_issue_gets_youtrack_artifact(self):
        self.yt.add("DEV2-1", "추출")
        code, report, _ = self.run_json("DEV2-1")

        self.assertEqual(code, 0)
        self.assertEqual(self.wp_posts(), [{"type": "artifact", "provider": "youtrack", "externalId": "DEV2-1",
                                            "title": "YouTrack DEV2-1", "url": f"{self.yt_url}/issue/DEV2-1",
                                            "status": "active"}])
        self.assertEqual(report["results"][0]["workProduct"]["action"], "attached")

    def test_skipped_issue_gets_artifact_only_when_missing(self):
        with_wp = self.pc.add_issue("DEV2-1 기존")
        self.pc.work_products[with_wp["id"]] = [{"provider": "youtrack", "externalId": "DEV2-1"}]
        without = self.pc.add_issue("DEV2-2 기존")
        self.pc.work_products[without["id"]] = [{"provider": "github", "externalId": "DEV2-2"},
                                                {"provider": "youtrack", "externalId": "DEV2-9"}]
        self.yt.add("DEV2-1", "추출")
        self.yt.add("DEV2-2", "추출")
        code, report, _ = self.run_json("DEV2-1", "DEV2-2")

        self.assertEqual(code, 0)
        self.assertEqual([r["workProduct"]["action"] for r in report["results"]], ["exists", "attached"])
        self.assertEqual([b["externalId"] for b in self.wp_posts()], ["DEV2-2"])

        self.run_tool("DEV2-1", "DEV2-2")  # 재실행 — 중복 부착 없음
        self.assertEqual(len(self.wp_posts()), 1)


class ClassifyTests(Base):
    def test_project_flag_patches_existing_issue_then_is_idempotent(self):
        issue = self.pc.add_issue("DEV2-1 로그인 오류", status="backlog", assigneeUserId="local-board")
        self.yt.add("DEV2-1", "로그인 오류")
        code, report, _ = self.run_json("--project", "쇼핑 데이터 추출", "DEV2-1")

        self.assertEqual(code, 0)
        self.assertEqual(report["results"][0]["result"], "updated")
        [(_, path, patch)] = self.pc.writes("PATCH")
        self.assertEqual(path, f"/api/issues/{issue['id']}")
        self.assertEqual(sorted(patch), ["executionPolicy", "executionWorkspaceSettings", "projectId"])
        self.assertEqual(patch["projectId"], PID)
        self.assertEqual(patch["executionPolicy"]["stages"][0]["participants"], [{"type": "agent", "agentId": REVIEWER}])
        self.assertEqual(self.issue_posts(), [])

        code, report, _ = self.run_json("--project", "쇼핑 데이터 추출", "DEV2-1")
        self.assertEqual(code, 0)
        self.assertEqual((report["results"][0]["result"], report["results"][0]["reason"]),
                         ("unchanged", "이미 같은 프로젝트·정책"))
        self.assertEqual(len(self.pc.writes("PATCH")), 1)

    def test_project_flag_sends_only_differing_fields(self):
        self.pc.add_issue("DEV2-1 x", projectId=PID_OTHER, executionWorkspaceSettings={"mode": "isolated_workspace"},
                          executionPolicy=FakePaperclip.normalized(SHOP_POLICY))
        self.yt.add("DEV2-1", "x")
        self.run_tool("--project", "쇼핑 데이터 추출", "DEV2-1")
        [(_, _, patch)] = self.pc.writes("PATCH")
        self.assertEqual(patch, {"projectId": PID})

    def test_project_flag_refuses_while_run_or_review_is_live(self):
        self.pc.add_issue("DEV2-1 a", executionRunId="run-1")
        self.pc.add_issue("DEV2-2 b", executionState={"status": "pending", "currentStageId": "s"})
        self.yt.add("DEV2-1", "a")
        self.yt.add("DEV2-2", "b")
        code, report, _ = self.run_json("--project", "쇼핑 데이터 추출", "DEV2-1", "DEV2-2")

        self.assertEqual(code, 1)
        self.assertEqual([r["result"] for r in report["results"]], ["error", "error"])
        self.assertIn("진행 중 실행 있음 (run-1)", report["results"][0]["reason"])
        self.assertIn("검토 단계 진행 중", report["results"][1]["reason"])
        self.assertEqual(self.pc.writes("PATCH"), [])

    def test_project_flag_creates_when_missing(self):
        self.yt.add("DEV2-1", "로그인 오류")  # 규칙에는 안 맞지만 사람이 지정한 프로젝트를 쓴다
        code, report, _ = self.run_json("--project", "쇼핑 데이터 추출", "DEV2-1")

        self.assertEqual(code, 0)
        self.assertEqual(report["results"][0]["rule"]["hit"], "--project")
        [body] = self.issue_posts()
        self.assertEqual((body["projectId"], body["status"], body["assigneeUserId"]), (PID, "backlog", "local-board"))
        self.assertIn("executionPolicy", body)

    def test_project_flag_dry_run_and_unknown_project(self):
        self.pc.add_issue("DEV2-1 a")
        self.yt.add("DEV2-1", "a")
        code, out, _ = self.run_tool("--project", "쇼핑 데이터 추출", "DEV2-1", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn('"patch"', out)
        self.assertEqual(self.pc.writes(), [])

        code, report, _ = self.run_json("--project", "없는 프로젝트", "DEV2-1")
        self.assertEqual(code, 1)
        self.assertIn("프로젝트 '없는 프로젝트' 없음", report["results"][0]["reason"])


class ProjectPolicyTests(Base):
    def test_each_project_gets_its_own_policy_on_create(self):
        self.yt.add("DEV2-1", "로그인 오류")
        self.yt.add("DEV2-2", "결제 화면 개선")
        self.assertEqual(self.run_tool("--project", "쇼핑 데이터 추출", "DEV2-1")[0], 0)
        self.assertEqual(self.run_tool("--project", "티켓 분석", "DEV2-2")[0], 0)

        shop, prep = self.issue_posts()
        self.assertEqual((shop["projectId"], shop["executionWorkspaceSettings"], shop["executionPolicy"]),
                         (PID, {"mode": "isolated_workspace"}, SHOP_POLICY))
        self.assertEqual((prep["projectId"], prep["executionPolicy"]), (PID_PREP, PREP_POLICY))
        self.assertNotIn("executionWorkspaceSettings", prep)
        self.assertEqual((prep["status"], prep["assigneeUserId"]), ("backlog", "local-board"))

    def test_ticket_prep_patch_has_no_isolation_and_approval_only(self):
        issue = self.pc.add_issue("DEV2-1 결제 화면 개선", status="backlog", assigneeUserId="local-board")
        self.yt.add("DEV2-1", "결제 화면 개선")
        code, out, _ = self.run_tool("--project", "티켓 분석", "DEV2-1", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.pc.writes(), [])
        self.assertNotIn("isolated_workspace", out)

        code, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1")
        self.assertEqual((code, report["results"][0]["result"]), (0, "updated"))
        [(_, path, patch)] = self.pc.writes("PATCH")
        self.assertEqual(path, f"/api/issues/{issue['id']}")
        self.assertEqual(patch, {"projectId": PID_PREP, "executionPolicy": PREP_POLICY})

        _, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1")
        self.assertEqual(report["results"][0]["result"], "unchanged")
        self.assertEqual(len(self.pc.writes("PATCH")), 1)

    def test_moving_isolated_issue_to_ticket_prep_clears_isolation(self):
        self.pc.add_issue("DEV2-1 x", projectId=PID, executionWorkspaceSettings={"mode": "isolated_workspace"},
                          executionPolicy=FakePaperclip.normalized(SHOP_POLICY))
        self.yt.add("DEV2-1", "x")
        self.run_tool("--project", "티켓 분석", "DEV2-1")
        [(_, _, patch)] = self.pc.writes("PATCH")
        self.assertEqual(patch, {"projectId": PID_PREP, "executionWorkspaceSettings": None,
                                 "executionPolicy": PREP_POLICY})

        _, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1")
        self.assertEqual(report["results"][0]["result"], "unchanged")

    def test_policy_change_still_refused_while_review_is_live(self):
        self.pc.add_issue("DEV2-1 x", projectId=PID, executionState={"status": "changes_requested"})
        self.yt.add("DEV2-1", "x")
        code, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1")
        self.assertEqual(code, 1)
        self.assertIn("검토 단계 진행 중 (changes_requested)", report["results"][0]["reason"])
        self.assertEqual(self.pc.writes("PATCH"), [])

    def test_project_missing_from_config_is_error_and_writes_nothing(self):
        config = self.write_config(projects={"쇼핑 데이터 추출": SHOP},
                                   rules=[{"project": "기타 요청", "when": {"summaryAny": ["추출"]}}])
        self.pc.add_issue("DEV2-1 a")
        self.yt.add("DEV2-1", "a")
        self.yt.add("DEV2-2", "추출")
        code, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1", config=config)
        self.assertEqual(code, 1)
        self.assertIn("설정 projects에 프로젝트 '티켓 분석' 없음", report["results"][0]["reason"])

        code, report, _ = self.run_json("DEV2-2", config=config)  # 규칙의 project도 맵을 본다
        self.assertEqual(code, 1)
        self.assertIn("설정 projects에 프로젝트 '기타 요청' 없음", report["results"][0]["reason"])
        self.assertEqual(self.pc.writes(), [])

    def test_project_in_config_but_not_in_paperclip(self):
        self.pc.projects = [p for p in self.pc.projects if p["name"] != "티켓 분석"]
        self.pc.add_issue("DEV2-1 a")
        self.yt.add("DEV2-1", "a")
        code, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1", "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("Paperclip 프로젝트 '티켓 분석' 없음 — Paperclip에 만들거나", report["results"][0]["reason"])

    def test_invalid_policy_config_exits_2(self):
        self.yt.add("DEV2-1", "추출")
        for projects in ({}, {"티켓 분석": {"stages": ["approval:local-board"]}},
                         {"티켓 분석": {"isolatedWorkspace": "no", "stages": ["approval:local-board"]}},
                         {"티켓 분석": {**PREP, "stages": []}},
                         {"티켓 분석": {**PREP, "stages": ["reviewer:SQL Reviewer"]}},
                         {"티켓 분석": {**PREP, "stages": ["approval:"]}},
                         ["티켓 분석"]):
            code, out, err = self.run_tool("DEV2-1", config=self.write_config(projects=projects))
            self.assertEqual((code, out), (2, ""), projects)
            self.assertIn("projects", err)
        self.assertEqual(self.pc.requests, [])


class AssigneeTests(Base):
    def test_other_or_missing_assignee_is_refused_and_nothing_is_written(self):
        self.pc.add_issue("DEV2-3 기존")  # skipped 경로의 work product 부착도 하지 않는다
        self.yt.add("DEV2-1", "추출", assignee="someone")
        self.yt.add("DEV2-2", "추출", assignee=None)
        self.yt.add("DEV2-3", "추출", assignee="someone")
        code, report, _ = self.run_json("DEV2-1", "DEV2-2", "DEV2-3")

        self.assertEqual(code, 1)
        self.assertEqual([r["result"] for r in report["results"]], ["error"] * 3)
        self.assertTrue(report["results"][0]["reason"].startswith("담당자 불일치: someone"))
        self.assertTrue(report["results"][1]["reason"].startswith("담당자 불일치: (없음)"))
        self.assertIn(f"토큰 사용자 {ME}", report["results"][0]["reason"])
        self.assertEqual(self.pc.writes(), [])

    def test_mine_proceeds_others_refused_in_project_and_query_paths(self):
        self.pc.add_issue("DEV2-1 a")
        self.pc.add_issue("DEV2-2 b")
        self.yt.add("DEV2-1", "a")
        self.yt.add("DEV2-2", "b", assignee="someone")
        code, report, _ = self.run_json("--project", "티켓 분석", "DEV2-1", "DEV2-2")
        self.assertEqual(code, 1)
        self.assertEqual([r["result"] for r in report["results"]], ["updated", "error"])
        self.assertIn("담당자 불일치: someone", report["results"][1]["reason"])
        self.assertEqual(len(self.pc.writes("PATCH")), 1)

        self.yt.add("DEV2-5", "추출", assignee="someone")
        self.yt.add("DEV2-6", "추출")
        self.yt.queries["tag: paperclip"] = ["DEV2-5", "DEV2-6"]
        _, report, _ = self.run_json("--query", "tag: paperclip")
        self.assertEqual([r["result"] for r in report["results"]], ["error", "created"])
        self.assertEqual([b["title"] for b in self.issue_posts()], ["DEV2-6 추출"])

    def test_token_user_lookup_failure_refuses_all(self):
        self.yt.me = None
        self.yt.add("DEV2-1", "추출")
        code, out, err = self.run_tool("DEV2-1", "--json")
        report = json.loads(out)
        self.assertEqual(code, 1)
        self.assertIn("YouTrack 토큰 사용자 조회 실패 — HTTP 401", report["results"][0]["reason"])
        self.assertNotIn(TOKEN, out + err)
        self.assertEqual(self.pc.requests, [])


if __name__ == "__main__":
    unittest.main()
