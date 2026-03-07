# Test Fixtures

Shared test fixtures used across Java and Python test suites.

## Databases

- `databases/postgres/`
- `databases/mysql/`
- `databases/sqlite/`
- `databases/sybase/`
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
