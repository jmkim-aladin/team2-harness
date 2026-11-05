#!/usr/bin/env python3
"""Q4: the whole operator flow with real processes against an owned loopback SQL Server.

Real immutable runtime bundle -> real gateway ``serve`` process -> real client
CLI processes -> host sqlcmd -> disposable Docker SQL Server.  Only three
seams are replaced, all inside child processes:

* HOME points to a private temporary directory, so the state ledger, stop.d,
  locks and worker journals never touch the production executor's files.
* ``SOCKET`` points to a private temporary socket, never ``/tmp/team2-db-<uid>``.
* The Keychain vault returns the fixture's ``sa`` credentials, and every sqlcmd
  stdin is teed to a file so the bytes actually sent can be compared with the
  SQL text the review displayed.

No production profile, Keychain item, socket, ledger or database is used.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[2]
sys.path.insert(0, str(HERE))
from go_transport import LoopbackLab  # noqa: E402  (also puts tools/ on sys.path)
from verify import DEFAULT_IMAGE  # noqa: E402
from db_prod_runtime import build_bundle  # noqa: E402
from db_query_control import Store  # noqa: E402

CHILD_PATH = "/usr/bin:/bin:/opt/homebrew/bin"
PRODUCTION_SOCKET = Path("/tmp") / ("team2-db-" + str(os.getuid())) / "query.sock"

GATEWAY_CHILD = r"""
import itertools, json, subprocess, sys
from pathlib import Path
bundle, sock, fixture, sent = sys.argv[1:5]
sys.path.insert(0, bundle)
import db_prod_transport as t
import db_prod_gateway as g
f = json.loads(Path(fixture).read_text())
creds = t.Credentials(f["host"], f["port"], f["account"], f["password"])
class Vault:
    def __init__(self, *args, **kwargs): pass
    def profile(self, target, *, observer=False):
        return dict(host=f["host"], port=f["port"], account=f["account"])
    def credentials(self, target, expected, *, observer=False):
        assert expected == self.profile(target)
        return creds
counter = itertools.count()
class Tee:
    def __init__(self, raw, path): self.raw, self.path = raw, path
    def write(self, data):
        written = self.raw.write(data)
        if isinstance(written, int) and written > 0:
            with open(self.path, "ab") as handle: handle.write(bytes(data[:written]))
        return written
    def __getattr__(self, name): return getattr(self.raw, name)
def popen(argv, **kwargs):
    process = subprocess.Popen(argv, **kwargs)
    stem = "%04d-%d" % (next(counter), process.pid)
    (Path(sent) / (stem + ".bin")).touch()
    tag = argv[argv.index("-H") + 1] if "-H" in argv else ""
    (Path(sent) / (stem + ".json")).write_text(json.dumps(dict(pid=process.pid, host_tag=tag)))
    process.stdin = Tee(process.stdin, Path(sent) / (stem + ".bin"))
    return process
class Recording(t.SqlcmdBackend):
    def __init__(self, *args, **kwargs):
        kwargs["popen_factory"] = popen
        super().__init__(*args, **kwargs)
t.SqlcmdBackend = Recording
g.LocalKeychain = Vault
g.SOCKET = Path(sock)
assert str(g.STATE).startswith(f["home"]) and str(g.LATCH).startswith(f["home"])
g.serve()
"""

CLIENT_CHILD = r"""
import json, sys
from pathlib import Path
bundle, sock, home = sys.argv[1:4]
sys.path.insert(0, bundle)
import db_prod_client as c
c.SOCKET = sock
assert str(c.STATE).startswith(home)
if sys.argv[4] == "--rpc":
    print(json.dumps(c.rpc(json.loads(sys.argv[5])), ensure_ascii=False, indent=2))
    raise SystemExit(0)
sys.argv = ["db_prod_client.py"] + sys.argv[4:]
raise SystemExit(c.main())
"""


def final_json(text):
    """Every client command ends with ``json.dumps(result, indent=2)``."""
    start = text.rfind("\n{\n")
    start = 0 if start < 0 and text.startswith("{\n") else start + 1
    return json.loads(text[start:])


def review_field(text, name):
    for line in text.splitlines():
        if line.startswith(name + ": "):
            return json.loads(line[len(name) + 2:])
    raise KeyError(name)


class Flow:
    def __init__(self, lab, root):
        self.lab, self.root = lab, root
        self.home = root / "home"
        self.state = self.home / "Library/Application Support/team2-db"
        self.sock = root / "q.sock"
        self.sent = root / "sent"
        self.fixture = root / "fixture.json"
        self.gateway = None
        self.results = []
        self.recovery_pieces = []

    # -- environment ----------------------------------------------------
    def prepare(self):
        self.state.mkdir(parents=True, mode=0o700)
        for path in (self.home, self.home / "Library", self.state.parent, self.state):
            path.chmod(0o700)
        self.sent.mkdir(mode=0o700)
        Store.initialize(self.state / "control.sqlite3")
        (self.state / "config.json").write_text(json.dumps(dict(
            allowed_uids=[os.getuid()],
            targets={"lego-prod": dict(enabled=True, read_only_verified=True)})))
        (self.state / "config.json").chmod(0o600)
        self.bundle = Path(build_bundle(str(TOOLS), str(self.root / "runtime")))
        host_port = self.lab.host_port()
        fd = os.open(self.fixture, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(dict(host="127.0.0.1", port=host_port, account="sa",
                           password=self.lab.passwords["sa"], home=str(self.home)), handle)

    def env(self):
        return {"HOME": str(self.home), "PATH": CHILD_PATH}

    def start_gateway(self):
        self.sock.unlink(missing_ok=True)
        self.gateway = subprocess.Popen(
            [sys.executable, "-I", "-c", GATEWAY_CHILD, str(self.bundle), str(self.sock),
             str(self.fixture), str(self.sent)],
            env=self.env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.gateway.poll() is not None:
                raise RuntimeError("gateway exited: " + self.gateway.stderr.read().decode(errors="replace")[-2000:])
            if self.sock.exists():
                try:
                    with socket.socket(socket.AF_UNIX) as probe:
                        probe.connect(str(self.sock))
                    return
                except OSError:
                    pass
            time.sleep(0.05)
        raise RuntimeError("gateway did not boot")

    def stop_gateway(self, sig=signal.SIGTERM):
        if self.gateway and self.gateway.poll() is None:
            self.gateway.send_signal(sig)
            try:
                self.gateway.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.gateway.kill()
                self.gateway.wait(timeout=10)

    def cli_args(self, *args):
        return [sys.executable, "-I", "-c", CLIENT_CHILD, str(self.bundle), str(self.sock), str(self.home), *args]

    def cli(self, *args, stdin=None, timeout=90):
        done = subprocess.run(self.cli_args(*args), env=self.env(), input=stdin, text=True,
                              capture_output=True, timeout=timeout)
        return done.returncode, done.stdout, done.stderr

    def cli_bg(self, *args):
        return subprocess.Popen(self.cli_args(*args), env=self.env(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)

    def rpc(self, request):
        code, out, err = self.cli("--rpc", json.dumps(request))
        if code:
            raise RuntimeError("rpc failed: " + err[-500:])
        return json.loads(out)

    def status(self):
        return self.rpc(dict(action="status"))

    # -- review / run ---------------------------------------------------
    def preview_csv(self, select, columns, *, max_file_bytes=1 << 20, timeout=30):
        code, out, err = self.cli("preview", "--target", "lego-prod", "--database", "master", "--timeout", str(timeout),
                                  "--output", "csv", "--columns", columns, "--purpose", "Q4 E2E 검증",
                                  "--max-file-bytes", str(max_file_bytes), stdin=select)
        if code:
            raise RuntimeError("csv preview failed: " + (out + err)[-1500:])
        review = final_json(out)["review"]
        return dict(text=out, review=review, id=review["request_id"], digest=review["approval_digest"],
                    actions=review["selected_actions"], tag=review["host_tag"],
                    directory=Path(review["export_spec"]["artifact_directory"]))

    def exports(self):
        root = self.state / "exports"
        return sorted(p.name for p in root.iterdir()) if root.exists() else []

    def preview(self, sql, timeout=30):
        code, out, err = self.cli("preview", "--target", "lego-prod", "--database", "master",
                                  "--timeout", str(timeout), stdin=sql)
        if code:
            raise RuntimeError("preview failed: " + (out + err)[-1500:])
        result = final_json(out)
        review = result["review"]
        return dict(text=out, review=review, id=review_field(out, "request_id"),
                    digest=review_field(out, "approval_digest"),
                    actions=review_field(out, "selected_actions"), tag=review_field(out, "host_tag"))

    def run(self, preview, digest=None):
        code, out, err = self.cli("run", preview["id"], "--from-chat-digest", digest or preview["digest"])
        try:
            return code, final_json(out), err
        except (ValueError, json.JSONDecodeError):
            return code, None, err

    # -- evidence -------------------------------------------------------
    def sent_entries(self):
        entries = []
        for meta in sorted(self.sent.glob("*.json")):
            data = json.loads(meta.read_text())
            data["bytes"] = meta.with_suffix(".bin").read_bytes()
            entries.append(data)
        return entries

    def wait_dispatch(self, sql, timeout=20):
        needle = sql.encode()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for entry in self.sent_entries():
                if needle in entry["bytes"]:
                    return entry
            time.sleep(0.05)
        raise RuntimeError("approved SQL was never dispatched")

    def sends_of(self, sql):
        return sum(entry["bytes"].count(sql.encode()) for entry in self.sent_entries())

    def sessions(self, tag):
        return int(self.lab.scalar(
            "SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE host_name = N'" + tag + "';"))

    def wait_sessions_closed(self, tag, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.sessions(tag) == 0:
                return True
            time.sleep(1)
        return False

    def wait_job(self, request_id, timeout=60):
        deadline = time.monotonic() + timeout
        status = None
        while time.monotonic() < deadline:
            status = self.rpc(dict(action="job_status", request_id=request_id))
            if status.get("job_state") not in ("admitting", "starting", "dispatching", "running", "finishing"):
                return status
            time.sleep(0.2)
        return status

    def recover(self):
        """Prepare, show, approve once and run the recovery observer through the CLI."""
        code, out, err = self.cli("recovery-prepare")
        review = final_json(out)["review"]
        recovery_id, digest = review["recovery_request_id"], review["digest"]
        code, shown, err = self.cli("recovery-review", recovery_id)
        if review_field(shown, "digest") != digest:
            raise RuntimeError("recovery review changed between prepare and display")
        self.recovery_pieces.append((review["observer_sql"], shown))
        code, out, err = self.cli("recovery-approve", recovery_id, "--from-chat-digest", digest)
        approved = final_json(out)
        code, out, err = self.cli("recovery-execute", recovery_id)
        executed = final_json(out)
        return dict(approved=approved, executed=executed)

    def check(self, name, passed, **evidence):
        self.results.append(dict(name=name, passed=bool(passed), **evidence))
        print(("PASS " if passed else "FAIL ") + name, flush=True)

    def displayed_only(self, previews):
        """Every byte sent to any sqlcmd stdin is one of the SQL texts a review displayed."""
        pieces = set()
        for p in previews:
            review = p["review"]
            pieces.update([review["sql"], review["control_sql"]["setup_sql"], review["control_sql"]["observer_sql"]])
            for piece in (review["sql"], review["control_sql"]["setup_sql"], review["control_sql"]["observer_sql"]):
                if json.dumps(piece, ensure_ascii=False) not in p["text"] and json.dumps(piece) not in p["text"]:
                    return False, "review text omits a SQL piece"
        for piece, text in self.recovery_pieces:
            if json.dumps(piece, ensure_ascii=False) not in text:
                return False, "recovery review omits its observer SQL"
            pieces.add(piece)
        ordered = sorted((piece.encode() for piece in pieces if piece), key=len, reverse=True)
        for entry in self.sent_entries():
            rest = entry["bytes"]
            while rest:
                for piece in ordered:
                    if rest.startswith(piece):
                        rest = rest[len(piece):]
                        break
                else:
                    return False, "undisplayed bytes sent: " + rest[:80].decode(errors="replace")
        return True, "ok"


def scenarios(flow):
    previews = []
    flow.start_gateway()
    s = flow.status()
    flow.check("boot: gateway starts halted without any DB connection",
               s["halted"] and s["reason"] == "service_started_requires_operator_resume"
               and s["active"] is None and not flow.sent_entries(), status=s)

    # 1. resume-required -> one approval -> one execution
    sql = "SELECT N'q4-재개' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    flow.check("resume preview selects execute_once + resume_current_stop, connects nothing",
               p["actions"] == ["execute_once", "resume_current_stop"] and not flow.sent_entries(), actions=p["actions"])
    code, result, _ = flow.run(p)
    s = flow.status()
    flow.check("resume + run: one approval resumes and returns the result",
               code == 0 and result and "q4-재개" in result.get("output", "") and not s["halted"]
               and flow.sends_of(sql) == 1, job_state=result and result.get("job_state"), status=s)

    # 2. ready -> execute only
    sql = "SELECT N'q4-준비' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    flow.check("ready preview selects execute_once only", p["actions"] == ["execute_once"], actions=p["actions"])
    code, result, _ = flow.run(p)
    flow.check("ready run returns result once", code == 0 and "q4-준비" in result.get("output", "")
               and flow.sends_of(sql) == 1)
    ready = p

    # 3. duplicate submit of a consumed approval
    before = len(flow.sent_entries())
    code, result, _ = flow.run(ready)
    flow.check("duplicate submit never re-executes", flow.sends_of("SELECT N'q4-준비' AS v;\n") == 1
               and len(flow.sent_entries()) == before, exit=code, result=result)

    # 4. changed SQL: approval digest of B presented for A (client and gateway)
    a = flow.preview("SELECT N'q4-변경A' AS v;\n"); previews.append(a)
    b = flow.preview("SELECT N'q4-변경B' AS v;\n"); previews.append(b)
    code, _, err = flow.run(a, digest=b["digest"])
    raw = flow.rpc(dict(action="approve_submit", request_id=a["id"], approval_digest=b["digest"],
                        selected_actions=a["actions"], approval_source="explicit-user-chat"))
    flow.check("changed SQL: mismatched approval refused by client and gateway, nothing sent",
               code != 0 and not raw.get("ok") and flow.sends_of("q4-변경") == 0, gateway=raw)

    # 5. a new stop after review invalidates the approval
    c = flow.preview("SELECT N'q4-경쟁' AS v;\n"); previews.append(c)
    flow.cli("stop")
    code, result, _ = flow.run(c)
    flow.check("new stop after review: approval refused, nothing sent",
               code != 0 and flow.sends_of("q4-경쟁") == 0, result=result)

    # 5b. CSV export: the generated batch is reviewed, run once, and published once
    select = ("SELECT v.id, v.s, v.n FROM (VALUES (CAST(2 AS bigint), N'a,\"b\"' + NCHAR(13) + NCHAR(10) + N'한글', "
              "CAST(NULL AS int)), (CAST(1 AS bigint), N'\\N', 0)) AS v(id, s, n) ORDER BY v.id")
    p = flow.preview_csv(select, "id:number,s:string,n:number"); previews.append(p)
    code, result, _ = flow.run(p)
    export = (result or {}).get("export") or {}
    final = p["directory"]
    rows = []
    if (final / "data.csv").is_file():
        rows = list(csv.reader(io.StringIO((final / "data.csv").read_bytes().decode("utf-8"), newline="")))
    manifest = json.loads((final / "manifest.json").read_text()) if (final / "manifest.json").is_file() else {}
    parts = dict(exit0=code == 0, exported=export.get("state") == "exported", action="export_csv" in p["actions"],
                 values=rows == [["id", "s", "n"], ["1", "\\\\N", "0"], ["2", 'a,"b"\r\n한글', "\\N"]],
                 manifest=manifest.get("spec_digest") == p["review"]["export_spec_digest"] and manifest.get("records") == 2,
                 private=oct(final.stat().st_mode & 0o777) == "0o700" if final.exists() else False,
                 batch_once=flow.sends_of(p["review"]["sql"]) == 1, no_staging=flow.exports() == [p["id"]])
    flow.check("csv export: reviewed batch runs once, values preserved, private artifact published",
               all(parts.values()), parts=parts, exit=code, export=export)

    # 5c. CSV file limit: refused while streaming, nothing published, block kept
    p = flow.preview_csv(select, "id:number,s:string,n:number", max_file_bytes=12); previews.append(p)
    code, result, _ = flow.run(p)
    s = flow.status()
    parts = dict(exit_nonzero=code != 0, failed=((result or {}).get("export") or {}).get("state") == "failed",
                 nothing=not p["directory"].exists() and len(flow.exports()) == 1,
                 closed=flow.wait_sessions_closed(p["tag"]), blocked=s["halted"])
    flow.check("csv file limit: refused mid-stream, no artifact, session closed, block kept",
               all(parts.values()), parts=parts, exit=code, status=s)

    # 5d. existing destination: never overwritten
    p = flow.preview_csv(select, "id:number,s:string,n:number"); previews.append(p)
    p["directory"].mkdir(mode=0o700)
    (p["directory"] / "mine.txt").write_text("keep")
    code, result, _ = flow.run(p)
    export = (result or {}).get("export") or {}
    parts = dict(exit_nonzero=code != 0, not_published=export.get("state") == "not_published",
                 reason=export.get("reason") == "destination_exists",
                 untouched=sorted(x.name for x in p["directory"].iterdir()) == ["mine.txt"],
                 no_staging=not any(name.startswith(".staging") for name in flow.exports()))
    flow.check("csv existing destination: left untouched, nothing published", all(parts.values()), parts=parts)

    # 5e. user stop during a long CSV query
    heavy = ("SELECT COUNT_BIG(*) AS c FROM sys.all_objects AS a CROSS JOIN sys.all_objects AS b "
             "CROSS JOIN sys.all_objects AS c")
    p = flow.preview_csv(heavy, "c:number"); previews.append(p)
    proc = flow.cli_bg("run", p["id"], "--from-chat-digest", p["digest"])
    flow.wait_dispatch(p["review"]["sql"])
    flow.cli("stop")
    out, _ = proc.communicate(timeout=60)
    result = final_json(out)
    parts = dict(exit_nonzero=proc.returncode != 0, failed=(result.get("export") or {}).get("state") == "failed",
                 nothing=not p["directory"].exists() and not any(n.startswith(".staging") for n in flow.exports()),
                 closed=flow.wait_sessions_closed(p["tag"]))
    flow.check("csv user stop: cancelled, staging removed, nothing published", all(parts.values()),
               parts=parts, job_state=result.get("job_state"))

    # 6. response loss: client dies after submit, job keeps ownership, same ID resumes
    sql = "WAITFOR DELAY '00:00:06';\nSELECT N'q4-유실' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    proc = flow.cli_bg("run", p["id"], "--from-chat-digest", p["digest"])
    flow.wait_dispatch(sql)
    os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=10)
    status = flow.wait_job(p["id"])
    code, out, _ = flow.cli("result", p["id"])
    fetched = final_json(out)
    flow.check("client loss: job completes, same-ID result delivered, SQL sent once",
               status.get("job_state") == "completed" and "q4-유실" in fetched.get("output", "")
               and flow.sends_of(sql) == 1 and flow.wait_sessions_closed(p["tag"]),
               job_state=status.get("job_state"), result_state=fetched.get("result_state"))

    # 7. user stop during execution
    sql = "WAITFOR DELAY '00:00:25';\nSELECT N'q4-취소' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    proc = flow.cli_bg("run", p["id"], "--from-chat-digest", p["digest"])
    flow.wait_dispatch(sql)
    started = time.monotonic()
    flow.cli("stop")
    out, _ = proc.communicate(timeout=60)
    elapsed = time.monotonic() - started
    result = final_json(out)
    s = flow.status()
    parts = dict(fast=elapsed < 15, no_result="q4-취소" not in result.get("output", ""),
                 job_failed=result.get("job_state") == "failed", closed=flow.wait_sessions_closed(p["tag"]),
                 ready=s["active"] is None and s["phase"] == "idle" and not s["halted"],
                 sent_once=flow.sends_of(sql) == 1)
    flow.check("user stop: cancelled quickly, server session closed, auto-ready, no result",
               all(parts.values()), parts=parts, elapsed=round(elapsed, 2), exit=proc.returncode, status=s)

    # 8. timeout keeps the block; next review carries the resume action
    sql = "WAITFOR DELAY '00:00:25';\nSELECT N'q4-시간' AS v;\n"
    p = flow.preview(sql, timeout=3); previews.append(p)
    started = time.monotonic()
    code, result, _ = flow.run(p)
    elapsed = time.monotonic() - started
    s = flow.status()
    nxt = flow.preview("SELECT N'q4-다음' AS v;\n"); previews.append(nxt)
    parts = dict(job_failed=(result or {}).get("job_state") == "failed", bounded=elapsed < 20,
                 no_result="q4-시간" not in (result or {}).get("output", ""),
                 closed=flow.wait_sessions_closed(p["tag"]), blocked=s["halted"] and s["active"] is None,
                 next_has_resume="resume_current_stop" in nxt["actions"], sent_once=flow.sends_of(sql) == 1)
    flow.check("timeout: fails within the bound, session closed, block kept, next review includes resume",
               all(parts.values()), parts=parts, elapsed=round(elapsed, 2), exit=code, status=s)

    # 9. worker (sqlcmd) process loss
    sql = "WAITFOR DELAY '00:00:20';\nSELECT N'q4-작업자' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    proc = flow.cli_bg("run", p["id"], "--from-chat-digest", p["digest"])
    worker = flow.wait_dispatch(sql)
    os.kill(worker["pid"], signal.SIGKILL)
    out, _ = proc.communicate(timeout=90)
    s = flow.status()
    job = flow.rpc(dict(action="job_status", request_id=p["id"]))
    parts = dict(no_result="q4-작업자" not in final_json(out).get("output", ""), sent_once=flow.sends_of(sql) == 1,
                 blocked=s["halted"], not_success=job.get("job_state") != "completed")
    flow.check("worker loss: no rerun, not reported as success, block kept",
               all(parts.values()), parts=parts, exit=proc.returncode, job_state=job.get("job_state"), status=s)
    flow.check("worker loss: server session eventually closed",
               flow.wait_sessions_closed(p["tag"], timeout=40))
    recovery = None
    if s["active"] is not None:
        recovery = flow.recover()
        s = flow.status()
        flow.check("worker loss recovery: displayed observer approved once, slot released, block kept",
                   s["active"] is None and s["phase"] == "idle" and s["halted"],
                   recovery=dict(approved=recovery["approved"], executed=recovery["executed"]), status=s)

    # 10. gateway (executor) loss mid-query, then a launchd-style restart
    sql = "WAITFOR DELAY '00:00:20';\nSELECT N'q4-실행기' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    proc = flow.cli_bg("run", p["id"], "--from-chat-digest", p["digest"])
    flow.wait_dispatch(sql)
    flow.stop_gateway(signal.SIGKILL)
    out, _ = proc.communicate(timeout=90)
    closed = flow.wait_sessions_closed(p["tag"], timeout=40)
    flow.start_gateway()
    s = flow.status()
    job = flow.rpc(dict(action="job_status", request_id=p["id"]))
    parts = dict(blocked=s["halted"], not_success=job.get("job_state") != "completed",
                 recovery=job.get("job_state") == "recovery_required", sent_once=flow.sends_of(sql) == 1,
                 client_no_result="q4-실행기" not in (out.rsplit("\n{\n", 1)[-1] if "\n{\n" in out else ""))
    flow.check("gateway loss: restart is halted, job not completed, no rerun",
               all(parts.values()), parts=parts, exit=proc.returncode, job=job, status=s)
    flow.check("gateway loss: watchdog fences the orphaned server session", closed)
    if s["active"] is not None:
        refused = flow.cli("preview", "--target", "lego-prod", "--database", "master", "--timeout", "5",
                           stdin="SELECT 1 AS v;\n")
        flow.check("gateway loss: new work is refused until recovery", refused[0] != 0)
        recovery = flow.recover()
        s = flow.status()
        flow.check("gateway loss recovery: slot released through approved observer, block kept",
                   s["active"] is None and s["phase"] == "idle" and s["halted"],
                   recovery=dict(approved=recovery["approved"], executed=recovery["executed"]), status=s)

    # 10b. gateway loss during a CSV export: restart reconciles, never publishes staging
    s = flow.status()
    p = flow.preview_csv(heavy, "c:number", timeout=60); previews.append(p)
    sent_before = flow.sends_of(p["review"]["sql"])  # 5e ran the same generated batch
    proc = flow.cli_bg("run", p["id"], "--from-chat-digest", p["digest"])
    flow.wait_dispatch(p["review"]["sql"])
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not any(n.startswith(".staging") for n in flow.exports()):
        time.sleep(0.05)
    staged = any(n.startswith(".staging") for n in flow.exports())
    flow.stop_gateway(signal.SIGKILL)
    proc.communicate(timeout=90)
    closed = flow.wait_sessions_closed(p["tag"], timeout=40)
    flow.start_gateway()
    job = flow.rpc(dict(action="job_status", request_id=p["id"]))
    export = job.get("export") or {}
    parts = dict(staged_before_kill=staged, fenced=closed, export_failed=export.get("state") == "failed",
                 reconciled=export.get("reason") == "gateway_restarted",
                 nothing=not p["directory"].exists() and not any(n.startswith(".staging") for n in flow.exports()),
                 not_success=job.get("job_state") != "completed",
                 sent_once=flow.sends_of(p["review"]["sql"]) - sent_before == 1)
    flow.check("csv gateway loss: restart discards staging, publishes nothing, no rerun",
               all(parts.values()), parts=parts, job=job)
    if flow.status()["active"] is not None:
        flow.recover()

    # 11. after all failures, the normal one-approval path still works and nothing was replayed
    sql = "SELECT N'q4-마지막' AS v;\n"
    p = flow.preview(sql); previews.append(p)
    code, result, _ = flow.run(p)
    flow.check("final: one approval resumes and runs after recovery",
               code == 0 and "q4-마지막" in result.get("output", "") and flow.sends_of(sql) == 1)
    exits = {r["name"].split(":")[0]: r.get("exit") for r in flow.results
             if r["name"].startswith(("user stop:", "timeout:", "worker loss: no rerun"))}
    flow.check("failed jobs exit nonzero (Q4 finding 1 fixed)",
               len(exits) == 3 and all(code not in (0, None) for code in exits.values()), exits=exits)
    ok, why = flow.displayed_only(previews)
    flow.check("every byte sent to sqlcmd was displayed in a review", ok, reason=why,
               processes=len(flow.sent_entries()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    production_socket_before = PRODUCTION_SOCKET.exists() and PRODUCTION_SOCKET.stat().st_ino
    lab = LoopbackLab(DEFAULT_IMAGE)
    lab.report["scope"] = "Q4 end-to-end: bundle + gateway process + client CLI + host sqlcmd on owned loopback SQL Server"
    root = Path(tempfile.mkdtemp(prefix="q4-", dir="/tmp"))
    flow = Flow(lab, root)
    error = None
    try:
        lab.start()
        flow.prepare()
        scenarios(flow)
    except Exception as exc:  # report what ran; never hide the failure
        error = type(exc).__name__ + ": " + lab.clean(str(exc))[:1500]
        print("ERROR " + error, flush=True)
    finally:
        flow.stop_gateway()
        lab.cleanup()
        production_socket_after = PRODUCTION_SOCKET.exists() and PRODUCTION_SOCKET.stat().st_ino
        flow.check("production socket untouched", production_socket_before == production_socket_after)
        shutil.rmtree(root, ignore_errors=True)
        lab.report.update(q4_checks=flow.results, error=error)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(lab.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [r["name"] for r in flow.results if not r["passed"]]
    print(json.dumps(dict(passed=len(flow.results) - len(failed), failed=failed, error=error), ensure_ascii=False))
    return 1 if failed or error else 0


if __name__ == "__main__":
    raise SystemExit(main())
