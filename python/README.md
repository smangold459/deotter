# deotter Python Package

`deotter` provides a Python interface to the Deotter Java connection manager so you can open JDBC connections from Python with a small API.

## Requirements

- Python `>=3.9`
- Java runtime/JDK installed and available on `PATH`
- A Deotter config file at:
	- `~/.config/deotter/config.properties`

## Install

```bash
pip install deotter
```

## Configure Database Aliases

Create `~/.config/deotter/config.properties` with a `databases` list and one block per alias:

```properties
databases=main,analytics

main.url=jdbc:postgresql://localhost:5432/app
main.user=app_user
main.password=secret

analytics.url=jdbc:mysql://localhost:3306/warehouse
analytics.user=warehouse_user
analytics.password=secret
```

## Optional JDBC Drivers

If your database driver is not already available in your Java runtime, place the driver JAR in:

- `python/resources/lib`

When `deotter` starts the JVM, it automatically builds the classpath from:

- `python/resources/out`
- all JARs matching `python/resources/lib/*.jar`

This lets you add or swap JDBC drivers without changing Python code.

## Quick Start

```python
import deotter

with deotter.connect("main", autocommit=False) as conn:
		with conn.cursor() as cur:
				cur.execute("""
				SELECT id, name
				FROM users
				WHERE id = {id}
				""", id=1)

				rows = cur.fetchall()
				print(rows)
```

## API

### `deotter.connect(db_alias: str, autocommit: bool = True)`

Creates and returns a `DeotterConnection` for the configured alias.

### `DeotterConnection`

- `cursor()` create a cursor
- `commit()` commit transaction when `autocommit=False`
- `rollback()` rollback transaction when `autocommit=False`
- `close()` close the connection
- Context manager support:
	- success path commits when `autocommit=False`
	- exception path rolls back when `autocommit=False`

### `DeotterCursor`

- `execute(sql_input, **kwargs)` execute SQL with named placeholders (`{name}`)
- `fetchone()` fetch one row
- `fetchmany(size=1)` fetch next `size` rows
- `fetchall()` fetch all rows
- `close()` close statement/result resources

## Result Helpers

Fetch methods return `DeotterResultSet`, which extends `list` and provides:

- `as_dict()` -> `list[dict]`
- `as_json(indent=None)` -> JSON string
- `as_dataframe()` -> `pandas.DataFrame`

## Troubleshooting: Driver Not Found

If you see errors like `No suitable driver`, `ClassNotFoundException`, or `NoClassDefFoundError`:

1. Confirm the JDBC driver JAR is present in `python/resources/lib`.
2. Confirm the alias in `~/.config/deotter/config.properties` has the correct JDBC URL format for that driver.
3. Restart the Python process after adding or replacing JARs so the JVM is started with the updated classpath.
4. Ensure your Java runtime version is compatible with the JDBC driver version.

## Notes

- SQL parameters are passed as keyword arguments and mapped to `{name}` placeholders.
- Connection aliases must exist in your `config.properties` file.
