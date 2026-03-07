#!/usr/bin/env python3
"""Generate database fixture artifacts for all supported engines from Iris CSV."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IrisRow:
    iris_id: int
    sepal_length_cm: float
    sepal_width_cm: float
    petal_length_cm: float
    petal_width_cm: float
    species: str


def parse_rows(csv_path: Path) -> list[IrisRow]:
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows: list[IrisRow] = []
        for record in reader:
            rows.append(
                IrisRow(
                    iris_id=int(record["Id"]),
                    sepal_length_cm=float(record["SepalLengthCm"]),
                    sepal_width_cm=float(record["SepalWidthCm"]),
                    petal_length_cm=float(record["PetalLengthCm"]),
                    petal_width_cm=float(record["PetalWidthCm"]),
                    species=record["Species"],
                )
            )
    return rows


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate_insert_values(rows: list[IrisRow]) -> list[str]:
    values: list[str] = []
    for row in rows:
        values.append(
            "(" + ", ".join(
                [
                    str(row.iris_id),
                    f"{row.sepal_length_cm:.1f}",
                    f"{row.sepal_width_cm:.1f}",
                    f"{row.petal_length_cm:.1f}",
                    f"{row.petal_width_cm:.1f}",
                    sql_string(row.species),
                ]
            ) + ")"
        )
    return values


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_sqlite_db(db_path: Path, rows: list[IrisRow]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS iris")
        cur.execute(
            """
            CREATE TABLE iris (
              id INTEGER PRIMARY KEY,
              sepal_length_cm REAL NOT NULL,
              sepal_width_cm REAL NOT NULL,
              petal_length_cm REAL NOT NULL,
              petal_width_cm REAL NOT NULL,
              species TEXT NOT NULL
            )
            """
        )
        cur.executemany(
            """
            INSERT INTO iris (
              id, sepal_length_cm, sepal_width_cm,
              petal_length_cm, petal_width_cm, species
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.iris_id,
                    row.sepal_length_cm,
                    row.sepal_width_cm,
                    row.petal_length_cm,
                    row.petal_width_cm,
                    row.species,
                )
                for row in rows
            ],
        )
        conn.commit()


def build_sql_files(fixtures_root: Path, rows: list[IrisRow]) -> None:
    values = ",\n  ".join(generate_insert_values(rows))

    sqlite_sql = f"""-- Generated from data/Iris.csv\nDROP TABLE IF EXISTS iris;\n\nCREATE TABLE iris (\n  id INTEGER PRIMARY KEY,\n  sepal_length_cm REAL NOT NULL,\n  sepal_width_cm REAL NOT NULL,\n  petal_length_cm REAL NOT NULL,\n  petal_width_cm REAL NOT NULL,\n  species TEXT NOT NULL\n);\n\nINSERT INTO iris (\n  id, sepal_length_cm, sepal_width_cm,\n  petal_length_cm, petal_width_cm, species\n) VALUES\n  {values};\n"""

    postgres_sql = f"""-- Generated from data/Iris.csv\nDROP TABLE IF EXISTS public.iris;\n\nCREATE TABLE public.iris (\n  id INTEGER PRIMARY KEY,\n  sepal_length_cm NUMERIC(4,1) NOT NULL,\n  sepal_width_cm NUMERIC(4,1) NOT NULL,\n  petal_length_cm NUMERIC(4,1) NOT NULL,\n  petal_width_cm NUMERIC(4,1) NOT NULL,\n  species VARCHAR(32) NOT NULL\n);\n\nINSERT INTO public.iris (\n  id, sepal_length_cm, sepal_width_cm,\n  petal_length_cm, petal_width_cm, species\n) VALUES\n  {values};\n"""

    mysql_sql = f"""-- Generated from data/Iris.csv\nDROP TABLE IF EXISTS iris;\n\nCREATE TABLE iris (\n  id INT PRIMARY KEY,\n  sepal_length_cm DECIMAL(4,1) NOT NULL,\n  sepal_width_cm DECIMAL(4,1) NOT NULL,\n  petal_length_cm DECIMAL(4,1) NOT NULL,\n  petal_width_cm DECIMAL(4,1) NOT NULL,\n  species VARCHAR(32) NOT NULL\n);\n\nINSERT INTO iris (\n  id, sepal_length_cm, sepal_width_cm,\n  petal_length_cm, petal_width_cm, species\n) VALUES\n  {values};\n"""

    mssql_sql = f"""-- Generated from data/Iris.csv\nIF OBJECT_ID('dbo.iris', 'U') IS NOT NULL\n  DROP TABLE dbo.iris;\nGO\n\nCREATE TABLE dbo.iris (\n  id INT NOT NULL PRIMARY KEY,\n  sepal_length_cm DECIMAL(4,1) NOT NULL,\n  sepal_width_cm DECIMAL(4,1) NOT NULL,\n  petal_length_cm DECIMAL(4,1) NOT NULL,\n  petal_width_cm DECIMAL(4,1) NOT NULL,\n  species NVARCHAR(32) NOT NULL\n);\nGO\n\nINSERT INTO dbo.iris (\n  id, sepal_length_cm, sepal_width_cm,\n  petal_length_cm, petal_width_cm, species\n) VALUES\n  {values};\nGO\n"""

    sybase_sql = f"""-- Generated from data/Iris.csv\nIF OBJECT_ID('iris') IS NOT NULL\nBEGIN\n  DROP TABLE iris\nEND\nGO\n\nCREATE TABLE iris (\n  id INT NOT NULL PRIMARY KEY,\n  sepal_length_cm DECIMAL(4,1) NOT NULL,\n  sepal_width_cm DECIMAL(4,1) NOT NULL,\n  petal_length_cm DECIMAL(4,1) NOT NULL,\n  petal_width_cm DECIMAL(4,1) NOT NULL,\n  species VARCHAR(32) NOT NULL\n)\nGO\n\nINSERT INTO iris (\n  id, sepal_length_cm, sepal_width_cm,\n  petal_length_cm, petal_width_cm, species\n) VALUES\n  {values}\nGO\n"""

    write_text(fixtures_root / "sqlite" / "init.sql", sqlite_sql)
    write_text(fixtures_root / "postgres" / "init.sql", postgres_sql)
    write_text(fixtures_root / "mysql" / "init.sql", mysql_sql)
    write_text(fixtures_root / "mssql" / "init.sql", mssql_sql)
    write_text(fixtures_root / "sybase" / "init.sql", sybase_sql)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default="data/Iris.csv",
        help="Path to source Iris CSV file (default: data/Iris.csv)",
    )
    parser.add_argument(
        "--fixtures-root",
        default="test-fixtures/databases",
        help="Root folder for DB fixture outputs",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    csv_path = (repo_root / args.csv).resolve()
    fixtures_root = (repo_root / args.fixtures_root).resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows = parse_rows(csv_path)
    build_sql_files(fixtures_root, rows)
    build_sqlite_db(fixtures_root / "sqlite" / "database.sqlite", rows)

    print(f"Generated fixture SQL files and SQLite DB from {csv_path}")
    print(f"Rows imported: {len(rows)}")


if __name__ == "__main__":
    main()
