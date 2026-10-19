"""SQL Server transaction-isolation checks for the disposable DB lab.

The checks intentionally keep the production-shaped reader as ``lab_prod`` and
use ``sa`` only to install the synthetic fixture and hold locks.  The fixture
is a separate database so the tests cannot change the existing permission
fixtures.  This module does not start Docker; ``verify.py`` owns the lab
lifecycle and calls :func:`verify_isolation` after ``Lab.setup``.

The expected behaviour follows SQL Server's documented locking rules:

* ``NOLOCK``/``READUNCOMMITTED`` can see an uncommitted row value, but the
  query still takes a schema-stability lock and therefore conflicts with a
  schema-modification lock.
* ordinary ``READ COMMITTED`` blocks on an uncommitted update when
  ``READ_COMMITTED_SNAPSHOT`` is off.
* with ``READ_COMMITTED_SNAPSHOT`` on, ordinary ``READ COMMITTED`` reads the
  last committed row version without waiting for the writer.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any


DATABASE = "IsolationFixture"
TABLE = "dbo.IsolationRow"
WRITER_DELAY = "00:00:08"
WRITER_TIMEOUT = 25
READER_TIMEOUT = 5
LOCK_TIMEOUT_MS = 1000


def _writer_sql(statement: str) -> str:
    """Make a sqlcmd stdin batch for a lock-holding fixture process."""

    return (
        "SET NOCOUNT ON;\n"
        "BEGIN TRANSACTION;\n"
        f"{statement}\n"
        f"WAITFOR DELAY '{WRITER_DELAY}';\n"
        "ROLLBACK TRANSACTION;\n"
        "GO\n"
    )


def _start_writer(lab: Any, statement: str) -> subprocess.Popen[str]:
    """Start a synthetic ``sa`` transaction and return its sqlcmd process."""

    process = subprocess.Popen(
        lab.sql_args("sa", DATABASE, WRITER_TIMEOUT),
        env=lab.sql_env("sa"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        if process.stdin is None:
            raise RuntimeError("writer sqlcmd stdin is unavailable")
        process.stdin.write(_writer_sql(statement))
        process.stdin.close()
    except Exception:
        _reap(process, terminate=True)
        raise
    return process


def _reap(process: subprocess.Popen[str], *, terminate: bool = False) -> tuple[int | None, str]:
    """Wait for a writer and close all pipes, including the failure path."""

    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
    if process.poll() is None and terminate:
        process.terminate()
    if process.poll() is None:
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    output_parts: list[str] = []
    for stream in (process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            try:
                output_parts.append(stream.read())
            finally:
                stream.close()
    return process.returncode, "".join(output_parts)


def _wait_for_writer(lab: Any, process: subprocess.Popen[str], *, lock: bool = False) -> None:
    """Wait until the writer is in ``WAITFOR`` and its DB lock is visible.

    Checking ``database_id`` prevents a coincidental WAITFOR in another
    database from being mistaken for this fixture's writer.  For a schema
    writer, the second predicate also requires a granted ``Sch-M`` lock.
    """

    if lock:
        sql = f"""
SELECT CASE WHEN EXISTS (
    SELECT 1
    FROM sys.dm_exec_requests AS r
    JOIN sys.dm_exec_sessions AS s ON s.session_id = r.session_id
    WHERE s.login_name = N'sa'
      AND r.database_id = DB_ID(N'{DATABASE}')
      AND r.command = N'WAITFOR'
      AND r.wait_type = N'WAITFOR'
) AND EXISTS (
    SELECT 1
    FROM sys.dm_tran_locks AS l
    JOIN sys.dm_exec_sessions AS s ON s.session_id = l.request_session_id
    WHERE s.login_name = N'sa'
      AND l.resource_database_id = DB_ID(N'{DATABASE}')
      AND l.request_mode = N'Sch-M'
      AND l.request_status = N'GRANT'
) THEN 1 ELSE 0 END;
"""
    else:
        sql = f"""
SELECT COUNT(*)
FROM sys.dm_exec_requests AS r
JOIN sys.dm_exec_sessions AS s ON s.session_id = r.session_id
WHERE s.login_name = N'sa'
  AND r.database_id = DB_ID(N'{DATABASE}')
  AND r.command = N'WAITFOR'
  AND r.wait_type = N'WAITFOR';
"""

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            _, output = _reap(process)
            raise RuntimeError(
                "isolation writer exited before its lock was observed: "
                + lab.clean(output)[-2000:]
            )
        if lab.scalar(sql) == "1":
            return
        time.sleep(0.2)
    raise RuntimeError("isolation writer did not reach the expected DMV state")


def _finish_writer(lab: Any, name: str, process: subprocess.Popen[str]) -> None:
    """Record a successful writer completion and surface its diagnostics."""

    exit_code, output = _reap(process)
    diagnostic = lab.clean(output).strip()
    lab.record(
        name,
        exit_code == 0 and not diagnostic,
        exit_code=exit_code,
        **({"failure_diagnostic": diagnostic[-2000:]} if diagnostic else {}),
    )


def _install_fixture(lab: Any, ownership: dict[str, bool]) -> None:
    """Create the isolated database, row, and read-only production user."""

    lab.require(
        lab.query(
            "sa",
            "master",
            f"""
IF DB_ID(N'{DATABASE}') IS NOT NULL
    THROW 51000, 'IsolationFixture already exists', 1;
CREATE DATABASE [{DATABASE}];
""",
        ),
        "isolation database",
    )
    # Set ownership immediately after CREATE succeeds.  A later setup failure
    # must still clean up this run's database, while a pre-existing database
    # rejected above must remain untouched.
    ownership["created"] = True
    lab.require(
        lab.query(
            "sa",
            "master",
            f"ALTER DATABASE [{DATABASE}] SET READ_COMMITTED_SNAPSHOT OFF WITH ROLLBACK IMMEDIATE;",
        ),
        "isolation RCSI off",
    )
    lab.require(
        lab.query(
            "sa",
            DATABASE,
            f"""
CREATE TABLE {TABLE} (
    Id int NOT NULL CONSTRAINT PK_IsolationRow PRIMARY KEY,
    Value nvarchar(60) NOT NULL
);
INSERT INTO {TABLE} (Id, Value) VALUES (1, N'committed');
CREATE USER lab_prod FOR LOGIN lab_prod;
GRANT SELECT ON {TABLE} TO lab_prod;
""",
        ),
        "isolation table and reader",
    )


def _drop_fixture(lab: Any) -> None:
    """Drop only the database created by this module."""

    lab.require(
        lab.query(
            "sa",
            "master",
            f"""
IF DB_ID(N'{DATABASE}') IS NOT NULL
BEGIN
    ALTER DATABASE [{DATABASE}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE [{DATABASE}];
END;
""",
        ),
        "isolation fixture cleanup",
    )


def verify_isolation(lab: Any) -> None:
    """Verify NOLOCK, READ COMMITTED, RCSI, and Sch-M interactions.

    ``lab.record`` deliberately remains the assertion boundary so the parent
    runner records each result in its existing report format.  Every started
    sqlcmd process is reaped in the ``finally`` block before the fixture is
    removed, including when an assertion or DMV probe fails.
    """

    processes: list[subprocess.Popen[str]] = []
    ownership = {"created": False}
    try:
        _install_fixture(lab, ownership)
        lab.check_sql(
            "isolation reader write denied",
            "lab_prod",
            DATABASE,
            f"UPDATE {TABLE} SET Value=N'not-allowed' WHERE Id=1;",
            errors=[229],
        )

        writer = _start_writer(lab, f"UPDATE {TABLE} SET Value=N'uncommitted' WHERE Id=1;")
        processes.append(writer)
        _wait_for_writer(lab, writer)

        nolock_started = time.monotonic()
        lab.check_sql(
            "NOLOCK reads uncommitted value",
            "lab_prod",
            DATABASE,
            f"SELECT Value FROM {TABLE} WITH (NOLOCK) WHERE Id=1;",
            expected="uncommitted",
            query_timeout=READER_TIMEOUT,
        )
        lab.record(
            "NOLOCK reader does not wait for row lock",
            time.monotonic() - nolock_started < 2,
            duration_seconds=round(time.monotonic() - nolock_started, 3),
        )

        lab.check_sql(
            "READ COMMITTED blocks with RCSI off",
            "lab_prod",
            DATABASE,
            f"""
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET LOCK_TIMEOUT {LOCK_TIMEOUT_MS};
SELECT Value FROM {TABLE} WHERE Id=1;
""",
            errors=[1222],
            query_timeout=READER_TIMEOUT,
        )
        _finish_writer(lab, "row writer completed and rolled back", writer)
        processes.remove(writer)
        lab.check_sql(
            "row value restored after rollback",
            "lab_prod",
            DATABASE,
            f"SELECT Value FROM {TABLE} WHERE Id=1;",
            expected="committed",
        )

        lab.require(
            lab.query(
                "sa",
                "master",
                f"ALTER DATABASE [{DATABASE}] SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;",
            ),
            "isolation RCSI on",
        )
        lab.record(
            "RCSI enabled for isolation fixture",
            lab.scalar(
                f"SELECT is_read_committed_snapshot_on FROM sys.databases WHERE name=N'{DATABASE}';"
            )
            == "1",
        )

        writer = _start_writer(lab, f"UPDATE {TABLE} SET Value=N'rcsi-uncommitted' WHERE Id=1;")
        processes.append(writer)
        _wait_for_writer(lab, writer)

        rcsi_started = time.monotonic()
        lab.check_sql(
            "RCSI READ COMMITTED reads last committed value",
            "lab_prod",
            DATABASE,
            f"""
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET LOCK_TIMEOUT {LOCK_TIMEOUT_MS};
SELECT Value FROM {TABLE} WHERE Id=1;
""",
            expected="committed",
            query_timeout=READER_TIMEOUT,
        )
        rcsi_duration = time.monotonic() - rcsi_started
        lab.record(
            "RCSI READ COMMITTED does not wait for row lock",
            rcsi_duration < 2,
            duration_seconds=round(rcsi_duration, 3),
        )
        _finish_writer(lab, "RCSI row writer completed and rolled back", writer)
        processes.remove(writer)

        schema_writer = _start_writer(
            lab,
            f"ALTER TABLE {TABLE} ADD SchMProbe int NULL;",
        )
        processes.append(schema_writer)
        _wait_for_writer(lab, schema_writer, lock=True)
        lab.check_sql(
            "NOLOCK still blocks on Sch-M",
            "lab_prod",
            DATABASE,
            f"""
SET LOCK_TIMEOUT {LOCK_TIMEOUT_MS};
GO
SELECT Value FROM {TABLE} WITH (NOLOCK) WHERE Id=1;
""",
            errors=[1222],
            query_timeout=READER_TIMEOUT,
        )
        _finish_writer(lab, "Sch-M writer completed and rolled back", schema_writer)
        processes.remove(schema_writer)
        lab.check_sql(
            "Sch-M DDL rolled back",
            "lab_prod",
            DATABASE,
            "SELECT CASE WHEN COL_LENGTH(N'dbo.IsolationRow', N'SchMProbe') IS NULL "
            "THEN N'absent' ELSE N'present' END;",
            expected="absent",
        )
    finally:
        for process in reversed(processes):
            _reap(process, terminate=True)
        if ownership["created"]:
            _drop_fixture(lab)


__all__ = ["verify_isolation"]
