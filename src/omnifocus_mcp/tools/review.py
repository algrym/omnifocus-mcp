"""Duplicates OmniFocus's Review workflow via Omni Automation.

`list_projects_due_for_review` walks flattenedProjects and filters where
`nextReviewDate <= asOf` and status is Active or OnHold.

`mark_project_reviewed` sets `lastReviewDate = now` and bumps `nextReviewDate`
by the project's reviewInterval (or a caller-supplied override).
"""

from __future__ import annotations

import json
from typing import Any, Optional

from ..bridge import run


def list_projects_due_for_review(
    as_of: Optional[str] = None,
    include_on_hold: bool = True,
) -> list[dict[str, Any]]:
    """Projects with `nextReviewDate <= as_of` (default: now) and active/on-hold status.

    Sorted most-overdue first.
    """
    body = f"""
      var asOf = _parseDate({json.dumps(as_of)}) || new Date();
      var includeOnHold = {json.dumps(include_on_hold)};
      var out = [];
      for (var i = 0; i < flattenedProjects.length; i++) {{
        var p = flattenedProjects[i];
        var s = p.status;
        if (s === Project.Status.Done || s === Project.Status.Dropped) continue;
        if (!includeOnHold && s === Project.Status.OnHold) continue;
        var nrd = p.nextReviewDate;
        if (!nrd) continue;
        if (nrd.getTime() > asOf.getTime()) continue;
        var j = _projectToJson(p);
        j.daysOverdue = Math.floor((asOf.getTime() - nrd.getTime()) / (86400 * 1000));
        out.push(j);
      }}
      out.sort(function(a, b) {{ return b.daysOverdue - a.daysOverdue; }});
      JSON.stringify(out);
    """
    return run(body)


def mark_project_reviewed(
    project_id: str,
    next_review: Optional[str] = None,
) -> dict[str, Any]:
    """Mark a project reviewed now. If `next_review` is given, sets it explicitly;
    otherwise OmniFocus advances `nextReviewDate` by the project's `reviewInterval`.
    """
    body = f"""
      var id = {json.dumps(project_id)};
      var p = _findProject(id);
      if (!p) throw new Error('project not found: ' + id);
      var nextReview = _parseDate({json.dumps(next_review)});
      p.lastReviewDate = new Date();
      if (nextReview) {{
        p.nextReviewDate = nextReview;
      }} else if (p.reviewInterval) {{
        var steps = p.reviewInterval.steps || 1;
        var unit = String(p.reviewInterval.unit || 'week');
        var n = new Date();
        if (unit === 'day') n.setDate(n.getDate() + steps);
        else if (unit === 'week') n.setDate(n.getDate() + steps * 7);
        else if (unit === 'month') n.setMonth(n.getMonth() + steps);
        else if (unit === 'year') n.setFullYear(n.getFullYear() + steps);
        p.nextReviewDate = n;
      }}
      JSON.stringify(_projectToJson(p));
    """
    return run(body)
