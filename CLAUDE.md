# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Hard prerequisite

OmniFocus 4 with the **Pro** in-app purchase, running on macOS. Non-Pro installs reject every scripting call with `"Scripting OmniFocus is a Pro feature."`. `check_permissions` surfaces this cleanly; nothing else works without Pro.

First scripting call per process triggers a one-time macOS Automation permission prompt.

## Commands

Most common tasks are wrapped in the `Makefile` — run `make help` for the menu. Key targets:

| Make target | What it does |
|---|---|
| `make install` | `uv sync --extra dev` |
| `make test` | Unit tests (77) — no OmniFocus needed |
| `make test-integration` | Live tests (7) — **mutates** real OmniFocus DB |
| `make test-all` | Unit + integration |
| `make smoke` | Live read-only smoke (`tests/_smoke.py`) |
| `make coverage` / `make coverage-html` | Coverage report |
| `make server` | Run the MCP server on stdio |
| `make install-tool` | `uv tool install --from . omnifocus-mcp --force` |
| `make scratch-clean` | Remove any `__mcp_test__*` residue left in OmniFocus from a failed integration run |
| `make clean` / `make distclean` | Caches + build artifacts / that plus `.venv` |

Ad-hoc invocations (for single-file or `-k` name filters) still want raw pytest:

```bash
uv run pytest tests/test_bridge.py
uv run pytest -k test_jxa_wrapper
```

Integration tests create a scratch project named `__mcp_test__` and delete it in a fixture; safe in principle, but back up OmniFocus first.

## Architecture

Every tool flows through one path: **Python → osascript subprocess (JXA) → `Application('OmniFocus').evaluateJavascript(script)` → OmniFocus Omni Automation runtime → JSON string → Python**. No daemon, no persistent state, one subprocess per call. Running inside Omni Automation (not raw JXA) is a deliberate choice — it avoids JXA type-conversion bugs with tags and repeats.

### Data flow per tool call

`src/omnifocus_mcp/bridge.py` owns the subprocess shell. `run_omni_js(script)` wraps the caller's script in a small JXA `run()` function that catches exceptions and returns either the JSON result or `{__error: msg}`. The bridge parses the returned string back into Python; `__error` becomes `OmniAutomationError`, subprocess failures become `BridgeError`.

`COMMON_JS` (loaded once from `src/omnifocus_mcp/scripts/common.js.tpl`) provides serializers `_taskToJson`, `_projectToJson`, `_tagToJson`, `_folderToJson` and finders `_findTask`, `_findProject`, `_findTag`, `_findFolder`. Every tool script opts into these via `bridge.run(body)` (which prepends COMMON_JS) rather than `bridge.run_omni_js(body)` (which doesn't — used only by the escape hatch).

### Tool modules

All tools live in `src/omnifocus_mcp/tools/`, one file per category: `read`, `create`, `update`, `review`, `destructive`, `escape`. Each Python function:

1. Validates inputs (FastMCP infers JSON Schema from type hints — no separate models.py).
2. Builds its Omni Automation JS inline with `json.dumps()` interpolation. **This is the injection-safety contract** — every value from Python enters JS only via `json.dumps()`. Do not use JS template literals (backticks); Python `string.Template` isn't used, but keep the convention.
3. Calls `bridge.run(body)` and returns the parsed dict/list directly (FastMCP serializes to MCP response format).

### Destructive tools

`src/omnifocus_mcp/tools/destructive.py` gates every complete/drop/delete on a `confirm: bool = False` parameter. Without `confirm=True`, they return a dry-run preview (`{preview: {...}, message: "..."}`) and do not touch the DB. With `confirm=True`, they execute and append a JSON line to `~/.omnifocus-mcp/audit.log` via `audit.append_audit()`. The escape hatch (`tools/escape.py`) audits every call unconditionally. **Do not add destructive tools without this pattern.**

### Server wiring

`src/omnifocus_mcp/server.py` registers all tools and three prompts (`review`, `weekly_review`, `inbox_triage`, text-only in `prompts.py`). Module imports use `t_read`, `t_create`, etc. aliases to avoid shadowing by same-named prompt functions. Entry point `omnifocus-mcp = omnifocus_mcp.server:main` runs FastMCP over stdio.

### Known limits and Omni Automation gotchas (all verified live)

- **Finders must be static** — `Task.byIdentifier(id)` / `Project.byIdentifier(id)` / `Tag.byIdentifier(id)` / `Folder.byIdentifier(id)`. The collection form (`flattenedTasks.byIdentifier`) does NOT exist; it silently returns `undefined`. Regression test in `test_update_tag_make_top_level_uses_tags_not_library` guards the related identifier choice.
- **Status enums stringify oddly** — `String(p.status)` returns `"[object Project.Status: Active]"`, not `"Active"`. Use `_enumName()` from `common.js.tpl` to serialize, and compare against `Project.Status.Active` (identity) for filtering, not strings.
- **Reserved globals** — `tags` is a built-in global bound to the top-level tag collection. Shadowing with `var tags = []` silently fails inside `evaluateJavascript`. Use distinct local names (the serializer uses `_tagNames` / `_tagIds`).
- **Top-level move destinations are distinct** — folders/projects move to `library.ending`; tags move to `tags.ending`. Not interchangeable.
- **Tag.Status** is `Active` / `OnHold` / `Dropped` only — there is no `Hidden`.
- **`Project.ReviewInterval` is read-only from automation** — no public constructor, no factory, and mutating `.steps` / `.unit` on a fetched instance silently no-ops. `create_project` and `update_project` do NOT expose interval-setting params; shift cadence via `next_review` / `last_review` dates instead.
- **`Task.byParsingTransportText` is minimal** — line 1 = name, rest = note, NO `@tag` / `@due(...)` / `@flagged` directive parsing. Always returns a one-element array. The `parse_transport_text` tool docstring says so; `create_task` is the real task-authoring path.
- **Property access is ~7 ms per call** — on a 980-task DB, `effectiveDueDate` on every task blew past 30 s. `get_forecast` uses raw `dueDate` / `deferDate` with early pruning; bridge default timeout is 60 s.
- **Perspectives can be listed but not executed** — the API returns names only, not task output. Use `list_tasks` with explicit filters to reproduce custom perspectives.
- **`moveTasks` / `moveSections` / `moveTags` mutate in place and return undefined.** Don't assign the result back; use the original array reference.
- **Review intervals advance approximately** — `mark_project_reviewed` does its own `day/week/month/year` stepping in JS; OmniFocus's own month-end logic may differ slightly. Pass `next_review` explicitly when precision matters.
