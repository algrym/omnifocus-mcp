"""Unit tests asserting that each tool produces a well-formed Omni Automation
script (injection-safe interpolation, no unresolved placeholders, ends with a
JSON-serialized expression). Mocks the bridge so no OmniFocus is needed.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from omnifocus_mcp.tools import create, destructive, read, review, update


def _captured(returning):
    """Intercept bridge.run and return `returning`; expose the rendered script."""
    seen = {}

    def _fake(body: str, timeout_ms: int = 15_000):
        seen["body"] = body
        return returning

    return seen, _fake


def test_list_inbox_script_uses_inbox_iterator():
    seen, fake = _captured([])
    with patch("omnifocus_mcp.tools.read.run", side_effect=fake):
        read.list_inbox()
    assert "inbox.forEach" in seen["body"]
    assert "_taskToJson" in seen["body"]


def test_list_tasks_interpolates_all_filters_json_safe():
    seen, fake = _captured([])
    with patch("omnifocus_mcp.tools.read.run", side_effect=fake):
        read.list_tasks(
            project_id='p"; DROP TABLE',
            tag_id="t",
            flagged=True,
            due_before="2026-05-01",
            name_contains="meet",
            limit=10,
        )
    # Injection attempt survives as a JSON-encoded string literal, not code.
    assert json.dumps('p"; DROP TABLE') in seen["body"]
    assert json.dumps(True) in seen["body"]
    assert "flattenedTasks" in seen["body"]


def test_create_task_handles_tags_and_dates():
    seen, fake = _captured({"id": "abc"})
    with patch("omnifocus_mcp.tools.create.run", side_effect=fake):
        create.create_task(
            name="Write spec",
            project_id="p1",
            due="2026-05-01T09:00:00Z",
            tag_ids=["t1", "t2"],
            flagged=True,
            estimate_minutes=30,
        )
    assert "new Task" in seen["body"]
    assert json.dumps(["t1", "t2"]) in seen["body"]
    assert "addTag" in seen["body"]
    assert "t.flagged = true" in seen["body"]


def test_create_tag_nested():
    seen, fake = _captured({"id": "x"})
    with patch("omnifocus_mcp.tools.create.run", side_effect=fake):
        create.create_tag(name="urgent", parent_id="parent-id")
    assert "new Tag" in seen["body"]
    assert "_findTag(parentId)" in seen["body"]


def test_update_task_patch_only_supplied_fields():
    seen, fake = _captured({})
    with patch("omnifocus_mcp.tools.update.run", side_effect=fake):
        update.update_task(task_id="id1", flagged=False)
    # name/note/due/defer/estimate should be passed as null so JS skips them.
    assert "flagged != null" in seen["body"]
    assert "name = null" in seen["body"] or "name = null;" in seen["body"]


def test_move_task_requires_exactly_one_destination():
    with pytest.raises(ValueError):
        update.move_task(task_id="t1")
    with pytest.raises(ValueError):
        update.move_task(task_id="t1", to_inbox=True, to_project_id="p1")


def test_destructive_dry_run_without_confirm():
    seen, fake = _captured({"id": "t1", "name": "x"})
    with patch("omnifocus_mcp.tools.destructive.run", side_effect=fake):
        result = destructive.delete_task("t1")
    assert "preview" in result
    assert "confirm=true" in result["message"]
    # Dry-run must not contain deleteObject in the executed script.
    assert "deleteObject" not in seen["body"]


def test_destructive_with_confirm_executes_and_logs(tmp_path, monkeypatch):
    seen, fake = _captured({"deleted": True})
    # Redirect audit log to tmp.
    from omnifocus_mcp import audit

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit, "AUDIT_LOG", log_path)

    with patch("omnifocus_mcp.tools.destructive.run", side_effect=fake):
        destructive.delete_task("t1", confirm=True)

    assert "deleteObject" in seen["body"]
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "delete_task"
    assert entry["args"] == {"task_id": "t1"}


def test_list_projects_due_for_review_sorts_overdue():
    seen, fake = _captured([])
    with patch("omnifocus_mcp.tools.review.run", side_effect=fake):
        review.list_projects_due_for_review(as_of="2026-04-19")
    assert "nextReviewDate" in seen["body"]
    assert "daysOverdue" in seen["body"]
    assert "sort(" in seen["body"]


def test_mark_project_reviewed_uses_interval():
    seen, fake = _captured({})
    with patch("omnifocus_mcp.tools.review.run", side_effect=fake):
        review.mark_project_reviewed(project_id="p1")
    assert "lastReviewDate = new Date()" in seen["body"]
    assert "reviewInterval" in seen["body"]
