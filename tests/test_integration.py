"""Integration tests that hit a running OmniFocus. Disabled by default.

Run with:  uv run pytest -m integration

These tests MUTATE YOUR OMNIFOCUS DATABASE. They create and delete a scratch
project named `__mcp_test__` and temporary tasks/tags/folders under it. Back
up first (File → Export…) if you're paranoid.

A macOS Automation permission prompt will appear on the first run; accept it.
"""

from __future__ import annotations

import pytest

from omnifocus_mcp.tools import create, destructive, read, review, update

SCRATCH_PREFIX = "__mcp_test__"


@pytest.fixture
def scratch_project():
    proj = create.create_project(name=SCRATCH_PREFIX + "_project")
    yield proj
    destructive.delete_project(proj["id"], confirm=True)


@pytest.mark.integration
def test_check_permissions():
    result = read.check_permissions()
    assert result.get("ok") is True


@pytest.mark.integration
def test_task_lifecycle(scratch_project):
    t = create.create_task(
        name=SCRATCH_PREFIX + "_task",
        project_id=scratch_project["id"],
        due="2030-01-01",
        flagged=True,
    )
    tid = t["id"]

    fetched = read.get_task(tid)
    assert fetched["name"].startswith(SCRATCH_PREFIX)
    assert fetched["flagged"] is True

    update.update_task(tid, name=SCRATCH_PREFIX + "_renamed", flagged=False)
    fetched2 = read.get_task(tid)
    assert fetched2["name"] == SCRATCH_PREFIX + "_renamed"
    assert fetched2["flagged"] is False

    destructive.complete_task(tid, confirm=True)
    fetched3 = read.get_task(tid)
    assert fetched3["completed"] is True


@pytest.mark.integration
def test_tag_crud_and_nesting():
    parent = create.create_tag(name=SCRATCH_PREFIX + "_parent")
    child = create.create_tag(name=SCRATCH_PREFIX + "_child", parent_id=parent["id"])
    try:
        assert child["parent"] == parent["id"]
        renamed = update.update_tag(child["id"], name=SCRATCH_PREFIX + "_child_renamed")
        assert renamed["name"] == SCRATCH_PREFIX + "_child_renamed"
    finally:
        destructive.delete_tag(child["id"], confirm=True)
        destructive.delete_tag(parent["id"], confirm=True)


@pytest.mark.integration
def test_parse_transport_text(scratch_project):
    # Transport-text parser is minimal: line 1 = name, rest = note, no
    # @-directive parsing. Always returns exactly one task.
    tasks = create.parse_transport_text(
        f"{SCRATCH_PREFIX}_via_transport\nThis is the note body.\nAnd another line.",
        project_id=scratch_project["id"],
    )
    assert len(tasks) == 1
    assert tasks[0]["name"] == f"{SCRATCH_PREFIX}_via_transport"
    assert "note body" in tasks[0]["note"]
    assert tasks[0]["project"] == scratch_project["id"]


@pytest.mark.integration
def test_review_flow(scratch_project):
    # Set nextReview in the past, then verify it appears in due-for-review.
    # Note: we don't set reviewInterval here — it's read-only from automation.
    # The project inherits the document default, which is enough for the flow.
    update.update_project(
        scratch_project["id"],
        next_review="2020-01-01",
    )
    due = review.list_projects_due_for_review()
    assert any(p["id"] == scratch_project["id"] for p in due)

    reviewed = review.mark_project_reviewed(
        scratch_project["id"],
        next_review="2030-01-01",
    )
    assert reviewed["lastReviewDate"] is not None
    # Passed-in date parsed as local midnight; serialized as UTC. Just confirm
    # it lands on the Dec-31-2029 / Jan-01-2030 boundary.
    assert reviewed["nextReviewDate"][:4] in ("2029", "2030")


@pytest.mark.integration
def test_destructive_dry_run_then_confirm(scratch_project):
    t = create.create_task(name=SCRATCH_PREFIX + "_del", project_id=scratch_project["id"])
    dry = destructive.delete_task(t["id"])
    assert "preview" in dry
    final = destructive.delete_task(t["id"], confirm=True)
    assert final.get("deleted") is True


@pytest.mark.integration
def test_escape_hatch():
    from omnifocus_mcp.tools import escape

    result = escape.run_omni_automation("JSON.stringify({n: flattenedTasks.length});")
    assert isinstance(result, dict)
    assert isinstance(result["n"], int)
