#!/usr/bin/env python3
"""로컬 자격증명 접근 — OS 금고를 한 인터페이스로.

macOS는 Keychain(`security` CLI, 의존성 0), Windows는 Credential Manager(python `keyring`,
1회 `pip install keyring`). 값은 어떤 경우에도 파일·문서·로그에 남기지 않는다.
정책: policies/local-credentials-policy.md

사용법:
    python3 tools/cred.py get <service>          # 값을 stdout으로 (파이프 용도)
    python3 tools/cred.py get <service> --account <account>  # account-scoped lookup
    python3 tools/cred.py set <service>          # 프롬프트 입력 — 인자로 값을 받지 않는다 (셸 히스토리 방지)
    pbpaste | python3 tools/cred.py set <service> --stdin-hex  # macOS stdin-only path
    python3 tools/cred.py check                  # manifest 선언분 존재 여부만 (값 출력 없음)
    python3 tools/cred.py check <service>        # 단건 존재 여부 (exit 0/1)
    python3 tools/cred.py check <service> --account <account>  # account-scoped lookup

네이밍: `sm-{service}-{module}-{env}-{resource}` 권장. 레거시 단축명(cool-dev 등)은
정책의 매핑 표가 SoT.
"""
import getpass
import json
import os
import platform
import re
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


ACCOUNT_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
SERVICE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,255}\Z")
# macOS `security -i` has a small command-line parser ceiling.  RSA-2048
# PKCS#8 PEM is typically 1704 bytes / 3408 hex characters; keep metadata and
# the terminating newline below the observed ~4096-byte limit.
MAX_STDIN_HEX_BYTES = 3800


def _validate_account(account):
    if not isinstance(account, str) or not ACCOUNT_PATTERN.fullmatch(account):
        raise ValueError("잘못된 Keychain account")


def _validate_service(service):
    if not isinstance(service, str) or not SERVICE_PATTERN.fullmatch(service):
        raise ValueError("잘못된 Keychain service")


def get(service, account=None):
    if IS_MAC:
        argv = ["security", "find-generic-password", "-s", service]
        if account is not None:
            _validate_account(account)
            argv.extend(["-a", account])
        argv.append("-w")
        r = subprocess.run(argv,
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
        return r.stdout.rstrip("\n")
    if account is not None:
        _validate_account(account)
        if account != getpass.getuser():
            raise ValueError("Windows Credential Manager account must match the current user")
    v = _keyring().get_password(service, getpass.getuser())
    return v


def set_(service):
    if IS_MAC:
        # Keep the secret out of Python memory and process argv.  With -w as
        # the final option, macOS security prompts on the controlling tty.
        r = subprocess.run(["security", "add-generic-password", "-U",
                            "-s", service, "-a", getpass.getuser(), "-w"])
        if r.returncode != 0:
            print("등록 실패: macOS Keychain이 값을 저장하지 않았습니다.", file=sys.stderr)
            sys.exit(1)
    else:
        value = getpass.getpass(f"{service} 값 입력 (화면에 표시되지 않음): ")
        if not value:
            print("빈 값 — 취소", file=sys.stderr)
            sys.exit(1)
        _keyring().set_password(service, getpass.getuser(), value)
    print(f"등록됨: {service} (금고: {'Keychain' if IS_MAC else 'Credential Manager'})")


def set_stdin_hex(service):
    """Store a bounded ASCII-hex value using macOS security's stdin mode.

    The value is intentionally not decoded: the workload adapter stores and
    later decodes hex-encoded PEM material.  ``security -i`` receives the
    command only on its stdin; the secret never appears in argv or env.
    """
    if not IS_MAC:
        raise ValueError("--stdin-hex는 macOS Keychain에서만 사용할 수 있습니다")
    _validate_service(service)
    account = getpass.getuser()
    _validate_account(account)
    raw = bytearray()
    command = bytearray()
    hex_value = ""
    try:
        data = sys.stdin.buffer.read(MAX_STDIN_HEX_BYTES + 1)
        raw = bytearray(data)
        if len(raw) > MAX_STDIN_HEX_BYTES:
            raise ValueError("Keychain 입력이 너무 깁니다")
        try:
            hex_value = bytes(raw).decode("ascii").rstrip("\r\n")
        except UnicodeDecodeError as error:
            raise ValueError("Keychain 입력은 ASCII hex여야 합니다") from error
        if (
            not hex_value
            or len(hex_value) % 2 != 0
            or re.fullmatch(r"[0-9A-Fa-f]+", hex_value) is None
        ):
            raise ValueError("Keychain 입력은 짝수 길이 ASCII hex여야 합니다")
        command = bytearray(
            f"add-generic-password -s {service} -a {account} -w {hex_value}\n".encode("ascii")
        )
        result = subprocess.run(
            ["security", "-i"],
            input=bytes(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(
                "macOS Keychain 등록 실패; partial item이 남았을 수 있습니다. "
                f"재시도 전 수동 정리: /usr/bin/security delete-generic-password "
                f"-s {service} -a {account}"
            )
    finally:
        for buffer in (raw, command):
            buffer[:] = b"\x00" * len(buffer)
        hex_value = ""


def exists(service, account=None):
    return get(service, account) is not None


def manifest_credentials():
    p = os.path.join(REPO, "harness.manifest.json")
    try:
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        return [c for c in m.get("credentials", []) if isinstance(c, dict)]
    except Exception:
        return []


def check(target=None, account=None):
    creds = manifest_credentials()
    if target:
        ok = exists(target, account)
        print(f"{'OK' if ok else '없음'}: {target}")
        sys.exit(0 if ok else 1)
    if not creds:
        print("manifest에 credentials 선언 없음")
        return
    missing = 0
    for c in creds:
        name = c["name"]
        if exists(name, account):
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
    positionals = []
    account = None
    stdin_hex = False
    i = 1
    while i < len(args):
        if args[i] == "--account":
            if account is not None or i + 1 >= len(args):
                print(__doc__, file=sys.stderr)
                sys.exit(2)
            account = args[i + 1]
            i += 2
        elif args[i] == "--stdin-hex":
            if stdin_hex or cmd != "set":
                print(__doc__, file=sys.stderr)
                sys.exit(2)
            stdin_hex = True
            i += 1
        elif args[i].startswith("-"):
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        else:
            positionals.append(args[i])
            i += 1
    if cmd == "get":
        if len(positionals) != 1:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        try:
            v = get(positionals[0], account)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            sys.exit(2)
        if v is None:
            print(f"없음: {positionals[0]} — 등록: python3 tools/cred.py set {positionals[0]}", file=sys.stderr)
            sys.exit(1)
        print(v)
    elif cmd == "set":
        if len(positionals) != 1 or account is not None:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        try:
            if stdin_hex:
                set_stdin_hex(positionals[0])
            else:
                set_(positionals[0])
        except ValueError as error:
            print(str(error), file=sys.stderr)
            sys.exit(2)
    else:
        if len(positionals) > 1:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        try:
            check(positionals[0] if positionals else None, account)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
