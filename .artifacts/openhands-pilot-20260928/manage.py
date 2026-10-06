"""Manage the isolated, offline OpenHands pilot. No external credentials loaded."""
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path("/private/tmp/team2-openhands-pilot-20260928")

def stop():
    for name in ("frontend", "backend"):
        pidfile = ROOT / (name + ".pid")
        if pidfile.exists():
            pid = int(pidfile.read_text())
            # Only signal a still-running process whose command identifies this pilot.
            command = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
            if str(ROOT) in command:
                try: os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError: pass

def start():
    stop()
    keyfile = ROOT / "state/local-test.key"
    if not keyfile.exists():
        keyfile.write_text(secrets.token_urlsafe(32))
        keyfile.chmod(0o600)
    key = keyfile.read_text()
    env = {
        "PATH": str(ROOT / "backend/bin") + ":/opt/homebrew/bin:/usr/bin:/bin",
        "TMPDIR": str(ROOT / "tmp"), "PYTHONUNBUFFERED": "1",
        "OH_CANVAS_SAFE_STATE_DIR": str(ROOT / "state"),
        "AGENT_CANVAS_DISABLE_TELEMETRY": "1", "VITE_DO_NOT_TRACK": "1",
        "OH_PERSISTENCE_DIR": str(ROOT / "state"),
        "OH_CONVERSATIONS_PATH": str(ROOT / "state/conversations"),
        "OH_WORKSPACE_PATH": str(ROOT / "workspace"),
        "OH_BASH_EVENTS_DIR": str(ROOT / "state/bash_events"),
        "OH_ENABLE_VSCODE": "false", "OH_PRELOAD_TOOLS": "false", "OH_TELEMETRY_EXPORTER": "none",
        "OH_SESSION_API_KEYS_0": key, "OH_SECRET_KEY": key,
        "LOCAL_BACKEND_API_KEY": key,
        "CANVAS_BUILD_DIR": str(ROOT / "runtime/node_modules/@openhands/agent-canvas/build"),
        "LITELLM_LOCAL_MODEL_COST_MAP": "True", "DO_NOT_TRACK": "1",
        "OPENHANDS_SUPPRESS_BANNER": "1",
    }
    commands = {
        "backend": [str(ROOT / "backend/bin/agent-server"), "--host", "127.0.0.1", "--port", "18763"],
        "frontend": ["/opt/homebrew/bin/node", str(ROOT / "serve.mjs")],
    }
    for name, command in commands.items():
        with (ROOT / (name + ".log")).open("w") as log:
            proc = subprocess.Popen(["/usr/bin/sandbox-exec", "-f", str(ROOT / "runtime.sb"), *command],
                env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            (ROOT / (name + ".pid")).write_text(str(proc.pid))
    for attempt in range(45):
        if check():
            print("Ready: http://127.0.0.1:18760")
            return
        time.sleep(1)
    print("Not ready; inspect redacted pilot logs.")
    raise SystemExit(1)

def check():
    key = (ROOT / "state/local-test.key").read_text()
    try:
        for port, path in ((18760, "/"), (18763, "/ready")):
            request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers={"X-Session-API-Key": key})
            with urllib.request.urlopen(request, timeout=1) as response:
                if response.status != 200: return False
        return True
    except Exception:
        return False

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "start": start()
    elif action == "stop": stop(); print("Pilot stopped")
    elif action == "status":
        ready = check()
        print(json.dumps({"ready": ready, "url": "http://127.0.0.1:18760"}))
        raise SystemExit(0 if ready else 1)
    else: raise SystemExit("Usage: manage.py start|stop|status")
