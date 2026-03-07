# Roadmap

This file tracks planned work for the repository using a lightweight, prioritized backlog.

## How To Use

- Add one item per line under `Now`, `Next`, or `Later`.
- Keep items outcome-focused and testable.
- Link to an issue/PR when available.
- Move completed items to `Done` with completion date.

## Priority And Status

- Priority: `P0` (critical), `P1` (high), `P2` (normal), `P3` (nice-to-have)
- Status: `todo`, `in-progress`, `blocked`, `done`

Template:

`- [ ] [P1][todo] Short outcome statement (owner: @name, issue: #123)`

## Now

- [ ] [P1][todo] Stabilize `python/src/deotter/wrapper.py` fixed-behavior test pass (owner: @smang, issue: #1)
- [ ] [P1][todo] Create functional dummy databases in `test-fixtures/databases` for supported engines (owner: @smang, issue: #2)
- [ ] [P1][todo] Add test execution on virtual machines emulating Windows and macOS/Linux environments (owner: @smang, issue: #3)
- [ ] [P1][todo] Document end-to-end packaging and runtime install flow for Python distribution (owner: @smang, issue: #4)

## Next

- [ ] [P2][todo] Add CI checks for Python tests and Java compile scripts on Windows and Linux (owner: @smang, issue: #5)
- [ ] [P2][todo] Add integration test path that validates JDBC driver discovery from `python/resources/lib` (owner: @smang, issue: #6)
- [ ] [P3][todo] Add contributor guide for local setup and common commands (owner: @smang, issue: #7)

## Later

- [ ] [P3][todo] Add sample fixture bundles for additional DB engines (owner: @smang, issue: #8)
- [ ] [P3][todo] Add release checklist and versioning workflow notes (owner: @smang, issue: #9)

## Blocked

- None

## Done

- 2026-03-07: Added cross-platform Java compile scripts in `scripts/`
- 2026-03-07: Added optional JDBC driver classpath folder `python/resources/lib`
- 2026-03-07: Added initial test fixture structure under `test-fixtures/databases`
