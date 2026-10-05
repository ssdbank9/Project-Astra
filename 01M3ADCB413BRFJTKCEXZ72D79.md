---
id: 01M3ADCB413BRFJTKCEXZ72D79
title: Record settings changes and let owners reopen a closed project
status: in-progress
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
updated-at: 2026-10-05T18:24:45Z
updated-by: Aly Jafferani
claimed-by: X1CarbonPC-63800
claimed-at: 2026-10-05T17:14:21Z
outcome-what: "Plan completed: inventory, event design, transactional settings audit, owner reopen route, history UI, tests and independent verification."
outcome-why: "Existing project_events and owner-notice infrastructure can support the selected decisions; the plan closes the ticket's prior ambiguity."
outcome-resolves: Makes Z72D79 ready for implementation without changing behavior yet.
---

# Record settings changes and let owners reopen a closed project

## Definition of Done

- [ ] Each listed settings change writes an audit row with actor, time and before/after values, shown in the relevant history; an owner (as Aly decides) can reopen a closed project with a required reason, recorded and notified; tests for each change and for reopen; existing tests green.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Inventory the existing project_events schema, history filters, notifications, settings write paths and closed-project UI/API.
  proof: Inventory recorded in ticket note; service.py, web.py, db.py and app.js paths inspected
- [x] Define event kinds and before/after detail shapes for project settings, app settings and project reopen; record why settings are history-only while reopen notifies other owners.
  proof: _project_setting_event and _app_setting_event define before/after detail JSON; reopen notification policy recorded in ticket note
- [x] Add transactional audit coverage to project calendar, holidays, budget, entity links/primary entity, entity active state and import template configuration writes.
  proof: set_working_days, add/remove_holiday, set_project_budget, set_project_entities, set_primary_entity, set_entity_active and set_import_template_config now write audit records
- [x] Add owner-only project reopen with a required reason, project history event and notifications to the other active owners; expose the service and HTTP route.
  proof: AstraService.reopen_project, POST /api/projects/{id}/reopen, required reason, project_reopened event and owner notification
- [x] Show new project setting and reopen events in project Activity, and show app-wide setting history in People and access.
  proof: Project event labels/detail rendering and People owner-event labels/detail rendering updated; Reopen project control added
- [ ] Add service, HTTP and UI tests for every setting path, reopen authorization/reason/notification, history visibility and no-write failures.
- [ ] Run focused checks, guard-removal checks, the full Windows suite, diff hygiene and independent review; prepare the ticket for signoff.

## Progress
- **2026-09-24 19:18 · Claude** — Filed by Claude 2026-09-24 under write lock #7 at Aly's request (ts 1790276936.363329). Nothing started; waits in backlog for Aly's answers to the open questions in the context.
- **2026-10-05 17:15 · Aly Jafferani** — Owner decisions already settled: any active Owner, including primary and secondary owners, may reopen a closed project; reopen requires a reason, is audited and notifies the other owners. Settings changes are recorded in history; app-wide settings history appears in People/access and project settings history appears in project Activity. Reopen notifications follow existing project-change notification behavior.
- **2026-10-05 17:18 · Aly Jafferani** — Inventory findings: project_events already stores project_id, event_type, actor, occurred_at, reason and detail_json; _project_event can notify other owners. project_events currently expose only project_schedule_changed and project_closed to non-managers. People history currently reads user_events for owner access. set_import_template_config already uses BEGIN IMMEDIATE but stores only current config/version, so app-wide history needs a separate history record or table. close_project has no reverse service/API/UI path.
