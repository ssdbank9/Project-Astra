---
id: 01M2JXM4NWFWH5J0BYJ35WZ4A8
title: Project schedule dates with change history
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Give projects their own start/target dates that can be changed, with every change recorded in an audit log — matching how task date changes are already logged."
context: |-
  Owner requirement (2026-09-15): 'a task or a project can have change in dates but history should be maintained with logs.'

  Current state — the TASK half is already done, the PROJECT half is missing:
  - Tasks: date changes ARE logged. service.update_task (src/astra/service.py) requires a reason for any start_date/due_date change and writes a task_updated event with full before/after JSON; the schedule-revision workflow (ticket JZACMP) adds baseline + propose/approve with a schedule_revised event. So no work is needed for tasks — verify and cite it.
  - Projects: projects have NO schedule dates. The projects table (src/astra/db.py) has only created_at / closed_at — no start_date or target/due date. So a project's dates cannot change and nothing is logged.

  What to build: add project start_date + target/end date; let the owner/project-manager change them; record every change as a project_events row (event_type e.g. project_schedule_changed) with actor, old value, new value, and a required reason. project_events already exists (used by close_project) — reuse it, do not invent a new audit table.

  Open design question for the owner before building: should a project's dates constrain its tasks' dates (e.g., warn/block a task due after the project end), or is the project date purely informational for now? Recommend informational-only for v1 to match the permissive calendar decision (XDA2JR).
definition-of-done: "Projects have an editable start_date and target/end date; changing either requires a reason and writes a project_events audit row capturing actor + old + new + reason; the change is visible in the project's history; task date-change logging is confirmed already working and cited (no regression); unit + HTTP tests cover the project date change + its audit row; existing tests green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T16:15:27Z
updated-at: 2026-09-19T06:14:44Z
claimed-by: X1CarbonPC-51136
claimed-at: 2026-09-15T16:36:33Z
updated-by: Aly Jafferani
question: "Confirm: is project schedule editing in the People/admin config panel the right home, and is config + audit-log enough for now — or do you want project start/target to also show as markers on the Gantt/timeline (a follow-up)?"
outcome-what: "Added project start/target markers to the Gantt timeline (dashed lines + labels, legend keys), scaled into the timeline range, with single- vs multi-project labelling."
outcome-why: "Owner wanted project start/target shown as markers on the Gantt, on top of config-panel editing + audit log."
outcome-resolves: "Markers render from list_projects schedule dates (guard test added that those fields are exposed); app.js syntax-checked; full suite green. Visual pass pending (no browser this session)."
---

# Project schedule dates with change history

## Definition of Done

- [x] Projects have an editable start_date and target/end date; changing either requires a reason and writes a project_events audit row capturing actor + old + new + reason; the change is visible in the project's history; task date-change logging is confirmed already working and cited (no regression); unit + HTTP tests cover the project date change + its audit row; existing tests green.
  proof: db v11 ALTER projects ADD start_date, target_date. service.set_project_schedule (can_manage_project; target>=start; reason REQUIRED on any change; writes project_events 'project_schedule_changed' with before/after + reason). Informational only — no task-date constraint (owner decision). web POST /api/projects/{id}/schedule. UI: project start/target + reason inputs in People project section. TASK date history confirmed already working (update_task before/after + reason) and covered by new test_task_date_change_is_logged_with_before_and_after. Tests: test_core.test_project_schedule_change_is_logged, test_project_schedule_requires_reason, test_project_target_cannot_precede_start, test_task_date_change_is_logged_with_before_and_after; test_web.test_project_schedule_over_http. 97 pass (was 92).

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-15 16:36 · Aly Jafferani** — DECISION (owner, 2026-09-15): project dates are INFORMATIONAL ONLY — recorded and change-logged, but never constrain/warn/block task dates (matches permissive calendar XDA2JR). PLAN: (1) db v11 ALTER projects ADD start_date, ADD target_date (both TEXT, nullable). (2) service.set_project_schedule(actor,project_id,start_date,target_date,reason) gated can_manage_project; validate target>=start; require reason when either value changes; write project_events 'project_schedule_changed' detail {before/after start+target} + reason. Dates already flow through get_project/list_projects (SELECT *). (3) web POST /api/projects/{id}/schedule. (4) UI: start/target date inputs + reason in the People dialog project section (beside budget/primary-entity). (5) tests: core (change logs old/new/reason; reason required; target<start rejected; no task constraint) + web roundtrip. TASK date history already done (update_task before/after + JZACMP) — cite, no change.
- **2026-09-15 16:40 · Aly Jafferani** — No real-browser visual pass (yolo-chrome down). Verified: 97 tests green incl. HTTP roundtrip; app.js node --check clean; migration v11 boots. Owner decision applied: project dates informational-only, never constrain tasks. project_events reused (no new audit table). Both halves of the requirement now satisfied: tasks (pre-existing) + projects (this ticket).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): in addition to config-panel editing + audit log, show project start/target as MARKERS on the Gantt/timeline. Add the markers.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Latest change: project start/target markers added to the Gantt timeline (dashed lines + labels + legend, scaled to range, single- vs multi-project labelling); schedule edit lives in People/admin with audit log. In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
