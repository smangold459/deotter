from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deotter import wrapper  # noqa: E402


class IterMetaData:
    def __init__(self, labels: list[str]):
        self._labels = labels

    def getColumnCount(self) -> int:
        return len(self._labels)

    def getColumnLabel(self, idx: int) -> str:
        return self._labels[idx - 1]


class IterResultSet:
    def __init__(self, labels: list[str], rows: list[tuple[Any, ...]]):
        self._labels = labels
        self._rows = rows
        self._idx = -1
        self.closed = False

    def getMetaData(self) -> IterMetaData:
        return IterMetaData(self._labels)

    def next(self) -> bool:
        self._idx += 1
        return self._idx < len(self._rows)

    def getObject(self, idx: int) -> Any:
        return self._rows[self._idx][idx - 1]

    def close(self) -> None:
        self.closed = True


class IterStatement:
    def __init__(self, rs: IterResultSet):
        self.rs = rs
        self.bound: dict[int, Any] = {}
        self.query_calls = 0
        self.update_calls = 0
        self.closed = False

    def setObject(self, idx: int, value: Any) -> None:
        self.bound[idx] = value

    def executeQuery(self) -> IterResultSet:
        self.query_calls += 1
        return self.rs

    def executeUpdate(self) -> int:
        self.update_calls += 1
        return 1

    def close(self) -> None:
        self.closed = True


class IterJavaConnection:
    def __init__(self, stmt: IterStatement):
        self.stmt = stmt
        self.prepared_sql: str | None = None
        self.closed = False

    def prepareStatement(self, sql: str) -> IterStatement:
        self.prepared_sql = sql
        return self.stmt

    def close(self) -> None:
        self.closed = True


class ManagerForFetch:
    def fetchAllRows(self, _rs: IterResultSet) -> list[list[Any]]:
        return [[10, "a"], [20, "b"]]

    def fetchManyRows(self, _rs: IterResultSet, size: int) -> list[list[Any]]:
        all_rows = [[30, "c"], [40, "d"], [50, "e"]]
        return all_rows[:size]


def test_execute_select_populates_description_and_binds_params() -> None:
    rs = IterResultSet(["id", "name"], [(1, "alice")])
    stmt = IterStatement(rs)
    conn = IterJavaConnection(stmt)
    cur = wrapper.DeotterCursor(conn, ManagerForFetch())

    cur.execute("SELECT id, name FROM users WHERE id = {id}", id=1)

    assert conn.prepared_sql == "SELECT id, name FROM users WHERE id = ?"
    assert stmt.bound == {1: 1}
    assert stmt.query_calls == 1
    assert cur.description == [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
    ]


def test_execute_accepts_path_input_for_sql_file(tmp_path: Path) -> None:
    sql_file = tmp_path / "query.sql"
    sql_file.write_text("SELECT * FROM x WHERE id = {id}\n", encoding="utf-8")

    rs = IterResultSet(["id"], [(1,)])
    stmt = IterStatement(rs)
    conn = IterJavaConnection(stmt)
    cur = wrapper.DeotterCursor(conn, ManagerForFetch())

    cur.execute(sql_file, id=1)

    assert conn.prepared_sql == "SELECT * FROM x WHERE id = ?\n"


def test_raw_fetchall_returns_cleaned_tuples() -> None:
    rs = IterResultSet(["id", "name"], [(1, "x")])
    cur = wrapper.DeotterCursor(IterJavaConnection(IterStatement(rs)), ManagerForFetch())
    cur._rs = rs

    rows = cur._raw_fetchall()

    assert rows == [(10, "a"), (20, "b")]


def test_raw_fetchmany_uses_size_and_returns_tuples() -> None:
    rs = IterResultSet(["id", "name"], [(1, "x")])
    cur = wrapper.DeotterCursor(IterJavaConnection(IterStatement(rs)), ManagerForFetch())
    cur._rs = rs

    rows = cur._raw_fetchmany(2)

    assert rows == [(30, "c"), (40, "d")]


def test_fetchmany_wraps_result_set_with_description() -> None:
    rs = IterResultSet(["id", "name"], [(1, "x")])
    stmt = IterStatement(rs)
    cur = wrapper.DeotterCursor(IterJavaConnection(stmt), ManagerForFetch())
    cur._rs = rs
    cur._description = [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
    ]

    wrapped = cur.fetchmany(2)

    assert isinstance(wrapped, wrapper.DeotterResultSet)
    assert wrapped == [(30, "c"), (40, "d")]


def test_raw_fetchone_returns_next_row_then_none() -> None:
    rs = IterResultSet(["id", "name"], [(1, "alice")])
    cur = wrapper.DeotterCursor(IterJavaConnection(IterStatement(rs)), ManagerForFetch())
    cur._rs = rs
    cur._description = [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
    ]

    assert cur.raw_fetchone() == (1, "alice")
    assert cur.raw_fetchone() is None


def test_fetchone_returns_wrapped_single_row() -> None:
    rs = IterResultSet(["id", "name"], [(7, "z")])
    cur = wrapper.DeotterCursor(IterJavaConnection(IterStatement(rs)), ManagerForFetch())
    cur._rs = rs
    cur._description = [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
    ]

    wrapped = cur.fetchone()

    assert isinstance(wrapped, wrapper.DeotterResultSet)
    assert wrapped == [(7, "z")]


def test_ensure_jvm_is_noop_if_jvm_already_started(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wrapper.jpype, "isJVMStarted", lambda: True)

    called = {"start": 0}

    def fake_start_jvm(*, classpath: list[str]) -> None:
        called["start"] += 1

    monkeypatch.setattr(wrapper.jpype, "startJVM", fake_start_jvm)

    wrapper.ensure_jvm()

    assert called["start"] == 0
