---
id: 01M377HR1EE7K43QRNTQT8WHJR
title: "Keep completed, cancelled and abandoned tasks immutable outside reopen"
status: done
ready: true
creator: Claude
assignee: Claude
goal: "A completed, cancelled or abandoned task is a fixed record that changes only through the governed reopen_task (reason plus revised due date)."
context: |-
  What is wrong: README.md ~58-65 says terminal tasks are immutable, but several write paths still change them.
  - src/astra/importer.py ~2597-2640 locks only the status; its apply UPDATE ~2814-2824 still writes title, due date, progress and criticality onto completed tasks, for both Owner and Manager.
  - src/astra/service.py set_parent (~1703) and confirm_criticality (~1727) have no terminal-status check.
  - service.py propose_schedule (~2415) and approve_schedule_proposal (~2439) let a completed task's dates change.
  - service.py add_task_dependency / remove_task_dependency (~2529-2600) have no check on the successor.
  - update_task on a closed task with no field change (only a reason) still bumps the revision and writes an event.
  Where found: the 2026-09-23 independent review of codex/migration-safety-remediation (SRFCZD gap 7).
  Decision: Aly Jafferani (App Owner) chose to block these writes rather than narrow the README (Slack, 2026-09-23 12:10 UTC, 'go with' Claude's best-practice recommendation).
  Stays allowed: attachment links and final-result mark/unmark on closed tasks (evidence often arrives after closure); adding a closed task as a predecessor of an open task.
  Out of scope: any other SRFCZD gap, UI redesign, importer follow-ups in 3NT40T.
definition-of-done: "Import: a row targeting an existing closed task is skipped with a per-row warning W_CLOSED_TASK; no field of that task changes (title, dates, progress, criticality, parent, predecessors, people, attachment links); tested for Owner and Manager."
tags:
  - astra
blocked-by: []
related:
  - 01M3549XTPENM6MSYCG2SRFCZD
commits:
  - fc2a35a
  - 754cae7
created-at: 2026-09-23T13:33:43Z
updated-at: 2026-09-23T19:50:49Z
updated-by: Aly Jafferani
claimed-by: vm-28185
claimed-at: 2026-09-23T13:34:25Z
outcome-what: "Closed (completed, cancelled, abandoned) tasks now refuse set_parent, confirm_criticality, propose_schedule, approve_schedule_proposal, dependency add/remove as successor, and any status-unchanged update_task with 400 'reopen the task first', re-checked inside the write transaction (409 when the task closes mid-flight); import rows for them are skipped whole with W_CLOSED_TASK; docs, README and matrix updated."
outcome-why: "README promised terminal tasks were immutable, but import, re-parenting, criticality, schedule approval and dependency edits still changed them; Aly chose to block rather than narrow the README (Slack 2026-09-23 12:10 UTC)."
outcome-resolves: "All six DoD items evidenced: regression tests for every rule and both roles failed on 8723263 and pass now, 13 of 14 guard mutations killed (the 14th is equivalent), race tests 10/10, full suite 249/249, node --check, compileall and git diff --check clean."
review-summary: "Shipped in fc2a35a + 754cae7 (rebased from 89e3c36 + ab24643): completed, cancelled and abandoned tasks refuse every write except the governed reopen, attachment links, final results and use as a predecessor or parent of an open task. update_task with the status unchanged, set_parent, confirm_criticality, propose/approve schedule, dependency add/remove as successor and reviewer add/remove return 400 'reopen the task first', re-checked inside the write transaction (409), and a Manager request filed against a task that changed meanwhile is 409. Import settles closed rows before cross-row checks and skips them whole with W_CLOSED_TASK, writing nothing; unchanged rows write nothing."
review-gaps: "1) The UI still shows the edit, criticality, add-predecessor and reviewer forms on closed tasks; they now return the 400 message (UI follow-up). 2) IMP-8: tests/import_fixtures.py stamps zip entries with the current time, so test_commit_refuses_a_plan_that_changed_since_the_preview flakes about 1 in 10; separate follow-up, not in this ticket. 3) Two mutants are equivalent: approve_schedule_proposal's in-transaction closed re-check (behind its revision check) and the skip block's entities=[] (behind the pass-2 skip for unchanged rows). 4) A closed import row with a duplicate key or project mismatch is still an error row. 5) Pass 2 now skips unchanged open rows too, so an unchanged legacy open task no longer gets a baseline backfilled by import."
review-verdict: "Sound; independent review plus skeptic, upheld findings fixed in 754cae7 (rebased from ab24643 onto R5 9fb4328). DoD items 1-7 hold: full suite 267/267 on the rebased branch, 25 of 27 guard mutations killed across both rounds (2 equivalent, explained in gaps), race loop 10/10, node --check, compileall and git diff --check clean."
review-check: "1. From the repo run .venv/bin/python tests/run.py; expect 'Ran 267 tests' (or more once other tickets land) and OK. 2. Start the fixture: .venv/bin/python tests/ui_fixture_server.py and open http://127.0.0.1:8766 . 3. Sign in as the fixture Owner, open a task, submit and accept it so it is Completed. 4. In the task, try Confirm criticality with a reason: expect the red message 'A completed task is a fixed record; reopen the task first.' 5. Try Add predecessor and Save changes (with only a reason): expect the same kind of message, and History shows no new entry. 6. Link an attachment: it is added (evidence is still allowed). 7. Reopen the task with a reason and a new due date, then Confirm criticality again: it now succeeds. 8. Import a file whose row for the completed task changes its title: the preview row shows the stored title with the warning 'This task is completed, a fixed record, so none of this row's changes were applied'. 9. Stop the server."
---

# Keep completed, cancelled and abandoned tasks immutable outside reopen

## Definition of Done

- [x] Import: a row targeting an existing closed task is skipped with a per-row warning W_CLOSED_TASK; no field of that task changes (title, dates, progress, criticality, parent, predecessors, people, attachment links); tested for Owner and Manager.
  proof: fc2a35a + 754cae7: importer.py _settle_closed runs right after _validate_row (stored parent, no dependency edges, own cell errors -> info), _finish_row skips with W_CLOSED_TASK and drops W_TITLE_CHANGED/W_LAG_IGNORED/W_PARENT_DEPTH/W_PERSON_BY_NAME/I_BASELINE_KEPT, preview and report show the stored task, unchanged rows skip pass 2, filed entities are no change. tests/test_import.py test_import_row_for_a_closed_task_is_skipped_for_either_role (Owner + Manager, every column incl. Entity, Original Due Date, x_ custom, Notes; raw DB row, reviewers, links, deps, events and project entities identical; report CSV shows stored title), test_closed_row_neither_forms_false_cycles_nor_poisons_other_rows, test_import_commit_refuses_when_the_task_closed_after_the_preview; failing before, passing after; 7 of 8 import mutations killed (entities=[] is equivalent behind the pass-2 skip).
- [x] set_parent (closed child), confirm_criticality, propose_schedule and approve_schedule_proposal on a closed task, and add_task_dependency / remove_task_dependency with a closed successor are refused with ValueError (400) 'reopen the task first'; the check re-reads status inside the write transaction and a task that closes between pre-check and write is refused (Conflict 409) with a two-connection race test; a closed task may still be added as a predecessor of an open task.
  proof: fc2a35a + 754cae7: service.py _refuse_closed/_refuse_closed_in_transaction in set_parent, confirm_criticality, propose_schedule, approve_schedule_proposal, add/remove_task_dependency; _request_protected_action re-checks the task revision under the write lock (Manager request racing a closure -> 409, no request). Race tests close by cancel AND by acceptance; test_schedule_approval_refuses_when_the_task_closes_before_its_write covers Owner and Manager (Manager cases failed before). approve's in-transaction closed re-check kept as commented defence in depth (equivalent mutant behind its revision check). Race loop 10/10.
- [x] Attachment links and final-result mark/unmark stay allowed on closed tasks; tested.
  proof: tests/test_state_integrity.py test_closed_task_may_be_a_predecessor_and_still_takes_evidence: Owner and Manager add/remove a closed predecessor of an open task, Owner links/removes an attachment and marks/unmarks a final result on a completed task, revision unchanged; test_closed_task_writes_work_again_after_the_governed_reopen.
- [x] update_task on a closed task that changes nothing (only a reason) does not bump the revision or write an event; tested.
  proof: Chose REFUSE (smaller change: dropped the any(field changed) clause, so update_task with unchanged status on a closed task always raises ValueError 'reopen the task first'). test_update_task_on_a_closed_task_with_no_change_writes_nothing (reason-only, same title, empty payload x 3 statuses) failed 9 subtests before, passes after; restoring the old clause fails 9.
- [x] Import design doc (docs/design/excel-import.md) and README integrity paragraph updated (and the authorization matrix where a row changes).
  proof: README.md, docs/design/authorization-matrix.md and docs/design/excel-import.md (Closed tasks section rewritten, commit paragraph) cover the reviewer rule, the request 409, the open-child-under-closed-parent exception, cell errors as info, no false cycles, unchanged rows write nothing.
- [x] Full suite (tests/run.py), node --check src/astra/static/app.js, compileall and git diff --check pass.
  proof: On the branch after 754cae7 (rebased onto R5 9fb4328): tests/run.py Ran 267 tests OK (282.3s); node --check src/astra/static/app.js, compileall src tests, git diff --check origin/claude/excel-import clean; race loop 10/10.
- [x] Collaborators, reviewers and approvers of a closed task cannot be added or removed (add_task_reviewer / remove_task_reviewer refused 400 before and 409 inside the write transaction); tested for Owner and Manager and by race.
  proof: 754cae7 src/astra/service.py add_task_reviewer/remove_task_reviewer: _refuse_closed + transaction with _refuse_closed_in_transaction. tests/test_state_integrity.py structural test (12 new subtests, 3 statuses x Owner/Manager) and test_writes_refuse_when_the_task_closes_before_their_write (cancel and accept closers) failed 16 subtests before, pass after; all four guard mutations killed.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Write failing regression tests for each rule (service, import, race) and confirm they fail on 8723263
  proof: 8 new tests; 49 failures + 4 errors across the new state/import tests on 8723263, plus the import 409 test
- [x] Implement in-transaction guards in service.py and the importer skip with W_CLOSED_TASK
  proof: service.py _refuse_closed/_refuse_closed_in_transaction; importer.py W_CLOSED_TASK
- [x] Update docs, README, matrix and app.js warning text
  proof: README.md, docs/design/excel-import.md, docs/design/authorization-matrix.md; app.js shows finding.message so needs no mapping
- [x] Mutation-test each guard, run full suite, node --check, compileall, diff --check, race loop x10
  proof: 14 mutations, 13 killed, 1 equivalent (approve in-transaction re-check); full suite 249 OK; race loop 10/10
- [x] R1: fix the upheld review findings SVC-1..4 and IMP-1..7 test first
  proof: 754cae7; failing-before outputs recorded; 12 of 13 new mutations killed, 1 equivalent

## Progress
- **2026-09-23 13:56 · Claude** — Doing: T8WHJR in worktree claude/closed-immutable-wip from 8723263 (not pushed).
Found: on 8723263 import applied title/dates/progress/criticality/parent/predecessors/people/links to closed tasks; set_parent, confirm_criticality, propose_schedule, approve_schedule_proposal and dependency add/remove had no closed check; a reason-only update_task bumped revision and wrote task_updated.
Chosen: rule 4 refuses (ValueError 400) instead of a no-op, because it is the smaller change and the UI full-form save on a closed task was already refused whenever progress or dates were sent.
Found: approve_schedule_proposal's in-transaction closed re-check is an equivalent mutant; its existing revision check refuses a mid-flight closure first.
Found: test_import.test_commit_refuses_a_plan_that_changed_since_the_preview is flaky (1 in 10 loop runs, once in a module run): tests/import_fixtures.py writestr stamps the zip entries with the current time, so two filled_template calls can hash differently. Pre-existing, not touched here.
Not blocked: add_task_reviewer on a closed task, set_parent that puts an OPEN child under a closed parent, reject_schedule_proposal; the UI still shows the criticality, dependency and edit forms on closed tasks, and they now return the 400 message.
Next: independent review; then Aly signoff.
- **2026-09-23 14:36 · Claude** — Independent review of 89e3c36 (skeptic on every finding) upheld SVC-1..4 and IMP-1..7; fixed test-first in ab24643.
SVC-1: add/remove_task_reviewer now refused on closed tasks (pre-check 400, in-transaction 409); an approver added after closure could otherwise file a reopen request.
SVC-2: chose the revision re-check inside _request_protected_action's transaction (smaller than per-action closure checks, covers every protected request); a Manager request racing a closure is 409, no queued request.
SVC-4: races now close by cancel and by acceptance; kept approve_schedule_proposal's in-transaction closed re-check with a defence-in-depth comment (equivalent mutant behind its revision check).
SVC-3: open child under/out of a closed parent stays allowed; documented in README, matrix, import doc.
IMP-1/2: _settle_closed runs right after _validate_row: stored parent, no edges, own cell errors -> info. Duplicate key / project mismatch still errors.
IMP-3: pass 2 skips every unchanged row (this also stops _ensure_baseline backfilling unchanged open rows; full suite green).
IMP-4: already-filed entities are no change for any row. IMP-5: five contradictory findings dropped on closed rows. IMP-6: test covers Entity, Original Due Date, x_ column, Notes, raw DB row, project entities, preview values, report CSV. The entities=[] mutant is now equivalent (pass-2 skip already prevents the write); combined with the pass-2 mutant the test fails.
Not done here: IMP-8 zip-timestamp flake in tests/import_fixtures.py (separate follow-up); UI still shows edit, criticality, dependency and reviewer forms on closed tasks.
Next: Aly signoff.
- **2026-09-23 19:10 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
