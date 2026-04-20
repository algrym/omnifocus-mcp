"""MCP prompt templates for common OmniFocus workflows.

These return prompt text intended to be injected by the client; they don't
orchestrate tool calls themselves. The text instructs Claude on how to use
the curated tools to reproduce a built-in OmniFocus workflow.
"""

from __future__ import annotations

REVIEW = """You're walking me through my OmniFocus project review. Follow this loop:

1. Call `list_projects_due_for_review` (include on-hold projects).
2. If the list is empty, tell me we're done and stop.
3. Otherwise, take the most overdue project (first in the list). Call
   `get_project` to fetch its note and root tasks.
4. Summarize the project in 2-3 lines: name, status, days overdue, note
   excerpt, and the 3-5 most salient root tasks (incomplete only).
5. Ask me what I want to do: keep & mark reviewed, reschedule next review
   only, change review interval, put on hold, mark done, drop, or skip.
6. Execute my choice with the appropriate tool (`mark_project_reviewed`,
   `update_project`, `complete_project`, `drop_project`). Destructive ops
   will require confirm=true — include it when I've clearly assented.
7. Go back to step 1.

Be concise — one project at a time, minimum chatter between steps."""


WEEKLY_REVIEW = """Run my weekly OmniFocus review in three phases:

PHASE 1 — INBOX TRIAGE
- Call `list_inbox`. For each item, propose a disposition: assign to a
  specific project (look it up first via `list_projects`), add tags, set
  due/defer dates, or convert to a standalone project. Wait for my OK, then
  apply.

PHASE 2 — PROJECT REVIEW
- Run the `review` flow described in that prompt until done.

PHASE 3 — HORIZON
- Call `get_forecast(days=14)`. Flag anything overdue or uncomfortably close
  together. Ask if I want to reschedule any of it.

Keep each phase tight; ask before doing anything destructive."""


INBOX_TRIAGE = """Triage my OmniFocus inbox. For each item from `list_inbox`:

1. Show the name + note excerpt + any existing tags/dates.
2. Suggest: project assignment (search with `list_projects` if unsure),
   tags (from `list_tags`), due/defer date, flag y/n.
3. Wait for my thumbs up or corrections, then apply via `update_task` and
   `move_task`.
4. Continue until the inbox is empty.

If an item should just be done in under 2 minutes, suggest completing it
immediately."""
