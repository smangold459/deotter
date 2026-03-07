# deotter

`deotter` is a small JDBC connection utility with:

- A Java core for loading database aliases from a config file and creating JDBC connections.
- A Python wrapper (via JPype) that uses the Java `ConnectionManager` from Python.

## Repository Layout

- `java/main/`: Java connection manager and provider interfaces/implementations.
- `java/tests/`: Java smoke test (`TestConn.java`) for alias-based connectivity.
- `python/`: Python package, packaging metadata, and tests.
- `scripts/`: helper scripts (project-specific automation).

## How It Works

The Java `ConnectionManager` loads config from:

`~/.config/deotter/config.properties`

It expects a `databases` list plus per-alias fields:

- `<alias>.url`
- `<alias>.user`
- `<alias>.password`

Example:

```properties
databases=main,analytics

main.url=jdbc:postgresql://localhost:5432/app
main.user=app_user
main.password=secret

analytics.url=jdbc:mysql://localhost:3306/warehouse
analytics.user=warehouse_user
analytics.password=secret
```

## Java Usage

Use the singleton manager and request connections by alias.

```java
ConnectionManager mgr = ConnectionManager.getInstance();
Connection conn = mgr.getConnection("main");
```

## Python Usage

The Python package lives under `python/` and uses JPype to start a JVM and call Java classes.

Install dependencies from `python/`:

```bash
uv sync
```

Basic usage:

```python
import deotter

with deotter.connect("main", autocommit=False) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        rows = cur.fetchall()
        print(rows)
```

Optional JDBC drivers:

- Drop driver JARs into `python/resources/lib`.
- At runtime, the Python wrapper adds both `python/resources/out` and all `python/resources/lib/*.jar` entries to the JVM classpath.

## Development Notes

- Python dependency for JPype is `jpype1` (not `jpype`).
- Python package metadata is in `python/pyproject.toml`.
- The project is currently lightweight and under active iteration.

## AI Assistance Disclosure

Parts of this repository, including documentation and testing artifacts, were
created with AI assistance and reviewed by a human maintainer before merge.

AI-generated output is treated as draft material and is validated through
manual review and local test execution.

## License

See `LICENSE`.