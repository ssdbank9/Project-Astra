---
id: 01M377HR1EE7K43QRNTQT8WHJR
title: "Keep completed, cancelled and abandoned tasks immutable outside reopen"
status: review
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
commits: []
created-at: 2026-09-23T13:33:43Z
updated-at: 2026-09-23T13:56:36Z
updated-by: Claude
claimed-by: vm-28185
claimed-at: 2026-09-23T13:34:25Z
outcome-what: "Closed (completed, cancelled, abandoned) tasks now refuse set_parent, confirm_criticality, propose_schedule, approve_schedule_proposal, dependency add/remove as successor, and any status-unchanged update_task with 400 'reopen the task first', re-checked inside the write transaction (409 when the task closes mid-flight); import rows for them are skipped whole with W_CLOSED_TASK; docs, README and matrix updated."
outcome-why: "README promised terminal tasks were immutable, but import, re-parenting, criticality, schedule approval and dependency edits still changed them; Aly chose to block rather than narrow the README (Slack 2026-09-23 12:10 UTC)."
outcome-resolves: "All six DoD items evidenced: regression tests for every rule and both roles failed on 8723263 and pass now, 13 of 14 guard mutations killed (the 14th is equivalent), race tests 10/10, full suite 249/249, node --check, compileall and git diff --check clean."
---

# Keep completed, cancelled and abandoned tasks immutable outside reopen

## Definition of Done

- [x] Import: a row targeting an existing closed task is skipped with a per-row warning W_CLOSED_TASK; no field of that task changes (title, dates, progress, criticality, parent, predecessors, people, attachment links); tested for Owner and Manager.
  proof: src/astra/importer.py _finish_row: touched row on a CLOSED task gets W_CLOSED_TASK, plan emptied (fields, people, attachments, predecessors, parent, baseline, entities, criticality), action unchanged, values show stored task; commit re-validates inside BEGIN IMMEDIATE. tests/test_import.py test_import_row_for_a_closed_task_is_skipped_for_either_role (Owner + Manager, completed/cancelled/abandoned, every field) and test_import_commit_refuses_when_the_task_closed_after_the_preview (409) failed before, pass after; removing the skip fails both.
- [x] set_parent (closed child), confirm_criticality, propose_schedule and approve_schedule_proposal on a closed task, and add_task_dependency / remove_task_dependency with a closed successor are refused with ValueError (400) 'reopen the task first'; the check re-reads status inside the write transaction and a task that closes between pre-check and write is refused (Conflict 409) with a two-connection race test; a closed task may still be added as a predecessor of an open task.
  proof: src/astra/service.py _refuse_closed (ValueError 400) + _refuse_closed_in_transaction (Conflict 409) in set_parent, confirm_criticality, propose_schedule, approve_schedule_proposal (before the Manager request branch), add/remove_task_dependency (successor only). tests/test_state_integrity.py test_closed_task_refuses_structural_and_schedule_writes_until_reopened (3 statuses x Owner/Manager x 6 writes, asserts plain ValueError, no request) and test_writes_refuse_when_the_task_is_cancelled_before_their_write (two-connection interleave, 5 writes) failed before (33+5 subtests), pass after; each pre-check and in-transaction mutation killed except approve's in-transaction re-check (equivalent: its revision check already refuses, test_schedule_approval_refuses_when_the_task_is_cancelled_before_its_write); race tests 10/10.
- [x] Attachment links and final-result mark/unmark stay allowed on closed tasks; tested.
  proof: tests/test_state_integrity.py test_closed_task_may_be_a_predecessor_and_still_takes_evidence: Owner and Manager add/remove a closed predecessor of an open task, Owner links/removes an attachment and marks/unmarks a final result on a completed task, revision unchanged; test_closed_task_writes_work_again_after_the_governed_reopen.
- [x] update_task on a closed task that changes nothing (only a reason) does not bump the revision or write an event; tested.
  proof: Chose REFUSE (smaller change: dropped the any(field changed) clause, so update_task with unchanged status on a closed task always raises ValueError 'reopen the task first'). test_update_task_on_a_closed_task_with_no_change_writes_nothing (reason-only, same title, empty payload x 3 statuses) failed 9 subtests before, passes after; restoring the old clause fails 9.
- [x] Import design doc (docs/design/excel-import.md) and README integrity paragraph updated (and the authorization matrix where a row changes).
  proof: docs/design/excel-import.md: new 'Closed tasks (W_CLOSED_TASK)' section, Status row, Manager warnings list and commit paragraph; README.md integrity paragraph lists the refused writes and allowed evidence; docs/design/authorization-matrix.md new closed-task row. app.js renders finding messages, not codes, so no UI change was needed.
- [x] Full suite (tests/run.py), node --check src/astra/static/app.js, compileall and git diff --check pass.
  proof: tests/run.py: Ran 249 tests OK (266.9s); node --check src/astra/static/app.js, compileall src tests, git diff --check origin/claude/excel-import all clean.

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

## Progress
- **2026-09-23 13:56 · Claude** — Doing: T8WHJR in worktree claude/closed-immutable-wip from 8723263 (not pushed).
Found: on 8723263 import applied title/dates/progress/criticality/parent/predecessors/people/links to closed tasks; set_parent, confirm_criticality, propose_schedule, approve_schedule_proposal and dependency add/remove had no closed check; a reason-only update_task bumped revision and wrote task_updated.
Chosen: rule 4 refuses (ValueError 400) instead of a no-op, because it is the smaller change and the UI full-form save on a closed task was already refused whenever progress or dates were sent.
Found: approve_schedule_proposal's in-transaction closed re-check is an equivalent mutant; its existing revision check refuses a mid-flight closure first.
Found: test_import.test_commit_refuses_a_plan_that_changed_since_the_preview is flaky (1 in 10 loop runs, once in a module run): tests/import_fixtures.py writestr stamps the zip entries with the current time, so two filled_template calls can hash differently. Pre-existing, not touched here.
Not blocked: add_task_reviewer on a closed task, set_parent that puts an OPEN child under a closed parent, reject_schedule_proposal; the UI still shows the criticality, dependency and edit forms on closed tasks, and they now return the 400 message.
Next: independent review; then Aly signoff.
