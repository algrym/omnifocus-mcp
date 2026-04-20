"""Read-only queries against OmniFocus."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from ..bridge import run

ProjectStatus = Literal["Active", "OnHold", "Done", "Dropped"]


def check_permissions() -> dict[str, Any]:
    """Trigger the macOS Automation permission prompt with a trivial round-trip.

    Returns {ok: true, ping: 2} on success. First call may prompt the user to
    grant OmniFocus automation access in System Settings > Privacy & Security.

    If OmniFocus Pro is not licensed, `evaluateJavascript` raises "Scripting
    OmniFocus is a Pro feature." — surfaced here as `ok: false, reason: ...`
    so the caller gets a clear diagnostic instead of a cryptic trace.
    """
    from ..bridge import OmniAutomationError

    try:
        result = run("JSON.stringify({ok: true, ping: 1 + 1});")
    except OmniAutomationError as e:
        msg = str(e)
        if "Pro feature" in msg:
            return {
                "ok": False,
                "reason": "OmniFocus Pro required",
                "detail": msg,
                "remedy": (
                    "Scripting is a Pro-only feature in OmniFocus 4. Upgrade via "
                    "OmniFocus > In-App Purchase, or (if already Pro) restart OmniFocus."
                ),
            }
        return {"ok": False, "reason": "OmniAutomationError", "detail": msg}
    return result if isinstance(result, dict) else {"ok": True, "raw": result}


def list_inbox() -> list[dict[str, Any]]:
    """Return all tasks currently in the inbox."""
    body = (
        "var out = [];"
        "inbox.forEach(function(t){ out.push(_taskToJson(t)); });"
        "JSON.stringify(out);"
    )
    return run(body)


def list_tasks(
    project_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    flagged: Optional[bool] = None,
    due_before: Optional[str] = None,
    defer_before: Optional[str] = None,
    available_only: bool = False,
    include_completed: bool = False,
    name_contains: Optional[str] = None,
    note_contains: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Flexible task query over flattenedTasks.

    Filters combine with AND. Dates are ISO-8601 strings (e.g., "2026-05-01").
    `available_only` excludes deferred and blocked tasks. `limit` caps result count.
    """
    body = f"""
      var pid = {json.dumps(project_id)};
      var tid = {json.dumps(tag_id)};
      var flagged = {json.dumps(flagged)};
      var dueBefore = _parseDate({json.dumps(due_before)});
      var deferBefore = _parseDate({json.dumps(defer_before)});
      var availableOnly = {json.dumps(available_only)};
      var includeCompleted = {json.dumps(include_completed)};
      var nameNeedle = {json.dumps((name_contains or "").lower() or None)};
      var noteNeedle = {json.dumps((note_contains or "").lower() or None)};
      var limit = {json.dumps(int(limit))};
      var out = [];
      var src = flattenedTasks;
      for (var i = 0; i < src.length && out.length < limit; i++) {{
        var t = src[i];
        if (!includeCompleted && (t.completed || t.dropped)) continue;
        if (pid) {{
          var p = t.containingProject;
          if (!p || p.id.primaryKey !== pid) continue;
        }}
        if (tid) {{
          var has = false;
          for (var j = 0; j < t.tags.length; j++) if (t.tags[j].id.primaryKey === tid) {{ has = true; break; }}
          if (!has) continue;
        }}
        if (flagged !== null && t.flagged !== flagged) continue;
        if (availableOnly) {{
          if (t.blocked || t.effectivelyDropped || t.effectivelyCompleted) continue;
          var dd = t.effectiveDeferDate;
          if (dd && dd.getTime() > Date.now()) continue;
        }}
        if (dueBefore) {{
          var d = t.effectiveDueDate || t.dueDate;
          if (!d || d.getTime() > dueBefore.getTime()) continue;
        }}
        if (deferBefore) {{
          var f = t.effectiveDeferDate || t.deferDate;
          if (!f || f.getTime() > deferBefore.getTime()) continue;
        }}
        if (nameNeedle && (!t.name || t.name.toLowerCase().indexOf(nameNeedle) < 0)) continue;
        if (noteNeedle && (!t.note || t.note.toLowerCase().indexOf(noteNeedle) < 0)) continue;
        out.push(_taskToJson(t));
      }}
      JSON.stringify(out);
    """
    return run(body)


def list_projects(
    folder_id: Optional[str] = None,
    status: Optional[ProjectStatus] = None,
) -> list[dict[str, Any]]:
    """List projects, optionally filtered by folder and status."""
    body = f"""
      var folderId = {json.dumps(folder_id)};
      var status = {json.dumps(status)};
      var out = [];
      var wantStatus = status ? _projectStatus(status) : null;
      for (var i = 0; i < flattenedProjects.length; i++) {{
        var p = flattenedProjects[i];
        if (wantStatus && p.status !== wantStatus) continue;
        if (folderId) {{
          if (!p.parentFolder || p.parentFolder.id.primaryKey !== folderId) continue;
        }}
        out.push(_projectToJson(p));
      }}
      JSON.stringify(out);
    """
    return run(body)


def list_tags(parent_id: Optional[str] = None) -> list[dict[str, Any]]:
    """List tags. If parent_id is given, list only its direct children; else all."""
    body = f"""
      var parentId = {json.dumps(parent_id)};
      var out = [];
      var src = parentId ? (_findTag(parentId) ? _findTag(parentId).children : []) : flattenedTags;
      for (var i = 0; i < src.length; i++) out.push(_tagToJson(src[i]));
      JSON.stringify(out);
    """
    return run(body)


def list_folders(parent_id: Optional[str] = None) -> list[dict[str, Any]]:
    """List folders. If parent_id given, list only its direct children."""
    body = f"""
      var parentId = {json.dumps(parent_id)};
      var out = [];
      var src;
      if (parentId) {{
        var p = _findFolder(parentId);
        src = p ? p.children : [];
      }} else {{
        src = flattenedFolders;
      }}
      for (var i = 0; i < src.length; i++) out.push(_folderToJson(src[i]));
      JSON.stringify(out);
    """
    return run(body)


def list_perspectives() -> list[dict[str, Any]]:
    """Names of built-in and custom perspectives. Cannot be executed programmatically."""
    body = """
      var out = [];
      if (typeof Perspective !== 'undefined') {
        try {
          var bi = Perspective.BuiltIn.all;
          for (var i = 0; i < bi.length; i++) out.push({name: bi[i].name, builtIn: true});
        } catch (e) {}
        try {
          var custom = Perspective.Custom.all;
          for (var i = 0; i < custom.length; i++) out.push({name: custom[i].name, builtIn: false, id: custom[i].identifier});
        } catch (e) {}
      }
      JSON.stringify(out);
    """
    return run(body)


def get_task(task_id: str) -> Optional[dict[str, Any]]:
    """Full detail for one task by id."""
    body = f"""
      var t = _findTask({json.dumps(task_id)});
      if (!t) JSON.stringify(null);
      else {{
        var base = _taskToJson(t);
        var children = [];
        for (var i = 0; i < t.children.length; i++) children.push(_taskToJson(t.children[i]));
        base.children = children;
        JSON.stringify(base);
      }}
    """
    return run(body)


def get_project(project_id: str) -> Optional[dict[str, Any]]:
    """Full detail for one project by id, including top-level tasks."""
    body = f"""
      var p = _findProject({json.dumps(project_id)});
      if (!p) JSON.stringify(null);
      else {{
        var base = _projectToJson(p);
        var children = [];
        for (var i = 0; i < p.tasks.length; i++) children.push(_taskToJson(p.tasks[i]));
        base.rootTasks = children;
        JSON.stringify(base);
      }}
    """
    return run(body)


def get_tag(tag_id: str) -> Optional[dict[str, Any]]:
    """Full detail for one tag by id."""
    body = f"""
      var t = _findTag({json.dumps(tag_id)});
      JSON.stringify(_tagToJson(t));
    """
    return run(body)


def get_folder(folder_id: str) -> Optional[dict[str, Any]]:
    """Full detail for one folder by id."""
    body = f"""
      var f = _findFolder({json.dumps(folder_id)});
      JSON.stringify(_folderToJson(f));
    """
    return run(body)


def get_forecast(days: int = 7) -> dict[str, Any]:
    """Tasks due or deferring within the next N days, grouped by date."""
    body = f"""
      /* Forecast uses raw dueDate/deferDate (not effective*) for speed —
         Omni Automation property access is ~7ms per call on this DB so the
         inherited variants would blow past any reasonable timeout. Tasks
         are pruned by cheap checks before any serializer runs. */
      var days = {json.dumps(int(days))};
      var horizon = new Date();
      horizon.setDate(horizon.getDate() + days);
      var hMs = horizon.getTime();
      var nMs = Date.now();
      var due = [], defer = [];
      for (var i = 0; i < flattenedTasks.length; i++) {{
        var t = flattenedTasks[i];
        var d = t.dueDate;
        var f = t.deferDate;
        var dueHit = d && d.getTime() <= hMs;
        var defHit = f && f.getTime() >= nMs && f.getTime() <= hMs;
        if (!dueHit && !defHit) continue;
        if (t.completed || t.dropped) continue;
        if (dueHit) due.push(_taskToJson(t));
        if (defHit) defer.push(_taskToJson(t));
      }}
      JSON.stringify({{horizonDays: days, dueWithinWindow: due, deferringWithinWindow: defer}});
    """
    return run(body)
