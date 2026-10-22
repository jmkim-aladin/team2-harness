#!/usr/bin/env python3
"""푸시·PR·YouTrack 게이트 — 에이전트 실행(PAPERCLIP_RUN_ID)과 사람 세션을 나눠 판정한다.

개발 흐름 (policies/ai-usage-policy.md §Paperclip 에이전트 실행 예외):
  에이전트가 구현·로컬 커밋 → 사람이 Paperclip 에서 승인 → 에이전트가 feature push·develop 대상 draft PR·자체 리뷰
  → merge·ready 전환·배포는 사람.

에이전트 실행 (PAPERCLIP_RUN_ID 있음, deny 로 닫는다):
  git push        PAPERCLIP_APPROVAL_STATUS=approved, 대상 feature/*, 강제·삭제 형태 없음일 때만 통과
  gh pr create    approved, --draft, --base develop 일 때만 통과
  항상 차단       gh pr merge·ready, gh workflow run, gh release create, gh api 의 merge·ref·dispatch·release 쓰기
  YouTrack 쓰기   항상 차단 — YouTrack→Paperclip 단방향이다
  운영 DB 경로    항상 차단 — db_prod_*·db_query_control·db_execute 실행, 게이트웨이 소켓, --from-chat-digest.
                  소켓 인증은 peer UID 뿐이고 chat digest 는 비대화 실행이 스스로 만들 수 있어서다.
                  소스 읽기(cat·grep·sed)는 허용, 개발 sqlcmd SELECT 는 sqlcmd-readonly 훅이 판정한다.
  승인 env 는 훅 프로세스(= Claude 프로세스) env 에서 읽는다. 에이전트가 Bash 에서 export 해도 판정은 바뀌지 않는다.
사람 세션 (PAPERCLIP_RUN_ID 없음): git push·gh pr create 에 ask 를 돌려준다.
  정적 permissions.ask 로 두지 않는 이유 — 훅 allow 는 ask 규칙을 넘지 못해 승인된 에이전트까지 막힌다.

경계: Bash 문자열 판정은 보안 경계가 아니다. git/gh 별칭, 스크립트 파일 안 호출, 명령 밖 변수는 놓칠 수 있다.
  셸 래핑(sh -c, eval, 따옴표 안) 속 push·PR 생성은 해석하지 않고 에이전트 실행에서 막는다.
실패 처리: 에이전트 실행의 판정 실패는 deny(닫힘), 사람 세션의 판정 실패는 무출력(열림).
의존성: python3 stdlib, git (현재 브랜치·push 설정 조회).
"""

import json
import os
import re
import shlex
import subprocess
import sys

RUN_ENV = "PAPERCLIP_RUN_ID"
APPROVAL_ENV = "PAPERCLIP_APPROVAL_STATUS"
PREFIX = "에이전트 실행(PAPERCLIP_RUN_ID)에서"
# policies/branching-strategy.md — 작업은 feature/{이슈ID}, PR 은 feature/* → develop
PUSH_BRANCH_PREFIXES = ("feature/",)
PR_BASES = ("develop",)
GIT_TIMEOUT = 3

_Q = r"(?:\"[^\"]*\"|'[^']*'|\S+)"
_SEP = r"(?:^|[\s;&|()<>`'\"\\/{}])"
_GIT_GLOBAL = (r"(?:\s+(?:-[Cc]\s*" + _Q
               + r"|--(?:git-dir|work-tree|namespace|config-env)(?:=|\s+)" + _Q
               + r"|-[A-Za-z]|--[A-Za-z][\w-]*(?:=\S+)?))*")
# 따옴표 안까지 원문 전체를 본다 — 구조 해석보다 많이 잡히면 래핑된 호출로 보고 막는다
PUSH_RE = re.compile(_SEP + r"git(?:\.exe)?" + _GIT_GLOBAL + r"\s+push\b")
PR_CREATE_RE = re.compile(_SEP + r"gh(?:\.exe)?\s+pr\s+(?:create|new)\b")
ALWAYS_DENY = (
    ("gh pr merge", re.compile(_SEP + r"gh(?:\.exe)?\s+pr\s+merge\b")),
    ("gh pr ready", re.compile(_SEP + r"gh(?:\.exe)?\s+pr\s+ready\b")),
    ("gh workflow run", re.compile(_SEP + r"gh(?:\.exe)?\s+workflow\s+run\b")),
    ("gh release create", re.compile(_SEP + r"gh(?:\.exe)?\s+release\s+create\b")),
    ("PR merge API", re.compile(r"pulls/[^/\s'\"]+/merge(?![\w-])")),
    ("GraphQL merge·ready", re.compile(r"\b(?:mergePullRequest|markPullRequestReadyForReview"
                                       r"|enablePullRequestAutoMerge)\b")),
)
# gh api 쓰기 중 사람 몫인 행동 — 리뷰·코멘트(pulls/{n}/reviews, issues/{n}/comments)는 해당 없음
API_WRITE_DENY = (
    ("gh api branch merge", re.compile(r"(?:^|/)merges$"), "merge는 사람이 한다."),
    ("gh api git refs 쓰기", re.compile(r"(?:^|/)git/refs(?:/|$)"), "push는 git push(feature/*)로 할 것."),
    ("gh api workflow dispatch", re.compile(r"(?:^|/)dispatches$"), "배포·워크플로 실행은 사람이 한다."),
    ("gh api release 쓰기", re.compile(r"(?:^|/)releases(?:/|$)"), "릴리스는 사람이 한다."),
    ("gh api PR 생성", re.compile(r"^repos/[^/]+/[^/]+/pulls$"), "`gh pr create --draft --base develop`으로 할 것."),
)

_HTTP_CLIENT = re.compile(_SEP + r"(?:curl|wget|http|https|xh|xhs)(?:\.exe)?(?=\s|$)")
_HTTP_WRITE = (
    re.compile(r"(?:^|\s)(?:-[A-Za-z]*X\s*|--request(?:=|\s+)|--method(?:=|\s+))['\"]?(?i:POST|PUT|PATCH|DELETE)\b"),
    re.compile(r"(?:^|\s)(?:-[A-Za-z]*[dFT]|--data[\w-]*|--json|--form[\w-]*|--upload-file"
               r"|--post-data|--post-file|--body-data|--body-file)(?=[\s='\"@{]|$)"),
    re.compile(r"(?:^|\s)(?:http|https|xh|xhs)\s+(?:-\S+\s+)*(?i:POST|PUT|PATCH|DELETE)\b"),
)
_HTTP_GET = re.compile(r"(?:^|\s)(?:-[A-Za-z]*G[A-Za-z]*|--get)(?=\s|$)")  # curl -G: 데이터 플래그가 쿼리가 된다
_INTERPRETER = re.compile(_SEP + r"(?:python[\d.]*|node|ruby|perl|deno|bun)(?=\s|$)")
_CODE_HTTP_WRITE = re.compile(r"\.(?:post|put|patch|delete)\s*\(|method\s*[=:]\s*['\"](?i:POST|PUT|PATCH|DELETE)")
_YT_MCP_WRITE = re.compile(r"(?:^|[_\-])(?:create|update|delete|add|remove|set|change|apply|link|unlink|post|comment"
                           r"|move|assign|edit|patch|put|execute|command|vote|star|attach|upload|import|merge"
                           r"|close|resolve|reopen|log|track|transition)")

# 운영 DB 경로 — 소켓 인증이 peer UID 뿐이고 --from-chat-digest 는 비대화 실행이 스스로 만들 수 있다
_DB_NAME = r"(?:db_prod_[a-z_]+|db_query_control|db_execute)"
_DB_FILE = re.compile(r"^" + _DB_NAME + r"\.py$")
_DB_MODULE = re.compile(r"(?:^|\.)" + _DB_NAME + r"$")
_DB_MENTION = re.compile(r"(?<![\w-])" + _DB_NAME + r"\.(?:py|swift)\b")
_DB_SOCKET = re.compile(r"(?:/tmp/+|/private/tmp/+|\$\{?TMPDIR\}?/+|/var/folders/\S*?/)team2-db-"
                        r"|team2-db-[^\s'\"/]*/query\.sock|team2-db/db-prod-keychain")
# 따옴표·다른 언어 문자열 안의 실행 형태 (python3 [옵션] …/db_prod_client.py, ['python3', '…'])
_DB_RUN_RAW = re.compile(r"(?:python[\d.]*|swiftc?)(?:\.exe)?['\"]?(?:[\s,]+['\"]?-[\w-]+['\"]?)*[\s,]+['\"]?"
                         r"[^\s;&|'\",]*?(?<![\w-])" + _DB_NAME + r"\.(?:py|swift)")
_DB_INLINE = re.compile(r"\b(?:import|from)\s+(?:[\w.]+\.)?" + _DB_NAME + r"\b"
                        r"|\bfrom\s+[\w.]+\s+import\s+(?:[\w\s,]*,\s*)?" + _DB_NAME + r"\b"
                        r"|(?:run_path|run_module|spec_from_file_location|SourceFileLoader|import_module|__import__"
                        r"|exec|execfile|system|Popen|run|call|check_output|check_call|execSync|spawn\w*)"
                        r"\s*\([^)]*" + _DB_NAME)
_PY_VALUE_OPTS = {"-W", "-X", "-Q"}

_PUNCT = ";&|<>()\n"
_WRAPPERS = {"sudo", "env", "command", "builtin", "exec", "nohup", "time", "nice", "xargs",
             "timeout", "rtk", "proxy", "caffeinate", "stdbuf"}
_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
_PUSH_VALUE_OPTS = {"--push-option", "--repo", "--receive-pack", "--exec"}
_PUSH_DANGER_LONG = {"--delete", "--mirror", "--all", "--branches", "--tags", "--follow-tags", "--prune"}


class Undetermined(Exception):
    """push 대상을 정할 수 없다 — 에이전트 실행에서는 막는다."""


def output(decision, reason):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}


def _approval_reason(label, env):
    status = env.get(APPROVAL_ENV) or "없음"
    return (f"{PREFIX} 승인 전 {label} 금지 (승인 상태: {status}). "
            "로컬 커밋까지 하고 사람 승인(request_board_approval) 후 재시도할 것.")


def _always_reason(label):
    return (f"{PREFIX} {label} 금지 — merge·ready 전환·배포는 사람이 한다. "
            "PR 링크와 자체 리뷰 결과를 Paperclip에 보고할 것.")


def _wrapped_reason():
    return (f"{PREFIX} 셸 래핑(sh -c·eval·따옴표 안) 속 push·PR 생성은 판정할 수 없어 차단. "
            "단독 명령으로 재시도할 것.")


# ---------- 명령 해석 ----------

def _tokens(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=_PUNCT)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def _simple_commands(tokens):
    """연산자에서 끊어 (단어 목록, 입력 리다이렉트 파일) 단위로. 리다이렉트 대상은 인자에서 뺀다."""
    out, words, inputs, i = [], [], [], 0
    while i < len(tokens):
        tok = tokens[i]
        if tok and all(c in _PUNCT for c in tok):
            if any(c in ";|()\n&" for c in tok.replace(">&", "").replace("&>", "")):
                if words or inputs:
                    out.append((words, inputs))
                words, inputs = [], []
            if ("<" in tok or ">" in tok):
                if words and words[-1].isdigit():
                    words.pop()  # 2>, 1>> 같은 fd 번호
                nxt = tokens[i + 1] if i + 1 < len(tokens) else None
                if nxt is not None and not all(c in _PUNCT for c in nxt):
                    if tok.endswith("<") and not tok.endswith("<<"):
                        inputs.append(nxt)  # heredoc 구분자·here-string 값은 파일이 아니다
                    i += 1
        else:
            words.append(tok)
        i += 1
    if words or inputs:
        out.append((words, inputs))
    return out


def _strip_wrappers(words):
    words = list(words)
    while words:
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            words.pop(0)
            continue
        name = os.path.basename(words[0]).lower()
        if name not in _WRAPPERS:
            break
        words.pop(0)
        while words and words[0].startswith("-"):
            words.pop(0)
        if name == "timeout" and words:
            words.pop(0)  # 시간 인자
    return words


def _expand(token):
    """명령 밖(훅 env)에서 정해진 변수만 푼다. 명령 안에서 정한 변수는 None."""
    s = os.path.expanduser(os.path.expandvars(token))
    return None if ("$" in s or "`" in s) else s


def _resolve_dir(token, cwd):
    s = _expand(token)
    if s is None or (not os.path.isabs(s) and cwd is None):
        return None
    return os.path.normpath(os.path.join(cwd or "", s))


def _git_split(args):
    """git 전역 옵션 → (위치 지정 옵션, 하위 명령, 나머지). -c 설정은 조회 git 에 넘기지 않는다."""
    loc, i = [], 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        if a in _GIT_VALUE_OPTS and i + 1 < len(args):
            if a in ("-C", "--git-dir", "--work-tree"):
                loc += [a, args[i + 1]]
            i += 2
            continue
        if a.startswith("-C") and len(a) > 2:
            loc += ["-C", a[2:]]
        elif a.startswith(("--git-dir=", "--work-tree=")):
            loc.append(a)
        i += 1
    return loc, (args[i] if i < len(args) else ""), args[i + 1:]


def _gh_parts(args):
    """gh 인자 → (그룹, 하위 명령, 나머지 인자). pr 의 -R/--repo 값은 건너뛴다."""
    picked, rest, i = [], [], 0
    while i < len(args):
        a = args[i]
        if len(picked) < 2 and a in ("-R", "--repo") and i + 1 < len(args):
            rest += args[i:i + 2]
            i += 2
            continue
        if len(picked) < 2 and not a.startswith("-"):
            picked.append(a)
        else:
            rest.append(a)
        i += 1
    picked += [""] * (2 - len(picked))
    return picked[0], picked[1], rest


def _scan(command, cwd):
    """단순 명령마다 git push·gh 호출을 찾는다. cd 는 이후 명령의 작업 위치를 바꾼다."""
    cur, found = cwd, []
    for words, _ in _simple_commands(_tokens(command)):
        words = _strip_wrappers(words)
        if not words:
            continue
        name, args = os.path.basename(words[0]).lower().removesuffix(".exe"), words[1:]
        if name in ("cd", "pushd"):
            if args and args[0] == "-":
                cur = None
            else:
                cur = _resolve_dir(next((a for a in args if not a.startswith("-")), "~"), cur)
        elif name == "git":
            loc, sub, rest = _git_split(args)
            if sub == "push":
                found.append(("push", loc, rest, cur))
        elif name == "gh":
            found.append(("gh",) + _gh_parts(args) + (args,))
    return found


def _opt_value(args, long, short):
    value = None
    for i, a in enumerate(args):
        if a in (long, short) and i + 1 < len(args):
            value = args[i + 1]
        elif a.startswith(long + "="):
            value = a.split("=", 1)[1]
        elif a.startswith(short) and len(a) > len(short) and not a.startswith("--"):
            value = a[len(short):]
    return value


# ---------- git push ----------

def _push_args(rest):
    """(위험 형태 또는 None, refspec 목록). 첫 위치 인자는 원격이다."""
    positional, i = [], 0
    while i < len(rest):
        a = rest[i]
        if a == "--":
            positional += rest[i + 1:]
            break
        if a.startswith("--"):
            name = a.split("=", 1)[0]
            if name.startswith("--force") or name in _PUSH_DANGER_LONG:
                return a, []
            if name in _PUSH_VALUE_OPTS and "=" not in a:
                i += 1
        elif a.startswith("-") and len(a) > 1:
            for j, ch in enumerate(a[1:]):
                if ch in "fd":
                    return a, []
                if ch == "o":  # -o <push-option>
                    if j == len(a) - 2:
                        i += 1
                    break
        else:
            positional.append(a)
        i += 1
    return None, positional[1:]


def _git(loc, cwd, *args):
    if cwd is None or not os.path.isdir(cwd):
        raise Undetermined
    locs = []
    for a in loc:
        value = _expand(a)
        if value is None:
            raise Undetermined
        locs.append(value)
    try:
        return subprocess.run(["git", *locs, *args], cwd=cwd, capture_output=True, text=True,
                              timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        raise Undetermined


def _current_branch(loc, cwd):
    r = _git(loc, cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if r.returncode != 0 or not r.stdout.strip():
        raise Undetermined
    return r.stdout.strip()  # 분리된 HEAD 는 "HEAD" — feature/* 가 아니므로 막힌다


def _implicit_push_config(loc, cwd):
    """refspec 없는 push 를 다른 브랜치로 보낼 수 있는 설정."""
    r = _git(loc, cwd, "config", "--get-regexp", r"^(push\.default|remote\..*\.push)$")
    if r.returncode not in (0, 1):
        raise Undetermined
    for line in r.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "push.default" and value.strip() in ("matching", "upstream", "tracking"):
            return f"push.default={value.strip()}"
        if key.startswith("remote.") and key.endswith(".push"):
            return key
    return None


def _push_reason(loc, rest, cwd, env):
    if env.get(APPROVAL_ENV) != "approved":
        return _approval_reason("git push", env)
    danger, refspecs = _push_args(rest)
    if danger:
        return f"{PREFIX} 강제·삭제 형태 push 금지 (옵션: {danger}). 옵션을 빼고 feature 브랜치로 일반 push할 것."
    targets = []
    try:
        if not refspecs:
            implicit = _implicit_push_config(loc, cwd)
            if implicit:
                return (f"{PREFIX} {implicit} 설정이라 push 대상이 암묵적이어서 차단. "
                        "`git push -u origin HEAD:feature/{이슈ID}`처럼 대상을 명시해 재시도할 것.")
            targets.append(_current_branch(loc, cwd))
        for raw in refspecs:
            spec = _expand(raw)
            if spec is None:
                raise Undetermined
            if spec.startswith("+"):
                return f"{PREFIX} 강제·삭제 형태 push 금지 (refspec: {raw}). `+`를 빼고 재시도할 것."
            src, _, dst = spec.partition(":")
            if ":" in spec and not src:
                return f"{PREFIX} 강제·삭제 형태 push 금지 (refspec: {raw}). 원격 브랜치 삭제는 사람이 한다."
            dst = dst if ":" in spec else src
            if not dst:
                raise Undetermined
            targets.append(_current_branch(loc, cwd) if dst in ("HEAD", "@") else dst)
    except Undetermined:
        return (f"{PREFIX} push 대상 브랜치를 판정하지 못해 차단. "
                "대상을 명시해 `git push -u origin feature/{이슈ID}`로 재시도할 것.")
    for target in targets:
        name = target.removeprefix("refs/heads/")
        if not any(name.startswith(p) and len(name) > len(p) for p in PUSH_BRANCH_PREFIXES):
            return (f"{PREFIX} feature/* 외 브랜치 push 금지 (대상: {target}). "
                    "`git push -u origin HEAD:feature/{이슈ID}` 형태로 재시도할 것.")
    return None


# ---------- gh ----------

def _pr_create_reason(args, env):
    if env.get(APPROVAL_ENV) != "approved":
        return _approval_reason("gh pr create", env)
    draft = any(a in ("--draft", "-d", "--draft=true") for a in args)
    base = _opt_value(args, "--base", "-B")
    if base is not None and _expand(base) not in PR_BASES:
        return (f"{PREFIX} develop 외 base PR 금지 (base: {base}). "
                "`--draft --base develop`으로 재시도할 것.")
    missing = [flag for flag, ok in (("--draft", draft), ("--base develop", base is not None)) if not ok]
    if missing:
        return (f"{PREFIX} draft PR만 허용 (누락: {' '.join(missing)}). "
                "`--draft --base develop` 추가 후 재시도할 것.")
    head = _opt_value(args, "--head", "-H")
    if head is not None:
        name = (_expand(head) or "").rsplit(":", 1)[-1]
        if not any(name.startswith(p) and len(name) > len(p) for p in PUSH_BRANCH_PREFIXES):
            return f"{PREFIX} feature/* 외 head PR 금지 (head: {head}). feature 브랜치에서 재시도할 것."
    return None


def _gh_api_reason(args):
    endpoint, method, fields, i = None, None, False, 0
    while i < len(args):
        a = args[i]
        if a in ("-X", "--method") and i + 1 < len(args):
            method, i = args[i + 1], i + 2
            continue
        if a in ("-f", "-F", "--field", "--raw-field", "--input"):
            fields, i = True, i + 2
            continue
        if a in ("-H", "--header", "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview"):
            i += 2
            continue
        if a.startswith("--method="):
            method = a.split("=", 1)[1]
        elif a.startswith("-X") and len(a) > 2:
            method = a[2:]
        elif a.startswith(("--field=", "--raw-field=", "--input=")) or (a[:2] in ("-f", "-F") and len(a) > 2):
            fields = True
        elif not a.startswith("-") and endpoint is None:
            endpoint = a
        i += 1
    write = method.upper() not in ("GET", "HEAD") if method else fields
    if not write or endpoint is None:
        return None
    path = endpoint.split("?", 1)[0].strip("/")
    for label, rx, hint in API_WRITE_DENY:
        if rx.search(path):
            return f"{PREFIX} {label} 금지 (엔드포인트: {endpoint}). {hint}"
    return None


def _gh_reason(group, sub, args, raw, env):
    if group == "pr":
        if sub in ("merge", "ready"):
            return _always_reason(f"gh pr {sub}")
        if sub in ("create", "new"):
            return _pr_create_reason(args, env)
        if sub == "edit":
            base = _opt_value(args, "--base", "-B")
            if base is not None and _expand(base) not in PR_BASES:
                return f"{PREFIX} develop 외 base 변경 금지 (base: {base}). base는 develop으로 둘 것."
        if sub == "review" and any(a in ("--approve", "-a") or a.startswith("--approve=") for a in args):
            return _always_reason("gh pr review --approve")
        return None
    if (group, sub) in (("workflow", "run"), ("release", "create")):
        return _always_reason(f"gh {group} {sub}")
    if group == "api":  # 엔드포인트 앞에 옵션이 올 수 있어 원래 순서로 본다
        return _gh_api_reason(raw[raw.index("api") + 1:])
    return None


# ---------- YouTrack ----------

def _youtrack_write(command):
    # 팀 도구는 명령에 YouTrack 이 안 보인다 — 쓰기 도구를 이름으로 판정한다
    if re.search(r"ticket_schedule\.py\b", command) and re.search(r"\bapply\b", command) \
            and "--dry-run" not in command:
        return "ticket_schedule.py apply"
    if "youtrack" not in command.casefold():
        return None
    for segment in re.split(r"\|\|?|;|&&|\n", command):
        if not _HTTP_CLIENT.search(segment):
            continue
        method, data, httpie = (rx.search(segment) for rx in _HTTP_WRITE)
        if method or httpie or (data and not _HTTP_GET.search(segment)):
            return "HTTP 쓰기 요청"
    if _INTERPRETER.search(command) and _CODE_HTTP_WRITE.search(command):
        return "스크립트 HTTP 쓰기"
    return None


# ---------- 운영 DB ----------

def _py_target(args):
    """python 인자 → ("file", 경로) | ("module", 이름) | ("code", None) | ("stdin", None)."""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-c" or (a.startswith("-") and not a.startswith("--") and "c" in a[1:] and a[1] != "m"):
            return "code", None
        if a == "-m" and i + 1 < len(args):
            return "module", args[i + 1]
        if a.startswith("-m") and len(a) > 2:
            return "module", a[2:]
        if a == "-":
            return "stdin", None
        if a in _PY_VALUE_OPTS:
            i += 2
            continue
        if not a.startswith("-"):
            return "file", a
        i += 1
    return "stdin", None


def _db_exec(command, depth=0):
    """단순 명령마다 DB 도구를 띄우는 형태를 찾는다. 읽기(cat·grep·sed)는 실행이 아니라 지나간다."""
    for words, inputs in _simple_commands(_tokens(command.replace("`", " ; "))):
        words = _strip_wrappers(words)
        if words and os.path.basename(words[0]).lower() == "uv" and words[1:2] == ["run"]:
            words = [w for w in words[2:] if not w.startswith("-")] or words
        if not words:
            continue
        name, args = os.path.basename(words[0]), words[1:]
        lower = name.lower().removesuffix(".exe")
        if _DB_FILE.match(name) or name == "db-prod-keychain":
            return f"{name} 실행"
        if re.match(r"^python[\d.]*$", lower):
            kind, target = _py_target(args)
            if kind == "file" and _DB_FILE.match(os.path.basename(target)):
                return f"{os.path.basename(target)} 실행"
            if kind == "module" and _DB_MODULE.search(target):
                return f"python -m {target} 실행"
            if kind == "stdin" and (any(_DB_FILE.match(os.path.basename(t)) for t in inputs)
                                    or _DB_MENTION.search(command)):
                return "DB 도구를 stdin 으로 실행"
        if lower in ("swift", "swiftc") and any(os.path.basename(a) == "db_prod_keychain.swift" for a in args):
            return "keychain 헬퍼 빌드·실행"
        if depth < 3 and lower in ("sh", "bash", "zsh", "dash", "ksh"):
            for i, arg in enumerate(args[:-1]):
                if re.match(r"^-[A-Za-z]*c[A-Za-z]*$", arg):
                    label = _db_exec(args[i + 1], depth + 1)
                    if label:
                        return label
                    break
        if depth < 3 and lower == "eval" and args:
            label = _db_exec(" ".join(args), depth + 1)
            if label:
                return label
    return None


def _db_reason(command):
    """운영 DB 실행 경로 — 승인 env 와 무관하게 막는다. 개발 sqlcmd SELECT 는 sqlcmd-readonly 몫이다."""
    if "--from-chat-digest" in command:
        label = "--from-chat-digest"
    elif _DB_SOCKET.search(command):
        label = "게이트웨이 소켓 경로"
    elif _DB_RUN_RAW.search(command):
        label = "DB 도구 실행"
    elif _INTERPRETER.search(command) and _DB_INLINE.search(command):
        label = "DB 도구 인라인 로드"
    else:
        try:
            label = _db_exec(command)
        except ValueError:
            label = "해석할 수 없는 명령의 DB 도구 언급" if _DB_MENTION.search(command) else None
    if not label:
        return None
    return (f"{PREFIX} 운영 DB 경로 금지 ({label}). SQL은 data-requests-dev2에 작성·로컬 커밋까지만 하고 "
            "운영 실행·개발 DML은 사람이 한다. 개발 DB 검증은 sqlcmd 단일 SELECT로 할 것.")


# ---------- 판정 ----------

def _agent_bash(command, cwd, env):
    reason = _db_reason(command)
    if reason:
        return reason
    label = _youtrack_write(command)
    if label:
        return (f"{PREFIX} YouTrack 쓰기 금지 (명령: {label}). "
                "YouTrack→Paperclip 단방향이므로 결과는 Paperclip 보고로 남길 것.")
    for label, rx in ALWAYS_DENY:
        if rx.search(command):
            return _always_reason(label)
    try:
        found = _scan(command, cwd)
    except ValueError:
        return _wrapped_reason() if (PUSH_RE.search(command) or PR_CREATE_RE.search(command)) else None
    pushes = [f for f in found if f[0] == "push"]
    creates = [f for f in found if f[0] == "gh" and f[1] == "pr" and f[2] in ("create", "new")]
    if len(PUSH_RE.findall(command)) > len(pushes) or len(PR_CREATE_RE.findall(command)) > len(creates):
        return _wrapped_reason()
    for item in found:
        reason = _push_reason(*item[1:], env) if item[0] == "push" else _gh_reason(*item[1:], env)
        if reason:
            return reason
    return None


def _human_bash(command, cwd):
    labels = []
    if PUSH_RE.search(command):
        labels.append("git push")
    if PR_CREATE_RE.search(command):
        labels.append("gh pr create")
    try:
        for item in _scan(command, cwd):
            label = "git push" if item[0] == "push" else (
                "gh pr create" if item[1] == "pr" and item[2] in ("create", "new") else None)
            if label and label not in labels:
                labels.append(label)
    except ValueError:
        pass
    if not labels:
        return None
    return ("ask", f"사용자 확인 필요: {', '.join(labels)} — 푸시·PR 생성은 사용자 확인 후 실행한다 (AI 사용 정책).")


def decide(event, env):
    """(decision, reason) 또는 None."""
    agent = bool(env.get(RUN_ENV))
    tool = event.get("tool_name") or ""
    payload = event.get("tool_input")
    if not isinstance(payload, dict):
        raise ValueError("tool_input")
    if tool.startswith("mcp__"):
        name = tool.casefold()
        if agent and "youtrack" in name and _YT_MCP_WRITE.search(name.split("__", 2)[-1]):
            return ("deny", f"{PREFIX} YouTrack 쓰기 금지 (도구: {tool}). "
                            "YouTrack→Paperclip 단방향이므로 결과는 Paperclip 보고로 남길 것.")
        return None
    command = payload.get("command", payload.get("cmd"))
    if command is None and tool != "Bash":
        return None
    if not isinstance(command, str):
        raise ValueError("command")
    command = re.sub(r"\\\r?\n", " ", command)  # 줄 연속은 한 명령이다
    cwd = event.get("cwd") or os.getcwd()
    if not agent:
        return _human_bash(command, cwd)
    reason = _agent_bash(command, cwd, env)
    return ("deny", reason) if reason else None


def main():
    agent = bool(os.environ.get(RUN_ENV))
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("event")
        result = decide(event, os.environ)
    except Exception as exc:  # 무인 실행은 판정 실패를 닫고, 사람 세션은 열어 둔다
        result = ("deny", f"{PREFIX} 가드가 입력을 판정하지 못해 차단 ({type(exc).__name__}). "
                          "하네스 설치·훅 입력 형식을 확인할 것.") if agent else None
    if result:
        print(json.dumps(output(*result), ensure_ascii=False))


if __name__ == "__main__":
    main()
