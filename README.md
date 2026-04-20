# omnifocus-mcp

A Model Context Protocol server that exposes OmniFocus 4 to **Claude Code** and **Claude Desktop**.

Talks to OmniFocus via `osascript -l JavaScript` → `Application('OmniFocus').evaluateJavascript(script)`, so everything runs inside OmniFocus's own Omni Automation runtime — sidestepping known JXA type-conversion bugs with tags and repeats.

## What's in the box

Curated tools for the common cases plus a `run_omni_automation` escape hatch for anything unusual.

**Read** — `list_inbox`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `get_task/project/tag/folder`, `get_forecast(days)`, `check_permissions`

**Create** — `create_task`, `create_project`, `create_tag`, `create_folder`, `parse_taskpaper` (uses OmniFocus's built-in TaskPaper parser)

**Update** — `update_task`, `update_project`, `update_tag`, `update_folder`, `move_task`

**Review** — `list_projects_due_for_review`, `mark_project_reviewed` (duplicates OmniFocus's Review workflow)

**Destructive** (require `confirm: true`, audit-logged to `~/.omnifocus-mcp/audit.log`) — `complete_task/project`, `drop_task/project`, `delete_task/project/tag/folder`

**Escape hatch** — `run_omni_automation(script, timeout_ms?)` runs any Omni Automation JavaScript and returns the result as JSON

**Prompts** — `review`, `weekly_review`, `inbox_triage`

## Install

### One-time setup

Clone or install from PyPI once released. For now, install from source:

```bash
uv tool install --from /path/to/omnifocus omnifocus-mcp
# or, from git:
# uv tool install --from git+https://github.com/<you>/omnifocus-mcp omnifocus-mcp
```

`uv tool install` puts the `omnifocus-mcp` script on your PATH. Verify:

```bash
which omnifocus-mcp
```

### Claude Code

Add to `~/.claude/settings.json` (or project-local `.claude/settings.local.json`):

```json
{
  "mcpServers": {
    "omnifocus": {
      "command": "omnifocus-mcp"
    }
  }
}
```

Then `claude mcp list` (or restart Claude Code) should show `omnifocus ✓`.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omnifocus": {
      "command": "omnifocus-mcp"
    }
  }
}
```

Restart Claude Desktop. The server appears under the tool picker.

If `omnifocus-mcp` isn't on Claude Desktop's PATH (GUI apps don't inherit shell PATH), use the absolute path:

```json
{
  "mcpServers": {
    "omnifocus": {
      "command": "/Users/YOU/.local/bin/omnifocus-mcp"
    }
  }
}
```

(Run `which omnifocus-mcp` to find yours.)

## Requires OmniFocus Pro

**Scripting is a Pro-only feature in OmniFocus 4.** On a non-Pro install, every
call fails with `"Scripting OmniFocus is a Pro feature."` — the server reports
this cleanly via `check_permissions`, but no tool can actually do anything.
If you're not on Pro, upgrade via **OmniFocus > In-App Purchase** first.

## Grant Automation permission

The first time the server talks to OmniFocus, macOS will prompt for Automation permission. You can trigger this deliberately by calling the `check_permissions` tool — it runs a trivial round-trip. After you approve once, subsequent calls work without prompting.

If you missed the prompt or denied it, fix via **System Settings → Privacy & Security → Automation → Claude (or Terminal) → OmniFocus: ON**.

## Safety model

- **Destructive tools require `confirm: true`.** Without it, they return a dry-run preview of what would be affected and ask you to re-call with `confirm: true`.
- **Audit log.** All destructive operations and every `run_omni_automation` call append a JSON line to `~/.omnifocus-mcp/audit.log` with timestamp, tool name, arguments, and result. Forensic trail if anything goes sideways.
- **Back up OmniFocus first** before running integration tests or large batch edits. OmniFocus's own `File → Export…` makes a snapshot.

## Development

```bash
uv sync --extra dev
uv run pytest              # unit tests (no OmniFocus needed)
uv run pytest -m integration  # requires OmniFocus running; mutates real data
```

## Limitations

- **Perspectives can't be executed programmatically.** Omni Automation lets us list them and set the current perspective in the UI, but there's no API to retrieve a perspective's task list. Use `list_tasks` with explicit filters instead.
- **Review intervals are approximated.** `mark_project_reviewed` advances `nextReviewDate` by the project's `reviewInterval`, but OmniFocus's internal calendar math (month-end handling etc.) may not match exactly. For precision, pass `next_review` explicitly.
- **First automation call prompts.** macOS Automation permission is a one-time user interaction; no way to pre-authorize programmatically.

## License

MIT
