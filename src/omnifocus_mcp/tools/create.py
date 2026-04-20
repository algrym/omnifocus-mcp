"""Create tasks, projects, tags, folders."""

from __future__ import annotations

import json
from typing import Any, Optional

from ..bridge import run


def create_task(
    name: str,
    project_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    note: Optional[str] = None,
    due: Optional[str] = None,
    defer: Optional[str] = None,
    tag_ids: Optional[list[str]] = None,
    flagged: bool = False,
    estimate_minutes: Optional[int] = None,
) -> dict[str, Any]:
    """Create a task. If neither project_id nor parent_task_id given, goes to inbox.

    Dates are ISO-8601 strings. `tag_ids` is a list of tag primary keys.
    """
    body = f"""
      var name = {json.dumps(name)};
      var projectId = {json.dumps(project_id)};
      var parentId = {json.dumps(parent_task_id)};
      var note = {json.dumps(note)};
      var due = _parseDate({json.dumps(due)});
      var defer = _parseDate({json.dumps(defer)});
      var tagIds = {json.dumps(tag_ids or [])};
      var flagged = {json.dumps(flagged)};
      var estimate = {json.dumps(estimate_minutes)};
      var container = inbox;
      if (parentId) {{
        var parent = _findTask(parentId);
        if (!parent) throw new Error('parent task not found: ' + parentId);
        container = parent;
      }} else if (projectId) {{
        var proj = _findProject(projectId);
        if (!proj) throw new Error('project not found: ' + projectId);
        container = proj;
      }}
      var t = new Task(name, container);
      if (note) t.note = note;
      if (due) t.dueDate = due;
      if (defer) t.deferDate = defer;
      if (flagged) t.flagged = true;
      if (estimate != null) t.estimatedMinutes = estimate;
      for (var i = 0; i < tagIds.length; i++) {{
        var tag = _findTag(tagIds[i]);
        if (tag) t.addTag(tag);
      }}
      JSON.stringify(_taskToJson(t));
    """
    return run(body)


def create_project(
    name: str,
    folder_id: Optional[str] = None,
    sequential: bool = False,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Create a project.

    NOTE: `reviewInterval` cannot be set from Omni Automation — the setter
    requires a `Project.ReviewInterval` instance and no public constructor
    exists. Projects inherit the default review interval from document
    settings. Use `next_review` via `update_project` to shift review dates.
    """
    body = f"""
      var name = {json.dumps(name)};
      var folderId = {json.dumps(folder_id)};
      var sequential = {json.dumps(sequential)};
      var note = {json.dumps(note)};
      var container = null;
      if (folderId) {{
        container = _findFolder(folderId);
        if (!container) throw new Error('folder not found: ' + folderId);
      }}
      var p = container ? new Project(name, container) : new Project(name);
      if (sequential) p.sequential = true;
      if (note) p.note = note;
      JSON.stringify(_projectToJson(p));
    """
    return run(body)


def create_tag(name: str, parent_id: Optional[str] = None) -> dict[str, Any]:
    """Create a tag, optionally nested under a parent tag."""
    body = f"""
      var name = {json.dumps(name)};
      var parentId = {json.dumps(parent_id)};
      var t;
      if (parentId) {{
        var parent = _findTag(parentId);
        if (!parent) throw new Error('parent tag not found: ' + parentId);
        t = new Tag(name, parent);
      }} else {{
        t = new Tag(name);
      }}
      JSON.stringify(_tagToJson(t));
    """
    return run(body)


def create_folder(name: str, parent_id: Optional[str] = None) -> dict[str, Any]:
    """Create a folder, optionally nested under a parent folder."""
    body = f"""
      var name = {json.dumps(name)};
      var parentId = {json.dumps(parent_id)};
      var f;
      if (parentId) {{
        var parent = _findFolder(parentId);
        if (!parent) throw new Error('parent folder not found: ' + parentId);
        f = new Folder(name, parent);
      }} else {{
        f = new Folder(name);
      }}
      JSON.stringify(_folderToJson(f));
    """
    return run(body)


def parse_transport_text(text: str, project_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Create a single task via OmniFocus's built-in transport-text parser.

    Despite the docs implying TaskPaper-style syntax, in OmniFocus 4 this
    parser is minimal: line 1 becomes the task name, subsequent lines become
    the note, and `@tag` / `@due(...)` / `@flagged` directives are NOT parsed
    (they stay in the name verbatim). Always returns a one-element list.

    For rich task creation with tags, dates, and flags, use `create_task`.
    """
    body = f"""
      var text = {json.dumps(text)};
      var projectId = {json.dumps(project_id)};
      var tasks = Task.byParsingTransportText(text);
      if (projectId) {{
        var proj = _findProject(projectId);
        if (!proj) throw new Error('project not found: ' + projectId);
        /* moveTasks mutates in place; it does NOT return the moved array. */
        moveTasks(tasks, proj.ending);
      }}
      var out = [];
      for (var i = 0; i < tasks.length; i++) out.push(_taskToJson(tasks[i]));
      JSON.stringify(out);
    """
    return run(body)
