---
id: 01M2HPGPQVKM6W59NTM99R7A87
title: Parent/subtask hierarchy and roll-up
status: signoff
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Make parent/subtask relationships usable and visible, with progress rolling up from children so a parent reflects its subtasks truthfully."
context: |-
  Astra project tracker (astra_project_tracker/), step 4 of the standalone-tracker gap work.
  Handoff flags Parent/subtask as Partial (section 11): tasks.parent_task_id exists and create_task enforces same-project, but there is no UI, no hierarchy view, no roll-up, and no subtask cycle/update policy.
  Section 6 requires: parent/subtask preserve stable identities and history; report declared progress separately from accepted/total subtasks; do not invent percentages.
  create_task already accepts parent_task_id and detail shows parent_title. Missing: list children, show a tree, compute roll-up (e.g. accepted subtasks / total), and prevent a task being its own ancestor.
  Start: add list_subtasks + roll-up counts in the service, expose in task_detail, add a subtasks section + parent picker in the UI.
definition-of-done: "Can create/view a task's subtasks in the UI; a hierarchy/roll-up view shows parent with its children; parent shows declared roll-up (accepted/total subtasks) separately from any manual progress, never invented; same-project enforced (already partial); subtask cycles prevented; unit + HTTP tests cover roll-up counts and cycle prevention; existing tests stay green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T04:52:00Z
updated-at: 2026-09-20T03:12:06Z
claimed-by: X1CarbonPC-46912
claimed-at: 2026-09-15T05:00:40Z
updated-by: Aly Jafferani
outcome-what: set_parent with cycle prevention; subtask roll-up (completed/total) in task_detail shown separately from declared progress; parent picker in create + change-parent in detail; clickable subtasks; 3 new tests (55 total).
outcome-why: "Section 6/11: parent/subtask was Partial — no UI, no roll-up, no cycle policy."
question: "Accept, or send back? Roll-up counts only DIRECT children as completed/total (not recursive descendants) and 'completed' means the accepted lifecycle state — is that the granularity you want?"
outcome-resolves: "DoD met: subtasks viewable, roll-up separate from progress, cycles prevented, cross-project parent rejected, unit+HTTP tests, existing tests green."
review-summary: "set_parent re-parents with three guards (self-parent rejected, same-project enforced, ancestor-walk cycle guard via _task_ancestors) and records a parent_changed audit event. list_subtasks returns DIRECT children; task_detail attaches subtask_rollup {total, completed} where completed = accepted lifecycle status, kept as a SEPARATE field that never overwrites the parent's declared progress (UI shows both). POST /api/tasks/{id}/parent, create-dialog parent picker, clickable subtasks in detail. Meets the accepted DoD: direct-children granularity, accepted=completed."
review-gaps: "None material. Notes: (1) rollup denominator counts all direct children incl. cancelled/abandoned, so a parent may read '2 of 5' with 3 dead - defensible under the accepted 'completed = accepted state' design. (2) The detail-dialog parent picker does not pre-filter the task's own descendants; a cycle pick is safely rejected server-side, so a UX nicety not a correctness hole. No cross-project re-parent path; update_task does not touch parent_task_id so the guard cannot be bypassed. Authz correct (manage to set, view to read). No N+1/unbounded recursion."
review-verdict: pass
review-check: "Read set_parent, _task_ancestors, list_subtasks, task_detail rollup, get_task/can_manage_project/update_task/create_task in service.py; web POST /parent; db parent_task_id FK; UI. Ran test_core.test_subtask_rollup_and_cycle_prevention and test_parent_must_be_same_project -> both pass; test_web.test_set_parent_and_rollup_over_http exists. No full-suite run, no edits. No real-browser pass (yolo-chrome down); UI code-verified."
---

# Parent/subtask hierarchy and roll-up

## Definition of Done

- [x] Can create/view a task's subtasks in the UI; a hierarchy/roll-up view shows parent with its children; parent shows declared roll-up (accepted/total subtasks) separately from any manual progress, never invented; same-project enforced (already partial); subtask cycles prevented; unit + HTTP tests cover roll-up counts and cycle prevention; existing tests stay green.
  proof: astra_project_tracker: service.set_parent (ancestor cycle guard) + list_subtasks + subtask_rollup in task_detail; POST /api/tasks/{id}/parent; UI parent picker + subtasks section; tests test_core.test_subtask_rollup_and_cycle_prevention, test_parent_must_be_same_project, test_web.test_set_parent_and_rollup_over_http; 55 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Add set_parent service method with ancestor cycle prevention (a task cannot become a descendant of itself); parent_changed audit event
- [x] Add list_subtasks + subtask roll-up (completed/total) to task_detail, kept separate from the parent's own declared progress
- [x] API: POST /api/tasks/{id}/parent
- [x] UI: parent picker in create dialog + change-parent control and subtasks/roll-up display in detail
- [x] Tests: roll-up counts, cycle prevention, cross-project parent rejected

## Progress
- **2026-09-15 05:03 · Aly Jafferani** — Roll-up reports completed/total subtasks and is shown SEPARATELY from the parent's own declared progress (never overwrites it, never invents a %). Re-parenting is supported via set_parent with an ancestor-walk cycle guard (a task cannot become a descendant of itself); parent must be same project. parent_changed audit event added. Subtasks are clickable in the detail dialog to drill in. No real-browser visual pass (no browser surface).
- **2026-09-15 05:51 · Aly Jafferani** — REQUIREMENT (owner, 2026-09-15): work is distributed across MULTIPLE PEOPLE via subtasks — each subtask has its own accountable owner, who can be a different person from the parent task's owner (and different people can hold different subtasks along a critical path). This is already supported: every task/subtask carries its own owner_user_id, plus separate collaborators/reviewers/approvers (task_reviewers). Model rule stays one PRIMARY accountable owner per task/subtask (section 6) — multiple people = multiple subtasks + collaborators, not multiple owners on one task. Design TaskDetail already shows subtasks owned by different people (Sara Karim, Imran Ali). Keep this when building the real Gantt/critical-path UI: show each subtask's own owner.
- **2026-09-15 18:32 · Aly Jafferani** — OWNER ACCEPTED (2026-09-15): direct-children roll-up granularity; accepted lifecycle state = completed. Proceeding to model review.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. PARKED in signoff - waiting on the App Owner (Codex cannot move it out). Review verdict: pass. Owner question: roll-up counts only DIRECT children, completed=accepted lifecycle state - is that the granularity wanted?
- **2026-09-20 03:12 · Aly Jafferani** — Owner confirmation recorded 2026-09-20: roll-up counts accepted/completed DIRECT children only and remains separate from declared progress.
