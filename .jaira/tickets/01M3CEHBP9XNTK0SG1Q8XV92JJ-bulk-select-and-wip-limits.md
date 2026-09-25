---
id: 01M3CEHBP9XNTK0SG1Q8XV92JJ
title: Bulk select and WIP limits
status: signoff
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
updated-at: 2026-09-25T17:47:14Z
updated-by: Claude
claimed-by: vm-26940
claimed-at: 2026-09-25T14:12:18Z
outcome-what: "Owners and the project's managers tick tasks on a project's Board or List (Shift-click range, Space and Shift+Arrow in the list) and change status (Draft/Ready/In progress), assignee or due dates in bulk. A preview names every blocked task and any schedule consequences. Apply is all-or-nothing: bulk leases on every task first, then one transaction holding the writes, per-task task_updated events and one bulk_change project event with one owner notice. There is a 15 s bulk Undo. Owners set optional WIP limits per open column (wip_limits, schema v20; wip_limit_changed). Board moves and bulk status changes over a limit are refused with the reason, and owners may override after a confirm (wip_limit_override). Column heads show n / limit. update_task's write body became _apply_task_update so bulk can share it."
outcome-why: "Aly's lock #12 (Slack ts 1790341004.453539), item C, under the JQY55P 2026-09-19 decisions on bulk dragging, bulk locking and workflow configuration authority."
outcome-resolves: "Ticket C of lock #12: bulk select and WIP limits."
review-summary: "Reviews 12c, 12d and 12e (2026-09-25) of 50e139d, 55ddf3c and 89e9229. Owners and a project's managers tick tasks on the Board or List (Shift-click and Shift+Arrow take ranges) and change Status (Draft, Ready, In progress), Assignee or a due-date offset in bulk. Review change previews counts and names every blocked task with its reason, schedule consequences and a WIP overflow; apply is all or nothing: bulk leases first (skipping tasks the actor already holds), then, in one transaction, the plan is rebuilt and any drift since the preview refuses the change, every task write, one bulk_change event and one notice; schedule consequences need confirmed. Undo within 15 seconds restores every task or none. The write reads the board once before and once after (_board_snapshot), so a 200-task change in a 1000-task project applies in about 0.2 s instead of 33 s (12d M1). Optional WIP limits per board column (schema v20 wip_limits, owners only, whole numbers, one request and one transaction) are a rule of every status-changing write a person makes, including approving a request: anyone but an owner is refused, an owner confirms and wip_limit_override is written in the same transaction; a dependency-driven entry into Blocked is exempt."
review-gaps: "Left for later: three revert experiments no test catches (review 12e L1): dropping the board-source-status check in undo_move, dropping the per-row revision check inside _write_bulk, and showing members the bulk checkboxes. Not tried on a real touch device (tablet long press, Playwright emulation only), no screen-reader run, and no live refresh (lock chips, banners and Inbox gate lines show the last load; the server rechecks at write and decision time). Review 12c I3: bulk assign, like the panel, accepts the chairman and project viewers; ask Aly whether viewers should be assignable. The Blocked WIP exemption: a card that enters Blocked because of a dependency is not refused, so a Blocked limit can be exceeded by an added link or a reopened predecessor. A manager's accept request on a waiting task is filed and the owner is asked at decision time (not refused at filing). An owner's own board Undo passes the dependency override itself (12d I1); the importer and templates bypass the WIP and dependency gates (owner-only, 12d I2)."
review-verdict: "approve with follow-ups: reviews 12a, 12b, 12c and re-review 12d each approved with follow-ups (no High); every finding fixed in 55ddf3cba30d4ce1cfe34603f25413aa9f32eb0a and 89e92295337e0edf7016e1fb1b2a85aeb0cae825; review 12e of 89e9229 approves (0 High, 0 Medium, 1 Low: three uncaught revert experiments, left as follow-ups); Ran 639 tests, OK"
review-check: "1. Repo root: .venv/bin/python tests/run.py (Windows: .venv\\Scripts\\python.exe tests\\run.py); expect 'Ran 639 tests' and 'OK'; test_board Review12dTests.test_m1_a_200_task_bulk_in_a_1000_task_project_is_quick is the speed check. 2. Sign in as the owner, open a project's Board, press Limits…, set Ready to 1 and Save: the Ready head shows 'n / 1'. 3. Use a card's Move to… to put a second card in Ready: 'Go over the limit' asks first. 4. Sign in as a manager and try the same: refused with 'Ready is at its work-in-progress limit'. 5. As the manager open the List, tick three Draft tasks, choose Status > Ready and press Review change: the preview names the limit and any blocked task with its reason; nothing changes until they are removed. 6. As the owner tick three tasks, set them to In progress, tick 'Go over the limit' if asked, Apply: one toast 'Changed 3 tasks' with Undo; press Undo: all three go back."
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
- **2026-09-25 17:27 · Claude** — Re-review 12d M1: _write_bulk called _top_column (a full enriched list_tasks) twice per task under BEGIN IMMEDIATE: 200 of 1000 tasks held the write lock 33 s and another writer failed. Now _board_snapshot (two plain queries: id/status/parent, and the set of waiting tasks) is read once before and once after the writes; _top_column reads one task, and _wip_entry_gate counts the project only when the entered column has a limit. The same 1000/200 bulk applies in about 0.2 s (Review12dTests timing test, bound 2 s; 23 s on 55ddf3c). Single-task paths load the enriched list at most once (a test counts list_tasks calls).
