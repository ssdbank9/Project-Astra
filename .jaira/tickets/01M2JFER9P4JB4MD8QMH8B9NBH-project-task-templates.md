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
updated-at: 2026-09-24T05:31:52Z
updated-by: Claude
claimed-by: X1CarbonPC-23928
claimed-at: 2026-09-15T15:21:12Z
question: "Three design calls to confirm: (1) Templates do NOT carry task OWNERS — every task instantiates unassigned (people change each cycle). Asana optionally copies assignees; want unassigned (current) or a suggested owner carried? (2) Attachment LINKS are carried into templates, so a templated task points at the SAME file path (good for a standard checklist, not for last cycle's output) — keep, or drop attachments from templates? (3) Task-template instantiation currently asks for the target project/parent via prompts (rough); fine for the pilot until the UX shell lands, or want a picker now?"
outcome-what: "Templates now capture a suggested owner (by display name); instantiation pre-fills that owner when they are still an assignable project member, else leaves the task unassigned. Updated code comment and UI help text."
outcome-why: "Owner wanted templates to carry a suggested owner rather than always instantiating unassigned."
outcome-resolves: "New test proves capture + conditional pre-fill (owner pre-filled; non-member left unassigned); existing template tests green; full suite green."
review-summary: |-
  What the current code does (src/astra/service.py lines 2052-2330, web.py routes, app.js lines 363-423):
  - Database: a `templates` table (db v9).
  - Saving: `save_project_as_template` and `save_task_as_template` store a JSON snapshot. `save_task_as_template` walks the task's whole subtree.
  - What a snapshot holds: title, description, criticality, parent/child links, dependencies inside the snapshot, attachment links, and dates stored as day offsets from the earliest date.
  - New for this ticket: each task also stores a `suggested_owner`, which is the display name of the task's current owner.
  - What a snapshot leaves out: status, progress, revision, baseline, events, submissions, checkpoints and schedule proposals.
  - Creating from a template: `create_project_from_template` and `create_task_from_template` insert new tasks in 'draft'. They recreate parents, dependencies and attachment links, apply the offsets to the caller's anchor date, and write one `task_created` event per task.
  - Owner pre-fill: `_resolve_suggested_owner` looks for exactly one active user with that display name, then runs the normal `_validate_assignee` check. If the user is unknown, ambiguous, inactive or not assignable on the target project, the task is left unassigned.
  - Access: all eight template methods call `require_owner`.
  - Errors: the web layer turns Forbidden into 403, KeyError into 404 and ValueError into 400, so a bad anchor date or a bad template or project id gets a controlled response.
  - UI: a Templates dialog (list, use, delete), a "Save as template" button for projects and tasks, and help text that mentions the suggested owner.
  - Tests: the full suite passes, 335 tests, `.venv/bin/python tests/run.py`, OK.
review-gaps: "1. Medium: the shipped behaviour differs from the owner's decision. Aly's 2026-09-15 18:31 note asks for a suggested owner that is \"role-based\". The 13:57 note says \"assignee ROLES (not specific people)\". The code instead stores one named person, by display name, from the last cycle. The outcome fields describe it as by display name and never mention the change.\n   - Effect on project templates: `_validate_assignee` needs a membership, and a new project has none. So a normal member's suggestion is always dropped, and only App Owner and Chairman users are ever pre-filled.\n   - The new test confirms this: it asserts that \"Member task\" comes out unassigned.\n   - For the recurring-project case this ticket was written for (an annual audit), pre-fill therefore does almost nothing.\n   - Aly needs to confirm that name-based is acceptable, or ask for role-based.\n2. Low to medium: the pre-filled assignment leaves no audit record. `_instantiate_tasks` writes `owner_user_id` straight into the new row. The `task_created` event records only {title, from_template}. By contrast, `create_task` records the full task in its event. So nothing in a template-made task's history shows who assigned the owner or why.\n3. Low: the owner-only rule is only partly tested.\n   - The tests cover save_project, list, create_project and delete for a non-owner.\n   - Nothing tests save_task_as_template or create_task_from_template for a non-owner.\n   - Mutation check: I removed `require_owner` from `save_task_as_template` in a scratch copy and every test still passed. That means a manager could save task templates and no test would notice. The live code does have the check.\n4. Low: other test gaps.\n   - No test covers the member-is-assignable case, where a task template is created inside a project the member belongs to and the member is pre-filled.\n   - The only HTTP test is the project round trip. There is none for from-task/create-task or for the suggested owner over HTTP.\n5. Process: no commit names 8B9NBH, so jaira's commit list will be empty. The handoff asks for a commit whose message names the handle, and that has not been made.\n6. The rest of the definition of done is met: save, create, structure only, owner-only in code, unit and HTTP tests exist, suite green. Two earlier design choices remain and are for the owner to confirm: attachment links are carried into templates, and task-template creation uses prompt() boxes in the UI.\nMutation evidence:\n- Replacing the `_validate_assignee` call with the raw user id is caught (1 failure).\n- Always storing suggested_owner=None is caught (1 failure).\n- Removing `require_owner` from save_task_as_template is not caught."
review-verdict: "Send back. The code meets the ticket's written definition of done. Save and create work for both project and task templates, only structure is copied, the owner-only check is in the code, and the suite is green (335 tests). The rework Aly asked for on 2026-09-15 is not delivered as asked. She wanted a role-based suggested owner. What shipped is a named person by display name, and for project templates it pre-fills only App Owner and Chairman users. Aly needs to accept that or ask for role-based. Also add a test that fails if the owner-only check on task templates is removed, and consider recording the pre-filled owner in the `task_created` event. I am fairly confident about the facts above. Whether name-based is acceptable is Aly's call."
review-check: |-
  1. cd /workspace/project-astra && git checkout codex/migration-safety-remediation
  2. Run `.venv/bin/python tests/run.py`. The last lines should read "Ran 335 tests" and "OK".
  3. Run `.venv/bin/python -m unittest discover -s tests -k test_template_carries_suggested_owner -v`. It should pass. Then open tests/test_core.py line 1223. Its last assertion says the project member's task ("Member task") comes out unassigned in the new project.
  4. Open src/astra/service.py line 2210 (`_resolve_suggested_owner`). It matches on `display_name`, not on a project role. Compare this with Aly's 2026-09-15 18:31 note in .jaira/tickets/01M2JFER9P4JB4MD8QMH8B9NBH-project-task-templates.md, which asks for "role-based".
  5. Mutation check, in a scratch copy and never in the clone: in the copy's src/astra/service.py, delete the line `self.require_owner(actor)` inside `save_task_as_template`, around line 2155. Run the copy's tests. They all still pass, which shows no test covers this owner-only check.
  6. Open src/astra/service.py around line 2267 (`_instantiate_tasks`, pass 2). The `task_created` event records only title and from_template. The pre-filled owner is not recorded.
  7. Optional, by hand: run the app, log in as the Owner, save a project with member-owned tasks as a template, then use it to create a new project. Those tasks come out unassigned. Only tasks the Owner owned are pre-filled.
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
- **2026-09-24 05:31 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: suggested owner is name-based, not the role-based version Aly asked for on 2026-09-15; no test catches removing require_owner from save_task_as_template. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name 8B9NBH.
