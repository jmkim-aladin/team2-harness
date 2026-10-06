"""Run the unmodified official launcher; preserve the existing local settings."""
import os
from pathlib import Path
import subprocess
import sys

root = Path("/private/tmp/team2-openhands-pilot-20260928")
manager = Path(__file__).with_name("manage.py")
subprocess.run([sys.executable, str(manager), "stop"], check=True)
canvas_state = root / "state/canvas"
canvas_state.mkdir(parents=True, exist_ok=True)
previous_conversations = root / "state/conversations"
previous_conversations.mkdir(exist_ok=True)
conversation_path = canvas_state / "dev_conversations"
if not conversation_path.exists():
    conversation_path.symlink_to(previous_conversations, target_is_directory=True)
env = os.environ.copy()
env.update({
    "PATH": str(root / "uv-tools/bin") + os.pathsep + env.get("PATH", "/usr/bin:/bin"),
    "OH_CANVAS_SAFE_STATE_DIR": str(canvas_state),
    "OH_SECRET_KEY_PATH": str(root / "state/local-test.key"),
    "OH_SESSION_API_KEY_PATH": str(root / "state/local-test.key"),
    "UV_CACHE_DIR": str(root / "uv-cache"),
    "npm_config_cache": str(root / "npm-cache"),
    "AGENT_CANVAS_DISABLE_TELEMETRY": "1",
    "VITE_DO_NOT_TRACK": "1",
})
# Drop only former pilot overrides if inherited. No OS sandbox or credential filtering.
for name in ("OH_PRELOAD_TOOLS", "OH_ENABLE_VSCODE", "OH_WORKSPACE_PATH"):
    env.pop(name, None)
command = ["/opt/homebrew/bin/node", str(root / "runtime/node_modules/@openhands/agent-canvas/bin/agent-canvas.mjs"), "--port", "18760"]
with (root / "default.log").open("w") as log:
    proc = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
(root / "default.pid").write_text(str(proc.pid))
print("Official launcher started, PID", proc.pid)
print("Logs:", root / "default.log")
