"""Exhaustive unit coverage: every curated tool renders a valid Omni
Automation script, every destructive tool respects the confirm flag, and the
escape hatch audit-logs. Mocks the bridge — no OmniFocus.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from omnifocus_mcp import audit, bridge
from omnifocus_mcp.tools import create, destructive, escape, read, review, update


def _patch_tool_run(module, returning):
    """Patch the `run` symbol inside a tool module; capture the script body."""
    seen = {}

    def _fake(body: str, timeout_ms: int = 15_000):
        seen.setdefault("bodies", []).append(body)
        return returning

    return seen, patch.object(module, "run", side_effect=_fake)


# --- Read tools -----------------------------------------------------------

READ_CALLS = [
    (read.check_permissions, (), {}, [], "1 + 1"),
    (read.list_inbox, (), {}, [], "inbox.forEach"),
    (read.list_tasks, (), {"project_id": "p1"}, [], "flattenedTasks"),
    (read.list_tasks, (), {"tag_id": "t1", "available_only": True}, [], "availableOnly"),
    (read.list_tasks, (), {"name_contains": "FOO", "note_contains": "BAR"}, [], "toLowerCase"),
    (read.list_projects, (), {}, [], "flattenedProjects"),
    (read.list_projects, (), {"status": "Active", "folder_id": "f1"}, [], "_projectStatus"),
    (read.list_tags, (), {}, [], "_tagToJson"),
    (read.list_tags, (), {"parent_id": "parent"}, [], "_findTag"),
    (read.list_folders, (), {}, [], "flattenedFolders"),
    (read.list_folders, (), {"parent_id": "root"}, [], "_findFolder"),
    (read.list_perspectives, (), {}, [], "Perspective"),
    (read.get_task, ("t1",), {}, None, "_taskToJson"),
    (read.get_project, ("p1",), {}, None, "_projectToJson"),
    (read.get_tag, ("t1",), {}, None, "_tagToJson"),
    (read.get_folder, ("f1",), {}, None, "_folderToJson"),
    (read.get_forecast, (), {"days": 3}, {}, "horizonDays"),
]


@pytest.mark.parametrize("fn,args,kwargs,returning,marker", READ_CALLS)
def test_read_tool_renders_script(fn, args, kwargs, returning, marker):
    seen, patcher = _patch_tool_run(read, returning)
    with patcher:
        fn(*args, **kwargs)
    assert marker in seen["bodies"][-1]


def test_check_permissions_surfaces_pro_error():
    """When OmniFocus returns the Pro-required error, check_permissions
    turns it into a structured diagnostic instead of raising."""
    def _fake(body, timeout_ms=15_000):
        raise bridge.OmniAutomationError("Error: Scripting OmniFocus is a Pro feature.")

    with patch.object(read, "run", side_effect=_fake):
        result = read.check_permissions()
    assert result["ok"] is False
    assert result["reason"] == "OmniFocus Pro required"


def test_check_permissions_surfaces_generic_error():
    def _fake(body, timeout_ms=15_000):
        raise bridge.OmniAutomationError("Something else broke")

    with patch.object(read, "run", side_effect=_fake):
        result = read.check_permissions()
    assert result["ok"] is False
    assert result["reason"] == "OmniAutomationError"


# --- Create tools ---------------------------------------------------------

def test_create_task_minimal():
    seen, patcher = _patch_tool_run(create, {"id": "x"})
    with patcher:
        create.create_task(name="x")
    assert "new Task" in seen["bodies"][-1]


def test_create_project_with_folder_and_note():
    seen, patcher = _patch_tool_run(create, {"id": "p"})
    with patcher:
        create.create_project(name="x", folder_id="f", sequential=True, note="n")
    body = seen["bodies"][-1]
    assert "new Project" in body
    assert "_findFolder" in body
    assert "p.sequential = true" in body
    assert "reviewInterval" not in body  # dropped — read-only from automation


def test_create_folder_top_level_and_nested():
    seen, patcher = _patch_tool_run(create, {"id": "f"})
    with patcher:
        create.create_folder(name="x")
        create.create_folder(name="x", parent_id="parent")
    assert "new Folder(name)" in seen["bodies"][0]
    assert "_findFolder(parentId)" in seen["bodies"][1]


def test_parse_transport_text_no_project():
    seen, patcher = _patch_tool_run(create, [])
    with patcher:
        create.parse_transport_text("Hello world")
    body = seen["bodies"][-1]
    assert "byParsingTransportText" in body
    # moveTasks is only invoked when project_id is set
    assert "moveTasks" not in body or "if (projectId)" in body


def test_parse_transport_text_with_project():
    seen, patcher = _patch_tool_run(create, [])
    with patcher:
        create.parse_transport_text("Hello world", project_id="p1")
    assert "moveTasks" in seen["bodies"][-1]


# --- Update tools ---------------------------------------------------------

def test_update_task_with_dates_and_clears():
    seen, patcher = _patch_tool_run(update, {})
    with patcher:
        update.update_task(
            task_id="t1",
            name="new",
            due="2026-05-01",
            clear_defer=True,
            tag_ids=["tag1"],
        )
    body = seen["bodies"][-1]
    assert "t.name = name" in body
    assert "t.deferDate = null" in body
    assert "addTag" in body


def test_update_project_covers_all_fields():
    seen, patcher = _patch_tool_run(update, {})
    with patcher:
        update.update_project(
            project_id="p1",
            name="n", note="note", folder_id="f", sequential=True,
            status="OnHold", next_review="2026-05-01", last_review="2026-04-01",
            flagged=True,
        )
    body = seen["bodies"][-1]
    for needle in ("moveSections", "_projectStatus", "nextReviewDate", "lastReviewDate"):
        assert needle in body
    assert "reviewInterval" not in body  # dropped


def test_update_tag_make_top_level_uses_tags_not_library():
    seen, patcher = _patch_tool_run(update, {})
    with patcher:
        update.update_tag(tag_id="t1", make_top_level=True)
    body = seen["bodies"][-1]
    assert "moveTags([t], tags.ending)" in body
    assert "library.ending" not in body  # regression guard


def test_update_tag_with_parent_and_status():
    seen, patcher = _patch_tool_run(update, {})
    with patcher:
        update.update_tag(tag_id="t1", parent_id="p", status="OnHold", allows_next_action=False)
    body = seen["bodies"][-1]
    assert "_findTag(parentId)" in body
    assert "_tagStatus" in body
    assert "allowsNextAction" in body


def test_update_folder_variants():
    seen, patcher = _patch_tool_run(update, {})
    with patcher:
        update.update_folder(folder_id="f1", name="x")
        update.update_folder(folder_id="f1", make_top_level=True)
        update.update_folder(folder_id="f1", parent_id="p")
    assert "library.ending" in seen["bodies"][1]  # top-level folder move IS library
    assert "_findFolder(parentId)" in seen["bodies"][2]


def test_move_task_exactly_one_destination():
    with pytest.raises(ValueError):
        update.move_task(task_id="t1")
    with pytest.raises(ValueError):
        update.move_task(task_id="t1", to_inbox=True, to_project_id="p")

    seen, patcher = _patch_tool_run(update, {})
    with patcher:
        update.move_task(task_id="t1", to_inbox=True)
        update.move_task(task_id="t1", to_project_id="p")
        update.move_task(task_id="t1", to_parent_task_id="pt")
    assert "inbox.ending" in seen["bodies"][0]
    assert "_findProject(toProject)" in seen["bodies"][1]
    assert "_findTask(toParent)" in seen["bodies"][2]


# --- Destructive tools ----------------------------------------------------

DESTRUCTIVE_TOOLS = [
    (destructive.complete_task, {"task_id": "t1"}, "markComplete"),
    (destructive.drop_task, {"task_id": "t1"}, "t.drop"),
    (destructive.delete_task, {"task_id": "t1"}, "deleteObject"),
    (destructive.complete_project, {"project_id": "p1"}, "Project.Status.Done"),
    (destructive.drop_project, {"project_id": "p1"}, "Project.Status.Dropped"),
    (destructive.delete_project, {"project_id": "p1"}, "deleteObject"),
    (destructive.delete_tag, {"tag_id": "tag1"}, "deleteObject"),
    (destructive.delete_folder, {"folder_id": "f1"}, "deleteObject"),
]


@pytest.mark.parametrize("fn,kwargs,confirm_marker", DESTRUCTIVE_TOOLS)
def test_destructive_dry_run_has_no_mutation(fn, kwargs, confirm_marker):
    seen, patcher = _patch_tool_run(destructive, {"preview": True})
    with patcher:
        result = fn(**kwargs)
    assert "preview" in result
    # Dry-run body must NOT contain the mutation marker.
    assert confirm_marker not in seen["bodies"][-1]


@pytest.mark.parametrize("fn,kwargs,confirm_marker", DESTRUCTIVE_TOOLS)
def test_destructive_confirm_executes_and_logs(fn, kwargs, confirm_marker, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "audit.log")

    seen, patcher = _patch_tool_run(destructive, {"ok": True})
    with patcher:
        fn(confirm=True, **kwargs)
    assert confirm_marker in seen["bodies"][-1]
    entry = json.loads((tmp_path / "audit.log").read_text().strip().splitlines()[-1])
    assert entry["tool"] == fn.__name__
    assert entry["args"] == kwargs


# --- Review tools ---------------------------------------------------------

def test_list_projects_due_for_review_respects_include_on_hold():
    seen, patcher = _patch_tool_run(review, [])
    with patcher:
        review.list_projects_due_for_review(include_on_hold=False)
    assert "includeOnHold" in seen["bodies"][-1]


def test_mark_project_reviewed_with_override():
    seen, patcher = _patch_tool_run(review, {})
    with patcher:
        review.mark_project_reviewed("p1", next_review="2030-01-01")
    body = seen["bodies"][-1]
    assert "lastReviewDate = new Date()" in body
    assert "_parseDate" in body


# --- Escape hatch ---------------------------------------------------------

def test_run_omni_automation_audits(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "audit.log")

    with patch.object(bridge, "run_omni_js", return_value={"ok": True}):
        result = escape.run_omni_automation("JSON.stringify({ok:true})")
    assert result == {"ok": True}
    entry = json.loads((tmp_path / "audit.log").read_text().strip())
    assert entry["tool"] == "run_omni_automation"
    assert entry["args"]["script"] == "JSON.stringify({ok:true})"


# --- Bridge convenience + edge paths --------------------------------------

def test_run_convenience_prepends_common_js():
    captured = {}

    def _fake(full_script, timeout_ms=15_000):
        captured["script"] = full_script
        return 42

    with patch.object(bridge, "run_omni_js", side_effect=_fake):
        assert bridge.run("JSON.stringify(6*7);") == 42
    assert "_taskToJson" in captured["script"]
    assert captured["script"].endswith("JSON.stringify(6*7);")


def test_run_omni_js_empty_stdout_returns_none():
    import subprocess
    from unittest.mock import patch as _patch

    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with _patch("subprocess.run", return_value=fake):
        assert bridge.run_omni_js("noop") is None
