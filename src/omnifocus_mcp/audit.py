"""Append-only JSONL audit log for destructive and escape-hatch operations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_DIR = Path(os.path.expanduser("~/.omnifocus-mcp"))
AUDIT_LOG = AUDIT_DIR / "audit.log"


def append_audit(tool: str, args: dict[str, Any], result: Any) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "result": result,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
