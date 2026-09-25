---
id: 01M3CEHBP9XNTK0SG1Q8XV92JJ
title: Bulk select and WIP limits
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Owners and managers select several tasks on the List or Board and change their status, assignee or due dates in one all-or-nothing change, previewed first and undoable. Owners set an optional work-in-progress limit per board column per project, and a move over it is refused with a reason unless an owner confirms an override."
context: |-
  What is wrong today (after X07XV4, 34eeca1):
  - Changing ten tasks means ten trips through the task panel or the board.
  - Nothing stops a column from filling up: there is no work-in-progress (WIP) limit.
  Trigger: Aly's lock #12 (Slack ts 1790341004.453539, 2026-09-25), item C.
  Governing rules: JQY55P Progress notes of 2026-09-19 (bulk dragging, bulk locking, workflow configuration authority). 'App Owner' means any active owner (Aly ts 1790277044.283429). Keep it lean.
  Known: task locks exist (task_locks, kind 'bulk' reserved). update_task writes one transaction per task, so a bulk change needs its own single transaction. Board columns and moves are in service.py BOARD_* and move_task.
  Plan: session file lock12-plan.md, decisions 7 and 8.
  Not here: project placement, tags or archive in bulk; swimlane configuration; the daily digest.
definition-of-done: "Server: preview and apply for bulk status (Draft/Ready/In progress), assignee and due-date offset; the preview lists counts and blocked items with reasons; apply is all-or-nothing in one transaction with bulk locks (any task in use by someone else names the holders and nothing starts), one bulk_change project event plus per-task task_updated events, and a bulk Undo that restores every task only if none changed since"
tags:
  - astra
blocked-by: []
related:
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M3CAJRFH9J4RJFVMSZJN1QYG
  - 01M3CCSS8AAJZS0MAY4BX07XV4
  - 01M3BSY3W3FH34MF87RACR121Z
commits: []
created-at: 2026-09-25T14:12:02Z
updated-at: 2026-09-25T16:03:09Z
updated-by: Claude
claimed-by: vm-26940
claimed-at: 2026-09-25T14:12:18Z
outcome-what: "Owners and the project's managers tick tasks on a project's Board or List (Shift-click range, Space and Shift+Arrow in the list) and change status (Draft/Ready/In progress), assignee or due dates in bulk. A preview names every blocked task and any schedule consequences. Apply is all-or-nothing: bulk leases on every task first, then one transaction holding the writes, per-task task_updated events and one bulk_change project event with one owner notice. There is a 15 s bulk Undo. Owners set optional WIP limits per open column (wip_limits, schema v20; wip_limit_changed). Board moves and bulk status changes over a limit are refused with the reason, and owners may override after a confirm (wip_limit_override). Column heads show n / limit. update_task's write body became _apply_task_update so bulk can share it."
outcome-why: "Aly's lock #12 (Slack ts 1790341004.453539), item C, under the JQY55P 2026-09-19 decisions on bulk dragging, bulk locking and workflow configuration authority."
outcome-resolves: "Ticket C of lock #12: bulk select and WIP limits."
---

# Bulk select and WIP limits

## Definition of Done

- [x] Server: preview and apply for bulk status (Draft/Ready/In progress), assignee and due-date offset; the preview lists counts and blocked items with reasons; apply is all-or-nothing in one transaction with bulk locks (any task in use by someone else names the holders and nothing starts), one bulk_change project event plus per-task task_updated events, and a bulk Undo that restores every task only if none changed since
  proof: service.py:2842 _bulk_plan, :2983 bulk_apply (one transaction via _write_bulk, bulk leases all-or-nothing), :3014 bulk_undo; test_board BulkChangeTests (8) incl. test_a_failure_part_way_rolls_every_task_back and test_a_task_in_use_by_someone_else_stops_the_whole_change
- [x] WIP limits: schema v20 wip_limits with migration tests; only an owner sets or clears limits per open board column per project (whole numbers, all columns in one transaction, audited as wip_limit_changed per changed column); every status-changing write a person makes (board, bulk and both Undos, panel status, hold, submit, reopen, request changes, create, promotion to top level) that would exceed a limit is refused with a clear reason, and an owner may override after a confirm (wip_limit_override in the same transaction); entry into Blocked caused by a dependency is not refused
  proof: db.py:795 _migrate_v20 + test_db WipLimitMigrationTests; service.py:2772 set_wip_limit, :2827 _wip_gate; test_board WipLimitTests; lock12-shots c07 (owner limits), c08 (manager refused), c09/c10 (owner override)
- [x] UI: checkboxes on board cards and schedule-list rows, Shift-click for a range, keyboard selection (Space toggles, Shift+Arrow extends on the list), a bulk bar with the three actions, a preview with counts and blocked items and a Remove blocked button, Undo toast; owners see WIP settings on the board, and column heads show n / limit
  proof: app.js pick boxes on board cards and list rows, :1109 pickRange (Shift-click), Space/Shift+Arrow on list boxes, :1130 bulk bar, :1178 preview with Remove blocked, Undo toast, :1202 Limits… dialog, n / limit heads; lock12-shots c01 (board selection), c02-c04 (preview, apply, Undo), c05/c06/c06b (list keyboard selection, blocked, remove), c07-c10 (WIP), c12/c13 (phone)
- [x] Behaviour tests (service, web, migration, node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Playwright evidence at 1440 and 390 (bulk bar, preview, WIP refusal) without CSP errors; README updated
  proof: full suite 586 OK (tests/run.py, 284 s); git diff --check clean; 0 CR; node --check app.js; jaira validate 0 errors; Playwright lock12-shots c01-c13 at 1440 and 390, 0 CSP errors; README

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v20 wip_limits(project_id, column_key, max_tasks, updated_by, updated_at; PK project+column); migration test
  proof: db.py:795 _migrate_v20; tests/test_db.py:1371 WipLimitMigrationTests
- [x] service: wip_limits read (list_projects carries them), set_wip_limit (owner only, project event), _wip_check in _move_task (non-owner refused and audited, owner NeedsConfirmation 'wip', override writes wip_limit_override)
  proof: service.py:2772 set_wip_limit, :2827 _wip_gate (called in _move_task); tests/test_board.py:363 WipLimitTests
- [x] service: refactor _write_task_update's body into _apply_task_update so bulk can write many tasks in one transaction; bulk_preview and bulk_apply (validation shared, locks all-or-nothing, bulk_change project event with the per-task list, one owner notice), bulk_undo
  proof: service.py:1290 _apply_task_update, :2842 _bulk_plan, :2933 _take_bulk_leases, :2983 bulk_apply, :3014 bulk_undo; tests/test_board.py:403 BulkChangeTests
- [x] web routes: POST /api/projects/<id>/bulk/preview, /bulk/apply, /bulk/undo, /wip-limits
  proof: src/astra/web.py bulk/preview|apply|undo and wip-limits routes; tests/test_web.py:1858 test_bulk_change_and_wip_limits_over_http
- [x] app.js: selection state and checkboxes on board and schedule list, Shift-click, keyboard, bulk bar and preview dialog, Undo toast; WIP settings dialog for owners and n / limit in column heads
  proof: app.js:1109 pickRange, :1130 renderBulkBar, :1157 reviewBulk, :1178 askBulk, :1202 openWipSettings; tests/test_web.py:3032 AstraBulkDriverTests
- [x] Tests and evidence; README
  proof: tests/test_board.py WipLimitTests, BulkChangeTests; test_web AstraBulkDriverTests; lock12-shots c01-c13; README bulk + WIP + schema 20

## Progress
- **2026-09-25 14:12 · Claude** — Why the plan looks like this: update_task commits one task per transaction and transaction() does not nest, so bulk_apply cannot call it N times and stay all-or-nothing. The row write, baseline, event and request resolution inside _write_task_update become _apply_task_update, called once per task inside one bulk transaction. The per-task validation stays _validate_task_update, the same code the panel uses. Bulk status offers only Draft/Ready/In progress from draft, assigned, in_progress or delayed sources. Holds, submissions, acceptances, closes and reopens need per-task reasons or records, so those items show as blocked with 'change it on its own'. Per-task events are written without notice, and one bulk_change project event carries the notice, so owners get one message rather than N. The WIP count is top-level open tasks shown in that column (the board's own mapping, including dependency-blocked cards in Blocked).
- **2026-09-25 14:29 · Claude** — Decisions made while building: bulk status offers only Draft, Ready and In progress. Holds, submissions, decisions and closes need a per-task reason or record, and the owner notes do not say bulk may skip that. The due-date offset shows its schedule consequences in the preview; the preview itself is the confirmation, and the parent event tells the owners. A manager cannot pass a WIP limit in bulk: the preview shows the limit with no Apply button. The board's WIP override is a task event (wip_limit_override on the task, noticed to the other owners); a bulk override is a project event. Undo of a board move back into a full column goes through update_task, so it is not WIP-checked; the column the card left always has room for it again unless someone filled it meanwhile. Found out: const declarations in app.js are not globals when eval'd by the node driver, so the driver reaches the bulk state through the __a export.
- **2026-09-25 16:03 · Claude** — Review 12c fix set: the WIP limit is now a server rule inside every status-changing write (_wip_entry_gate after the row changes, in the same transaction). Anyone but an owner gets RuleRefusal; an owner gets a wip confirm, and an owner's approval of a request counts as the override. Dependency-driven entry into Blocked is exempt. Bulk now: rebuilds the plan inside _write_bulk after the leases (drift refuses), checks WIP for the columns entered and writes wip_limit_override there, never replaces the actor's own lease, requires expected_revisions as ints, blocks out-of-range date shifts, and requires confirmed for schedule consequences. set_wip_limits saves several columns at once, taking whole numbers only.
