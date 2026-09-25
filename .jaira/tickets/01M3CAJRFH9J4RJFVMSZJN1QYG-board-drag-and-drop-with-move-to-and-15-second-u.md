---
id: 01M3CAJRFH9J4RJFVMSZJN1QYG
title: Board drag and drop with Move to and 15-second Undo
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Owners and managers change a task's status by dragging its card to another board column, and its priority by dragging it within a column, with the same server rules as today, a keyboard/phone Move to menu, and a 15-second Undo for ordinary moves."
context: |-
  What is wrong today (after Gate 2, 77fcfce):
  - The project board (#/project/<id>/board, app.js renderBoard) is read-only. Status changes only happen in the task panel.
  - Cards in a column have no saved order; they follow the list sort.
  Trigger: Aly's lock #12 (Slack ts 1790341004.453539, 2026-09-25): the post-Gate-2 batch (drag and drop, Undo, bulk select, WIP limits).
  Governing rules: JQY55P Progress notes of 2026-09-19 (Kanban dragging, protected Kanban status authority, Undo/recovery, notifications, touch/mobile). 'App Owner' now means any active owner (Aly ts 1790277044.283429). Keep it lean.
  What the server already enforces (service.py): update_task needs owner or manager and expected_revision; a reason is required for status changes; submitted/completed/on_hold/reopened only through their dedicated actions; managers' protected moves become Owner requests (_request_protected_action).
  Plan and decisions: session file lock12-plan.md. Ordinary drops record a system reason ('Board move: A → B') and apply at once; Blocked/Closed ask for the reason the rules demand; Submitted/Accepted confirm; a task waiting on an unfinished predecessor cannot be dropped into In progress, Submitted or Accepted (owners may override, audited).
  Not here: task locks and Gantt dragging (ticket B), bulk select and WIP limits (ticket C), cross-project moves.
definition-of-done: "Server: a persisted board order (schema v18 tasks.board_rank, migration with tests) and board move/reorder/undo endpoints that reuse today's rules (role limits, reason rules, dedicated actions, Owner requests for managers' protected moves), refuse dependency-blocked forward moves (owner override with confirm), and audit every successful and blocked move"
tags:
  - astra
blocked-by: []
related:
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M3BSY3W3FH34MF87RACR121Z
  - 01M3C0MZ2TASFSNYRN1E3C1Z74
commits: []
created-at: 2026-09-25T13:02:54Z
updated-at: 2026-09-25T13:39:52Z
updated-by: Claude
claimed-by: vm-1562
claimed-at: 2026-09-25T13:03:12Z
outcome-what: "The project board is now movable by owners and the project's managers. Drag within a column to reorder it (tasks.board_rank, schema v18). Drag across columns to change status through today's server rules (Blocked = hold dialog, Submitted/Accepted confirm, Closed and reopen ask for reasons, a manager's protected drops file Owner requests). Waiting-on-predecessor cards cannot go forward, and only an owner may override (dependency_override). Refusals are audited as board_move_blocked. Every card has a Move to menu for the keyboard and phones. Ordinary moves and reorders show a 15-second Undo, which is a new audited change. Also: Aly's 2026-09-25 decision lets a project manager put work on hold directly."
outcome-why: "Aly's lock #12 (Slack ts 1790341004.453539) asked for board drag and drop, Move to and Undo under the JQY55P 2026-09-19 owner decisions. The manager-hold change is Aly's decision of Slack ts 1790342529.695749."
outcome-resolves: "Ticket A of lock #12: board drag and drop, Move to, 15-second Undo, and the manager on-hold rule."
---

# Board drag and drop with Move to and 15-second Undo

## Definition of Done

- [x] Server: a persisted board order (schema v18 tasks.board_rank, migration with tests) and board move/reorder/undo endpoints that reuse today's rules (role limits, reason rules, dedicated actions, Owner requests for managers' protected moves), refuse dependency-blocked forward moves (owner override with confirm), and audit every successful and blocked move
  proof: src/astra/service.py:2376 move_task; tests/test_board.py BoardMoveTests (11); tests/test_db.py:1226 BoardRankMigrationTests; test_web AstraGovernedDragWebTests.test_board_move_undo_and_order_over_http
- [x] Board UI: owners and managers drag cards with a mouse or trackpad (within a column to reorder, across columns to change status); invalid drops snap back with the server's reason; members and viewers cannot drag; every card has a Move to menu usable from the keyboard and on phones (where dragging is off)
  proof: src/astra/static/app.js:792 moveCard, :874 pointer drag, :896 openMoveMenu; test_web.AstraBoardDragDriverTests; lock12-shots a02 (mouse drag), a05 (refused), a07/a08 (keyboard Move to), a11 (member read-only), a13 (phone menu)
- [x] Undo: an ordinary move shows a 15-second toast with Undo; Undo is a new audited change through the same rules, refused if the task changed since; requests, submissions, acceptances and closes do not offer Undo
  proof: service.py:2468 undo_board_move; test_board test_undo_is_a_new_audited_change_and_refuses_after_a_later_change, test_undo_window_is_fifteen_seconds_plus_grace; test_web AstraBoardDragDriverTests.test_an_ordinary_move_posts_once_and_offers_undo_for_fifteen_seconds; lock12-shots a03/a04, a14/a15
- [x] Behaviour tests (service, web, migration, node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Playwright evidence at 1440 and 390 (mouse drag, keyboard Move to, Undo) without CSP errors; README updated
  proof: full suite 540 OK (tests/run.py, 269 s); git diff --check clean; 0 CR; node --check app.js; jaira validate; Playwright lock12-shots a01-a15 at 1440 and 390, 0 CSP errors; README board drag and drop + schema 18 + manager hold

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v18: tasks.board_rank REAL (NULL = unranked, sorted after ranked by the list order); migration test (fresh, upgrade, rollback/retry)
  proof: src/astra/db.py:755 _migrate_v18; tests/test_db.py:1226 BoardRankMigrationTests
- [x] service.move_task(actor, task_id, payload): map column to today's action, dependency block check, blocked-move audit (board_move_blocked, owner notice under the KBWY86 cap), return {task|request, undo}
  proof: src/astra/service.py:2376 move_task
- [x] service.reorder_board (reorder within a column, recorded in project history as board_reordered, no notice) and undo_board_move (same rules; refused if the task changed since, 20 s passed, or it is someone else's move; a new task_updated event whose reason names the original event)
  proof: src/astra/service.py:2468 undo_board_move, :2490 reorder_board
- [x] web.py routes: POST /api/tasks/<id>/board-move, POST /api/tasks/<id>/board-undo, POST /api/projects/<id>/board-order
  proof: src/astra/web.py board-move/board-undo/board-order routes; tests/test_web.py:1814 AstraGovernedDragWebTests
- [x] app.js: drag with pointer events (threshold, ghost, drop highlight, auto-scroll inside the board), Move to menu, dialogs for Blocked/Closed/Submitted/Accepted, Undo toast; board sorts by board_rank
  proof: src/astra/static/app.js:792 moveCard, :874 pointer drag, :896 openMoveMenu
- [x] Tests and evidence: service/web/migration/node tests; Playwright mouse drag, keyboard Move to, Undo at 1440 and 390; README
  proof: tests/test_board.py; tests/test_web.py AstraBoardDragDriverTests; lock12-shots a01-a15; README board section

## Progress
- **2026-09-25 13:35 · Claude** — Aly decided on 2026-09-25 (Slack ts 1790342529.695749, 'yes they can put it directly with reason.'): a project manager puts work on hold directly via set_on_hold. It no longer files an Owner request. The reason, checkpoint and hold owner are still required, it is still audited as task_on_hold, and it still notifies the other owners. Leaving on_hold is unchanged: a manager files an Owner request. A designated approver who is not a manager still files a request; everyone else is refused, as today. Folded into this ticket. The state-integrity tests that used a manager's hold to make a set_on_hold request now make it through a designated approver (_hold_request helper).
- **2026-09-25 13:35 · Claude** — What I found out: a task that waits on an unfinished predecessor shows in Blocked (boardColumn), whatever its status. So moving it to Ready/Draft changes its status but the card stays under Blocked; the toast says so. Dropping it on its own status column is refused ('already draft; it shows under Blocked because it waits on X'). Rank is one number per task that persists across columns. So a move places the card in the target column: at the drop point, or at the end when it comes from the menu or a column head. Undo also restores the old column order (best effort). A reorder that changes nothing is not saved.
- **2026-09-25 13:35 · Claude** — Chose not to: HTML5 drag-and-drop. Pointer events work the same for mouse, pen and touch, and keep scrolling intact. Phones (max-width 760px) never start a drag, and a touch long-press of 450 ms starts one only on wider touch screens. Undo is offered only for direct ordinary moves among Draft/Ready/In progress (and delayed as a source), plus reorders. Requests, holds, submissions, acceptances, closes and reopens have their own records. The console shows one 400 in the evidence run: the expected refused drop (the browser logs every failed fetch).
