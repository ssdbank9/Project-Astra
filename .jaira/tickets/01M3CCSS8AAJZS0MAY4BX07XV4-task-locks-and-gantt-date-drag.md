---
id: 01M3CCSS8AAJZS0MAY4BX07XV4
title: Task locks and Gantt date drag
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "Only one person changes a task at a time: dragging or editing takes a short renewable lease that others see and owners may force-unlock. Owners and managers change start and due dates by dragging or resizing Gantt bars, with a live date preview, Undo for ordinary moves and an impact confirm that notifies the other owners."
context: |-
  What is wrong today (after JN1QYG, a2161a0):
  - Two people can edit the same task at once. The second save fails on expected_revision, after the work is lost.
  - Nobody can see that someone else is changing a task.
  - The Gantt (#/project/<id>/timeline, app.js renderGantt) is read-only. Dates change only in the task panel.
  Trigger: Aly's lock #12 (Slack ts 1790341004.453539, 2026-09-25), item B.
  Governing rules: JQY55P Progress notes of 2026-09-19 (multi-user locks, lock expiry, Gantt dragging, notifications, touch). 'App Owner' means any active owner (Aly ts 1790277044.283429). Keep it lean.
  Known: owners and managers already change dates through update_task with a reason. There are no milestones in the schema, so the project target date stands in. The critical path is computed in list_tasks (is_critical_path).
  Plan: session file lock12-plan.md, decisions 5 and 6.
  Not here: bulk locks and WIP limits (ticket C), downstream shifting, dependency connector dragging, what-if mode.
definition-of-done: "Server: task_locks table (schema v19, migration with tests); acquire, renew, release and owner force-unlock (audited as task_lock_forced, holder notified); every task write refuses with 409 naming the holder and expiry while someone else holds an unexpired lease; leases expire after 60 s"
tags:
  - astra
blocked-by: []
related:
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M3CAJRFH9J4RJFVMSZJN1QYG
  - 01M3BSY3W3FH34MF87RACR121Z
  - 01M3C0MZ2TASFSNYRN1E3C1Z74
commits: []
created-at: 2026-09-25T13:41:41Z
updated-at: 2026-09-25T17:47:12Z
updated-by: Claude
claimed-by: vm-32647
claimed-at: 2026-09-25T13:41:59Z
outcome-what: "Tasks now take renewable 60-second leases (task_locks, schema v19). Board and Gantt drags take a drag lease and the panel's Edit form an edit lease; they renew every 20 s while in use and are released on drop, save or close. Every task write checks the lease inside its write transaction (_event guard) and refuses with a 409 naming the holder and expiry. Cards show a lock chip, the panel a banner, and owners may Force unlock (task_lock_forced, holder noticed). Gantt bars can be dragged or resized by owners and managers, with a live date tip. Ordinary moves have a 15 s Undo (undo_move, generalised from the board). Moves that break a dependency, touch the critical path or pass the project target confirm first and notify the other owners (schedule_impact_confirmed). Invalid dates are refused and audited (gantt_move_blocked)."
outcome-why: "Aly's lock #12 (Slack ts 1790341004.453539), item B, under the JQY55P 2026-09-19 decisions on multi-user locks, lock expiry and Gantt dragging."
outcome-resolves: "Ticket B of lock #12: task locks and Gantt date drag."
review-summary: "Reviews 12b, 12d and 12e (2026-09-25) of 34eeca1, 55ddf3c and 89e9229. Task locks are 60-second leases (schema v19 task_locks): a board or Gantt drag takes a drag lease and typing in the panel's Edit form an edit lease, renewed every 20 seconds and released on drop, cancel, save or close (an idle form lets go after a minute). While someone else holds one, every task write is refused with 409 naming the holder and the local expiry time; the check sits in _event inside the write transaction and now also covers reviewer changes (reviewer_added and reviewer_removed are task events), links from a locked predecessor and board reorders. An expired lease cannot be renewed; a drag borrows your own edit lease; any owner can force unlock (task_lock_forced, holder told). The Gantt gains bar drag and resize with a live tip; the server validates the dates, applies ordinary moves with a 15-second Undo (move_kind gantt) and asks first when a move breaks a finish-to-start link, touches the critical path or passes the project target, writing schedule_impact_confirmed in the same transaction. That date rule now holds on every path: panel, API, reopen with a revised due date and approving a schedule proposal (12d L1). A successor may start on its predecessor's due day. A drag loads the project once (12d M1)."
review-gaps: "Left for later: three revert experiments no test catches (review 12e L1): dropping the board-source-status check in undo_move, dropping the per-row revision check inside _write_bulk, and showing members the bulk checkboxes. Not tried on a real touch device (tablet long press, Playwright emulation only), no screen-reader run, and no live refresh (lock chips, banners and Inbox gate lines show the last load; the server rechecks at write and decision time). Review 12c I3: bulk assign, like the panel, accepts the chairman and project viewers; ask Aly whether viewers should be assignable. The Blocked WIP exemption: a card that enters Blocked because of a dependency is not refused, so a Blocked limit can be exceeded by an added link or a reopened predecessor. A manager's accept request on a waiting task is filed and the owner is asked at decision time (not refused at filing). An owner's own board Undo passes the dependency override itself (12d I1); the importer and templates bypass the WIP and dependency gates (owner-only, 12d I2)."
review-verdict: "approve with follow-ups: reviews 12a, 12b, 12c and re-review 12d each approved with follow-ups (no High); every finding fixed in 55ddf3cba30d4ce1cfe34603f25413aa9f32eb0a and 89e92295337e0edf7016e1fb1b2a85aeb0cae825; review 12e of 89e9229 approves (0 High, 0 Medium, 1 Low: three uncaught revert experiments, left as follow-ups); Ran 639 tests, OK"
review-check: "1. Repo root: .venv/bin/python tests/run.py (Windows: .venv\\Scripts\\python.exe tests\\run.py); expect 'Ran 639 tests' and 'OK'. 2. Sign in as a manager in one browser and open a task's Edit form, then type in the title. 3. Sign in as the owner in a second browser (private window) and drag the same card on the Board: it snaps back with 'is in use. <manager> is changing this task … until <local time>'. 4. Open that task as the owner: an amber banner names the holder; press Force unlock and give a reason: the manager is told. 5. Open the project's Timeline and drag a bar a few days right: the tip shows the new dates and a toast offers Undo. 6. Drag a bar's right end past the project target: 'Confirm the new dates' lists the consequence; confirm, and task History shows schedule_impact_confirmed. 7. Reopen a completed task with a due date past the target: the same confirm appears."
---

# Task locks and Gantt date drag

## Definition of Done

- [x] Server: task_locks table (schema v19, migration with tests); acquire, renew (only a live lease) and release, and owner force-unlock (audited as task_lock_forced, holder notified); while someone else holds an unexpired lease, every task write refuses with 409 naming the holder and expiry, including reviewer changes (reviewer_added/reviewer_removed events), links from a locked predecessor and board reorders; leases expire after 60 s
  proof: db.py:771 _migrate_v19 + test_db TaskLockMigrationTests; service.py:2580 acquire/renew/release, :2627 force_unlock_task (task_lock_forced, holder noticed), _event guard :2574; test_board TaskLockTests (8) incl. test_every_write_path_revalidates_the_lock and the 60 s expiry test
- [x] Gantt: owners and managers drag a bar to move it and drag its ends to change start or due, with a live date tip; members, viewers and phones cannot drag (the task panel date fields stay); invalid dates are refused with a reason; ordinary moves apply with a 15-second Undo; a move that breaks a dependency, touches the critical path or passes the project target opens an impact confirm, and the confirmed move notifies the other owners
  proof: service.py:2676 reschedule_task + :2649 _schedule_impact; app.js:1050 Gantt drag and grips (no data-drag for members/viewers, closed or undated tasks, phones, touch); test_board GanttRescheduleTests (5); test_web AstraGanttDragDriverTests; lock12-shots b02 (live tip), b03/b04 (Undo), b05/b06 (impact confirm and notice), b13 (phone, no grips)
- [x] Lock UI: the task panel takes an edit lease while its form is in use and shows who holds a lease and until when; board cards show a lock chip; board and Gantt drags take a drag lease; owners get Force unlock
  proof: app.js:985 wireEditLease, :951 takeLease (board startDrag and Gantt drag take drag leases), lockBanner/lock chip, Force unlock; lock12-shots b07 (manager editing), b08 (lock chip), b09 (drag refused), b10/b11/b12 (banner, force unlock), b14 (phone banner)
- [x] Behaviour tests (service, web, migration, node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Playwright evidence at 1440 and 390 of a Gantt drag with Undo and a lock conflict between two sessions, without CSP errors; README updated
  proof: full suite 564 OK (tests/run.py, 283 s); git diff --check clean; 0 CR; node --check app.js; jaira validate 0 errors; Playwright lock12-shots b01-b14 at 1440 and 390 with two sessions, 0 CSP errors; README

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v19 task_locks(task_id PK, holder_user_id, kind drag|edit|bulk, token, acquired_at, expires_at); migration test
  proof: src/astra/db.py:771 _migrate_v19; tests/test_db.py:1294 TaskLockMigrationTests
- [x] service: acquire/renew/release/force_unlock_task; TaskLocked(Conflict); the guard sits in _event for every task-changing event kind, inside the write transaction, so every write path is covered and the final write revalidates; tasks carry lock {holder, kind, expires_at}
  proof: service.py:2574 _assert_task_unlocked (called from _event for LOCK_GUARDED_KINDS), :2580 acquire_task_lock, :2627 force_unlock_task; tests/test_board.py:180 TaskLockTests
- [x] service.reschedule_task: validate dates, impact (FS dependency violated either way, critical path, past the project target) as NeedsConfirmation; apply through update_task with reason 'Gantt drag: …'; confirmed impact writes schedule_impact_confirmed (owners notified); undo_move generalised from undo_board_move
  proof: service.py:2649 _schedule_impact, :2676 reschedule_task, :2497 undo_move; tests/test_board.py:289 GanttRescheduleTests
- [x] web routes: POST /api/tasks/<id>/lock, /lock/renew, /lock/release, /lock/force, /reschedule, /undo-move; 409 carries lock
  proof: src/astra/web.py lock/reschedule/undo-move routes, TaskLocked 409 with lock; tests/test_web.py:1858 test_locks_and_gantt_reschedule_over_http
- [x] app.js: Gantt bar drag and resize (pointer events, live tip, CSSOM transform), impact dialog, Undo; board drag takes a drag lease; panel edit lease with 20 s renew; lock chip and banner; Force unlock
  proof: app.js:951 takeLease, :985 wireEditLease, :1027 rescheduleTask, :1050 Gantt pointer drag; tests/test_web.py:2888 AstraGanttDragDriverTests
- [x] Tests and evidence; README
  proof: tests/test_board.py TaskLockTests, GanttRescheduleTests; test_web AstraGanttDragDriverTests; lock12-shots b01-b14; README locks + Gantt drag + schema 19

## Progress
- **2026-09-25 13:42 · Claude** — Why the lock guard sits in _event and not at the top of each write method: every task-changing path already writes exactly one task event inside its own BEGIN IMMEDIATE transaction. A check there is race-free (it runs under the write lock), covers all about twenty write paths at once, and makes a refused write roll back the row change it follows. Audit-only kinds (task_created, protected_action_blocked, board_move_blocked, task_lock_forced, the lock events themselves) are not guarded. The guard is holder-based: the lease holder's own writes pass, whatever tab they come from. An owner approving a request on a locked task also gets the 409, which is what 'others cannot modify it' means; the owner can force-unlock. Board reorder writes ranks only, with no task event, so it is not lock-checked (noted as a gap).
- **2026-09-25 14:00 · Claude** — Found out while building it: the app has no live refresh. Another person's lock chip and banner appear when the board or panel loads, not the moment the lease is taken. The refusal (409 naming the holder) is what always tells the truth at write time. Lease timestamps are compared as ISO strings from datetime.now(timezone.utc).isoformat(), the same format now_text() writes. Phones default the Timeline to the schedule table; in the chart, phones get no data-drag and no grips. A touch pointer never starts a bar drag at any width, so tablets use the panel date fields. The critical-path impact counts only when a date of that task changes. A dependency impact counts only when this task's relevant date changed, so an old overlap the move leaves alone does not ask again. Undo was generalised: undo_board_move became undo_move, keyed by the reason prefix ('Board move: ' restores status, 'Gantt drag: ' restores start and due), and /board-undo became /undo-move. Neither is pushed yet.
- **2026-09-25 14:00 · Claude** — Gaps left on purpose (lean): board reorder writes ranks only, with no task event, so it does not check locks. Adding or removing reviewers writes no task event, so it is not lock-guarded either. Leases are per person, not per tab: the holder's second tab passes. The release on tab close relies on the 60 s expiry (sendBeacon cannot carry the CSRF header).
- **2026-09-25 15:40 · Claude** — Review 12b fix set (not yet committed): the gaps noted earlier are closed. Reviewer add and remove now write reviewer_added and reviewer_removed events, which are lock-guarded and shown only to managers. add_task_dependency and remove_task_dependency check the predecessor's lease. reorder_board checks every id. A renew needs a live lease. Gantt Undo relies on move_kind='gantt'. The date-impact confirm now runs in update_task on every path. DoD item 1 has been reworded to match.
- **2026-09-25 17:27 · Claude** — Re-review 12d L1: reopen_task (revised due date) and approve_schedule_proposal now run _date_impact_gate inside their transaction, with confirmed (also on /reopen, /schedule-proposals/<id>/approve, the board's reopen drop and the owner-request decision). The Gantt passes its own impact reading down to update_task (known_impact), so a drag loads the project once. The 15:40 note's 'not yet committed' work landed in 34eeca1.
