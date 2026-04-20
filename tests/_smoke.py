"""Live read-only smoke script. Not a pytest test — run directly:
    uv run python tests/_smoke.py

Exercises every read tool against the live OmniFocus, surfacing any Omni
Automation API identifier that doesn't exist. Read-only: no mutations, no
audit log entries (except the escape-hatch one at the end).
"""

from __future__ import annotations

import traceback

from omnifocus_mcp.tools import read

CHECKS = [
    ("check_permissions", lambda: read.check_permissions()),
    ("list_inbox", lambda: read.list_inbox()[:3]),
    ("list_tasks(flagged=True, limit=5)", lambda: read.list_tasks(flagged=True, limit=5)),
    ("list_tasks(available_only=True, limit=3)", lambda: read.list_tasks(available_only=True, limit=3)),
    ("list_projects(status=Active)", lambda: read.list_projects(status="Active")[:3]),
    ("list_tags()", lambda: read.list_tags()[:5]),
    ("list_folders()", lambda: read.list_folders()[:5]),
    ("list_perspectives", lambda: read.list_perspectives()),
    ("get_forecast(days=3)", lambda: {"keys": list(read.get_forecast(days=3).keys())}),
]

def main() -> int:
    failures = 0
    for name, fn in CHECKS:
        try:
            val = fn()
            preview = repr(val)[:160]
            print(f"  OK  {name}: {preview}")
        except Exception as e:
            failures += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print()
    print(f"{len(CHECKS) - failures}/{len(CHECKS)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
