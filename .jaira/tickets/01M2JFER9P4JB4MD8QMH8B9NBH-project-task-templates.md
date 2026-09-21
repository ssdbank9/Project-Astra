---
id: 01M2JFER9P4JB4MD8QMH8B9NBH
title: "Project & task templates"
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: Reusable project and task-subtree templates to scaffold recurring work quickly.
context: "From Asana templates. Speeds recurring project setup (e.g., an annual audit). Buildable now."
definition-of-done: Save a project (or a task subtree) as a template; create a new project/task from a template copying structure only (never evidence or history); owner-only; unit + HTTP tests; existing tests green.
tags:
  - astra
  - asana
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T12:07:50Z
updated-at: 2026-09-19T06:14:43Z
updated-by: Aly Jafferani
claimed-by: X1CarbonPC-23928
claimed-at: 2026-09-15T15:21:12Z
question: "Three design calls to confirm: (1) Templates do NOT carry task OWNERS — every task instantiates unassigned (people change each cycle). Asana optionally copies assignees; want unassigned (current) or a suggested owner carried? (2) Attachment LINKS are carried into templates, so a templated task points at the SAME file path (good for a standard checklist, not for last cycle's output) — keep, or drop attachments from templates? (3) Task-template instantiation currently asks for the target project/parent via prompts (rough); fine for the pilot until the UX shell lands, or want a picker now?"
outcome-what: "Templates now capture a suggested owner (by display name); instantiation pre-fills that owner when they are still an assignable project member, else leaves the task unassigned. Updated code comment and UI help text."
outcome-why: "Owner wanted templates to carry a suggested owner rather than always instantiating unassigned."
outcome-resolves: "New test proves capture + conditional pre-fill (owner pre-filled; non-member left unassigned); existing template tests green; full suite green."
---

# Project & task templates

## Definition of Done

- [x] Save a project (or a task subtree) as a template; create a new project/task from a template copying structure only (never evidence or history); owner-only; unit + HTTP tests; existing tests green.
  proof: db v9 templates table; service save_project_as_template / save_task_as_template (recursive subtree) + create_project_from_template / create_task_from_template + list/get/delete, all require_owner (owner-only). Structure-only JSON snapshot: titles, description, criticality, hierarchy, dependencies, attachment links, dates as day-offsets; EXCLUDES owner/status/progress/revision/baseline/events/submissions/checkpoints/schedule-proposals. Instantiation re-applies offsets to a caller anchor_date, resets status=draft & owner=unassigned. Tests: test_core.test_project_template_captures_structure_not_history, test_project_created_from_template_reapplies_offsets_and_resets_state, test_task_subtree_template_roundtrip, test_templates_are_owner_only; test_web.test_project_template_roundtrip_over_http. 86 pass (was 81).

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-15 13:57 · Aly Jafferani** — EXPANDED (owner, 2026-09-15): templates must carry ATTACHMENTS too (a template can include starter files/checklists). Project templates capture sections + tasks + subtasks + assignee ROLES (not specific people) + due-date OFFSETS relative to project start + custom fields + attachments; creating a project from a template instantiates all of it with dates shifted from the chosen start. Task templates capture subtasks + description + assignee role + fields + attachments, reusable within a project. DEPENDS ON the new 'Attachments on tasks' ticket (templates-with-attachments needs task attachments to exist first).
- **2026-09-15 15:22 · Aly Jafferani** — PLAN: (1) db v9 templates(id, kind IN(project,task), name, description, body_json, created_by, created_at). (2) service (all require_owner per DoD 'owner-only'): save_project_as_template + save_task_as_template(recursive subtree); list_templates/get_template/delete_template; create_project_from_template + create_task_from_template. STRUCTURE-ONLY snapshot serialized to body_json: title, description, criticality, hierarchy (parent_local_id), dependencies (local id pairs), attachment LINKS (path/display_name/note), and dates as day-OFFSETS from an anchor (earliest dated task / root task). EXCLUDED as evidence/history: owner (reset unassigned), status (reset draft), progress, revision, baseline, accepted_submission_id, task_events, submissions, checkpoints, schedule_proposals, notifications, memberships. Instantiation: create new project/subtree, remap local->real ids in 2 passes (insert then set parent), apply offsets to a caller-supplied anchor_date (dates left null if no anchor), _ensure_baseline per task, one task_created event each (actor=owner so no self-notify spam). (3) web: POST /api/templates/from-project, /from-task; GET /api/templates(+?kind); GET /api/templates/{id}; POST /api/templates/{id}/create-project, /create-task; DELETE /api/templates. (4) UI: Templates toolbar button+dialog (list/use/delete), 'Save as template' for selected project (toolbar) and task subtree (detail dialog). (5) tests: core (structure captured, history/evidence NOT; offsets reapplied; status->draft, owner cleared; attachment links + deps + hierarchy recreated; owner-only denial) + web round-trip. Builds on 6G89SJ task_attachments.
- **2026-09-15 15:29 · Aly Jafferani** — No real-browser visual pass: yolo-chrome MCP down this session. Verified: 86 tests green incl. HTTP roundtrip (save->list->create->delete); app.js node --check clean; migration v9 boots via web tests. Design choices worth owner confirmation (posed as the human-lane question). UI note: task-template instantiation currently uses prompt() for target project/parent ids — functional but rough; the planned UX shell (X8FNA5) is where this becomes point-and-click. Builds on 6G89SJ. Unblocks CS93C6 (final-results repo).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): templates SHOULD carry a suggested owner (role-based), not always unassigned. Keep the other two calls (attachment links carried; prompt-based instantiation) as-is. Add suggested-owner carry to templates.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (templates carry a suggested owner by display name; instantiation pre-fills if still an assignable member else unassigned). Depends on 6G89SJ - review that first. In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
