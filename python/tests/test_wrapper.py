from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Allow importing from the local src-layout package during tests.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deotter import wrapper  # noqa: E402


class FakeMetaData:
    def __init__(self, labels: list[str]):
        self._labels = labels

    def getColumnCount(self) -> int:
        return len(self._labels)

    def getColumnLabel(self, i: int) -> str:
        return self._labels[i - 1]


class FakeResultSet:
    def __init__(self, labels: list[str] | None = None):
        self._labels = labels or ["id", "name"]
        self.closed = False
        self._next_calls = 0

    def getMetaData(self) -> FakeMetaData:
        return FakeMetaData(self._labels)

    def next(self) -> bool:
        self._next_calls += 1
        return False

    def getObject(self, i: int) -> Any:
        values = {1: 1, 2: "alice"}
        return values[i]

    def close(self) -> None:
        self.closed = True


class FakeStatement:
    def __init__(self, rs: FakeResultSet | None = None):
        self._rs = rs or FakeResultSet()
        self.bound: dict[int, Any] = {}
        self.query_executed = False
        self.update_executed = False
        self.closed = False

    def setObject(self, i: int, value: Any) -> None:
        self.bound[i] = value

    def executeQuery(self) -> FakeResultSet:
        self.query_executed = True
        return self._rs

    def executeUpdate(self) -> int:
        self.update_executed = True
        return 1

    def close(self) -> None:
        self.closed = True


class FakeJavaConnection:
    def __init__(self, stmt: FakeStatement | None = None):
        self._stmt = stmt or FakeStatement()
        self._autocommit = True
        self.closed = False
        self.commit_calls = 0
        self.rollback_calls = 0
        self.prepared_sql: str | None = None

    def prepareStatement(self, sql: str) -> FakeStatement:
        self.prepared_sql = sql
        return self._stmt

    def getAutoCommit(self) -> bool:
        return self._autocommit

    def setAutoCommit(self, value: bool) -> None:
        self._autocommit = value

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.closed = True


class FakeManager:
    def __init__(self):
        self.all_rows = [[1, "alice"], [2, "bob"]]
        self.many_rows = [[3, "carol"]]

    def fetchAllRows(self, _rs: FakeResultSet) -> list[list[Any]]:
        return self.all_rows

    def fetchManyRows(self, _rs: FakeResultSet, _size: int) -> list[list[Any]]:
        return self.many_rows


class BigDecimalLike:
    pass


class DateLike:
    pass


BigDecimalLike.__name__ = "BigDecimal"
DateLike.__name__ = "Date"


def test_result_set_helpers_dict_and_json() -> None:
    rs = wrapper.DeotterResultSet([(1, "a"), (2, "b")], ["id", "name"])

    assert rs.as_dict() == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    as_json = rs.as_json(indent=2)
    assert json.loads(as_json) == [[1, "a"], [2, "b"]]


def test_clean_value_handles_common_cases() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())

    assert cursor._clean_value(None) is None
    assert cursor._clean_value("x") == "x"

    big = BigDecimalLike()
    big.toString = lambda: "12.34"  # type: ignore[attr-defined]
    assert cursor._clean_value(big) == 12.34

    date_val = DateLike()
    date_val.toString = lambda: "2026-01-01 10:00:00"  # type: ignore[attr-defined]
    assert cursor._clean_value(date_val) == "2026-01-01 10:00:00"


def test_wrap_rows_returns_deotter_result_set() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())
    cursor._description = ["id", "name"]

    wrapped = cursor._wrap_rows([(1, "alice")])

    assert isinstance(wrapped, wrapper.DeotterResultSet)
    assert wrapped.columns == ["id", "name"]


def test_execute_accepts_path_input_for_sql_file(tmp_path: Path) -> None:
    sql_file = tmp_path / "query.sql"
    sql_file.write_text("SELECT * FROM users WHERE id = {id}\n", encoding="utf-8")

    stmt = FakeStatement(FakeResultSet(["id", "name"]))
    conn = FakeJavaConnection(stmt)
    cursor = wrapper.DeotterCursor(conn, FakeManager())

    cursor.execute(sql_file, id=1)

    assert conn.prepared_sql == "SELECT * FROM users WHERE id = ?\n"


def test_execute_non_select_binds_params_and_updates() -> None:
    stmt = FakeStatement()
    conn = FakeJavaConnection(stmt)
    cursor = wrapper.DeotterCursor(conn, FakeManager())

    cursor.execute("""UPDATE t\nSET c = {value} WHERE id = {id}""", value="x", id=42)

    assert conn.prepared_sql == "UPDATE t\nSET c = ? WHERE id = ?"
    assert stmt.bound == {1: "x", 2: 42}
    assert stmt.update_executed is True
    assert cursor.description is None


def test_execute_select_updates_description() -> None:
    stmt = FakeStatement(FakeResultSet(["id", "name"]))
    conn = FakeJavaConnection(stmt)
    cursor = wrapper.DeotterCursor(conn, FakeManager())

    cursor.execute("""SELECT id, name\nFROM users WHERE id = {id}""", id=1)

    assert stmt.query_executed is True
    assert cursor.description == [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
    ]


def test_execute_raises_key_error_for_missing_param() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())

    with pytest.raises(KeyError, match="requires parameter 'id'"):
        cursor.execute("""SELECT *\nFROM users WHERE id = {id}""")


def test_raw_fetchall_returns_cleaned_rows() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())
    cursor._rs = FakeResultSet()

    assert cursor._raw_fetchall() == [(1, "alice"), (2, "bob")]


def test_raw_fetchmany_returns_cleaned_rows() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())
    cursor._rs = FakeResultSet()

    assert cursor._raw_fetchmany(1) == [(3, "carol")]


def test_fetchmany_wraps_rows() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())
    cursor._rs = FakeResultSet()
    cursor._description = ["id", "name"]

    wrapped = cursor.fetchmany(5)

    assert isinstance(wrapped, wrapper.DeotterResultSet)
    assert wrapped == [(3, "carol")]


def test_raw_fetchone_returns_none_when_result_set_is_none() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())
    cursor._rs = None

    assert cursor.raw_fetchone() is None


def test_fetchone_returns_empty_wrapper_when_result_set_missing() -> None:
    cursor = wrapper.DeotterCursor(FakeJavaConnection(), FakeManager())
    cursor._description = ["id", "name"]

    wrapped = cursor.fetchone()

    assert isinstance(wrapped, wrapper.DeotterResultSet)
    assert wrapped == []


def test_cursor_close_closes_result_set_and_statement() -> None:
    rs = FakeResultSet()
    stmt = FakeStatement(rs)
    cursor = wrapper.DeotterCursor(FakeJavaConnection(stmt), FakeManager())
    cursor._rs = rs
    cursor._stmt = stmt

    cursor.close()

    assert rs.closed is True
    assert stmt.closed is True


def test_cursor_context_manager_closes_on_exit() -> None:
    rs = FakeResultSet()
    stmt = FakeStatement(rs)
    cursor = wrapper.DeotterCursor(FakeJavaConnection(stmt), FakeManager())
    cursor._rs = rs
    cursor._stmt = stmt

    with cursor:
        pass

    assert rs.closed is True
    assert stmt.closed is True


def test_ensure_jvm_starts_when_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    monkeypatch.setattr(wrapper.jpype, "isJVMStarted", lambda: False)
    monkeypatch.setattr(wrapper, "ensure_java_resources", lambda: None)
    monkeypatch.setattr(wrapper, "discover_java_driver_jars", lambda: [])

    def fake_start_jvm(*, classpath: list[str]) -> None:
        called["classpath"] = classpath

    monkeypatch.setattr(wrapper.jpype, "startJVM", fake_start_jvm)

    wrapper.ensure_jvm()

    assert "classpath" in called
    assert str(wrapper.JAVA_BIN.resolve()) in called["classpath"]


def test_ensure_jvm_noop_if_already_started(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wrapper.jpype, "isJVMStarted", lambda: True)
    monkeypatch.setattr(wrapper, "ensure_java_resources", lambda: None)

    called = {"start": 0}

    def fake_start_jvm(*, classpath: list[str]) -> None:
        called["start"] += 1

    monkeypatch.setattr(wrapper.jpype, "startJVM", fake_start_jvm)

    wrapper.ensure_jvm()

    assert called["start"] == 0


def test_discover_java_driver_jars_returns_empty_if_directory_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_dir = tmp_path / "missing-drivers"
    monkeypatch.setattr(wrapper, "JAVA_DRIVERS", missing_dir)

    assert wrapper.discover_java_driver_jars() == []


def test_ensure_jvm_includes_discovered_driver_jars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    drivers_dir = tmp_path / "drivers"
    drivers_dir.mkdir()
    jar = drivers_dir / "demo-driver.jar"
    jar.write_bytes(b"jar")

    called: dict[str, Any] = {}

    monkeypatch.setattr(wrapper.jpype, "isJVMStarted", lambda: False)
    monkeypatch.setattr(wrapper, "ensure_java_resources", lambda: None)
    monkeypatch.setattr(wrapper, "JAVA_DRIVERS", drivers_dir)

    def fake_start_jvm(*, classpath: list[str]) -> None:
        called["classpath"] = classpath

    monkeypatch.setattr(wrapper.jpype, "startJVM", fake_start_jvm)

    wrapper.ensure_jvm()

    assert str(jar.resolve()) in called["classpath"]


def test_connection_properties_commit_rollback_and_close() -> None:
    conn = wrapper.DeotterConnection.__new__(wrapper.DeotterConnection)
    conn._java_conn = FakeJavaConnection()
    conn._mgr = FakeManager()
    conn._closed = False

    assert conn.autocommit is True

    conn.autocommit = False
    assert conn.autocommit is False

    conn.commit()
    conn.rollback()
    assert conn._java_conn.commit_calls == 1
    assert conn._java_conn.rollback_calls == 1

    conn.close()
    assert conn.is_closed is True
    assert conn._java_conn.closed is True


def test_connection_cursor_raises_after_close() -> None:
    conn = wrapper.DeotterConnection.__new__(wrapper.DeotterConnection)
    conn._java_conn = FakeJavaConnection()
    conn._mgr = FakeManager()
    conn._closed = True

    with pytest.raises(RuntimeError, match="Connection is closed"):
        conn.cursor()


def test_connection_exit_commits_on_success_and_rolls_back_on_error() -> None:
    conn = wrapper.DeotterConnection.__new__(wrapper.DeotterConnection)
    conn._java_conn = FakeJavaConnection()
    conn._mgr = FakeManager()
    conn._closed = False
    conn.autocommit = False

    conn.__exit__(None, None, None)
    assert conn._java_conn.commit_calls == 1

    conn._closed = False
    conn.__exit__(Exception, Exception("boom"), None)
    assert conn._java_conn.rollback_calls == 1


def test_connection_init_uses_java_connection_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_java_conn = FakeJavaConnection()

    class FakeConnectionManager:
        @staticmethod
        def getInstance() -> "FakeConnectionManager":
            return FakeConnectionManager()

        def getConnection(self, alias: str) -> FakeJavaConnection:
            assert alias == "main"
            return fake_java_conn

    monkeypatch.setattr(wrapper, "ensure_jvm", lambda: None)

    import types

    com_module = types.ModuleType("com")
    deotter_module = types.ModuleType("com.deotter")
    db_module = types.ModuleType("com.deotter.db")
    db_module.ConnectionManager = FakeConnectionManager

    monkeypatch.setitem(sys.modules, "com", com_module)
    monkeypatch.setitem(sys.modules, "com.deotter", deotter_module)
    monkeypatch.setitem(sys.modules, "com.deotter.db", db_module)

    conn = wrapper.DeotterConnection("main", autocommit=False)

    assert conn._mgr is not None
    assert conn._java_conn is fake_java_conn
    assert conn.autocommit is False
