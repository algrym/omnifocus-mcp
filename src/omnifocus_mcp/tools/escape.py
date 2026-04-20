"""Escape hatch: execute arbitrary Omni Automation JavaScript."""

from __future__ import annotations

from typing import Any

from ..audit import append_audit
from ..bridge import DEFAULT_TIMEOUT_MS, run_omni_js


def run_omni_automation(script: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> Any:
    """Run an arbitrary Omni Automation JavaScript snippet inside OmniFocus.

    The script runs in OmniFocus's Omni Automation context (not JXA). The full
    Omni Automation API is available: Task, Project, Tag, Folder, flattenedTasks,
    inbox, moveTasks, etc. The script must end with a JSON-serializable
    expression (return value is JSON-encoded and returned to the caller).

    Serializer helpers from COMMON_JS are NOT prepended — this is the raw
    escape hatch. Use `run_omni_automation` for full control; prefer the
    curated tools when they fit.

    All invocations are audit-logged to ~/.omnifocus-mcp/audit.log.
    """
    result = run_omni_js(script, timeout_ms=timeout_ms)
    append_audit(
        "run_omni_automation",
        {"script": script, "timeout_ms": timeout_ms},
        result,
    )
    return result
