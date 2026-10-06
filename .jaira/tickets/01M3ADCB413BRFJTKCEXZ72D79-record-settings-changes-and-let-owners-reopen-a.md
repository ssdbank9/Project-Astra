---
id: 01M3ADCB413BRFJTKCEXZ72D79
title: Record settings changes and let owners reopen a closed project
status: human
ready: true
creator: Claude
assignee: Aly Jafferani
goal: "Every change to a project's or the app's settings leaves an audit record (who, when, old and new value), and an owner can reopen a closed project with a recorded reason."
context: "What is wrong today (branch codex/migration-safety-remediation at 39f4faf; line numbers from the option-4 scout at that commit):\n- These settings changes write no audit row and notify nobody (src/astra/service.py):\n  - project working days (set_working_days, ~749)\n  - project holidays add/remove (~767, ~780)\n  - project budget (set_project_budget, ~788)\n  - project entities and primary entity (~669, ~834)\n  - app-wide: entity active flag (~652) and the import template configuration (~3549; only the last updated_by and version are kept)\n- A closed project cannot be reopened: close_project (~2984) has no reverse path, so a mistaken close is permanent.\n- Project closes and date changes are already audited and, since XX9RFM, notified to the other owners.\nTriggered by: Aly asked for this as a separate ticket (Slack thread ts 1790256175.671249, ts 1790276936.363329: 'A record of settings changes and a way to reopen projects will go on a separate ticket. Okay').\nOpen questions for Aly before building:\n- Who may reopen a closed project (any owner, like close, or the primary only)?\n- Should settings changes also notify the other owners, or only be recorded in history?\n- Where the app-wide changes are shown (People screen history, or a new settings history)."
definition-of-done: "Each listed settings change writes an audit row with actor, time and before/after values, shown in the relevant history; an owner (as Aly decides) can reopen a closed project with a required reason, recorded and notified; tests for each change and for reopen; existing tests green."
tags:
  - astra
blocked-by: []
related:
  - 01M3ADA4DRPMWYVBJ2ZJXX9RFM
  - 01M39HQB2EFDXWXH92WYGTEYTG
commits: []
created-at: 2026-09-24T19:13:21Z
updated-at: 2026-10-06T00:46:21Z
updated-by: Aly Jafferani
claimed-by: X1CarbonPC-63800
claimed-at: 2026-10-05T17:14:21Z
outcome-what: "Independent review completed; implementation is ready for Aly's human acceptance with browser checks called out."
outcome-why: "Full suite passed and the read-only review found no atomicity defect; remaining browser and role-notice verification is explicitly disclosed."
outcome-resolves: Moves Z72D79 to Aly for acceptance.
review-summary: "The diff adds transactional before/after audit events for project calendar, holidays, budget, entity links and primary entity, plus app entity-active and import-template settings. It adds owner/Chairman reopen with a required reason, project history and owner notices, an HTTP route, Activity/People history rendering, and tests; the full suite reports 720 tests OK with one skip."
review-gaps: "The source is atomic and the focused/full tests pass. Browser acceptance of the new reopen control and rendered Settings history is unverified, and the added HTTP test covers owner reopen rather than Chairman HTTP reopen or notification recipients directly."
review-verdict: "Conditional approval for Aly: implementation is ready for human review; browser acceptance and the remaining role/notice checks should be confirmed before signoff."
review-check: "1. Run .venv\\\\Scripts\\\\python.exe tests\\\\run.py. 2. Confirm the output ends with Ran 720 tests and OK (skipped=1). 3. Log in as an active owner, close a project, reopen it with a reason, and open Activity. 4. Confirm project_reopened shows the actor, reason and before/after status. 5. Open People & access and confirm Settings history is separate from Owner access history. 6. Repeat reopen as the Chairman and confirm it succeeds with a reason."
question: "Aly: please perform the browser acceptance steps in review-check, especially owner and Chairman reopen, Activity history, and separate People Settings history; then accept or return the ticket."
---

# Record settings changes and let owners reopen a closed project

## Definition of Done

- [x] Each listed settings change writes an audit row with actor, time and before/after values, shown in the relevant history; an owner (as Aly decides) can reopen a closed project with a required reason, recorded and notified; tests for each change and for reopen; existing tests green.
  proof: tests/test_core.py:test_project_settings_are_audited_and_closed_project_can_reopen; tests/run.py (720 tests, OK)

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Inventory the existing project_events schema, history filters, notifications, settings write paths and closed-project UI/API.
  proof: Inventory recorded in ticket note; service.py, web.py, db.py and app.js paths inspected
- [x] Define event kinds and before/after detail shapes for project settings, app settings and project reopen; record why settings are history-only while reopen notifies other owners.
  proof: _project_setting_event and _app_setting_event define before/after detail JSON; reopen notification policy recorded in ticket note
- [x] Add audit coverage to project calendar, holidays, budget, entity links/primary entity, entity active state and import template configuration writes; make each audit write atomic with its setting change.
  proof: src/astra/service.py:settings mutation transactions and _project_setting_event/_app_setting_event
- [x] Add owner-only project reopen with a required reason, project history event and notifications to the other active owners; expose the service and HTTP route.
  proof: AstraService.reopen_project, POST /api/projects/{id}/reopen, required reason, project_reopened event and owner notification
- [x] Show new project setting and reopen events in project Activity, and show app-wide setting history in People and access.
  proof: Project event labels/detail rendering and People owner-event labels/detail rendering updated; Reopen project control added
- [x] Add service, HTTP and UI tests for every setting path, reopen authorization/reason/notification, history visibility and no-write failures.
  proof: tests/test_core.py:test_all_settings_paths_record_before_and_after_values; tests/test_web.py:test_reopen_project_over_http_requires_reason_and_records_history
- [x] Run focused checks, guard-removal checks, the full Windows suite, diff hygiene and independent review; prepare the ticket for signoff.
  proof: tests/run.py: Ran 720 tests in 525.252s, OK (skipped=1); independent review by plan_review: atomicity clean

## Progress
- **2026-09-24 19:18 · Claude** — Filed by Claude 2026-09-24 under write lock #7 at Aly's request (ts 1790276936.363329). Nothing started; waits in backlog for Aly's answers to the open questions in the context.
- **2026-10-05 17:15 · Aly Jafferani** — Owner decisions already settled: any active Owner, including primary and secondary owners, may reopen a closed project; reopen requires a reason, is audited and notifies the other owners. Settings changes are recorded in history; app-wide settings history appears in People/access and project settings history appears in project Activity. Reopen notifications follow existing project-change notification behavior.
- **2026-10-05 17:18 · Aly Jafferani** — Inventory findings: project_events already stores project_id, event_type, actor, occurred_at, reason and detail_json; _project_event can notify other owners. project_events currently expose only project_schedule_changed and project_closed to non-managers. People history currently reads user_events for owner access. set_import_template_config already uses BEGIN IMMEDIATE but stores only current config/version, so app-wide history needs a separate history record or table. close_project has no reverse service/API/UI path.
- **2026-10-06 00:46 · Aly Jafferani** — Browser verification 2026-10-06: local browser confirmed the accessible Close project dialog, required closure note, exceptional checkbox, closed state, Reopen project button, accessible reopen dialog, and empty-reason blocking. Submitting a valid reopen reason reached the running server but returned HTML 404/Unexpected token '<' because the local Astra backend process predates the /reopen route; backend route remains unverified in this running instance. Replaced unsupported prompt() calls with dialog forms in commit 55d550c; tests/test_web.py Ran 220 tests, OK.
