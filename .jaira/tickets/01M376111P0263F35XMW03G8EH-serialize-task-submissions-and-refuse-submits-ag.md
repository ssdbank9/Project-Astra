---
id: 01M376111P0263F35XMW03G8EH
title: Serialize task submissions and refuse submits against a changed task
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Two simultaneous submissions of one task produce exactly one submission and one event, and a submit can never overwrite a task that was cancelled, accepted or otherwise changed after the submitter loaded it."
context: |-
  What is wrong: AstraService.submit_task (src/astra/service.py:1427-1456 at 8723263) checks the task status and computes MAX(version)+1 BEFORE BEGIN IMMEDIATE.
  Its UPDATE tasks SET status='submitted' ... WHERE id=? (service.py:1450-1453) has no status or revision predicate.
  task_submissions has only a non-unique index idx_submissions_task on (task_id, version) (src/astra/db.py:232), so nothing in the database stops a duplicate version.
  Effect (a): two concurrent submits of one task both succeed - two 'submitted' rows both at version 1, two task_submitted events, revision bumped twice. Reproduced 40/40 unsynchronised runs. After one is accepted the other can never be decided.
  Effect (b): if the Owner cancels or accepts the task between submit's check and its write, submit overwrites the terminal status with 'submitted'; a later accept turns the cancelled task into 'completed' with no reopen record.
  This is real in production: web.py serves each request on its own connection under ThreadingHTTPServer (double-click, or Owner and collaborator at once).
  Found by the 2026-09-23 independent review of the codex/migration-safety-remediation branch; three reviewers reproduced it independently.
  It was listed as 'unverified' in CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.2 and is now reproduced. It pre-dates that branch.
  Sibling: SRFCZD fixed the same pattern for accept_submission; submit_task was outside its DoD.
  The HTTP submit body today carries only {note}; the UI (app.js lifecycleAction) sends no expected_revision, so a required revision would break the UI.
definition-of-done: |-
  submit_task's status check and version allocation run inside BEGIN IMMEDIATE, and its UPDATE is guarded (status not in submitted/completed/cancelled/abandoned, plus expected revision if the API carries one), raising Conflict (409) on rowcount 0.
  A two-connection barrier regression shows one success, one Conflict, one submission row and one task_submitted event.
  A regression shows a submit racing an Owner cancel is refused and the task stays cancelled.
  A new schema migration v14 adds UNIQUE(task_id, version) on task_submissions safely: it first detects existing duplicate (task_id, version) rows and refuses the migration with a clear error rather than silently deleting data (or a note explains why a unique index is too risky and only the transactional fix is kept); migration tests cover fresh v14, upgrade from v13, and rollback on injected failure.
  Full suite, node --check and git diff --check pass.
tags:
  - astra
blocked-by: []
related:
  - 01M3549XTPENM6MSYCG2SRFCZD
commits: []
created-at: 2026-09-23T13:07:06Z
updated-at: 2026-09-23T13:22:35Z
updated-by: Claude
claimed-by: vm-11750
claimed-at: 2026-09-23T13:08:02Z
outcome-what: "submit_task (src/astra/service.py) now re-reads the task inside BEGIN IMMEDIATE, refuses with Conflict (HTTP 409) when the revision changed since its permission check or the status is submitted/completed/cancelled/abandoned, allocates MAX(version)+1 under the lock, and guards its UPDATE with WHERE id=? AND revision=? AND status NOT IN (...) (Conflict on rowcount != 1). Schema v14 (src/astra/db.py _migrate_v14, SCHEMA_VERSION 14) adds UNIQUE index idx_submissions_task_version on task_submissions(task_id, version) and raises SchemaMigrationRefused, rolled back at v13 with nothing deleted, if duplicate pairs already exist. Four race regressions in tests/test_state_integrity.py, four migration tests in tests/test_db.py, README integrity paragraph. HTTP/UI contract unchanged: the submit body is still {note}."
outcome-why: "Status check and version allocation ran before BEGIN IMMEDIATE and the UPDATE had no predicate, so two overlapping submits both succeeded (two version-1 rows, two task_submitted events; 28/40 unsynchronised runs here, 40/40 for the reviewers) and a submit could overwrite an Owner cancel or acceptance with 'submitted', letting a later accept complete a cancelled task with no reopen record. Found by the 2026-09-23 independent review; listed as unverified in CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.2; pre-dates the branch."
outcome-resolves: "DoD1: the in-transaction re-read plus guarded UPDATE in submit_task, Conflict mapped to 409 by web.py _error. DoD2: test_concurrent_submissions_have_one_winner_one_row_and_one_event (one ok, one Conflict, one row, one event). DoD3: test_submit_refuses_when_the_owner_cancels_before_its_write (task stays cancelled), plus accepted-in-window and reassigned-in-window variants. DoD4: v14 unique index with duplicate refusal; fresh, v13 upgrade (schema equals fresh), duplicate refusal leaving data and v13 intact, and injected CREATE INDEX failure rollback/retry tests. DoD5: 249/249 full suite, node --check, compileall, git diff --check origin/claude/excel-import. All new race tests failed on 8723263; 10/10 loop green; mutation removing both guards fails all four."
executed-by: claude-opus-5-5
---

# Serialize task submissions and refuse submits against a changed task

## Definition of Done

- [x] submit_task's status check and version allocation run inside BEGIN IMMEDIATE, and its UPDATE is guarded (status not in submitted/completed/cancelled/abandoned, plus expected revision if the API carries one), raising Conflict (409) on rowcount 0.
  proof: src/astra/service.py submit_task (line 1428+): inside transaction() it re-reads status/revision, refuses a revision changed since the permission check or an UNSUBMITTABLE_STATUSES status with Conflict, allocates MAX(version)+1 under the lock, and runs UPDATE ... WHERE id=? AND revision=? AND status NOT IN ('submitted','completed','cancelled','abandoned') with Conflict on rowcount != 1; web.py _error maps Conflict to 409. HTTP body carries no expected_revision, so none was added (UI unchanged).
- [x] A two-connection barrier regression shows one success, one Conflict, one submission row and one task_submitted event.
  proof: tests/test_state_integrity.py test_concurrent_submissions_have_one_winner_one_row_and_one_event (two connections via _race barrier inside service.transaction): one ok, one Conflict, rows == [(1,'submitted',winner note)], 1 task_submitted event, revision +1. Failed on 8723263 (2 winners); passes now; 10/10 loop green. Unsynchronised probe: 28/40 duplicate runs before, 0/40 after.
- [x] A regression shows a submit racing an Owner cancel is refused and the task stays cancelled.
  proof: tests/test_state_integrity.py test_submit_refuses_when_the_owner_cancels_before_its_write (Owner cancel committed on another connection after submit's checks): Conflict, task stays cancelled at cancel revision, 0 submissions, 0 task_submitted. Also test_submit_refuses_when_the_task_is_submitted_and_accepted_before_its_write (stays completed, 1 accepted row) and test_submit_refuses_when_the_task_is_reassigned_away_before_its_write (revision-only change). All failed on 8723263.
- [x] A new schema migration v14 adds UNIQUE(task_id, version) on task_submissions safely: it first detects existing duplicate (task_id, version) rows and refuses the migration with a clear error rather than silently deleting data (or a note explains why a unique index is too risky and only the transactional fix is kept); migration tests cover fresh v14, upgrade from v13, and rollback on injected failure.
  proof: src/astra/db.py SCHEMA_VERSION=14, _migrate_v14: in one BEGIN IMMEDIATE, V14_DUPLICATE_SUBMISSION_VERSIONS probe raises SchemaMigrationRefused listing the pairs (nothing deleted, stays v13), else CREATE UNIQUE INDEX idx_submissions_task_version ON task_submissions(task_id, version) + user_version 14. tests/test_db.py test_fresh_v14_database_refuses_a_second_submission_at_one_version, test_v13_database_with_submissions_upgrades_to_v14_and_matches_fresh_schema, test_v13_duplicate_submission_versions_refuse_the_upgrade_without_touching_data, test_failure_creating_the_v14_index_rolls_back_to_v13_and_retries; all four fail with v14 disabled.
- [x] Full suite, node --check and git diff --check pass.
  proof: tests/run.py: Ran 249 tests in 296.610s OK (was 241); test_db+test_state_integrity 43/43; node --check src/astra/static/app.js clean; compileall clean; git diff --check origin/claude/excel-import clean.
A two-connection barrier regression shows one success, one Conflict, one submission row and one task_submitted event.
A regression shows a submit racing an Owner cancel is refused and the task stays cancelled.
A new schema migration v14 adds UNIQUE(task_id, version) on task_submissions safely: it first detects existing duplicate (task_id, version) rows and refuses the migration with a clear error rather than silently deleting data (or a note explains why a unique index is too risky and only the transactional fix is kept); migration tests cover fresh v14, upgrade from v13, and rollback on injected failure.
Full suite, node --check and git diff --check pass.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Read callers: web.py POST /api/tasks/<id>/submit and app.js lifecycleAction; confirm the body carries only {note} and no expected_revision
- [x] Write race regressions in tests/test_state_integrity.py: two-connection barrier double submit (via _race/_one_winner); Owner cancel interleaved before submit's write; Owner accept (after another submit) interleaved before submit's write
- [x] Run the new race tests against 8723263 and record that they fail
- [x] Move submit_task's re-read, status check and MAX(version)+1 inside transaction(); refuse a changed revision; guard the UPDATE on status and revision; Conflict on rowcount 0
- [x] Write migration tests in tests/test_db.py: fresh v14 has the unique index; v13 upgrade; v13 with duplicate (task_id, version) rows is refused with a clear error and stays v13 with data intact; injected CREATE INDEX failure rolls back to v13 and retries
- [x] Add migration v14 in src/astra/db.py (duplicate probe, CREATE UNIQUE INDEX, user_version 14, one BEGIN IMMEDIATE) and bump SCHEMA_VERSION
- [x] Update README integrity paragraph
- [x] Mutation: remove the in-transaction guard and confirm the race tests fail; restore
- [x] Full suite, test_db, test_state_integrity, 10x race loop, node --check, compileall, git diff --check origin/claude/excel-import

## Progress
- **2026-09-23 13:08 · Claude** — Why this shape: the HTTP submit body is {note} only and app.js sends no revision, so expected_revision is NOT added to the contract (it would break the UI). Instead submit_task follows accept_submission's SRFCZD pattern: pre-checks outside the transaction keep today's 400 ValueError for plainly stale requests; inside BEGIN IMMEDIATE the task is re-read and compared with the revision seen at the permission check, so any change in the window (cancel, accept, reassignment, edit) is a 409 Conflict. The UPDATE also carries status NOT IN (...) AND revision=? so the write itself cannot overwrite a terminal state even if the re-read were removed.
- **2026-09-23 13:21 · Claude** — Found out: (1) tests/run.py ignores its arguments and always runs the whole suite (~5 min); run single tests with 'cd tests && PYTHONPATH=../src python -m unittest test_x.Class.test_y'. (2) Mutation matrix: removing only the in-transaction re-read, or only the UPDATE predicate, keeps all four race tests green - each layer alone is sufficient (deliberate defence in depth); removing both fails all four; a status-only UPDATE predicate without re-read fails the reassignment test, which is what pins the revision guard. (3) With the unique index but the old service, the double submit's loser becomes sqlite3.IntegrityError (HTTP 500), so the index is a backstop, not the fix. (4) A sequential double-click whose second request arrives after the first commits still gets today's 400 ValueError from the pre-check; only a truly overlapping one gets 409 - same split as accept_submission. (5) Schema 14 refuses to start on a database that already has duplicate (task_id, version) rows; the Owner must pick which pending submission to keep, so nothing is auto-deleted. (6) The body text of this ticket repeats DoD items 2-5 as plain lines below the checklist: jaira create put only the first --dod line in the checklist and the rest were added with 'jaira dod --add'; tickets are not hand-edited, so the duplicate lines remain.
