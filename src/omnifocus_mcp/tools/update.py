"""Update tasks, projects, tags, folders (non-destructive mutations)."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from ..bridge import run

ProjectStatus = Literal["Active", "OnHold", "Done", "Dropped"]
TagStatus = Literal["Active", "OnHold", "Dropped"]


def update_task(
    task_id: str,
    name: Optional[str] = None,
    note: Optional[str] = None,
    due: Optional[str] = None,
    defer: Optional[str] = None,
    tag_ids: Optional[list[str]] = None,
    flagged: Optional[bool] = None,
    estimate_minutes: Optional[int] = None,
    clear_due: bool = False,
    clear_defer: bool = False,
) -> dict[str, Any]:
    """Patch a task in place. Only supplied fields change.

    `clear_due`/`clear_defer` override due/defer to null. Pass `tag_ids=[]` to
    clear tags; pass None to leave them alone.
    """
    body = f"""
      var id = {json.dumps(task_id)};
      var t = _findTask(id);
      if (!t) throw new Error('task not found: ' + id);
      var name = {json.dumps(name)};
      var note = {json.dumps(note)};
      var due = {json.dumps(due)};
      var defer = {json.dumps(defer)};
      var tagIds = {json.dumps(tag_ids)};
      var flagged = {json.dumps(flagged)};
      var estimate = {json.dumps(estimate_minutes)};
      var clearDue = {json.dumps(clear_due)};
      var clearDefer = {json.dumps(clear_defer)};
      if (name != null) t.name = name;
      if (note != null) t.note = note;
      if (clearDue) t.dueDate = null;
      else if (due != null) t.dueDate = _parseDate(due);
      if (clearDefer) t.deferDate = null;
      else if (defer != null) t.deferDate = _parseDate(defer);
      if (flagged != null) t.flagged = flagged;
      if (estimate != null) t.estimatedMinutes = estimate;
      if (tagIds != null) {{
        while (t.tags.length > 0) t.removeTag(t.tags[0]);
        for (var i = 0; i < tagIds.length; i++) {{
          var tg = _findTag(tagIds[i]);
          if (tg) t.addTag(tg);
        }}
      }}
      JSON.stringify(_taskToJson(t));
    """
    return run(body)


def update_project(
    project_id: str,
    name: Optional[str] = None,
    note: Optional[str] = None,
    folder_id: Optional[str] = None,
    sequential: Optional[bool] = None,
    status: Optional[ProjectStatus] = None,
    next_review: Optional[str] = None,
    last_review: Optional[str] = None,
    flagged: Optional[bool] = None,
) -> dict[str, Any]:
    """Patch a project in place.

    NOTE: `reviewInterval` is read-only from automation (see `create_project`).
    Shift review cadence via `next_review` / `last_review` instead.
    """
    body = f"""
      var id = {json.dumps(project_id)};
      var p = _findProject(id);
      if (!p) throw new Error('project not found: ' + id);
      var name = {json.dumps(name)};
      var note = {json.dumps(note)};
      var folderId = {json.dumps(folder_id)};
      var sequential = {json.dumps(sequential)};
      var status = {json.dumps(status)};
      var nextReview = {json.dumps(next_review)};
      var lastReview = {json.dumps(last_review)};
      var flagged = {json.dumps(flagged)};
      if (name != null) p.name = name;
      if (note != null) p.note = note;
      if (sequential != null) p.sequential = sequential;
      if (flagged != null) p.flagged = flagged;
      if (status) p.status = _projectStatus(status);
      if (folderId != null) {{
        var target = _findFolder(folderId);
        if (!target) throw new Error('folder not found: ' + folderId);
        moveSections([p], target.ending);
      }}
      if (nextReview != null) p.nextReviewDate = _parseDate(nextReview);
      if (lastReview != null) p.lastReviewDate = _parseDate(lastReview);
      JSON.stringify(_projectToJson(p));
    """
    return run(body)


def update_tag(
    tag_id: str,
    name: Optional[str] = None,
    parent_id: Optional[str] = None,
    make_top_level: bool = False,
    status: Optional[TagStatus] = None,
    allows_next_action: Optional[bool] = None,
) -> dict[str, Any]:
    """Patch a tag. Set `make_top_level=True` to detach from any parent."""
    body = f"""
      var id = {json.dumps(tag_id)};
      var t = _findTag(id);
      if (!t) throw new Error('tag not found: ' + id);
      var name = {json.dumps(name)};
      var parentId = {json.dumps(parent_id)};
      var makeTop = {json.dumps(make_top_level)};
      var status = {json.dumps(status)};
      var ana = {json.dumps(allows_next_action)};
      if (name != null) t.name = name;
      if (makeTop) {{
        moveTags([t], tags.ending);
      }} else if (parentId) {{
        var p = _findTag(parentId);
        if (!p) throw new Error('parent tag not found: ' + parentId);
        moveTags([t], p.ending);
      }}
      if (status) t.status = _tagStatus(status);
      if (ana != null) t.allowsNextAction = ana;
      JSON.stringify(_tagToJson(t));
    """
    return run(body)


def update_folder(
    folder_id: str,
    name: Optional[str] = None,
    parent_id: Optional[str] = None,
    make_top_level: bool = False,
) -> dict[str, Any]:
    """Patch a folder. Set `make_top_level=True` to detach from any parent."""
    body = f"""
      var id = {json.dumps(folder_id)};
      var f = _findFolder(id);
      if (!f) throw new Error('folder not found: ' + id);
      var name = {json.dumps(name)};
      var parentId = {json.dumps(parent_id)};
      var makeTop = {json.dumps(make_top_level)};
      if (name != null) f.name = name;
      if (makeTop) {{
        moveSections([f], library.ending);
      }} else if (parentId) {{
        var p = _findFolder(parentId);
        if (!p) throw new Error('parent folder not found: ' + parentId);
        moveSections([f], p.ending);
      }}
      JSON.stringify(_folderToJson(f));
    """
    return run(body)


def move_task(
    task_id: str,
    to_project_id: Optional[str] = None,
    to_parent_task_id: Optional[str] = None,
    to_inbox: bool = False,
) -> dict[str, Any]:
    """Move a task. Provide exactly one destination."""
    dests = sum(bool(x) for x in (to_project_id, to_parent_task_id, to_inbox))
    if dests != 1:
        raise ValueError("Specify exactly one of to_project_id, to_parent_task_id, to_inbox")
    body = f"""
      var id = {json.dumps(task_id)};
      var t = _findTask(id);
      if (!t) throw new Error('task not found: ' + id);
      var toProject = {json.dumps(to_project_id)};
      var toParent = {json.dumps(to_parent_task_id)};
      var toInbox = {json.dumps(to_inbox)};
      var target = null;
      if (toInbox) target = inbox.ending;
      else if (toProject) {{
        var p = _findProject(toProject);
        if (!p) throw new Error('project not found: ' + toProject);
        target = p.ending;
      }} else if (toParent) {{
        var par = _findTask(toParent);
        if (!par) throw new Error('parent task not found: ' + toParent);
        target = par.ending;
      }}
      moveTasks([t], target);
      JSON.stringify(_taskToJson(t));
    """
    return run(body)
