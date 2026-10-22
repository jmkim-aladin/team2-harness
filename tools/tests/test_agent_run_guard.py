"""푸시·PR·YouTrack 게이트 회귀 — 임시 git fixture 만 쓴다. 원격·실제 설정에는 닿지 않는다."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("agent_run_guard", ROOT / "tools/agent_run_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
HOOK = ROOT / ".claude/hooks/agent-run-guard.sh"

YT_POST = ('BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"; '
           'AUTH="Authorization: Bearer $YOUTRACK_TOKEN"; '
           "curl -s -X POST -H \"$AUTH\" -H 'Content-Type: application/json' "
           "-d '{\"text\":\"done\"}' \"$BASE/api/issues/DEV2-1/comments?fields=id\"")
YT_GET = ('BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"; '
          'curl -s -G -H "Authorization: Bearer $YOUTRACK_TOKEN" '
          '--data-urlencode "query=tag: 2605-planned" "$BASE/api/issues"')
FEATURE = "feature/DEV2-1"


def agent(status=None):
    return {"PAPERCLIP_RUN_ID": "run-1", **({"PAPERCLIP_APPROVAL_STATUS": status} if status else {})}


class GuardFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        empty = self.tmp / "gitconfig"
        empty.write_text("", encoding="utf-8")
        # 개인 ~/.gitconfig 의 push.default 가 판정에 섞이지 않게 격리한다
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.feature_repo = self.repo("feat", FEATURE)
        self.develop_repo = self.repo("dev", "develop")
        self.plain = self.tmp / "plain"
        self.plain.mkdir()

    def repo(self, name, branch):
        path = self.tmp / name
        run = lambda *a: subprocess.run(["git", "-C", str(path), *a], check=True, capture_output=True)
        subprocess.run(["git", "init", "-q", "-b", branch, str(path)], check=True, capture_output=True)
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
        return path

    def decide(self, command, env, cwd=None, tool="Bash"):
        event = {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(cwd or self.plain)}
        return guard.decide(event, env)

    def reason(self, command, env, cwd=None):
        result = self.decide(command, env, cwd)
        self.assertIsNotNone(result, command)
        self.assertEqual(result[0], "deny")
        return result[1]


class PushMatrixTests(GuardFixture):
    """승인 상태 × 대상 브랜치 × 강제·삭제 형태."""

    def test_approval_by_target(self):
        targets = [  # (명령, cwd, 허용 여부)
            (f"git push -u origin {FEATURE}", None, True),
            (f"git push origin HEAD:{FEATURE}", None, True),
            (f"git push origin HEAD:refs/heads/{FEATURE}", None, True),
            ("git push origin develop", None, False),
            ("git push origin HEAD:main", None, False),
            ("git push origin HEAD", "feature", True),
            ("git push", "feature", True),
            ("git push origin HEAD", "develop", False),
            ("git push", "develop", False),
        ]
        for status in [None, "approved", "rejected"]:
            for command, where, allowed in targets:
                cwd = {"feature": self.feature_repo, "develop": self.develop_repo}.get(where)
                with self.subTest(status=status, command=command, cwd=where):
                    result = self.decide(command, agent(status), cwd)
                    if status == "approved" and allowed:
                        self.assertIsNone(result)
                    elif status != "approved":
                        self.assertIn("request_board_approval", result[1])
                    else:
                        self.assertIn("feature/* 외 브랜치", result[1])

    def test_force_and_delete_forms_denied_even_when_approved(self):
        forms = [f"git push -f origin {FEATURE}", f"git push --force origin {FEATURE}",
                 f"git push --force-with-lease origin {FEATURE}", f"git push -uf origin {FEATURE}",
                 f"git push --delete origin {FEATURE}", f"git push -d origin {FEATURE}",
                 "git push --mirror origin", "git push --all origin", "git push --tags origin",
                 f"git push --prune origin {FEATURE}", f"git push origin +{FEATURE}", f"git push origin :{FEATURE}"]
        for status in [None, "approved", "rejected"]:
            for command in forms:
                with self.subTest(status=status, command=command):
                    reason = self.reason(command, agent(status), self.feature_repo)
                    self.assertIn("강제·삭제" if status == "approved" else "request_board_approval", reason)

    def test_current_branch_resolution(self):
        ok = agent("approved")
        self.assertIsNone(self.decide(f"git -C {self.feature_repo} push", ok))
        self.assertIsNone(self.decide(f'cd "{self.feature_repo}" && git push -u origin HEAD', ok))
        self.assertIsNone(self.decide(f"git add . && git commit -m wip && rtk git push origin {FEATURE}", ok))
        self.assertIn("판정하지 못해", self.reason("git push", ok, self.plain))
        self.assertIn("판정하지 못해", self.reason('B=$(git branch --show-current); git push origin "$B"', ok))
        subprocess.run(["git", "-C", str(self.feature_repo), "checkout", "-q", "--detach"], check=True)
        self.assertIn("대상: HEAD", self.reason("git push origin HEAD", ok, self.feature_repo))

    def test_implicit_push_config_requires_explicit_refspec(self):
        subprocess.run(["git", "-C", str(self.feature_repo), "config", "push.default", "upstream"], check=True)
        self.assertIn("push.default=upstream", self.reason("git push", agent("approved"), self.feature_repo))
        self.assertIsNone(self.decide(f"git push origin HEAD:{FEATURE}", agent("approved"), self.feature_repo))

    def test_wrapped_push_denied(self):
        for command in [f"sh -c 'git push origin {FEATURE}'", f'eval "git push origin {FEATURE}"',
                        f'git commit -m "then git push" && git push origin {FEATURE}']:
            with self.subTest(command=command):
                self.assertIn("셸 래핑", self.reason(command, agent("approved"), self.feature_repo))

    def test_export_inside_command_does_not_grant_approval(self):
        command = f"export PAPERCLIP_APPROVAL_STATUS=approved && git push origin {FEATURE}"
        self.assertIn("request_board_approval", self.reason(command, agent(), self.feature_repo))


class PullRequestTests(GuardFixture):
    def test_create_requires_approval_draft_and_develop_base(self):
        cases = [("gh pr create --draft --base develop --fill", True), ("gh pr create -d -B develop -t x", True),
                 ("gh pr create --draft --base=develop", True), ("gh pr new --draft --base develop", True),
                 ("gh pr -R o/r create --draft --base develop", True),
                 (f"gh pr create --draft --base develop --head {FEATURE}", True),
                 ("gh pr create --base develop", False), ("gh pr create --draft", False),
                 ("gh pr create --draft --base main", False), ("gh pr create --fill", False),
                 ("gh pr create --draft --base develop --head main", False)]
        for status in [None, "approved", "rejected"]:
            for command, allowed in cases:
                with self.subTest(status=status, command=command):
                    result = self.decide(command, agent(status))
                    if status == "approved" and allowed:
                        self.assertIsNone(result)
                    else:
                        self.assertEqual(result[0], "deny")
                        if status != "approved":
                            self.assertIn("request_board_approval", result[1])
        self.assertIn("`--draft --base develop` 추가", self.reason("gh pr create --fill", agent("approved")))
        self.assertIn("셸 래핑", self.reason('bash -c "gh pr create --draft --base develop"', agent("approved")))

    def test_always_denied_even_when_approved(self):
        for command in ["gh pr merge 12 --squash", "gh pr merge --auto 12", "gh pr -R o/r merge 12",
                        "gh pr ready 12", "gh workflow run deploy.yml", "gh release create v1.0.0",
                        "gh api -X PUT repos/o/r/pulls/12/merge",
                        "gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'",
                        "gh api -X PATCH repos/o/r/git/refs/heads/main -f sha=abc",
                        "gh api repos/o/r/actions/workflows/deploy.yml/dispatches -f ref=develop",
                        "gh api repos/o/r/releases -f tag_name=v1", "gh api repos/o/r/pulls -f head=x -f base=main",
                        "gh pr review 12 --approve", "gh pr edit 12 --base main"]:
            with self.subTest(command=command):
                self.reason(command, agent("approved"))

    def test_review_and_comment_allowed(self):
        for status in [None, "approved"]:
            for command in ['gh pr review 12 --comment -b "LGTM 아님: 3건"', "gh pr comment 12 --body-file /tmp/r.md",
                            "gh api repos/o/r/pulls/12/reviews -f event=COMMENT -f body=x",
                            "gh api repos/{owner}/{repo}/issues/12/comments -f body=x",
                            "gh api repos/o/r/pulls/12/comments", "gh api repos/o/r/pulls/12",
                            "gh pr view 12", "gh pr diff 12", "gh pr checks 12", "gh pr edit 12 --title x",
                            "git status --short", "git commit -m 'feat: x'", "git stash push -m wip"]:
                with self.subTest(status=status, command=command):
                    self.assertIsNone(self.decide(command, agent(status)))


class YouTrackTests(GuardFixture):
    def test_writes_denied(self):
        for command in [YT_POST, YT_POST.replace("-X POST", "-XPOST"),
                        'curl -s -H "$AUTH" \\\n  -X POST "$YOUTRACK_BASE_URL/api/issues"',
                        'curl -s --request PUT "https://aladincommunication.youtrack.cloud/api/x"',
                        'python3 -c "import requests; requests.post(\'https://x.youtrack.cloud/api/issues\')"',
                        "python3 tools/ticket_schedule.py apply --plan /tmp/plan.json"]:
            with self.subTest(command=command):
                self.assertIn("YouTrack 쓰기 금지", self.reason(command, agent("approved")))

    def test_reads_allowed_and_human_session_untouched(self):
        for command in [YT_GET, "python3 tools/ticket_schedule.py apply --plan /tmp/p.json --dry-run",
                        "curl -s -X POST https://example.com/hook"]:
            with self.subTest(command=command):
                self.assertIsNone(self.decide(command, agent("approved")))
        self.assertIsNone(self.decide(YT_POST, {}))

    def test_mcp(self):
        event = lambda tool: {"tool_name": tool, "tool_input": {}}
        self.assertEqual(guard.decide(event("mcp__youtrack__create_issue"), agent("approved"))[0], "deny")
        self.assertIsNone(guard.decide(event("mcp__youtrack__get_issue"), agent("approved")))
        self.assertIsNone(guard.decide(event("mcp__youtrack__create_issue"), {}))


class ProductionDbTests(GuardFixture):
    """운영 DB 경로 — 승인 env 와 무관하게 막고, 소스 읽기와 개발 sqlcmd SELECT 는 지나간다."""

    DENY = [
        "python3 tools/db_prod_client.py status",
        "python3 /Users/x/team2/tools/db_prod_client.py prepare < /tmp/q.sql",
        "./tools/db_prod_client.py stop", "tools/db_prod_gateway.py", "python3 -u tools/db_prod_gateway.py",
        "sh -c 'python3 tools/db_query_control.py status'",
        'bash -lc "./tools/db_execute.py --task DEV2-1 --database WebCatalog"',
        "env PYTHONPATH=tools python3 tools/db_execute.py --task DEV2-1",
        "rtk proxy python3 tools/db_prod_client.py status", "timeout 30 python3 tools/db_prod_recovery.py",
        "cd tools && python3 db_prod_watchdog.py", "echo x | xargs python3 tools/db_prod_client.py",
        "python3 -m tools.db_prod_client status", "PYTHONPATH=tools python3 -m db_prod_diagnostics",
        "python3 - < tools/db_prod_client.py", "cat tools/db_prod_client.py | python3 -",
        "X=`python3 tools/db_prod_client.py status`", "uv run tools/db_prod_transport.py",
        "nc -U /tmp/team2-db-501/query.sock", 'socat - UNIX-CONNECT:"$TMPDIR/team2-db-501/query.sock"',
        "python3 -c \"import socket; s=socket.socket(socket.AF_UNIX); s.connect('/tmp/team2-db-501/query.sock')\"",
        "python3 tools/db_prod_client.py approve --from-chat-digest abc123", "some-tool --from-chat-digest abc",
        'python3 -c "import db_prod_client; db_prod_client.main()"', 'python3 -c "from tools import db_prod_gateway"',
        "python3 - <<'EOF'\nimport importlib.util\nspec = importlib.util.spec_from_file_location('c', "
        "'tools/db_prod_client.py')\nEOF",
        "node -e \"require('child_process').execSync('python3 tools/db_prod_client.py status')\"",
        "python3 -c \"import subprocess; subprocess.run(['python3', 'tools/db_prod_client.py', 'status'])\"",
        "swiftc tools/db_prod_keychain.swift -o /tmp/k",
        '"$HOME/Library/Application Support/team2-db/db-prod-keychain"',
    ]
    ALLOW = [
        "cat tools/db_prod_client.py", 'grep -n "def main" tools/db_prod_gateway.py',
        "sed -n 180,200p tools/db_prod_gateway.py", "rg -n SOCKET tools/db_prod_client.py tools/db_query_control.py",
        "wc -l tools/db_execute.py", "git diff tools/db_prod_gateway.py", "head -50 tools/db_prod_keychain.swift",
        "python3 -m pytest tools/tests/test_db_prod_gateway.py -q", "python3 tools/db_sqlcmd_guard.py < /tmp/e.json",
        "sqlcmd -S rds-cluster-cool-dev.cleuiesc8bqi.ap-northeast-2.rds.amazonaws.com -d WebCatalog -U u -C -b "
        "-Q 'SELECT TOP 1 name FROM sys.tables'",
    ]

    def test_execution_paths_denied_regardless_of_approval(self):
        for status in [None, "approved"]:
            for command in self.DENY:
                with self.subTest(status=status, command=command):
                    reason = self.reason(command, agent(status))
                    self.assertIn("운영 DB 경로 금지", reason)
                    self.assertIn("data-requests-dev2", reason)

    def test_source_reads_and_dev_select_pass(self):
        for command in self.ALLOW:
            with self.subTest(command=command):
                self.assertIsNone(self.decide(command, agent("approved")))

    def test_human_session_untouched(self):
        for command in self.DENY[:3] + ["nc -U /tmp/team2-db-501/query.sock"]:
            with self.subTest(command=command):
                self.assertIsNone(self.decide(command, {}))


class HumanSessionTests(GuardFixture):
    def test_push_and_pr_create_ask(self):
        for command in ["git push", f"git push origin {FEATURE}", "rtk git push", "gh pr create --fill",
                        "gh pr new", "gh pr -R o/r create", "cd x && git -C y push --force"]:
            with self.subTest(command=command):
                decision, reason = self.decide(command, {})
                self.assertEqual(decision, "ask")
                self.assertIn("사용자 확인", reason)

    def test_other_commands_silent(self):
        for command in ["git status", "gh pr merge 1", "gh pr view 1", "git stash push", YT_POST,
                        "echo 'unterminated"]:
            with self.subTest(command=command):
                self.assertIsNone(self.decide(command, {}))


class FailureModeTests(GuardFixture):
    def run_main(self, stdin, env):
        out = io.StringIO()
        base = {k: v for k, v in os.environ.items() if not k.startswith("PAPERCLIP_")}
        with mock.patch.dict(os.environ, {**base, **env}, clear=True), \
                mock.patch("sys.stdin", io.StringIO(stdin)), contextlib.redirect_stdout(out):
            guard.main()
        return out.getvalue()

    def test_agent_run_fails_closed_without_echoing(self):
        for payload in ["not-json-sensitive", "null", "{}", '{"tool_name":"Bash","tool_input":null}',
                        '{"tool_name":"Bash","tool_input":{"command":1}}']:
            with self.subTest(payload=payload):
                output = json.loads(self.run_main(payload, agent("approved")))["hookSpecificOutput"]
                self.assertEqual(output["permissionDecision"], "deny")
                self.assertIn("판정하지 못해", output["permissionDecisionReason"])
                self.assertNotIn("not-json-sensitive", output["permissionDecisionReason"])

    def test_internal_error_closed_for_agent_open_for_human(self):
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}})
        with mock.patch.object(guard, "decide", side_effect=RuntimeError("boom")):
            self.assertIn('"deny"', self.run_main(event, agent("approved")))
            self.assertEqual(self.run_main(event, {}), "")
        self.assertEqual(self.run_main("not-json push", {}), "")

    def test_wrapper_when_body_missing(self):
        broken = self.tmp / "broken/.claude/hooks"
        broken.mkdir(parents=True)
        shutil.copy2(HOOK, broken / HOOK.name)
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}})
        base = {k: v for k, v in os.environ.items() if not k.startswith("PAPERCLIP_")}
        run = lambda env: subprocess.run(["bash", str(broken / HOOK.name)], input=event, text=True,
                                         capture_output=True, env=env, check=True).stdout
        self.assertEqual(json.loads(run({**base, **agent()}))["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(run(base), "")


class HookProtocolTests(GuardFixture):
    """실제 진입점(.sh)으로 Claude Code 훅 입출력을 재현한다."""

    def run_hook(self, command, env, cwd=None):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command},
                 "cwd": str(cwd or self.feature_repo), "transcript_path": "/Users/x/.claude/projects/p/s.jsonl"}
        base = {k: v for k, v in os.environ.items() if not k.startswith("PAPERCLIP_")}
        result = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), text=True, capture_output=True,
                                env={**base, **env}, check=True)
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] if result.stdout else None

    def test_matrix(self):
        cases = [  # (명령, 사람 세션, 승인 전 에이전트, 승인 후 에이전트)
            (f"git push -u origin {FEATURE}", "ask", "deny", None),
            ("git push origin develop", "ask", "deny", "deny"),
            ("gh pr create --draft --base develop", "ask", "deny", None),
            ("gh pr merge 7 --squash", None, "deny", "deny"),
            (YT_POST, None, "deny", "deny"),
            ("python3 tools/db_prod_client.py status", None, "deny", "deny"),
            ("git status --short", None, None, None),
        ]
        for command, human, pending, approved in cases:
            for label, env, want in [("human", {}, human), ("pending", agent("pending"), pending),
                                     ("approved", agent("approved"), approved)]:
                with self.subTest(command=command, session=label):
                    self.assertEqual(self.run_hook(command, env), want)

    def test_human_prefilter_skips_python(self):
        broken = self.tmp / "broken/.claude/hooks"
        broken.mkdir(parents=True)
        shutil.copy2(HOOK, broken / HOOK.name)
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"},
                            "transcript_path": "/Users/x/.claude/projects/p/s.jsonl"})
        base = {k: v for k, v in os.environ.items() if not k.startswith("PAPERCLIP_")}
        with mock.patch.dict(os.environ, {}):
            result = subprocess.run(["bash", "-x", str(broken / HOOK.name)], input=event, text=True,
                                    capture_output=True, env=base, check=True)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("python3", result.stderr)  # 접두 필터에서 끝난다


if __name__ == "__main__":
    unittest.main()
