---
id: 01M2JXM4NWFWH5J0BYJ35WZ4A8
title: Project schedule dates with change history
status: review
ready: true
creator: Aly Jafferani
assignee: Claude
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
updated-at: 2026-09-24T06:27:06Z
claimed-by: vm-21109
claimed-at: 2026-09-24T06:15:34Z
updated-by: Claude
question: "Confirm: is project schedule editing in the People/admin config panel the right home, and is config + audit-log enough for now — or do you want project start/target to also show as markers on the Gantt/timeline (a follow-up)?"
outcome-what: "Rework after review send-back: added GET /api/projects/{id}/events (reuses service.project_events, gated by can_view_project) and a Project history dialog (toolbar button when one project is selected) that lists project events newest first, rendering schedule changes as Start/Target old -> new with actor and reason; moved the old-date read inside the write transaction in set_project_schedule; added 6 tests (3 core, 1 HTTP, 2 static UI) and tightened test_project_schedule_over_http to read the audit row back; README documents the feature."
outcome-why: "Review verdict 'send back' (gaps 1-4): nothing failed if the authorization check was deleted or before/after swapped, the HTTP test never read the audit row, and no user could see a project date change. Gap 5 (stale 'before' under concurrent edits) was cheap to close. Aly approved reassignment and the fix (Slack ts 1790228901.999149)."
outcome-resolves: "DoD 1: editable dates, reason required, one project_events row with actor/before/after/reason (pinned by test_project_schedule_audit_row_records_actor_before_after_and_reason), history visible via GET /api/projects/{id}/events and the Project history dialog, task date log cited and tested. DoD 2: auth + audit-content tests at service and HTTP level; fault injection (guard removed, before/after swapped) now fails them. DoD 3: members incl. viewers read history (200), non-members 403; before/after screenshots taken on 127.0.0.1. Full suite 357 OK, node --check, compileall, git diff --check clean."
review-summary: |-
  What shipped (read from the code, since there is no diff):
  (1) Migration v11 (src/astra/db.py _migrate_v11) adds nullable projects.start_date and projects.target_date.
  (2) AstraService.set_project_schedule (src/astra/service.py:418):
  - checks can_manage_project, so only the owner or a project manager can change dates;
  - parses dates with date.fromisoformat and rejects a target earlier than the start;
  - rejects a no-op change and requires a non-blank reason;
  - in one BEGIN IMMEDIATE transaction, updates both columns and writes a project_events row. That row has event_type project_schedule_changed, actor_user_id = the actor, reason, and detail_json {before:{start,target}, after:{start,target}}.
  (3) POST /api/projects/{id}/schedule (src/astra/web.py:237) calls it. Errors map to 403 (Forbidden), 400 (ValueError) and 404 (KeyError).
  (4) UI: start/target date inputs and a reason field in the People/admin project block (app.js:1119-1137).
  (5) Gantt start/target markers (app.js:131-151): dashed lines plus escaped labels, scaled into the date range, prefixed with the project name when several projects are shown.
  (6) Tests:
  - test_core: test_project_schedule_change_is_logged, test_project_schedule_requires_reason, test_project_target_cannot_precede_start, test_task_date_change_is_logged_with_before_and_after, test_list_projects_exposes_schedule_dates_for_gantt_markers;
  - test_web: test_project_schedule_over_http.
  Task date logging already existed (update_task writes task_updated with before/after JSON and a reason) and is now covered by a test.
  What I checked myself:
  - Full suite at 1c45904: 335 tests OK.
  - A probe script confirmed: a viewer or non-member gets Forbidden; a manager can set dates and the row records that manager's id, the reason and the right before/after; a bad date or an unknown project fails in a controlled way.
review-gaps: |-
  1. MEDIUM. Nothing in the suite covers authorization. I deleted the can_manage_project check from set_project_schedule in a scratch copy and all 335 tests still passed. The code gates correctly today (probe: viewer and outsider get Forbidden), but no test stops a regression on this mutating endpoint.
  2. MEDIUM. The tests do not check the audit row's content. test_project_schedule_change_is_logged only checks that "2026-06-30" appears somewhere in detail_json, and that there are two events. Swapping before and after in the code passed every schedule test. Nothing asserts actor_user_id; the actor-is-None mutation was caught only by the NOT NULL constraint. The DoD asks that the audit row capture actor + old + new + reason, and asks for tests of it.
  3. MEDIUM. The HTTP test does not check the audit row. test_project_schedule_over_http checks the 200 response and the 400 when the reason is missing, but never reads the project_events row. The DoD says the HTTP tests cover the change "+ its audit row".
  4. MEDIUM. "The change is visible in the project's history" holds only at the service layer. AstraService.project_events() exists, but no HTTP route serves it (web.py has /api/tasks/{id}/events only) and no UI shows it. No user can see a project date change after it is made. app.js:1364 also tells users "Every change is ... in the project activity", and that view does not exist.
  5. LOW. set_project_schedule reads the old values through get_project before BEGIN IMMEDIATE. Two concurrent edits can both record the same "before". The saved dates end up correct, but the audit trail can misstate one transition.
  6. LOW. The outcome fields describe only the Gantt-marker follow-up, not the core schedule and audit work. The markers have no automated rendering test (the implementer noted "visual pass pending") and I did not open a browser either.
  7. INFO. Closed projects accept schedule changes. This matches the budget and primary-entity setters and is not in the DoD.
review-verdict: |-
  Send back.
  The behaviour is correct:
  - the dates are editable;
  - a reason is required;
  - one project_events row records the actor, before, after and reason, in one transaction;
  - authorization is enforced;
  - errors are controlled;
  - the task date log is cited and tested;
  - the suite is green (335).
  The DoD is not fully met on two points:
  - The required tests do not pin the audit row or access control. Swapping before/after survives the schedule tests, and removing the auth check survives the whole suite. The HTTP test never checks the audit row.
  - The "visible in the project's history" item has no user-facing surface.
  To fix:
  (a) In test_project_schedule_change_is_logged, assert actor_user_id, the reason, and parsed before/after on both changes.
  (b) Add a test that a viewer and a non-member get Forbidden (service) and 403 (HTTP), and that a manager succeeds.
  (c) In test_project_schedule_over_http, read the project_events row back and check it.
  (d) Either add GET /api/projects/{id}/events (gated by can_view_project through project_events) and a small history list in the UI, or have Aly confirm in writing that service-level history meets "visible".
  Optionally, move the old-value read inside the transaction.
  I am confident in the gaps above. The marker rendering was not checked visually.
review-check: |-
  1. cd /workspace/project-astra
  2. .venv/bin/python -m unittest -k schedule tests.test_core tests.test_web. Expect: 13 tests, OK.
  3. .venv/bin/python -m astra (or however you normally start Astra), log in as the owner and open People. Pick a project and set Project start 2026-03-01 and Project target 2026-06-30.
  4. Click "Save project dates" with the Reason box empty. Expect the red message "A reason is required to change the project schedule."
  5. Type a reason and save again. Expect "Saved and logged.".
  6. Open the Gantt for that project. Expect dashed Start and Target lines with labels at those dates.
  7. Look for somewhere in the app that shows the project's change history. Expect: there is none (this is gap 4).
  8. To see the log row, run: sqlite3 <your astra db> "select event_type, actor_user_id, reason, detail_json from project_events where event_type='project_schedule_changed' order by occurred_at desc limit 1;". Expect your user id, your reason, and before/after JSON.
  9. To confirm gap 1: in a scratch copy, delete the two can_manage_project lines at the top of set_project_schedule in src/astra/service.py, then run tests/run.py. Expect all tests still pass.
---

# Project schedule dates with change history

## Definition of Done

- [x] Projects have an editable start_date and target/end date; changing either requires a reason and writes a project_events audit row capturing actor + old + new + reason; the change is visible in the project's history; task date-change logging is confirmed already working and cited (no regression); unit + HTTP tests cover the project date change + its audit row; existing tests green.
  proof: db v11 projects.start_date/target_date; service.set_project_schedule (src/astra/service.py:418: can_manage_project gate, target>=start, reason required, old values read inside BEGIN IMMEDIATE, one project_events 'project_schedule_changed' row {before,after}+reason+actor); POST /api/projects/{id}/schedule; history visible via GET /api/projects/{id}/events + Project history dialog (app.js openProjectHistory/renderProjectEvent); task date log cited+tested (update_task task_updated before/after+reason: test_core.test_task_date_change_is_logged_with_before_and_after). Tests: test_core.test_project_schedule_change_is_logged, test_project_schedule_audit_row_records_actor_before_after_and_reason, test_project_schedule_change_requires_manage_access, test_project_history_readable_by_members_not_outsiders, test_project_schedule_requires_reason, test_project_target_cannot_precede_start; test_web.test_project_schedule_over_http (reads audit row back), test_project_schedule_and_history_authorization_over_http. Full suite tests/run.py: 357 OK on 2026-09-24 (base branch 351; stale '97 pass' proof replaced).
- [x] Rework (review gaps 1-3): tests fail if the can_manage_project check is removed from set_project_schedule (service Forbidden + HTTP 403 for viewer and non-member, manager succeeds) and pin the audit row: actor_user_id, reason, parsed before/after for both changes, at service and HTTP level.
  proof: test_core.test_project_schedule_change_requires_manage_access (viewer+outsider Forbidden, nothing written, manager ok); test_core.test_project_schedule_audit_row_records_actor_before_after_and_reason (actor_user_id, actor_name, reason, parsed detail_json before/after for owner then manager change); test_web.test_project_schedule_and_history_authorization_over_http (viewer/outsider POST 403, manager 200, audit row actor+reason); test_web.test_project_schedule_over_http (GET events row: reason, actor_name, before/after). Fault injection: removing the can_manage_project guard fails 3 assertions; swapping before/after fails the audit-row test.
- [x] Rework (review gap 4): GET /api/projects/{id}/events serves the project's history to anyone who can view the project (403 for non-members), and the UI shows it (Project history dialog from the toolbar when one project is selected), with before-and-after screenshots.
  proof: src/astra/web.py do_GET: /api/projects/{id}/events -> service.project_events (get_project -> can_view_project); index.html #project-history-btn + #project-history-dialog; app.js openProjectHistory/renderProjectEvent (reuses .history list, .muted, inbox/search dialog CSS); tests test_core.test_project_history_readable_by_members_not_outsiders, test_web.test_project_schedule_and_history_authorization_over_http (viewer 200, outsider 403, anonymous 401/403), test_web.AstraProjectHistoryUiTests (2). Screenshots (127.0.0.1, synthetic data) in session scratchpad ui-shots/5WZ4A8-before-{owner,viewer}-toolbar.png and 5WZ4A8-after-{owner,viewer}-{toolbar,history}.png.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Write failing tests first: service auth (viewer/outsider Forbidden, manager ok), audit row contents, HTTP 403 + audit read-back, GET /api/projects/{id}/events 200 for member / 403 for outsider
- [x] Add GET /api/projects/{id}/events in web.py reusing service.project_events (gated by get_project -> can_view_project)
- [x] Move the old-value read inside the transaction in set_project_schedule (gap 5)
- [x] UI: Project history button + dialog reusing .history list styles; label project_schedule_changed with before -> after dates; fix app.js 'project activity' wording to point at it
- [x] Screenshots before/after on 127.0.0.1 with synthetic data; full suite, node --check, compileall, diff --check
- [x] Update ticket proof/outcome and README/docs if they list endpoints

## Progress
- **2026-09-15 16:36 · Aly Jafferani** — DECISION (owner, 2026-09-15): project dates are INFORMATIONAL ONLY — recorded and change-logged, but never constrain/warn/block task dates (matches permissive calendar XDA2JR). PLAN: (1) db v11 ALTER projects ADD start_date, ADD target_date (both TEXT, nullable). (2) service.set_project_schedule(actor,project_id,start_date,target_date,reason) gated can_manage_project; validate target>=start; require reason when either value changes; write project_events 'project_schedule_changed' detail {before/after start+target} + reason. Dates already flow through get_project/list_projects (SELECT *). (3) web POST /api/projects/{id}/schedule. (4) UI: start/target date inputs + reason in the People dialog project section (beside budget/primary-entity). (5) tests: core (change logs old/new/reason; reason required; target<start rejected; no task constraint) + web roundtrip. TASK date history already done (update_task before/after + JZACMP) — cite, no change.
- **2026-09-15 16:40 · Aly Jafferani** — No real-browser visual pass (yolo-chrome down). Verified: 97 tests green incl. HTTP roundtrip; app.js node --check clean; migration v11 boots. Owner decision applied: project dates informational-only, never constrain tasks. project_events reused (no new audit table). Both halves of the requirement now satisfied: tasks (pre-existing) + projects (this ticket).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): in addition to config-panel editing + audit log, show project start/target as MARKERS on the Gantt/timeline. Add the markers.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Latest change: project start/target markers added to the Gantt timeline (dashed lines + labels + legend, scaled to range, single- vs multi-project labelling); schedule edit lives in People/admin with audit log. In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
- **2026-09-24 05:33 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: no test covers authorization or the audit row contents; project history is not visible via HTTP or UI. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name 5WZ4A8.
- **2026-09-24 06:15 · Claude** — Reassigned to Claude with Aly Jafferani's approval (Slack thread 1790160392.461299, message ts 1790228901.999149, 2026-09-24 05:48 UTC: 'Yes please fix them'). Reworking review-gaps 1-4 (and 5/6 where cheap).
- **2026-09-24 06:22 · Claude** — Rework findings the repo does not say: (1) Fault injection confirmed the new tests bite: deleting the can_manage_project guard in set_project_schedule now fails test_project_schedule_change_requires_manage_access + test_project_schedule_and_history_authorization_over_http; swapping before/after fails test_project_schedule_audit_row_records_actor_before_after_and_reason (outputs kept in session scratchpad 5wz-mutA/B.txt). (2) GET /api/projects/{id}/events reuses service.project_events, which gates via get_project -> can_view_project (owner, chairman, any member incl. viewer). It returns ALL project_events kinds, not only schedule changes: project_closed, import_committed, protected_action_blocked/approved/rejected/cancelled. That is deliberate (it is the project's history; the import-done copy in app.js already promised 'project activity') but a viewer can therefore see blocked-attempt rows for the project; flag to Aly if that is unwanted. (3) The CSP (web.py style-src 'self') blocks inline style= attributes, so the many style="color:#667085;font-size:12px" hints in app.js render unstyled — use existing classes (.muted) instead; I did. Pre-existing, not fixed here. (4) The toolbar does not wrap at 1280px, so the right-hand buttons (incl. Project history) are squeezed/off-screen until scrolled — pre-existing layout issue, not fixed. (5) Dev servers on 8791/8792 collided with other tracks' servers; use a high random port for screenshots. (6) Gap 5 fixed: old dates are now read inside BEGIN IMMEDIATE; the no-op and reason checks moved inside and roll back.
