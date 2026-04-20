"""Bridge to OmniFocus via `osascript -l JavaScript` + `evaluateJavascript`.

Every call spawns one osascript process, passes a JXA wrapper on stdin that
hands our Omni Automation script to OmniFocus's own runtime, and returns the
JSON-parsed result.

Tools build scripts by concatenating `COMMON_JS` (serializer helpers) with
their own body, interpolating values via `json.dumps(...)` for injection
safety. No template engine — plain string concat.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_MS = 60_000

_SCRIPTS_DIR = Path(__file__).parent / "scripts"
COMMON_JS = (_SCRIPTS_DIR / "common.js.tpl").read_text(encoding="utf-8")


class BridgeError(RuntimeError):
    """osascript itself failed (permission denied, crash, timeout)."""


class OmniAutomationError(RuntimeError):
    """The Omni Automation script ran but raised an exception inside OmniFocus."""


def run_omni_js(script: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> Any:
    """Execute an Omni Automation JS snippet inside OmniFocus, return parsed JSON.

    The caller's `script` must end with a JSON-serializable expression; we do
    NOT prepend COMMON_JS automatically — callers opt in via `build_script`.
    """
    wrapper = (
        "function run() {\n"
        "  const of = Application('OmniFocus');\n"
        "  try {\n"
        f"    const result = of.evaluateJavascript({json.dumps(script)});\n"
        "    return typeof result === 'string' ? result : JSON.stringify(result);\n"
        "  } catch (e) {\n"
        "    return JSON.stringify({__error: String(e && e.message ? e.message : e)});\n"
        "  }\n"
        "}\n"
    )
    try:
        proc = subprocess.run(
            ["/usr/bin/osascript", "-l", "JavaScript"],
            input=wrapper,
            capture_output=True,
            text=True,
            timeout=max(timeout_ms / 1000, 1.0),
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise BridgeError(f"osascript timed out after {timeout_ms}ms") from e

    if proc.returncode != 0:
        raise BridgeError(
            f"osascript exit {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"
        )

    out = proc.stdout.strip()
    if not out:
        return None
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return out  # Plain scalar / unquoted string.
    if isinstance(parsed, dict) and "__error" in parsed:
        raise OmniAutomationError(parsed["__error"])
    return parsed


def build_script(body: str) -> str:
    """Prepend COMMON_JS helpers to a tool-supplied script body."""
    return COMMON_JS + "\n" + body


def run(body: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> Any:
    """Convenience: prepend COMMON_JS and execute."""
    return run_omni_js(build_script(body), timeout_ms=timeout_ms)
