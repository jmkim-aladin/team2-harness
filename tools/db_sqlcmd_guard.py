#!/usr/bin/env python3
"""Conservative guard for visible sqlcmd calls; never a SQL/network security boundary.

No DB connection or credential access. Raw sqlcmd is read-only; DML uses db_execute.py.
Scripts, other drivers, shell aliases and runtime hook registration need separate controls.
"""

import json
import re
import shlex
import sys

DEV_HOST = "rds-cluster-cool-dev.cleuiesc8bqi.ap-northeast-2.rds.amazonaws.com"
DEV_DATABASES = {"webcatalog", "tobe", "community", "weblog", "webmarket"}
VALUE_OPTIONS = {"-S", "-d", "-U", "-Q", "-h", "-l", "-t", "-w", "-s", "-r", "-f"}
FLAG_OPTIONS = {"-C", "-W", "-b", "-u", "-R", "-X"}
BLOCKED_WORDS = set("""
MERGE DROP ALTER TRUNCATE CREATE EXEC EXECUTE GRANT REVOKE DENY
BULK BACKUP RESTORE DBCC USE DECLARE BEGIN COMMIT ROLLBACK SAVE TRANSACTION
WAITFOR SHUTDOWN KILL RECONFIGURE GO OPENQUERY OPENROWSET OPENDATASOURCE
NEXT ENABLE DISABLE
""".split())


def sql_reason(sql):
    # Restrict the accepted surface rather than trying to parse arbitrary T-SQL.
    if any(marker in sql for marker in ("$", "`", "\\", "--", "/*", "*/")):
        return "SQL 확장·주석은 자동 경로 밖입니다. 리터럴 SQL을 사용하세요."
    if re.search(r"(?m)^\s*[:!]", sql):
        return "sqlcmd 내부 명령은 자동 경로 밖입니다."
    # sqlcmd processes batch delimiters before SQL Server parses literals.
    # Inspect raw input so a GO line inside a quoted value cannot escape the
    # executor's transaction/row-count wrapper.
    if re.search(r"(?im)^\s*GO\b", sql):
        return "sqlcmd GO 배치 구분자는 문자열 안에서도 자동 경로 밖입니다."
    without_strings = re.sub(r"N?'(?:[^']|'')*'", "''", sql, flags=re.I)
    if "'" in without_strings.replace("''", ""):
        return "닫히지 않은 SQL 문자열입니다."
    body = without_strings.strip().removesuffix(";").strip()
    if ";" in body:
        return "자동 경로는 SQL 한 문장만 허용합니다."
    words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", body.upper())
    if not words or words[0] not in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
        return "개발 자동 경로는 SELECT·INSERT VALUES·조건부 UPDATE/DELETE 한 문장입니다."
    if set(words) & BLOCKED_WORDS:
        return "DDL·프로시저·세션 명령은 별도 승인 실행 경로를 사용하세요."
    if set(words[1:]) & {"INSERT", "UPDATE", "DELETE"}:
        return "자동 경로는 변경문 한 개만 허용합니다."
    if "SET" in words and words[0] != "UPDATE":
        return "세션 설정 변경은 자동 경로 밖입니다."
    # Cross-database/server names are deliberately outside the automatic path.
    identifier = r'(?:\[[^\]]+\]|"[^"]+"|[A-Za-z_][\w]*)'
    if re.search(identifier + r"\s*\.\s*(?:" + identifier + r")?\s*\.", body):
        return "다른 DB·링크드 서버 참조는 자동 경로 밖입니다."
    if words[0] == "SELECT" and "INTO" in words:
        return "SELECT INTO는 테이블 생성이므로 별도 승인 대상입니다."
    if words[0] == "INSERT":
        if "VALUES" not in words or "SELECT" in words or "OUTPUT" in words:
            return "개발 입력은 INSERT VALUES만 허용합니다. 대량 복사·OUTPUT은 별도 검토 대상입니다."
    if words[0] in {"UPDATE", "DELETE"}:
        if "WHERE" not in words or "SELECT" in words or "OUTPUT" in words or "JOIN" in words:
            return "수정·삭제는 직접 대상 조건이 있는 단일 테이블 문장을 사용하세요. 하위 조회·조인·OUTPUT은 별도 검토 대상입니다."
        if words[0] == "UPDATE" and "FROM" in words:
            return "UPDATE FROM은 별도 검토 대상입니다."
    if words[0] != "SELECT":
        # Literal DML only. This deliberately rejects expressions/subqueries and
        # tautological predicates instead of attempting full SQL interpretation.
        value = r"(?:''|NULL|0x[0-9A-F]+|[-+]?\d+(?:\.\d+)?)"
        table = identifier + r"(?:\s*\.\s*" + identifier + r")?"
        values = value + r"(?:\s*,\s*" + value + r")*"
        predicate = identifier + r"\s*(?:=\s*" + value + r"|IN\s*\(\s*" + values + r"\s*\))"
        where = predicate + r"(?:\s+AND\s+" + predicate + r")*"
        assignment = identifier + r"\s*=\s*" + value
        if words[0] == "INSERT":
            row = r"\(\s*" + values + r"\s*\)"
            columns = identifier + r"(?:\s*,\s*" + identifier + r")*"
            pattern = r"INSERT\s+INTO\s+" + table + r"\s*\(\s*" + columns + r"\s*\)\s+VALUES\s*" + row + r"(?:\s*,\s*" + row + r"){0,99}"
        elif words[0] == "UPDATE":
            pattern = r"UPDATE\s+" + table + r"\s+SET\s+" + assignment + r"(?:\s*,\s*" + assignment + r")*\s+WHERE\s+" + where
        else:
            pattern = r"DELETE\s+FROM\s+" + table + r"\s+WHERE\s+" + where
        if not re.fullmatch(pattern, body, flags=re.I):
            return "자동 DML은 열을 지정한 리터럴 VALUES(100행 이하), 또는 열=값/IN과 AND로 대상을 지정한 단순 수정·삭제만 지원합니다."
    return None


def call_reason(args):
    options = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in FLAG_OPTIONS:
            i += 1
            continue
        key = arg[:2]
        if key not in VALUE_OPTIONS:
            return "sqlcmd는 리터럴 -S/-d/-Q 경로만 지원합니다. 파일·대화형·변수·리다이렉트 입력은 별도 검토하세요."
        if key in options:
            return "중복 sqlcmd 옵션은 자동 경로 밖입니다."
        if len(arg) > 2:
            value = arg[2:]
        else:
            i += 1
            if i == len(args):
                return "sqlcmd 옵션 값이 없습니다."
            value = args[i]
        options[key] = value
        i += 1
    if options.get("-S", "").lower() != DEV_HOST:
        return "등록된 개발 호스트만 직접 조회·입력할 수 있습니다. 운영 접근은 전용 실행기 개통 후 가능합니다."
    if options.get("-d", "").lower() not in DEV_DATABASES:
        return "등록된 개발 DB를 -d에 명시하세요."
    if "-Q" not in options:
        return "자동 경로는 -Q 한 번 실행만 허용합니다."
    reason = sql_reason(options["-Q"])
    if reason:
        return reason
    if not re.match(r"\s*SELECT\b", options["-Q"], re.I):
        return "개발 DML은 tools/db_execute.py로 실행하세요. 실제 변경 건수·작업 누적 한도와 timeout을 실행 단계에서 검사합니다."
    return None


def command_reason(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return "sqlcmd 명령을 해석할 수 없습니다." if "sqlcmd" in command.lower() else None
    for index, token in enumerate(tokens):
        if token.replace("\\", "/").rsplit("/", 1)[-1].lower() not in {"sqlcmd", "sqlcmd.exe"}:
            continue
        end = index + 1
        while end < len(tokens) and tokens[end] not in {";", "&&", "||", "\n"}:
            end += 1
        reason = call_reason(tokens[index + 1:end])
        if reason:
            return reason
    return None


def main():
    try:
        event = json.load(sys.stdin)
        payload = event.get("tool_input", {})
        command = payload.get("command", payload.get("cmd"))
        if not isinstance(command, str):
            raise ValueError("missing command")
        reason = command_reason(command)
    except (ValueError, TypeError, AttributeError):
        reason = "DB 명령 훅 입력을 해석할 수 없습니다. 실행기 연결을 확인하세요."
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
