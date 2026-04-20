"""FastMCP server exposing OmniFocus 4 via stdio MCP.

Registers every tool from omnifocus_mcp.tools.* and the prompt templates.
Run as: `omnifocus-mcp` (entry point) or `python -m omnifocus_mcp.server`.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import prompts
from .tools import create as t_create
from .tools import destructive as t_destructive
from .tools import escape as t_escape
from .tools import read as t_read
from .tools import review as t_review
from .tools import update as t_update

mcp = FastMCP("omnifocus")

# --- Read tools ---
mcp.add_tool(t_read.check_permissions)
mcp.add_tool(t_read.list_inbox)
mcp.add_tool(t_read.list_tasks)
mcp.add_tool(t_read.list_projects)
mcp.add_tool(t_read.list_tags)
mcp.add_tool(t_read.list_folders)
mcp.add_tool(t_read.list_perspectives)
mcp.add_tool(t_read.get_task)
mcp.add_tool(t_read.get_project)
mcp.add_tool(t_read.get_tag)
mcp.add_tool(t_read.get_folder)
mcp.add_tool(t_read.get_forecast)

# --- Create ---
mcp.add_tool(t_create.create_task)
mcp.add_tool(t_create.create_project)
mcp.add_tool(t_create.create_tag)
mcp.add_tool(t_create.create_folder)
mcp.add_tool(t_create.parse_transport_text)

# --- Update ---
mcp.add_tool(t_update.update_task)
mcp.add_tool(t_update.update_project)
mcp.add_tool(t_update.update_tag)
mcp.add_tool(t_update.update_folder)
mcp.add_tool(t_update.move_task)

# --- Review ---
mcp.add_tool(t_review.list_projects_due_for_review)
mcp.add_tool(t_review.mark_project_reviewed)

# --- Destructive ---
mcp.add_tool(t_destructive.complete_task)
mcp.add_tool(t_destructive.drop_task)
mcp.add_tool(t_destructive.delete_task)
mcp.add_tool(t_destructive.complete_project)
mcp.add_tool(t_destructive.drop_project)
mcp.add_tool(t_destructive.delete_project)
mcp.add_tool(t_destructive.delete_tag)
mcp.add_tool(t_destructive.delete_folder)

# --- Escape hatch ---
mcp.add_tool(t_escape.run_omni_automation)


@mcp.prompt()
def review() -> str:
    """Walk through projects due for review, one at a time."""
    return prompts.REVIEW


@mcp.prompt()
def weekly_review() -> str:
    """Inbox triage + project review + 14-day forecast."""
    return prompts.WEEKLY_REVIEW


@mcp.prompt()
def inbox_triage() -> str:
    """Process inbox items one-by-one: assign project, tag, schedule."""
    return prompts.INBOX_TRIAGE


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
