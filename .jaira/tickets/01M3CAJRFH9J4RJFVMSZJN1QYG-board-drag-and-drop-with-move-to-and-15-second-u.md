---
id: 01M3CAJRFH9J4RJFVMSZJN1QYG
title: Board drag and drop with Move to and 15-second Undo
status: signoff
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
updated-at: 2026-09-26T02:27:46Z
updated-by: Claude
claimed-by: vm-1562
claimed-at: 2026-09-25T13:03:12Z
outcome-what: "The project board is now movable by owners and the project's managers. Drag within a column to reorder it (tasks.board_rank, schema v18). Drag across columns to change status through today's server rules (Blocked = hold dialog, Submitted/Accepted confirm, Closed and reopen ask for reasons, a manager's protected drops file Owner requests). Waiting-on-predecessor cards cannot go forward, and only an owner may override (dependency_override). Refusals are audited as board_move_blocked. Every card has a Move to menu for the keyboard and phones. Ordinary moves and reorders show a 15-second Undo, which is a new audited change. Also: Aly's 2026-09-25 decision lets a project manager put work on hold directly."
outcome-why: "Aly's lock #12 (Slack ts 1790341004.453539) asked for board drag and drop, Move to and Undo under the JQY55P 2026-09-19 owner decisions. The manager-hold change is Aly's decision of Slack ts 1790342529.695749."
outcome-resolves: "Ticket A of lock #12: board drag and drop, Move to, 15-second Undo, and the manager on-hold rule."
review-summary: "Reviews 12a-12e (2026-09-25) of a2161a0, 55ddf3c and 89e9229. The project board gains governed drag and drop (pointer events for mouse, pen and touch; phones never drag), a Move to menu for keyboard and phones, a persisted column order (schema v18 tasks.board_rank; a reorder renumbers the whole column) and a 15-second Undo for ordinary moves among Draft, Ready and In progress. A drop runs the action that already governs the target status (hold, submit, accept, close, reopen), so role limits, reasons and a manager's Owner requests are unchanged; a project manager puts work on hold directly with a reason (Aly, ts 1790342529.695749). Undo is keyed by a move_kind mark on the event, never the reason text, and is refused once the task changed or 20 seconds passed. The dependency rule holds on every path (board, panel, API, submit, accept, and approving a request): anyone but an owner is refused, an owner confirms and dependency_override is written in the same transaction. Only permission and rule refusals are audited as board_move_blocked and noticed under the cap. Review 12d M2: an approval re-runs the dependency, WIP and date rules at decision time and the owner confirms each; the Inbox and Home request cards show what approving would override."
review-gaps: "Left for later: three revert experiments no test catches (review 12e L1): dropping the board-source-status check in undo_move, dropping the per-row revision check inside _write_bulk, and showing members the bulk checkboxes. Not tried on a real touch device (tablet long press, Playwright emulation only), no screen-reader run, and no live refresh (lock chips, banners and Inbox gate lines show the last load; the server rechecks at write and decision time). Review 12c I3: bulk assign, like the panel, accepts the chairman and project viewers; ask Aly whether viewers should be assignable. The Blocked WIP exemption: a card that enters Blocked because of a dependency is not refused, so a Blocked limit can be exceeded by an added link or a reopened predecessor. A manager's accept request on a waiting task is filed and the owner is asked at decision time (not refused at filing). An owner's own board Undo passes the dependency override itself (12d I1); the importer and templates bypass the WIP and dependency gates (owner-only, 12d I2)."
review-verdict: "approve with follow-ups: reviews 12a, 12b, 12c and re-review 12d each approved with follow-ups (no High); every finding fixed in 55ddf3cba30d4ce1cfe34603f25413aa9f32eb0a and 89e92295337e0edf7016e1fb1b2a85aeb0cae825; review 12e of 89e9229 approves (0 High, 0 Medium, 1 Low: three uncaught revert experiments, left as follow-ups); Ran 639 tests, OK"
review-check: "1. Linux or macOS, repo root: .venv/bin/python tests/run.py (Windows: .venv\\Scripts\\python.exe tests\\run.py); expect 'Ran 639 tests' and 'OK'. 2. Start Astra, sign in as a project manager, open Projects > a project > Board. 3. Drag a Draft card to Ready: it moves and a toast offers Undo for 15 seconds; press Undo: it goes back. 4. Drag a card that shows 'Waits on …' to In progress: it snaps back with 'Only an owner may override a dependency'. 5. On a card press Move to…, then use the arrow keys and Enter: the card moves without a mouse. 6. Sign in as the owner and drag the same waiting card: 'Override dependency' asks first; confirm and the task History shows dependency_override. 7. As the manager, ask to move an on-hold task back to In progress; as the owner open Inbox > Needs action: the card says 'Approving overrides: …' when a rule applies, and Approve asks you to confirm it."
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
- **2026-09-25 16:03 · Claude** — Review 12a fix set: the dependency rule now holds on every path (the _dependency_gate helper runs in update_task, submit_task and accept_submission, inside the write). Other 12a fixes: Undo keys off move_kind (not the reason text); the board revision is compared inside hold, submit, accept and reopen; reorders renumber the whole column; only permission and rule refusals are audited; aria-expanded on the menu opener is fixed; the touchmove listener is attached only during a drag; 'Put on hold…' shows for dependency-blocked cards; there is a lane hint. Tests changed: test_state_integrity _closed_fixture, close-race test and _closers now pass override_dependencies for the owner.
- **2026-09-25 17:27 · Claude** — Re-review 12d M2: an owner's approval no longer counts as the dependency override by itself. decide_owner_action_request runs the action's own gates at decision time (the owner_decision exemption is gone from _dependency_gate, _wip_entry_gate and _date_impact_gate) and answers NeedsConfirmation; the Inbox sends override_dependencies / override_wip / confirmed on the decision and the override is recorded in the deciding owner's name. list_owner_action_requests adds gates {lines, column} per pending request for the card. Kept as before: a manager's accept_submission still files the request while the task waits (the owner is asked at decision time); the coordinator asked for the confirm, not a refusal at filing.
- **2026-09-26 02:27 · Claude** — Lock #13 (2026-09-26): review 12e L1 test gaps closed in a test-only commit. test_board Review12eTests.test_undo_is_refused_for_every_status_the_board_never_undoes pins the undo source-status check for changes_requested, on_hold, submitted and reopened. The earlier test was already caught: review 12e's revert experiment left a dangling line continuation (a SyntaxError), so unittest crashed on import and its harness saw no FAIL line. Verified: removing the check cleanly fails both tests.
