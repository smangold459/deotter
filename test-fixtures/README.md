# Test Fixtures

Shared test fixtures used across Java and Python test suites.

## Databases

- `databases/postgres/`
- `databases/mysql/`
- `databases/sqlite/`
- `databases/sybase/`

Container orchestration for local fixture testing:

- `databases/docker-compose.yml`
	- launches `postgres`, `mysql`, and `mssql` locally
	- mounts the corresponding `init.sql` files for seeding
- `databases/mssql/`

Add engine-specific setup files such as:

- `docker-compose.yml`
- `init.sql`
- seed data files

## Iris Fixture Generation

The repository includes `scripts/generate-iris-fixtures.py`, which converts
`data/Iris.csv` into fixture artifacts for all supported engines.

Generated files:

- `databases/sqlite/database.sqlite`
- `databases/sqlite/init.sql`
- `databases/postgres/init.sql`
- `databases/mysql/init.sql`
- `databases/mssql/init.sql`
- `databases/sybase/init.sql`

Run from repository root:

```powershell
./python/.venv/Scripts/python.exe ./scripts/generate-iris-fixtures.py
```

## Launch And Validate Fixture Databases

From repository root (Windows PowerShell):

```powershell
./scripts/run-fixture-db-tests.ps1
```

This workflow:

- regenerates fixture SQL and SQLite database from `data/Iris.csv`
- starts local Postgres/MySQL/MSSQL containers
- seeds each container with the dummy `iris` data
- runs `java/tests/TestConn.java` to query and validate fixture rows

Optional Sybase inclusion:

- If a Sybase server is available externally, set these env vars to include it
	in the same validation run:
	- `DEOTTER_SYBASE_JDBC_URL`
	- `DEOTTER_SYBASE_USER`
	- `DEOTTER_SYBASE_PASSWORD`
