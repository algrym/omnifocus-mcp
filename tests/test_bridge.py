"""Unit tests for the osascript bridge. No OmniFocus required."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from omnifocus_mcp import bridge


def _fake_completed(stdout: str, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["osascript"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_run_omni_js_parses_json_object():
    with patch("subprocess.run", return_value=_fake_completed('{"ok": true, "n": 3}')):
        assert bridge.run_omni_js("JSON.stringify({ok:true, n:3})") == {"ok": True, "n": 3}


def test_run_omni_js_parses_scalar():
    with patch("subprocess.run", return_value=_fake_completed("42")):
        assert bridge.run_omni_js("6*7") == 42


def test_run_omni_js_returns_raw_on_non_json_output():
    with patch("subprocess.run", return_value=_fake_completed("hello world")):
        assert bridge.run_omni_js("'hello world'") == "hello world"


def test_run_omni_js_surfaces_omni_error():
    err_blob = json.dumps({"__error": "Task.byIdentifier is not a function"})
    with patch("subprocess.run", return_value=_fake_completed(err_blob)):
        with pytest.raises(bridge.OmniAutomationError) as exc:
            bridge.run_omni_js("bogus")
        assert "byIdentifier" in str(exc.value)


def test_run_omni_js_bridge_error_on_nonzero_exit():
    with patch(
        "subprocess.run",
        return_value=_fake_completed("", returncode=1, stderr="boom"),
    ):
        with pytest.raises(bridge.BridgeError):
            bridge.run_omni_js("anything")


def test_run_omni_js_bridge_error_on_timeout():
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="osascript", timeout=1.0),
    ):
        with pytest.raises(bridge.BridgeError) as exc:
            bridge.run_omni_js("anything", timeout_ms=1000)
        assert "timed out" in str(exc.value)


def test_jxa_wrapper_injection_safe():
    """The script is passed via json.dumps into the JXA wrapper, so embedded
    quotes, backslashes, and newlines cannot break out of the string literal."""
    nasty = '"); system("rm -rf /"); //'
    captured = {}

    def _capture(*args, **kwargs):
        captured["input"] = kwargs["input"]
        return _fake_completed('"ok"')

    with patch("subprocess.run", side_effect=_capture):
        bridge.run_omni_js(nasty)
    # The nasty payload appears exactly once, inside a JSON-string literal.
    assert json.dumps(nasty) in captured["input"]
    assert 'system("rm -rf /")' not in captured["input"].replace(json.dumps(nasty), "")


def test_build_script_prepends_common_js():
    body = "JSON.stringify({a:1});"
    merged = bridge.build_script(body)
    assert "_taskToJson" in merged
    assert merged.endswith(body)


def test_common_js_loaded_once_at_import():
    assert "function _taskToJson" in bridge.COMMON_JS
    assert "function _findTask" in bridge.COMMON_JS
