# Scripts

## Compile Java Assets

These scripts compile Java sources from:

- `java/main/*.java`
- `java/tests/*.java` (optional)

and output class files to:

- `python/resources/out`

Driver jars can be placed in:

- `python/resources/lib`

The Python runtime loads both compiled classes (`out`) and optional driver jars (`lib/*.jar`) into the JVM classpath.

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
./scripts/compile-java.ps1 -OutDir "./python/resources/out"
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
./scripts/compile-java.sh --out-dir ./python/resources/out
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
