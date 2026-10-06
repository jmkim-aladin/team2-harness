"""Offline boundary probe: sends requests only to local mock servers."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path("/private/tmp/team2-openhands-pilot-20260928")
received = []
class Mock(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        received.append([self.server.server_port, self.command])
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"mock")
    do_POST = do_GET
    do_PUT = do_GET
    do_PATCH = do_GET
    do_DELETE = do_GET
    def log_message(self, *_):
        pass

def run(command):
    return subprocess.run(
        ["/usr/bin/sandbox-exec", "-f", str(ROOT / "boundary.sb"), *command],
        cwd=ROOT, env={"PATH": "/opt/homebrew/bin:/usr/bin:/bin",
            "TMPDIR": str(ROOT / "tmp"),
            "OH_CANVAS_SAFE_STATE_DIR": str(ROOT / "state"),
            "AGENT_CANVAS_DISABLE_TELEMETRY": "1", "VITE_DO_NOT_TRACK": "1"},
        capture_output=True, text=True, timeout=20)

servers = []
try:
    for port in [18761, 18762]:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Mock)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
    results = {}
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        p = run(["/usr/bin/curl", "--silent", "--max-time", "3", "-X", method,
                 "http://127.0.0.1:18762/api/issues/MOCK-1"])
        results["blocked_" + method] = p.returncode != 0
    p = run(["/usr/bin/curl", "--silent", "--max-time", "3", "http://127.0.0.1:18761/"])
    results["allowed_mock_control"] = p.returncode == 0 and p.stdout == "mock"
    p = run(["/bin/cat", "/Users/jm/Documents/workspace/team2/CLAUDE.md"])
    results["home_read_blocked"] = p.returncode != 0 and not p.stdout
    p = run(["/bin/sh", "-c", "curl --silent --max-time 3 -X POST http://127.0.0.1:18762/api/articles"])
    results["child_shell_blocked"] = p.returncode != 0
    p = run(["/opt/homebrew/bin/node", "-e", "require('child_process').execFileSync('/usr/bin/curl',['--silent','--max-time','3','-X','DELETE','http://127.0.0.1:18762/api/issues/MOCK-1'])"])
    results["node_child_blocked"] = p.returncode != 0
    p = run(["/opt/homebrew/bin/node", str(ROOT / "runtime/node_modules/@openhands/agent-canvas/bin/agent-canvas.mjs"), "--version"])
    results["canvas_installed"] = p.returncode == 0 and "1.24.0" in p.stdout
    results["blocked_mock_received_zero"] = all(port != 18762 for port, _ in received)
    output = {"checks": results, "mock_received": received,
              "scope": "OS sandbox and subprocesses; no LLM, MCP, real credentials or external-service requests"}
    print(json.dumps(output, indent=2))
    (ROOT / "boundary-result.json").write_text(json.dumps(output, indent=2) + "\n")
    if not all(results.values()):
        raise SystemExit(1)
finally:
    for server in servers:
        server.shutdown()
        server.server_close()
