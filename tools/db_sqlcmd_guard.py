#!/usr/bin/env python3
"""Conservative guard for visible sqlcmd calls; never a SQL/network security boundary.

No DB connection or credential access. Raw sqlcmd on the registered dev host may run
read scripts (-Q literal or -i file): SELECT/CTE, variables, control flow, session
read options, #temp tables, dev-DB 3-part names. Permanent-object DML uses
db_execute.py (sql_reason below is its single-statement check). Scripts, other
drivers, shell aliases and runtime hook registration need separate controls.
"""

import json
import os
import re
import shlex
import stat
import sys

DEV_HOST = "rds-cluster-cool-dev.cleuiesc8bqi.ap-northeast-2.rds.amazonaws.com"
DEV_DATABASES = {"webcatalog", "tobe", "community", "weblog", "webmarket"}
VALUE_OPTIONS = {"-S", "-d", "-U", "-Q", "-i", "-h", "-l", "-t", "-w", "-s", "-r", "-f"}
FLAG_OPTIONS = {"-C", "-W", "-b", "-u", "-R", "-X"}
BLOCKED_WORDS = set("""
MERGE DROP ALTER TRUNCATE CREATE EXEC EXECUTE GRANT REVOKE DENY
BULK BACKUP RESTORE DBCC USE DECLARE BEGIN COMMIT ROLLBACK SAVE TRANSACTION
WAITFOR SHUTDOWN KILL RECONFIGURE GO OPENQUERY OPENROWSET OPENDATASOURCE
NEXT ENABLE DISABLE
""".split())


def sql_reason(sql):
    """Single literal DML/SELECT statement check shared with tools/db_execute.py."""
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


# ---------- 개발 DB 읽기 스크립트 (2026-10-22 사용자 결정: 개발 DB 조회 제한 해제) ----------

MAX_SCRIPT_BYTES = 1024 * 1024
DEV_DB_LIST = "WebCatalog/ToBe/Community/WebLog/WebMarket"
DML_MESSAGE = ("영구 테이블 변경은 읽기 스크립트 밖입니다. 개발 DML은 tools/db_execute.py로 실행하세요. "
               "실제 변경 건수·작업 누적 한도와 timeout을 실행 단계에서 검사합니다.")
DDL_MESSAGE = ("영구 객체 DDL(CREATE·ALTER·DROP·TRUNCATE 등)은 별도 승인 대상입니다. "
               "읽기 스크립트에서는 임시 테이블(#이름)만 만들고 비우고 지울 수 있습니다.")
EXEC_MESSAGE = ("프로시저 실행은 sp_help·sp_helptext·sp_columns(리터럴 인자)만 허용합니다. "
                "임의 SP·sp_executesql·동적 SQL은 별도 승인 실행 경로를 사용하세요.")
TRAN_MESSAGE = "트랜잭션 제어(BEGIN TRAN·COMMIT·ROLLBACK·SAVE)는 읽기 스크립트 밖입니다. 문장 단위 자동 커밋으로 조회하세요."
SET_MESSAGE = ("지원하지 않는 세션 설정입니다. 변수 대입(SET @x = …)과 NOCOUNT·STATISTICS·"
               "TRANSACTION ISOLATION LEVEL 같은 조회용 옵션만 허용합니다.")
CURSOR_MESSAGE = "커서 구문은 읽기 스크립트에서 지원하지 않습니다. 집합 쿼리나 임시 테이블을 쓰세요."
INTO_MESSAGE = ("SELECT INTO·OUTPUT INTO는 임시 테이블(#이름)이나 테이블 변수만 대상으로 할 수 있습니다. "
                "영구 테이블 생성은 별도 승인 대상입니다.")
GLOBAL_TEMP_MESSAGE = "전역 임시 테이블(##이름)은 다른 세션과 공유되므로 허용하지 않습니다. #이름을 쓰세요."
SQLCMD_COMMAND_MESSAGE = ("sqlcmd 내부 명령(:r·:!!·:connect·:setvar·!!·ED·EXIT 등)은 자동 경로 밖입니다. "
                          "필요한 SQL을 파일 하나에 직접 쓰세요.")

# T-SQL 예약어 전체. 예약어는 따옴표 없이 이름으로 쓸 수 없으므로 문자열·주석·[이름] 밖에
# 나타나면 그 구문이다. 읽기 스크립트에 필요한 것만 ALLOWED_RESERVED로 열고 나머지는 거부한다.
RESERVED = set("""
ADD ALL ALTER AND ANY AS ASC AUTHORIZATION BACKUP BEGIN BETWEEN BREAK BROWSE BULK BY CASCADE CASE
CHECK CHECKPOINT CLOSE CLUSTERED COALESCE COLLATE COLUMN COMMIT COMPUTE CONSTRAINT CONTAINS
CONTAINSTABLE CONTINUE CONVERT CREATE CROSS CURRENT CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP
CURRENT_USER CURSOR DATABASE DBCC DEALLOCATE DECLARE DEFAULT DELETE DENY DESC DISK DISTINCT
DISTRIBUTED DOUBLE DROP DUMP ELSE END ERRLVL ESCAPE EXCEPT EXEC EXECUTE EXISTS EXIT EXTERNAL FETCH
FILE FILLFACTOR FOR FOREIGN FREETEXT FREETEXTTABLE FROM FULL FUNCTION GOTO GRANT GROUP HAVING
HOLDLOCK IDENTITY IDENTITY_INSERT IDENTITYCOL IF IN INDEX INNER INSERT INTERSECT INTO IS JOIN KEY
KILL LEFT LIKE LINENO LOAD MERGE NATIONAL NOCHECK NONCLUSTERED NOT NULL NULLIF OF OFF OFFSETS ON
OPEN OPENDATASOURCE OPENQUERY OPENROWSET OPENXML OPTION OR ORDER OUTER OVER PERCENT PIVOT PLAN
PRECISION PRIMARY PRINT PROC PROCEDURE PUBLIC RAISERROR READ READTEXT RECONFIGURE REFERENCES
REPLICATION RESTORE RESTRICT RETURN REVERT REVOKE RIGHT ROLLBACK ROWCOUNT ROWGUIDCOL RULE SAVE
SCHEMA SECURITYAUDIT SELECT SEMANTICKEYPHRASETABLE SEMANTICSIMILARITYDETAILSTABLE
SEMANTICSIMILARITYTABLE SESSION_USER SET SETUSER SHUTDOWN SOME STATISTICS SYSTEM_USER TABLE
TABLESAMPLE TEXTSIZE THEN TO TOP TRAN TRANSACTION TRIGGER TRUNCATE TRY_CONVERT TSEQUAL UNION
UNIQUE UNPIVOT UPDATE UPDATETEXT USE USER VALUES VARYING VIEW WAITFOR WHEN WHERE WHILE WITH
WITHIN WRITETEXT
""".split())
ALLOWED_RESERVED = set("""
ALL AND ANY AS ASC BEGIN BETWEEN BREAK BROWSE BY CASE CHECK CLUSTERED COALESCE COLLATE CONSTRAINT
CONTAINS CONTAINSTABLE CONTINUE CONVERT CREATE CROSS CURRENT CURRENT_DATE CURRENT_TIME
CURRENT_TIMESTAMP CURRENT_USER DECLARE DEFAULT DELETE DESC DISTINCT DOUBLE DROP ELSE END ESCAPE
EXCEPT EXEC EXECUTE EXISTS FETCH FOR FREETEXT FREETEXTTABLE FROM FULL GROUP HAVING HOLDLOCK
IDENTITY IDENTITYCOL IF IN INDEX INNER INSERT INTERSECT INTO IS JOIN KEY LEFT LIKE NATIONAL
NONCLUSTERED NOT NULL NULLIF OF OFF ON OPTION OR ORDER OUTER OVER PERCENT PIVOT PRECISION PRIMARY
PRINT RAISERROR READ RETURN RIGHT ROWCOUNT SELECT SESSION_USER SET SOME STATISTICS SYSTEM_USER TABLE
TABLESAMPLE TEXTSIZE THEN TOP TRAN TRANSACTION TRUNCATE TRY_CONVERT UNION UNIQUE UNPIVOT UPDATE USE
USER VALUES WHEN WHERE WHILE WITH WITHIN
""".split())
RESERVED_MESSAGES = {
    **dict.fromkeys(["COMMIT", "ROLLBACK", "SAVE", "DISTRIBUTED"], TRAN_MESSAGE),
    **dict.fromkeys(["CURSOR", "OPEN", "CLOSE", "DEALLOCATE"], CURSOR_MESSAGE),
    **dict.fromkeys(["ALTER", "ADD", "TRIGGER", "VIEW", "PROC", "PROCEDURE", "FUNCTION", "DATABASE",
                     "SCHEMA", "REFERENCES", "FOREIGN", "CASCADE", "NOCHECK"], DDL_MESSAGE),
    "MERGE": "MERGE는 자동 경로 밖입니다. 개발 DML은 tools/db_execute.py, 그 밖의 변경은 별도 승인 경로를 사용하세요.",
    **dict.fromkeys(["GRANT", "REVOKE", "DENY", "BACKUP", "RESTORE", "DBCC", "SHUTDOWN", "KILL",
                     "RECONFIGURE", "CHECKPOINT", "SETUSER", "REVERT", "DUMP", "LOAD", "DISK"],
                    "권한·관리 명령은 별도 승인 실행 경로를 사용하세요."),
    **dict.fromkeys(["BULK", "OPENQUERY", "OPENROWSET", "OPENDATASOURCE", "OPENXML", "EXTERNAL", "FILE"],
                    "외부 데이터 접근(BULK·OPENQUERY·OPENROWSET 등)은 다른 서버·파일에 닿을 수 있어 자동 경로 밖입니다."),
}
# 예약어가 아니어서 열 이름일 수도 있는 위험 구문 단어 — 열이면 [대괄호]로 감싸게 안내한다.
NONRESERVED_DENIED = {"RECEIVE", "SEND", "CONVERSATION", "DIALOG", "ENABLE", "DISABLE"}
BATCH_STARTS = {"SELECT", "WITH", "DECLARE", "SET", "IF", "WHILE", "BEGIN", "PRINT", "RAISERROR", "RETURN",
                "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "TRUNCATE", "USE", "EXEC", "EXECUTE"}
STATEMENT_WORDS = BATCH_STARTS | {"ELSE", "END", "BREAK", "CONTINUE"}
ALLOWED_PROCS = {"SP_HELP", "SP_HELPTEXT", "SP_COLUMNS"}
SET_OPTIONS = set("""
NOCOUNT STATISTICS ANSI_NULLS ANSI_WARNINGS ANSI_PADDING ANSI_NULL_DFLT_ON ANSI_NULL_DFLT_OFF
ARITHABORT ARITHIGNORE CONCAT_NULL_YIELDS_NULL NUMERIC_ROUNDABORT XACT_ABORT DATEFIRST DATEFORMAT
LANGUAGE LOCK_TIMEOUT ROWCOUNT TEXTSIZE DEADLOCK_PRIORITY QUERY_GOVERNOR_COST_LIMIT FMTONLY NOEXEC
PARSEONLY FORCEPLAN SHOWPLAN_TEXT SHOWPLAN_ALL SHOWPLAN_XML
""".split())
STATISTICS_KINDS = {"IO", "TIME", "XML", "PROFILE"}
ISOLATION_LEVELS = [("READ", "UNCOMMITTED"), ("READ", "COMMITTED"), ("REPEATABLE", "READ"),
                    ("SNAPSHOT",), ("SERIALIZABLE",)]
XML_METHODS = {"VALUE", "QUERY", "NODES", "EXIST"}
NAME_KINDS = {"word", "bracket", "dquote", "temp", "var"}
EOF = ("eof", "")

_TOKEN = re.compile(r"""
  (?P<ws>\s+)
| (?P<line_comment>--[^\n]*)
| (?P<string>[Nn]?'(?:[^']|'')*')
| (?P<bracket>\[(?:[^\]]|\]\])*\])
| (?P<dquote>"(?:[^"]|"")*")
| (?P<number>0[xX][0-9A-Fa-f]*|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
| (?P<var>@[\w@#$]*)
| (?P<temp>\#[\w@#$]+)
| (?P<word>[^\W\d][\w@#$]*)
| (?P<op>[-+*/%=<>!&|^~(),.;])
""", re.X)


def _raw_reason(sql):
    """sqlcmd가 T-SQL 해석 전에 줄 단위로 처리하는 것 — 문자열·주석 안에서도 본다."""
    if len(sql.encode("utf-8", "surrogatepass")) > MAX_SCRIPT_BYTES:
        return "SQL이 1 MiB를 넘습니다. 나눠서 검증하세요."
    if "\x00" in sql:
        return "SQL에 NUL 문자가 있습니다. 텍스트 SQL을 사용하세요."
    if "$(" in sql:
        return "sqlcmd 변수 $( )는 실행 전에 치환돼 검사한 SQL과 달라질 수 있습니다. 값을 리터럴로 쓰세요."
    # 백틱은 sqlcmd·T-SQL에 의미가 없다 — 문자열·주석 밖이면 토큰화에서 거부하고, -Q는 셸 확장이라 call_reason이 거부한다.
    # 줄 경계가 sqlcmd와 어긋나면 GO·내부 명령 판정도 어긋난다.
    if re.search(r"\r(?!\n)|[\x0b\x0c\x1c-\x1e\x85\u2028\u2029]", sql):
        return "줄바꿈은 \\n 또는 \\r\\n만 지원합니다."
    for line in sql.split("\n"):
        line = line.removesuffix("\r")
        if re.match(r"\s*(?::|!!)", line) or re.match(r"(?i)\s*(?:ED|RESET|EXIT|QUIT)(?=\s|\(|$)", line):
            return SQLCMD_COMMAND_MESSAGE
        if re.match(r"(?i)\s*GO\b", line) and not re.fullmatch(r"(?i)[ \t]*GO[ \t]*", line):
            return "GO는 한 줄에 단독으로만 쓰세요. 반복 횟수·같은 줄 주석은 지원하지 않습니다."
    return None


def _tokenize(batch):
    tokens = []
    pos = 0
    while pos < len(batch):
        if batch.startswith("/*", pos):
            depth, pos = 1, pos + 2  # T-SQL 블록 주석은 중첩된다
            while depth and pos < len(batch):
                if batch.startswith("/*", pos):
                    depth, pos = depth + 1, pos + 2
                elif batch.startswith("*/", pos):
                    depth, pos = depth - 1, pos + 2
                else:
                    pos += 1
            if depth:
                return None, "닫히지 않은 블록 주석입니다. 주석·문자열 안의 GO 줄에서도 sqlcmd는 배치를 나눕니다."
            continue
        match = _TOKEN.match(batch, pos)
        if not match:
            char = batch[pos]
            if char == "'":
                return None, "닫히지 않은 SQL 문자열입니다. 문자열 안의 GO 줄에서도 sqlcmd는 배치를 나눕니다."
            if char in '["':
                return None, "닫히지 않은 [이름]·\"이름\"입니다."
            return None, f"읽기 스크립트에서 해석할 수 없는 문자({char!r})입니다. 문자열 밖의 $·\\·:·{{ }}는 지원하지 않습니다."
        kind = match.lastgroup
        if kind not in {"ws", "line_comment"}:
            tokens.append((kind, match.group()))
        pos = match.end()
    return _Tokens(tokens), None


class _Tokens(list):
    """범위 밖 인덱스는 EOF — 앞뒤를 내다보는 규칙이 경계에서 IndexError로 열리지 않게 한다."""

    def __getitem__(self, index):
        if isinstance(index, int) and not 0 <= index < len(self):
            return EOF
        return super().__getitem__(index)


def _name(token):
    kind, text = token
    if kind == "bracket":
        return text[1:-1].replace("]]", "]")
    if kind == "dquote":
        return text[1:-1].replace('""', '"')
    return text


def _word(token, *words):
    return token[0] == "word" and (not words or token[1].upper() in words)


def _local_target(token, allow_var=True):
    """세션 안에서만 보이는 대상 — #임시 테이블(전역 ## 제외) 또는 테이블 변수."""
    kind, text = token
    return (kind == "temp" and not text.startswith("##")) or (allow_var and kind == "var" and not text.startswith("@@"))


def _after_paren(toks, j):
    """toks[j] == '(' 일 때 짝 ')' 다음 위치."""
    depth = 0
    for k in range(j, len(toks)):
        if toks[k] == ("op", "("):
            depth += 1
        elif toks[k] == ("op", ")"):
            depth -= 1
            if not depth:
                return k + 1
    return len(toks)  # 짝이 없으면 EOF 위치


def _skip_top(toks, j):
    if _word(toks[j], "TOP") and toks[j + 1] == ("op", "("):
        j = _after_paren(toks, j + 1)
        if _word(toks[j], "PERCENT"):
            j += 1
    return j


def _temp_index(toks, j):
    """CREATE [UNIQUE] [CLUSTERED|NONCLUSTERED] INDEX 이름 ON #임시 — 임시 테이블 DDL이다."""
    if _word(toks[j], "UNIQUE"):
        j += 1
    if _word(toks[j], "CLUSTERED", "NONCLUSTERED"):
        j += 1
    return (_word(toks[j], "INDEX") and toks[j + 1][0] in {"word", "bracket"} and _word(toks[j + 2], "ON")
            and _local_target(toks[j + 3], allow_var=False) and toks[j + 4] != ("op", "."))


def _literal_at(toks, k):
    """리터럴 인자 길이(없으면 0) — 문자열·숫자·NULL·DEFAULT, 부호 붙은 숫자."""
    kind = toks[k][0]
    if kind in {"string", "number"} or _word(toks[k], "NULL", "DEFAULT"):
        return 1
    if toks[k] in {("op", "-"), ("op", "+")} and toks[k + 1][0] == "number":
        return 2
    return 0


def _exec_reason(toks, i):
    j = i + 1
    if _word(toks[j], "SYS") and toks[j + 1] == ("op", "."):
        j += 2
    if not _word(toks[j], *ALLOWED_PROCS) or toks[j + 1] == ("op", "."):
        return EXEC_MESSAGE
    k = j + 1
    while True:
        size = _literal_at(toks, k)
        if not size and _local_target(toks[k]) and toks[k + 1] == ("op", "="):
            size = _literal_at(toks, k + 2)
            size = size + 2 if size else 0
        if not size:
            break
        k += size
        if toks[k] != ("op", ","):
            break
        k += 1
    if toks[k] not in {EOF, ("op", ";")} and not _word(toks[k], *STATEMENT_WORDS):
        return EXEC_MESSAGE
    return None


def _set_reason(toks, i):
    j = i + 1
    if _local_target(toks[j]):
        return None  # 변수 대입
    if _word(toks[j], "TRAN", "TRANSACTION"):
        if _word(toks[j + 1], "ISOLATION") and _word(toks[j + 2], "LEVEL"):
            level = (toks[j + 3][1].upper(), toks[j + 4][1].upper())
            if any(level[:len(option)] == option for option in ISOLATION_LEVELS):
                return None
        return SET_MESSAGE
    # SET A, B ON / SET STATISTICS IO, TIME ON — 쉼표로 이은 옵션도 모두 목록 안이어야 한다.
    names = STATISTICS_KINDS if _word(toks[j], "STATISTICS") else SET_OPTIONS - {"STATISTICS"}
    if _word(toks[j], "STATISTICS"):
        j += 1
    while _word(toks[j], *names):
        j += 1
        if toks[j] != ("op", ","):
            return None
        j += 1
    return SET_MESSAGE


def _batch_reason(toks):
    reason = _keyword_reason(toks)
    if reason:
        return reason
    start = 0
    while toks[start] == ("op", ";"):
        start += 1
    if toks[start] != EOF and not _word(toks[start], *BATCH_STARTS):
        # 배치 첫 문장은 EXEC 없이도 프로시저 호출로 실행된다.
        return ("배치 첫 구문이 허용 목록(SELECT·WITH·DECLARE·SET·IF·WHILE·BEGIN·PRINT·임시 테이블 작업·"
                "USE·EXEC sp_help 등) 밖입니다. EXEC 없는 프로시저 호출은 지원하지 않습니다.")
    return _names_reason(toks)


def _keyword_reason(toks):
    update_sets = set()
    for i, token in enumerate(toks):
        kind, text = token
        if kind == "temp" and text.startswith("##"):
            return GLOBAL_TEMP_MESSAGE
        if kind != "word" or (i and toks[i - 1] == ("op", ".")):
            continue  # 점 뒤 단어는 이름의 일부
        word = text.upper()
        nxt = toks[i + 1]
        if word in RESERVED and word not in ALLOWED_RESERVED:
            return RESERVED_MESSAGES.get(word, f"읽기 스크립트에서 지원하지 않는 구문입니다({word}). 별도 검토 경로를 사용하세요.")
        if word in NONRESERVED_DENIED:
            return f"서비스 브로커·트리거 제어 구문({word})은 자동 경로 밖입니다. 같은 이름의 열이면 [대괄호]로 감싸세요."
        if word == "SP_EXECUTESQL" or word.startswith("XP_"):
            return EXEC_MESSAGE
        if word == "NEXT" and _word(nxt, "VALUE"):
            return "NEXT VALUE FOR는 시퀀스 값을 소비하므로 읽기 스크립트 밖입니다."
        if word == "FETCH" and not _word(toks[i - 1], "ROW", "ROWS"):
            return CURSOR_MESSAGE
        if word in {"TRAN", "TRANSACTION"} and not _word(toks[i - 1], "SET"):
            return TRAN_MESSAGE
        if word == "BEGIN" and _word(nxt, "TRAN", "TRANSACTION", "DISTRIBUTED"):
            return TRAN_MESSAGE
        if word == "INSERT":
            j = _skip_top(toks, i + 1)
            if _word(toks[j], "INTO"):
                j += 1
            if not _local_target(toks[j]):
                return DML_MESSAGE
        elif word == "UPDATE":
            j = _skip_top(toks, i + 1)
            if _word(toks[j], "STATISTICS"):
                return DDL_MESSAGE
            if not _local_target(toks[j]):
                return DML_MESSAGE
            j += 1
            if _word(toks[j], "WITH") and toks[j + 1] == ("op", "("):
                j = _after_paren(toks, j + 1)
            if not _word(toks[j], "SET"):
                return "임시 테이블 UPDATE는 UPDATE #이름 SET … 형태로 쓰세요."
            update_sets.add(j)
        elif word == "DELETE":
            j = _skip_top(toks, i + 1)
            if _word(toks[j], "FROM"):
                j += 1
            if not _local_target(toks[j]):
                return DML_MESSAGE
        elif word == "TRUNCATE":
            if not (_word(nxt, "TABLE") and _local_target(toks[i + 2], allow_var=False)):
                return DDL_MESSAGE
        elif word == "CREATE":
            if not (_word(nxt, "TABLE") and _local_target(toks[i + 2], allow_var=False)) and not _temp_index(toks, i + 1):
                return DDL_MESSAGE
        elif word == "RAISERROR":
            # 진행 메시지(WITH NOWAIT)는 읽기 스크립트 관용구다. WITH LOG만 서버 오류 로그에 쓴다.
            if nxt != ("op", "("):
                return "RAISERROR는 RAISERROR(메시지, 심각도, 상태) 형태로 쓰세요."
            j = _after_paren(toks, i + 1)
            if _word(toks[j], "WITH"):
                j += 1
                while _word(toks[j], "NOWAIT", "SETERROR", "LOG"):
                    if _word(toks[j], "LOG"):
                        return "RAISERROR … WITH LOG는 서버 오류 로그에 기록하므로 자동 경로 밖입니다."
                    if toks[j + 1] != ("op", ","):
                        break
                    j += 2
        elif word == "DROP":
            j = i + 2
            if _word(toks[j], "IF") and _word(toks[j + 1], "EXISTS"):
                j += 2
            if not _word(nxt, "TABLE"):
                return DDL_MESSAGE
            while True:
                if not _local_target(toks[j], allow_var=False):
                    return DDL_MESSAGE
                if toks[j + 1] != ("op", ","):
                    break
                j += 2
        elif word == "INTO":
            if nxt[0] == "temp" and nxt[1].startswith("##"):
                return GLOBAL_TEMP_MESSAGE
            if not _local_target(nxt) or toks[i + 2] == ("op", "."):
                return INTO_MESSAGE
        elif word in {"EXEC", "EXECUTE"}:
            reason = _exec_reason(toks, i)
            if reason:
                return reason
        elif word == "USE":
            if not (_word(nxt, "HINT") or (nxt[0] in {"word", "bracket", "dquote"}
                                           and _name(nxt).lower() in DEV_DATABASES)):
                return f"USE는 등록된 개발 DB({DEV_DB_LIST})만 가능합니다."
        elif word == "SET" and i not in update_sets:
            reason = _set_reason(toks, i)
            if reason:
                return reason
    return None


def _names_reason(toks):
    """여러 부분 이름: 3부는 개발 DB·tempdb만, 4부 이상(링크드 서버)은 거부."""
    i = 0
    while i < len(toks):
        if toks[i][0] not in NAME_KINDS or (i and toks[i - 1] == ("op", ".")):
            i += 1
            continue
        parts = [toks[i]]
        j = i + 1
        while toks[j] == ("op", "."):
            j += 1
            if toks[j][0] in NAME_KINDS or toks[j] == ("op", "*"):
                parts.append(toks[j])
                j += 1
            else:
                parts.append(None)  # db..object
        count = len(parts)
        if count >= 3 and toks[j] == ("op", "(") and parts[-1] and _word(parts[-1], *XML_METHODS):
            count -= 1  # 별칭.열.value(...) 같은 XML 메서드
        if count >= 4:
            return "4부 이상 이름(링크드 서버 참조)은 자동 경로 밖입니다."
        if count == 3 and _name(parts[0]).lower() not in DEV_DATABASES | {"tempdb"}:
            return (f"3부 이름은 등록된 개발 DB({DEV_DB_LIST})·tempdb만 참조할 수 있습니다. "
                    "열은 별칭(t.열)으로 참조하세요.")
        i = j
    return None


def script_reason(sql):
    """개발 DB 읽기 스크립트 판정. None이면 허용."""
    reason = _raw_reason(sql)
    if reason:
        return reason
    statements = 0
    # sqlcmd는 문자열·주석과 무관하게 GO 단독 줄에서 배치를 나눈다. 같은 기준으로 나눠야
    # 주석·문자열 안에 숨긴 GO 뒤 배치를 놓치지 않는다.
    for batch in re.split(r"(?im)^[ \t]*GO[ \t]*\r?$", sql):
        toks, reason = _tokenize(batch)
        if reason:
            return reason
        reason = _batch_reason(toks)
        if reason == DML_MESSAGE:
            pre_check = sql_reason(sql)
            return DML_MESSAGE + (f" 이 SQL은 db_execute.py 사전 검사에서도 거부됩니다 — {pre_check}" if pre_check else "")
        if reason:
            return reason
        statements += len(toks)
    if not statements:
        return "실행할 SQL이 없습니다."
    return None


# ---------- sqlcmd 명령 해석 ----------

_TERMINATORS = {";", "&&", "||", "\n"}
_SHELL_OPS = ["&&", "||", ";;", ">>", "<<", "&>", ">&", "<&", "|&", ";", "&", "|", "(", ")", "<", ">", "\n"]
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_CREDENTIAL_ARG = re.compile(r"[\w@.:/+=-]*|\$\(whoami\)")


def _parse_options(args):
    options = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in FLAG_OPTIONS:
            i += 1
            continue
        key = arg[:2]
        if key not in VALUE_OPTIONS:
            return None, "sqlcmd는 리터럴 -S/-d와 -Q 또는 -i 경로만 지원합니다. 대화형·변수·리다이렉트·파이프 입력은 별도 검토하세요."
        if key in options:
            return None, "중복 sqlcmd 옵션은 자동 경로 밖입니다."
        if len(arg) > 2:
            value = arg[2:]
        else:
            i += 1
            if i == len(args):
                return None, "sqlcmd 옵션 값이 없습니다."
            value = args[i]
        options[key] = value
        i += 1
    return options, None


def _read_input_file(path):
    if not os.path.isabs(path) or re.search(r"[~$`*?\[\]{},]", path):
        return None, "-i는 확장·글롭·여러 파일 없이 절대 경로 파일 하나만 검사합니다. 셸 cwd와 훅 cwd가 다를 수 있습니다."
    try:
        # FIFO·장치에서 훅이 멈추지 않게 비차단으로 열고 일반 파일만 읽는다.
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return None, "-i 입력은 일반 파일이어야 합니다."
            data = handle.read(MAX_SCRIPT_BYTES + 1)
    except OSError:
        return None, "-i 파일을 읽을 수 없어 검사하지 못했습니다. 파일을 먼저 저장한 뒤 절대 경로로 실행하세요."
    if len(data) > MAX_SCRIPT_BYTES:
        return None, "SQL이 1 MiB를 넘습니다. 나눠서 검증하세요."
    try:
        return data.decode("utf-8-sig"), None
    except UnicodeDecodeError:
        return None, "-i 파일은 UTF-8로 저장해야 검사할 수 있습니다."


def call_reason(args):
    options, reason = _parse_options(args)
    if reason:
        return reason
    if options.get("-S", "").lower() != DEV_HOST:
        return "등록된 개발 호스트만 직접 조회·입력할 수 있습니다. 운영 접근은 전용 실행기 개통 후 가능합니다."
    if options.get("-d", "").lower() not in DEV_DATABASES:
        return "등록된 개발 DB를 -d에 명시하세요."
    if ("-Q" in options) == ("-i" in options):
        return "자동 경로는 -Q 리터럴 SQL 또는 -i 절대 경로 파일 중 하나로 한 번 실행합니다."
    if "-Q" in options:
        sql = options["-Q"]
        if "$" in sql or "`" in sql:
            return ("-Q 값의 $·`는 셸 확장으로 실행 SQL이 달라질 수 있습니다. SQL을 파일로 저장해 -i 절대 경로로 "
                    "넘기세요(sqlcmd 변수 $( )는 파일에서도 거부).")
    else:
        # 파일은 -f 코드 페이지대로 읽힌다. 가드가 읽는 UTF-8과 같을 때만 같은 SQL을 본다.
        if "-f" in options and not re.fullmatch(r"(?i)65001|i:65001(?:,o:\d+)?|o:\d+(?:,i:65001)?", options["-f"]):
            return "-i 파일은 UTF-8(-f 65001)로 읽을 때만 검사할 수 있습니다."
        sql, reason = _read_input_file(options["-i"])
        if reason:
            return reason
    return script_reason(sql)


def _bash_normalize(command):
    """bash처럼 따옴표 밖 주석(단어 첫 #)과 작은따옴표 밖 백슬래시-줄바꿈을 지운다.

    줄을 이어 쓴 옵션도 같은 sqlcmd 호출로 검사하고, 주석 안 따옴표가 인용 판정을 흐리지 않게 한다.
    """
    out = []
    i = 0
    quote = None
    while i < len(command):
        char = command[i]
        if quote == "'":
            out.append(char)
            if char == "'":
                quote = None
            i += 1
            continue
        if char == "\\":
            if command.startswith("\n", i + 1):
                i += 2
                continue
            out.append(command[i:i + 2])
            i += 2
            continue
        if char == "#" and quote is None and (not out or out[-1][-1] in " \t\r\n;&|()<>"):
            while i < len(command) and command[i] != "\n":
                i += 1
            continue
        if char in "'\"" and quote is None:
            quote = char
        elif char == '"' and quote == '"':
            quote = None
        out.append(char)
        i += 1
    return "".join(out)


def _split_operators(tokens):
    """shlex가 붙여 내는 연산자 묶음(예: ')\\n')을 개별 연산자로 나눈다."""
    result = []
    for token in tokens:
        if not token or any(char not in ";&|<>()\n" for char in token):
            result.append(token)
            continue
        while token:
            op = next(op for op in _SHELL_OPS if token.startswith(op))
            result.append(op)
            token = token[len(op):]
    return result


def _plain(token):
    return not any(char in token for char in ";&|<>()\n") and "$(" not in token and "`" not in token


def _input_file_context_reason(tokens, call_starts):
    """-i 파일은 훅 시점에 읽는다. 같은 명령의 다른 부분이 파일을 바꾸지 못하는 형태만 허용한다."""
    segments, start = [], 0
    for index, token in enumerate(tokens + [";"]):
        if token in _TERMINATORS:
            segments.append((start, index))
            start = index + 1
    for begin, end in segments:
        segment = tokens[begin:end]
        calls = [index - begin for index in call_starts if begin <= index < end]
        if calls:
            prefix = segment[:calls[0]]
            if all(_ASSIGNMENT.match(token) and _plain(token) for token in prefix):
                continue
        elif all(_plain(token) for token in segment) and (
                all(_ASSIGNMENT.match(token) for token in segment)
                or (segment[0] in {"unset", "export"} and len(segment) > 1)):
            continue
        elif (len(segment) >= 5 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=\$", segment[0])
              and segment[1:4] == ["(", "security", "find-generic-password"] and segment[-1] == ")"
              and all(_CREDENTIAL_ARG.fullmatch(token) for token in segment[4:-1])):
            continue  # PW=$(security find-generic-password … -w)
        return ("-i 파일 실행은 같은 명령에 자격증명 조회·환경변수 지정 외의 다른 명령이 없을 때만 검사합니다. "
                "파일을 먼저 저장하고 sqlcmd를 따로 실행하세요.")
    return None


def command_reason(command):
    if "$'" in command and "sqlcmd" in command.lower():
        return "sqlcmd 명령을 해석할 수 없습니다. $'…' 인용 대신 작은따옴표를 쓰세요."
    lexer = shlex.shlex(_bash_normalize(command), posix=True, punctuation_chars=";&|<>()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""  # 주석은 _bash_normalize가 bash 기준(단어 첫 #)으로 지웠다
    try:
        tokens = _split_operators(list(lexer))
    except ValueError:
        return "sqlcmd 명령을 해석할 수 없습니다." if "sqlcmd" in command.lower() else None
    call_starts, uses_input_file = [], False
    for index, token in enumerate(tokens):
        if token.replace("\\", "/").rsplit("/", 1)[-1].lower() not in {"sqlcmd", "sqlcmd.exe"}:
            continue
        end = index + 1
        while end < len(tokens) and tokens[end] not in _TERMINATORS:
            end += 1
        args = tokens[index + 1:end]
        reason = call_reason(args)
        if reason:
            return reason
        call_starts.append(index)
        uses_input_file = uses_input_file or "-i" in (_parse_options(args)[0] or {})
    if uses_input_file:
        return _input_file_context_reason(tokens, call_starts)
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
