#!/usr/bin/env python3
"""로컬 자격증명 접근 — OS 금고를 한 인터페이스로.

macOS는 Keychain(`security` CLI, 의존성 0), Windows는 Credential Manager(python `keyring`,
1회 `pip install keyring`). 값은 어떤 경우에도 파일·문서·로그에 남기지 않는다.
정책: policies/local-credentials-policy.md

사용법:
    python3 tools/cred.py get <service>          # 값을 stdout으로 (파이프 용도)
    python3 tools/cred.py set <service>          # 프롬프트 입력 — 인자로 값을 받지 않는다 (셸 히스토리 방지)
    python3 tools/cred.py check                  # manifest 선언분 존재 여부만 (값 출력 없음)
    python3 tools/cred.py check <service>        # 단건 존재 여부 (exit 0/1)

네이밍: `sm-{service}-{module}-{env}-{resource}` 권장. 레거시 단축명(cool-dev 등)은
정책의 매핑 표가 SoT.
"""
import getpass
import json
import os
import platform
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_MAC = platform.system() == "Darwin"


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        print("keyring 미설치 — Windows/Linux에서는 `pip install keyring` 1회 필요", file=sys.stderr)
        sys.exit(2)


def get(service):
    if IS_MAC:
        r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
        return r.stdout.rstrip("\n")
    v = _keyring().get_password(service, getpass.getuser())
    return v


def set_(service):
    value = getpass.getpass(f"{service} 값 입력 (화면에 표시되지 않음): ")
    if not value:
        print("빈 값 — 취소", file=sys.stderr)
        sys.exit(1)
    if IS_MAC:
        # -U: 있으면 갱신
        r = subprocess.run(["security", "add-generic-password", "-U",
                            "-s", service, "-a", getpass.getuser(), "-w", value],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"등록 실패: {r.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
    else:
        _keyring().set_password(service, getpass.getuser(), value)
    print(f"등록됨: {service} (금고: {'Keychain' if IS_MAC else 'Credential Manager'})")


def exists(service):
    return get(service) is not None


def manifest_credentials():
    p = os.path.join(REPO, "harness.manifest.json")
    try:
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        return [c for c in m.get("credentials", []) if isinstance(c, dict)]
    except Exception:
        return []


def check(target=None):
    creds = manifest_credentials()
    if target:
        ok = exists(target)
        print(f"{'OK' if ok else '없음'}: {target}")
        sys.exit(0 if ok else 1)
    if not creds:
        print("manifest에 credentials 선언 없음")
        return
    missing = 0
    for c in creds:
        name = c["name"]
        if exists(name):
            print(f"  OK    {name}")
        else:
            missing += 1
            hint = c.get("hint", "")
            print(f"  없음  {name}" + (f" — {hint}" if hint else ""))
            print(f"        등록: python3 tools/cred.py set {name}")
    sys.exit(1 if missing else 0)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("get", "set", "check"):
        print(__doc__)
        sys.exit(2)
    cmd = args[0]
    if cmd == "get":
        if len(args) != 2:
            sys.exit(2)
        v = get(args[1])
        if v is None:
            print(f"없음: {args[1]} — 등록: python3 tools/cred.py set {args[1]}", file=sys.stderr)
            sys.exit(1)
        print(v)
    elif cmd == "set":
        if len(args) != 2:
            sys.exit(2)
        set_(args[1])
    else:
        check(args[1] if len(args) > 1 else None)


if __name__ == "__main__":
    main()
