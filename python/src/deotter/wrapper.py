"""
Copyright 2026 Shane R. Mangold

Licensed under the Apache License, Version 2.0.
See http://www.apache.org/licenses/LICENSE-2.0 or LICENSE file for details.
"""

from __future__ import annotations

import platform
from pathlib import Path
import re
import subprocess
from types import TracebackType
from typing import Optional, Type

import jpype
import jpype.imports


class DeotterResultSet(list):
    """A list that knows how to turn itself into other formats"""

    def __init__(self, data, columns):
        super().__init__(data)
        self.columns = columns

    def as_dataframe(self) -> "DataFrame":  # noqa: F821
        """Converts the reuslts to a Pandas Dataframe"""
        import pandas as pd
        return pd.DataFrame(self, columns=self.columns)
    
    def as_dict(self) -> "list[dict]":
        """Converts the results to a list of dicts"""
        return [dict(zip(self.columns, row)) for row in self]
    
    def as_json(self, indent=None) -> "JSON":  # noqa: F821
        """Converts results to a JSON"""
        import json
        return json.dumps(self, indent=indent, ensure_ascii=False)
    

class DeotterCursor:
    """
    Emulates a cursor object for python api
    """
    
    def __init__(
            self,
            java_conn:"java.sql.Connection",  # noqa: F821
            mgr:"ConnectionManager"  # noqa: F821
        ):
        self._conn = java_conn
        self._mgr = mgr
        self._rs = None
        self._stmt = None
        self._description = None

    @property
    def description(self):
        """
        Returns metatdata: (
            name,
            type_code,
            display_size,
            internal_size,
            precision,
            scale,
            null_ok
        )
        """
        return self._description
    
    def execute(self, sql_input:"str|Path", **kwargs) -> None:
        """
        Exceutes sql statement

        Args:
            sql_input (str): Either a raw SQL string or a path to sql file
        """
        if isinstance(sql_input, Path):
            sql = sql_input.expanduser().read_text(encoding="utf-8")
        elif isinstance(sql_input, str):
            input_str = sql_input
            if "\n" in input_str or len(input_str) > 225:
                sql = input_str
            else:
                p = Path(input_str).expanduser()
                if p.is_file():
                    sql = p.read_text(encoding="utf-8")
                else:
                    sql = input_str
        else:
            raise TypeError("sql_input must be of type str or pathlib.Path")

        param_names = re.findall(r"\{(\w+)\}", sql)
        jdbc_sql = re.sub(r"\{(\w+)\}", "?", sql)

        self._stmt = self._conn.prepareStatement(jdbc_sql)

        for i, name in enumerate(param_names, start=1):
            if name not in kwargs:
                raise KeyError(
                    f"SQL requires parameter '{name}', but it wasnt provided"
                )
            self._stmt.setObject(i, kwargs[name])

        if jdbc_sql.strip().lower().startswith("select"):
            self._rs = self._stmt.executeQuery()
            self._update_description()
        else:
            self._stmt.executeUpdate()
            self._description = None

    def _update_description(self):
        """Updates meta data related to result set"""
        meta = self._rs.getMetaData()
        self._description = [
            (meta.getColumnLabel(i), None, None, None, None, None, None)
            for i in range(1, meta.getColumnCount() + 1)
        ]


    def _clean_value(self, val):
        """Simple converter to convert any Java types that Jpype doesnt auto-convert"""
        if val is None:
            return None
        
        java_class = str(type(val))

        if "BigDecimal" in java_class:
            return float(val.toString())
        if "timestamp" in java_class or "Date" in java_class:
            return str(val.toString())
        
        return val
    
    def _wrap_rows(self, rows:"list[tuple]") -> DeotterResultSet:
        return DeotterResultSet(rows, self.description)
    
    def _raw_fetchall(self) -> "list[tuple]":
        if not self._rs:
            return []
        
        java_data = self._mgr.fetchAllRows(self._rs)

        return [tuple(self._clean_value(v) for v in row) for row in java_data]
    
    def fetchall(self) -> DeotterResultSet:
        """Fetches all rows from the result set"""
        return self._wrap_rows(self._raw_fetchall())
    
    def _raw_fetchmany(self, size: int) -> "list[tuple]":
        if not self._rs:
            return []
        
        java_data = self._mgr.fetchManyRows(self._rs, size)

        return [tuple(self._clean_value(val) for val in row) for row in java_data]
    
    def fetchmany(self, size: int = 1) -> DeotterResultSet:
        """Fetches the next 'size' rows from the result set"""
        return self._wrap_rows(self._raw_fetchmany(size))
    
    def raw_fetchone(self) -> tuple | None:
        if not self._rs or not self._rs.next():
            return None

        num_cols = len(self.description or [])
        return tuple(
            self._clean_value(self._rs.getObject(i)) for i in range(1, num_cols + 1)
        )

    def fetchone(self) -> DeotterResultSet:
        """Fetches one row from the result set"""
        row = self.raw_fetchone()
        if row is None:
            return self._wrap_rows([])
        return self._wrap_rows([row])
    
    def close(self):
        """Closes the cursor"""
        if self._rs:
            self._rs.close()
        if self._stmt:
            self._stmt.close()
    
    def __enter__(self):
        return self
    
    def __exit__(
        self,
        t: Optional[Type[BaseException]],
        v: Optional[BaseException],
        tb: Optional[TracebackType]
    ) -> None:
        self.close()


JAVA_BASE = Path(__file__).resolve().parents[2] / "resources"
JAVA_OUT = JAVA_BASE / "out"
DEOTTER_HOME = Path.home() / ".deotter"
JAVA_BIN = DEOTTER_HOME / "bin"
JAVA_DRIVERS = DEOTTER_HOME / "drivers"


def discover_java_driver_jars() -> list[str]:
    """Returns driver JAR paths from ~/.deotter/drivers when present."""
    if not JAVA_DRIVERS.exists():
        return []
    return [str(j.resolve()) for j in sorted(JAVA_DRIVERS.glob("*.jar"))]

def ensure_jvm():
    """Ensures JVM is started and if not, starts it."""
    if jpype.isJVMStarted():
        return

    ensure_java_resources()

    cp = [str(JAVA_BIN.resolve())]
    # Drivers may come from the Java runtime or from user-provided jars in ~/.deotter/drivers.
    cp.extend(discover_java_driver_jars())

    # Backward compatibility for local dev layouts that still compile into repo resources/out.
    if JAVA_OUT.exists():
        cp.append(str(JAVA_OUT.resolve()))

    jpype.startJVM(classpath=cp)

def ensure_java_resources():
    """
    Checks the user's home directory for .deotter/bin, and that the necessary java
    resources have been compiled into it.
    """
    bin_dir = JAVA_BIN
    bin_dir.mkdir(parents=True, exist_ok=True)
    bin_dir_classes = {p.name for p in bin_dir.glob("*.class")}

    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    java_dir = repo_root / "java" / "main"
    java_class_names = {f"{p.stem}.class" for p in java_dir.glob("*.java")}

    os_name = platform.system()
    if os_name == "Windows":
        compile_script = repo_root / "scripts" / "compile-java.ps1"
    else:
        compile_script = repo_root / "scripts" / "compile-java.sh"

    if java_class_names.issubset(bin_dir_classes):
        return
    else:
        if os_name == "Windows":
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(compile_script),
                    "-OutDir",
                    str(bin_dir),
                    "-MainOnly",
                ],
                check=True,
                cwd=repo_root,
            )
        else:
            subprocess.run(
                [
                    "bash",
                    str(compile_script),
                    "--out-dir",
                    str(bin_dir),
                    "--main-only",
                ],
                check=True,
                cwd=repo_root,
            )

class DeotterConnection:
    """
    Python wrapper for using deotter's java connections
    """

    def __init__(self, db_alias: str, autocommit=True):
        ensure_jvm()
        from com.deotter.db import ConnectionManager

        self._mgr = ConnectionManager.getInstance()
        self._java_conn = self._mgr.getConnection(db_alias)
        self.autocommit = autocommit
        self._closed = False
    
    @property
    def is_closed(self) -> bool:
        """Returns True if the connection has been closed"""
        return self._closed
    
    def close(self):
        """Close the connection and update state"""
        if not self._closed:
            if hasattr(self, "_java_conn") and self._java_conn:
                self._java_conn.close()
            self._closed = True
    
    @property
    def autocommit(self) -> bool:
        return self._java_conn.getAutoCommit()
    
    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self._java_conn.setAutoCommit(value)

    def cursor(self) -> DeotterCursor:
        """Create cursor object"""
        if self.is_closed:
            raise RuntimeError("Connection is closed")
        return DeotterCursor(self._java_conn, self._mgr)
    
    def commit(self) -> None:
        if not self.autocommit:
            self._java_conn.commit()

    def rollback(self) -> None:
        if not self.autocommit:
            self._java_conn.rollback()

    def __enter__(self):
        return self
    
    def __exit__(
        self,
        t:Optional[Type[BaseException]],
        v: Optional[BaseException],
        tb: Optional[TracebackType]
    ) -> None:
        try:
            if not self.autocommit:
                if t is not None:
                    self.rollback()
                else:
                    self.commit()
        finally:
            self.close()
