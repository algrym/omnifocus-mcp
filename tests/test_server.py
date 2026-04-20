"""Smoke tests for the FastMCP server wiring. No OmniFocus, no subprocess."""

from __future__ import annotations

import pytest

from omnifocus_mcp import prompts, server


@pytest.mark.asyncio
async def test_server_registers_all_tools():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    # Curated tools plus escape hatch = 33; guard against accidental drops.
    assert len(names) == 33
    for expected in (
        "check_permissions",
        "list_inbox",
        "create_task",
        "update_tag",
        "mark_project_reviewed",
        "delete_project",
        "parse_transport_text",
        "run_omni_automation",
    ):
        assert expected in names


@pytest.mark.asyncio
async def test_server_registers_three_prompts():
    items = await server.mcp.list_prompts()
    names = {p.name for p in items}
    assert names == {"review", "weekly_review", "inbox_triage"}


def test_prompt_text_has_expected_keywords():
    assert "list_projects_due_for_review" in prompts.REVIEW
    assert "inbox_triage" in prompts.WEEKLY_REVIEW.lower() or "inbox" in prompts.WEEKLY_REVIEW.lower()
    assert "list_inbox" in prompts.INBOX_TRIAGE


@pytest.mark.asyncio
@pytest.mark.parametrize("name,expected", [
    ("review", prompts.REVIEW),
    ("weekly_review", prompts.WEEKLY_REVIEW),
    ("inbox_triage", prompts.INBOX_TRIAGE),
])
async def test_get_prompt_returns_expected_body(name, expected):
    # Exercise each prompt's function body so coverage sees it, and confirm
    # the returned MCP prompt content matches the source in prompts.py.
    result = await server.mcp.get_prompt(name)
    joined = "\n".join(m.content.text for m in result.messages if hasattr(m.content, "text"))
    assert expected.strip() in joined


def test_main_invokes_mcp_run(monkeypatch):
    called = {}
    monkeypatch.setattr(server.mcp, "run", lambda: called.setdefault("ran", True))
    server.main()
    assert called == {"ran": True}
