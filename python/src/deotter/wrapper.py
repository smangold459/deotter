from pathlib import Path
import re
from types import TracebackType
from typing import Optional, Type

import jpype
import jpype.imports


class DeotterResultSet(list):
    """A list that knows how to turn itself into other formats"""

    def __init__(self, data, columns):
        super().__init__(data)
        self.columns = columns

    def as_dataframe(self) -> "DataFrame":
        """Converts the reuslts to a Pandas Dataframe"""
        import pandas as pd
        return pd.DataFrame(self, columns=self.columns)
    
    def as_dict(self) -> "list[dict]":
        """Converts the results to a list of dicts"""
        return [dict(zip(self.columns, row)) for row in self]
    
    def as_json(self, indent=None) -> "JSON":
        """Converts results to a JSON"""
        import json
        return json.dumps(self, indent=indent, ensure_ascii=False)
    

class DeotterCursor:
    """
    Emulates a cursor object for python api
    """
    
    def __init__(
            self,
            java_conn:"java.sql.Connection",
            mgr:"ConnectionManager"
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
        input_str = str(sql_input)
        if not isinstance(sql_input, str):
            raise TypeError("sql_input must be of type str or pathlib.Path")
        elif "\n" in input_str or len(input_str) > 225:
            sql = input_str
        else:
            p = Path(input_str).expanduser()
            if p.is_file():
                sql = p.read_text()
            else:
                self = input_str

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
            self._updater_description()
        else:
            self._stmt.executeUpdate()
            self._description = None

    def _update_description(self):
        """Updates meta data related to result set"""
        mata = self._rs.getMetaData()
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

        return [tuple(self._clean_values(v) for v in row) for v in java_data]
    
    def fetchall(self) -> DeotterResultSet:
        """Fetches all rows from the result set"""
        return self._wrap_rows(self._raw_fetchall())
    
    def _raw_fetchmany(self, size: int) -> "list[tuple]":
        if not self._rs:
            return []
        
        java_data = self._mgr.fetchManyRows(self._rs, size)

        return [tuple(self._clean_values(val) for val in row) for row in java_data]
    
    def fetchmany(self, size: int = 1) -> DeotterResultSet:
        """Fetches the next 'size' rows from the result set"""
        return self._wrap_rows(self._raw_fetchmany(), size)
    
    def raw_fetchone(self) -> tuple:
        if not self._rs and self._rs.next():
            return None
        
        num_cols = list(self.description)
        return tuple(
            self._clean_value(self._rs.getObject(i)) for i in range(1, num_cols + 1)
        )

    def fetchone(self) -> DeotterResultSet:
        """Fetches one row from the result set"""
        return self._wrap_rows(self.raw_fetchone(self.raw_fetchone()))
    
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
JAVA_LIB = JAVA_BASE / "lib"

def manage_jvm():
    if jpype.isJVMStarted():
        return

    cp = [str(JAVA_OUT.resolve())]

    if JAVA_LIB.exists():
        cp.extend(str(j.resolve()) for j in sorted(JAVA_LIB.glob("*.jar")))

    jpype.startJVM(classpath=cp)

class DeotterConnection:
    """
    Python wrapper for using deotter's java connections
    """

    def __init__(self, db_alias: str, autocommit=True):
        manage_jvm()
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
