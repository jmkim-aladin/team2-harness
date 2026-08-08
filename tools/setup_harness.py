#!/usr/bin/env python3
"""하네스 환경 수렴 도구 — harness.manifest.json 선언 상태로 ~/.claude, ~/.codex 를 맞춘다.

멱등: 몇 번 돌려도 같은 결과. "초기화 후 재설치"가 아니라 "선언으로 수렴"이다.
새 머신 = git clone → 이 스크립트 실행 → 토큰 입력 → 끝. Mac/Windows 동일.

모드:
    python3 tools/setup_harness.py            # 수렴 — 부족한 것 추가, 초과분은 경고만
    python3 tools/setup_harness.py --check    # 보고만 (드리프트 있으면 exit 1)
    python3 tools/setup_harness.py --reset    # 관리 영역 초과분을 격리 후 수렴

관리 영역: ~/.claude/skills, ~/.claude/commands/ad, ~/.codex/skills, settings.json 훅·env, 팀 메모리 링크.
비관리(절대 안 건드림): 인증·토큰 값, ~/.claude/projects 세션 로그, 개인 CLAUDE.md 내용, plugins on/off.
--reset 도 삭제하지 않는다 — ~/.claude/harness-quarantine-<ts>/ 로 이동 (되돌리기 = mv).

의존성: python3 stdlib 만. (부트스트랩 도구는 새 머신에서 pip 없이 돌아야 한다)
"""
import argparse
import fnmatch
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
CODEX = os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex"))
IS_WIN = platform.system() == "Windows"
OS_KEY = "windows" if IS_WIN else "darwin"

ok_list, warn_list, fix_list = [], [], []


def ok(msg):   ok_list.append(msg)
def warn(msg): warn_list.append(msg)
def fixed(msg): fix_list.append(msg)


def expand(p):
    return os.path.expanduser(p) if not IS_WIN else os.path.expandvars(os.path.expanduser(p))


def load_manifest():
    with open(os.path.join(REPO, "harness.manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def read_settings():
    p = os.path.join(CLAUDE, "settings.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f), p
    return {}, p


def write_settings(s, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


def make_link(src, dest, apply):
    """심볼릭 링크 보장. Windows 는 디렉토리면 junction 폴백."""
    src, dest = os.path.abspath(src), expand(dest)
    if os.path.islink(dest):
        if os.path.realpath(dest) == os.path.realpath(src):
            ok(f"링크 {dest}")
            return
        if apply:
            os.unlink(dest)
        else:
            warn(f"링크 대상 불일치 {dest} → 수렴 필요")
            return
    elif os.path.exists(dest):
        warn(f"{dest} 가 링크가 아닌 실체 — 수동 확인 필요 (건드리지 않음)")
        return
    if not apply:
        warn(f"링크 없음 {dest} → 수렴 필요")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        os.symlink(src, dest)
        fixed(f"링크 생성 {dest} → {src}")
    except OSError:
        if IS_WIN and os.path.isdir(src):
            subprocess.run(["cmd", "/c", "mklink", "/J", dest, src], check=True, capture_output=True)
            fixed(f"junction 생성 {dest} → {src}")
        else:
            raise


def quarantine(path, qdir):
    os.makedirs(qdir, exist_ok=True)
    shutil.move(path, os.path.join(qdir, os.path.basename(path)))


def converge_env(m, apply):
    s, p = read_settings()
    env = s.setdefault("env", {})
    want = {"TEAM2_HARNESS_PATH": REPO}
    for k, v in m["env"].items():
        want[k] = v[OS_KEY] if isinstance(v, dict) else v
    for k, v in want.items():
        v = expand(v)
        if env.get(k) == v:
            ok(f"env {k}")
        elif apply:
            env[k] = v
            fixed(f"env {k}={v}")
        else:
            warn(f"env {k} 누락/불일치")
    if apply:
        write_settings(s, p)
    if "YOUTRACK_TOKEN" in env:
        warn("YOUTRACK_TOKEN 이 settings.json 에 평문으로 있음 — Keychain 이관: python3 tools/cred.py set youtrack-token 후 env 에서 제거 (local-credentials-policy)")


def converge_links(m, apply):
    tl = m["team_links"]
    make_link(os.path.join(REPO, tl["claude_commands"]["src"]), tl["claude_commands"]["dest"], apply)
    for e in tl["claude_skills"]:
        make_link(os.path.join(REPO, e["src"]), e["dest"], apply)
    for src in sorted(glob.glob(os.path.join(REPO, tl["codex_skills_glob"]["src"]))):
        if not os.path.isdir(src):
            continue
        make_link(src, os.path.join(tl["codex_skills_glob"]["dest_dir"], os.path.basename(src)), apply)


def converge_vendored(m, apply):
    """vendor 스킬을 ~/.claude/skills 와 ~/.codex/skills 양쪽에 링크."""
    for name, e in (m.get("vendored") or {}).items():
        if not isinstance(e, dict):
            continue
        excl = set(e.get("link_exclude", []))
        for src in sorted(glob.glob(os.path.join(REPO, e["src_glob"]))):
            if not os.path.isdir(src):
                continue
            base = os.path.basename(src)
            if base in excl:
                continue
            make_link(src, os.path.join(CLAUDE, "skills", base), apply)
            make_link(src, os.path.join(CODEX, "skills", base), apply)


def converge_memory(m, apply):
    mem = m["memory"]
    make_link(os.path.join(REPO, mem["src"]), mem["dest"], apply)
    target = expand(mem["import_into"])
    line = mem["import_line"]
    body = ""
    if os.path.isfile(target):
        with open(target, encoding="utf-8") as f:
            body = f.read()
    if line in body.split("\n"):
        ok(f"import {line} in {target}")
    elif apply:
        with open(target, "w", encoding="utf-8") as f:
            f.write(line + "\n" + body)
        fixed(f"import 추가 {line} → {target}")
    else:
        warn(f"{target} 에 {line} 없음 → 수렴 필요")


def audit_skills(m, mode, qdir):
    ext = m["external_skills"]
    team_names = {os.path.basename(e["dest"]) for e in m["team_links"]["claude_skills"]}
    vendored_names = set()
    for e in (m.get("vendored") or {}).values():
        if not isinstance(e, dict):
            continue
        vendored_names |= {os.path.basename(x) for x in glob.glob(os.path.join(REPO, e["src_glob"])) if os.path.isdir(x)}
    declared = set(ext["claude_keep"]) | set(ext["claude_unmanaged_links"]) | team_names | vendored_names
    sdir = os.path.join(CLAUDE, "skills")
    if os.path.isdir(sdir):
        for d in sorted(os.listdir(sdir)):
            full = os.path.join(sdir, d)
            if not (os.path.isdir(full) or os.path.islink(full)) or d in declared:
                continue
            if mode == "reset":
                quarantine(full, qdir)
                fixed(f"격리 ~/.claude/skills/{d}")
            else:
                warn(f"선언 밖 스킬 ~/.claude/skills/{d}")
    # skills-disabled 는 --reset 시 통째 격리 (manifest.removed 에 기록됨)
    dis = os.path.join(CLAUDE, "skills-disabled")
    if os.path.isdir(dis) and mode == "reset":
        quarantine(dis, qdir)
        fixed("격리 ~/.claude/skills-disabled/")

    # codex 쪽
    if ext.get("codex_keep_same_as_claude"):
        codex_declared = set(ext["claude_keep"]) | vendored_names
        codex_declared |= {os.path.basename(p) for p in glob.glob(os.path.join(REPO, m["team_links"]["codex_skills_glob"]["src"]))}
        personal = ext.get("codex_personal_prefixes", [])
        pending = set(ext.get("codex_pending_until_mattpocock", []))
        cdir = os.path.join(CODEX, "skills")
        if os.path.isdir(cdir):
            for d in sorted(os.listdir(cdir)):
                if d.startswith(".") or d in codex_declared or d in pending:
                    continue
                if any(d.startswith(px) for px in personal):
                    continue
                if mode == "reset":
                    quarantine(os.path.join(cdir, d), qdir)
                    fixed(f"격리 ~/.codex/skills/{d}")
                else:
                    warn(f"선언 밖 스킬 ~/.codex/skills/{d}")


def audit_hooks(m, mode):
    s, p = read_settings()
    allow = m["hooks_allow"]
    changed = False
    for ev, groups in list((s.get("hooks") or {}).items()):
        kept_groups = []
        for g in groups:
            hooks = []
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                if any(a in cmd for a in allow):
                    hooks.append(h)
                elif mode == "reset":
                    fixed(f"훅 제거 [{ev}] {cmd[:60]}")
                    changed = True
                else:
                    warn(f"미등록 훅 [{ev}] {cmd[:60]}")
                    hooks.append(h)
            if hooks:
                g["hooks"] = hooks
                kept_groups.append(g)
        if kept_groups:
            s["hooks"][ev] = kept_groups
        elif ev in s.get("hooks", {}):
            del s["hooks"][ev]
            changed = True
    if changed:
        write_settings(s, p)


def audit_plugins(m):
    s, _ = read_settings()
    actual = s.get("enabledPlugins", {})
    for k, v in m["plugins"]["expected"].items():
        if actual.get(k) == v:
            ok(f"plugin {k}={v}")
        else:
            warn(f"plugin {k}: 기대 {v}, 실제 {actual.get(k)} — 사람이 판단 (도구가 안 바꿈)")


def check_credentials(m):
    """manifest 선언 자격증명의 존재만 검사 — 값은 읽지도 출력하지도 않는다."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import cred
    except ImportError:
        warn("tools/cred.py 로드 실패 — 자격증명 검사 생략")
        return
    for c in m.get("credentials", []):
        if not isinstance(c, dict):
            continue
        name = c["name"]
        if cred.exists(name):
            ok(f"credential {name}")
        else:
            warn(f"credential {name} 미등록 — python3 tools/cred.py set {name}" +
                 (f" ({c['hint']})" if c.get("hint") else ""))


def check_cli():
    if shutil.which("gh"):
        auth = subprocess.run(["gh", "auth", "status"], capture_output=True)
        ok("gh 인증됨") if auth.returncode == 0 else warn("gh 인증 필요: gh auth login")
    else:
        warn("gh CLI 미설치 — brew install gh (mac) / winget install GitHub.cli (win)")


def show_planned(m):
    # 계획 스택은 드리프트가 아니라 정보 — --check 의 exit code 에 반영하지 않는다
    for name, e in m.get("planned", {}).items():
        print(f"  [계획] {name} ({e['pin']}) — 설치: {e['source']} / install {len(e['install'])}종, exclude {len(e['exclude'])}종")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="보고만, 변경 없음")
    g.add_argument("--reset", action="store_true", help="관리 영역 초과분 격리 후 수렴")
    a = ap.parse_args()
    mode = "check" if a.check else ("reset" if a.reset else "converge")
    apply = mode != "check"
    qdir = os.path.join(CLAUDE, f"harness-quarantine-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

    m = load_manifest()
    converge_env(m, apply)
    converge_links(m, apply)
    converge_vendored(m, apply)
    converge_memory(m, apply)
    audit_skills(m, mode, qdir)
    audit_hooks(m, mode)
    audit_plugins(m)
    check_credentials(m)
    check_cli()

    print(f"===== setup_harness [{mode}] ({OS_KEY}) =====")
    print(f"  정상   {len(ok_list)}")
    for x in fix_list:  print(f"  [수렴] {x}")
    for x in warn_list: print(f"  [경고] {x}")
    show_planned(m)
    if os.path.isdir(qdir):
        print(f"  격리 위치: {qdir}  (되돌리기: mv)")
    if mode == "check" and (warn_list or fix_list):
        sys.exit(1)


if __name__ == "__main__":
    main()
