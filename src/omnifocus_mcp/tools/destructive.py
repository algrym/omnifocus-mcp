"""Destructive operations (complete/drop/delete). Each requires confirm=True.

Without confirm, returns a dry-run preview. With confirm, executes and appends
a JSON line to ~/.omnifocus-mcp/audit.log.
"""

from __future__ import annotations

import json
from typing import Any

from ..audit import append_audit
from ..bridge import run

_CONFIRM_MSG = (
    "Destructive: re-call with confirm=true to execute. "
    "This will be audit-logged to ~/.omnifocus-mcp/audit.log."
)


def _preview_task(task_id: str) -> dict[str, Any]:
    body = f"""
      var t = _findTask({json.dumps(task_id)});
      if (!t) JSON.stringify(null);
      else {{
        var info = _taskToJson(t);
        info.childCount = t.children ? t.children.length : 0;
        JSON.stringify(info);
      }}
    """
    return {"preview": run(body), "message": _CONFIRM_MSG}


def _preview_project(project_id: str) -> dict[str, Any]:
    body = f"""
      var p = _findProject({json.dumps(project_id)});
      if (!p) JSON.stringify(null);
      else {{
        var info = _projectToJson(p);
        info.taskCount = p.flattenedTasks ? p.flattenedTasks.length : 0;
        JSON.stringify(info);
      }}
    """
    return {"preview": run(body), "message": _CONFIRM_MSG}


def _preview_tag(tag_id: str) -> dict[str, Any]:
    body = f"""
      var t = _findTag({json.dumps(tag_id)});
      if (!t) JSON.stringify(null);
      else {{
        var info = _tagToJson(t);
        info.taggedTaskCount = t.tasks ? t.tasks.length : 0;
        JSON.stringify(info);
      }}
    """
    return {"preview": run(body), "message": _CONFIRM_MSG}


def _preview_folder(folder_id: str) -> dict[str, Any]:
    body = f"""
      var f = _findFolder({json.dumps(folder_id)});
      if (!f) JSON.stringify(null);
      else {{
        var info = _folderToJson(f);
        info.projectCount = f.projects ? f.projects.length : 0;
        JSON.stringify(info);
      }}
    """
    return {"preview": run(body), "message": _CONFIRM_MSG}


def complete_task(task_id: str, confirm: bool = False) -> dict[str, Any]:
    """Mark a task complete. Requires confirm=True."""
    if not confirm:
        return _preview_task(task_id)
    body = f"""
      var t = _findTask({json.dumps(task_id)});
      if (!t) throw new Error('task not found: ' + {json.dumps(task_id)});
      t.markComplete();
      JSON.stringify(_taskToJson(t));
    """
    result = run(body)
    append_audit("complete_task", {"task_id": task_id}, result)
    return result


def drop_task(task_id: str, confirm: bool = False) -> dict[str, Any]:
    """Drop a task (mark permanently irrelevant, kept for history). Requires confirm=True."""
    if not confirm:
        return _preview_task(task_id)
    body = f"""
      var t = _findTask({json.dumps(task_id)});
      if (!t) throw new Error('task not found: ' + {json.dumps(task_id)});
      t.drop(false);
      JSON.stringify(_taskToJson(t));
    """
    result = run(body)
    append_audit("drop_task", {"task_id": task_id}, result)
    return result


def delete_task(task_id: str, confirm: bool = False) -> dict[str, Any]:
    """Permanently delete a task. Requires confirm=True."""
    if not confirm:
        return _preview_task(task_id)
    body = f"""
      var t = _findTask({json.dumps(task_id)});
      if (!t) throw new Error('task not found: ' + {json.dumps(task_id)});
      var snap = _taskToJson(t);
      deleteObject(t);
      JSON.stringify({{deleted: true, task: snap}});
    """
    result = run(body)
    append_audit("delete_task", {"task_id": task_id}, result)
    return result


def complete_project(project_id: str, confirm: bool = False) -> dict[str, Any]:
    """Mark a project Done. Requires confirm=True."""
    if not confirm:
        return _preview_project(project_id)
    body = f"""
      var p = _findProject({json.dumps(project_id)});
      if (!p) throw new Error('project not found: ' + {json.dumps(project_id)});
      p.status = Project.Status.Done;
      JSON.stringify(_projectToJson(p));
    """
    result = run(body)
    append_audit("complete_project", {"project_id": project_id}, result)
    return result


def drop_project(project_id: str, confirm: bool = False) -> dict[str, Any]:
    """Mark a project Dropped. Requires confirm=True."""
    if not confirm:
        return _preview_project(project_id)
    body = f"""
      var p = _findProject({json.dumps(project_id)});
      if (!p) throw new Error('project not found: ' + {json.dumps(project_id)});
      p.status = Project.Status.Dropped;
      JSON.stringify(_projectToJson(p));
    """
    result = run(body)
    append_audit("drop_project", {"project_id": project_id}, result)
    return result


def delete_project(project_id: str, confirm: bool = False) -> dict[str, Any]:
    """Permanently delete a project and its tasks. Requires confirm=True."""
    if not confirm:
        return _preview_project(project_id)
    body = f"""
      var p = _findProject({json.dumps(project_id)});
      if (!p) throw new Error('project not found: ' + {json.dumps(project_id)});
      var snap = _projectToJson(p);
      deleteObject(p);
      JSON.stringify({{deleted: true, project: snap}});
    """
    result = run(body)
    append_audit("delete_project", {"project_id": project_id}, result)
    return result


def delete_tag(tag_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a tag. Does not delete tasks that had it. Requires confirm=True."""
    if not confirm:
        return _preview_tag(tag_id)
    body = f"""
      var t = _findTag({json.dumps(tag_id)});
      if (!t) throw new Error('tag not found: ' + {json.dumps(tag_id)});
      var snap = _tagToJson(t);
      deleteObject(t);
      JSON.stringify({{deleted: true, tag: snap}});
    """
    result = run(body)
    append_audit("delete_tag", {"tag_id": tag_id}, result)
    return result


def delete_folder(folder_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a folder and all nested projects/folders. Requires confirm=True."""
    if not confirm:
        return _preview_folder(folder_id)
    body = f"""
      var f = _findFolder({json.dumps(folder_id)});
      if (!f) throw new Error('folder not found: ' + {json.dumps(folder_id)});
      var snap = _folderToJson(f);
      deleteObject(f);
      JSON.stringify({{deleted: true, folder: snap}});
    """
    result = run(body)
    append_audit("delete_folder", {"folder_id": folder_id}, result)
    return result
