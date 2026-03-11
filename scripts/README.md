# Scripts

## Compile Java Assets

These scripts compile Java sources from:

- `java/main/*.java`
- `java/tests/*.java` (optional)

and output class files to:

- `~/.deotter/bin` (runtime target used by the Python wrapper)

Driver jars can be placed in:

- `~/.deotter/drivers`

The Python runtime loads both compiled classes (`~/.deotter/bin`) and optional driver jars (`~/.deotter/drivers/*.jar`) into the JVM classpath.

### Windows (PowerShell)

```powershell
./scripts/compile-java.ps1
```

Options:

- `-MainOnly` compile only `java/main`
- `-Clean` remove output folder before compile
- `-OutDir <path>` custom output directory

Examples:

```powershell
./scripts/compile-java.ps1 -MainOnly -Clean
./scripts/compile-java.ps1 -OutDir "$HOME/.deotter/bin"
```

### macOS/Linux (Bash)

```bash
./scripts/compile-java.sh
```

Options:

- `--main-only` compile only `java/main`
- `--clean` remove output folder before compile
- `--out-dir <path>` custom output directory

Examples:

```bash
./scripts/compile-java.sh --main-only --clean
./scripts/compile-java.sh --out-dir ~/.deotter/bin
```

## Generate Iris DB Fixtures

Build fixture SQL and SQLite artifacts from `data/Iris.csv` for all database
folders under `test-fixtures/databases`.

### Windows (PowerShell)

```powershell
./python/.venv/Scripts/python.exe ./scripts/generate-iris-fixtures.py
```

### macOS/Linux (Bash)

```bash
./python/.venv/bin/python ./scripts/generate-iris-fixtures.py
```

Optional args:

- `--csv <path>` custom source CSV path
- `--fixtures-root <path>` custom output root

## Run End-to-End Fixture DB Validation (Windows)

Launches local Postgres, MySQL, and MSSQL test databases via Docker, seeds them
from `test-fixtures/databases/*/init.sql`, uses the SQLite fixture file, and runs
`com.deotter.tests.TestConn` to validate row access against dummy `iris` data.

```powershell
./scripts/run-fixture-db-tests.ps1
```

Options:

- `-KeepRunning` leaves containers up after tests for manual inspection.

Optional Sybase validation:

- If you already have a Sybase instance running, set these env vars before
	running the script to include it in the same Java validation pass:
	- `DEOTTER_SYBASE_JDBC_URL`
	- `DEOTTER_SYBASE_USER`
	- `DEOTTER_SYBASE_PASSWORD`
