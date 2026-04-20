/* Shared helpers prepended to every script. Do not use JS template literals
   (backticks) in this file or any *.js.tpl; Python string.Template interprets
   ${name}. Write $$ for a literal $ if needed. */

function _iso(d) { return d ? d.toISOString() : null; }

function _str(v) { return v == null ? null : String(v); }

/* OmniFocus enum values stringify as "[object Foo.Bar: Name]". Extract "Name".
   Falls back to the raw string if the pattern doesn't match. */
function _enumName(v) {
  if (v == null) return null;
  var s = String(v);
  var m = s.match(/:\s*([^\]]+)\]$/);
  return m ? m[1].trim() : s;
}

function _taskToJson(t) {
  if (!t) return null;
  /* NOTE: `tags` is a reserved global in Omni Automation; shadowing it with
     `var tags` causes silent failures on some paths. Use distinct names. */
  var _tagNames = [];
  var _tagIds = [];
  try { t.tags.forEach(function(x){ _tagNames.push(x.name); _tagIds.push(x.id.primaryKey); }); } catch (e) {}
  var proj = null, projName = null;
  try { if (t.containingProject) { proj = t.containingProject.id.primaryKey; projName = t.containingProject.name; } } catch (e) {}
  var parent = null;
  try {
    if (t.parent && t.parent !== inbox && t.parent !== t.containingProject) {
      parent = t.parent.id ? t.parent.id.primaryKey : null;
    }
  } catch (e) {}
  return {
    id: t.id.primaryKey,
    name: t.name,
    note: t.note,
    flagged: t.flagged,
    completed: t.completed,
    dropped: t.dropped,
    due: _iso(t.effectiveDueDate || t.dueDate),
    defer: _iso(t.effectiveDeferDate || t.deferDate),
    estimatedMinutes: t.estimatedMinutes,
    tags: _tagNames,
    tagIds: _tagIds,
    project: proj,
    projectName: projName,
    parent: parent,
    inInbox: t.inInbox === true,
  };
}

function _projectToJson(p) {
  if (!p) return null;
  var folderId = null, folderName = null;
  try { if (p.parentFolder) { folderId = p.parentFolder.id.primaryKey; folderName = p.parentFolder.name; } } catch (e) {}
  var interval = null;
  try {
    if (p.reviewInterval) {
      interval = { steps: p.reviewInterval.steps, unit: _str(p.reviewInterval.unit) };
    }
  } catch (e) {}
  return {
    id: p.id.primaryKey,
    name: p.name,
    note: p.note,
    status: _enumName(p.status),
    sequential: p.sequential,
    folder: folderId,
    folderName: folderName,
    dueDate: _iso(p.dueDate),
    deferDate: _iso(p.deferDate),
    reviewInterval: interval,
    nextReviewDate: _iso(p.nextReviewDate),
    lastReviewDate: _iso(p.lastReviewDate),
    flagged: p.flagged === true,
    taskCount: p.flattenedTasks ? p.flattenedTasks.length : 0,
  };
}

function _tagToJson(t) {
  if (!t) return null;
  var children = [];
  try { t.children.forEach(function(c){ children.push({id: c.id.primaryKey, name: c.name}); }); } catch (e) {}
  return {
    id: t.id.primaryKey,
    name: t.name,
    status: _enumName(t.status),
    parent: t.parent ? t.parent.id.primaryKey : null,
    parentName: t.parent ? t.parent.name : null,
    children: children,
    allowsNextAction: t.allowsNextAction !== false,
  };
}

function _folderToJson(f) {
  if (!f) return null;
  var children = [];
  try { f.children.forEach(function(c){ children.push({id: c.id.primaryKey, name: c.name}); }); } catch (e) {}
  var projects = [];
  try { f.projects.forEach(function(p){ projects.push({id: p.id.primaryKey, name: p.name}); }); } catch (e) {}
  return {
    id: f.id.primaryKey,
    name: f.name,
    parent: f.parent ? f.parent.id.primaryKey : null,
    parentName: f.parent ? f.parent.name : null,
    children: children,
    projects: projects,
  };
}

/* Use the static Class.byIdentifier form — the collection-method form
   (flattenedTasks.byIdentifier) does not exist and silently returns null. */
function _findTask(id) {
  if (!id) return null;
  try { return Task.byIdentifier(id); } catch (e) { return null; }
}
function _findProject(id) {
  if (!id) return null;
  try { return Project.byIdentifier(id); } catch (e) { return null; }
}
function _findTag(id) {
  if (!id) return null;
  try { return Tag.byIdentifier(id); } catch (e) { return null; }
}
function _findFolder(id) {
  if (!id) return null;
  try { return Folder.byIdentifier(id); } catch (e) { return null; }
}

function _parseDate(s) {
  if (s == null || s === "") return null;
  var d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function _tagStatus(s) {
  if (s === "Active") return Tag.Status.Active;
  if (s === "OnHold") return Tag.Status.OnHold;
  if (s === "Dropped") return Tag.Status.Dropped;
  return Tag.Status.Active;
}

function _projectStatus(s) {
  if (s === "Active") return Project.Status.Active;
  if (s === "OnHold") return Project.Status.OnHold;
  if (s === "Done") return Project.Status.Done;
  if (s === "Dropped") return Project.Status.Dropped;
  return Project.Status.Active;
}
