---
id: 01M37EBC38J3S424MAG239DNZT
title: "Maintainability: replace the repeated migrate() version blocks with a step registry"
status: done
ready: true
creator: Claude
assignee: Claude
goal: "Migration steps are declared once in an ordered registry and run by one loop that owns the transaction, the user_version bump and fault handling."
context: |-
  Maintainability, not a demonstrated defect.
  src/astra/db.py migrate() (~74-445) is fourteen hand-written 'if version < N: with transaction(connection): ... PRAGMA user_version = N' blocks; v13 and v14 are separate functions with their own guards.
  Every step repeats the same control flow, so a step can drift (for example a user_version bump outside its transaction) and per-step fault injection needs per-step test code.
  Suggested in Codex's handoff CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 item 1; re-listed by the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Do after the per-version migration fault tests ticket, so those tests guard the refactor. Keep the resulting schema byte-for-byte equal to today's (catalog comparison).
definition-of-done: "migrate() runs steps from one ordered registry; each step's statements and user_version bump share one transaction by construction"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:32:34Z
updated-at: 2026-09-23T19:51:04Z
updated-by: Aly Jafferani
claimed-by: vm-17591
claimed-at: 2026-09-23T16:33:48Z
outcome-what: "Independent review approved"
outcome-why: "DoD met, no medium or high findings"
outcome-resolves: "review-verdict: Approve"
review-summary: "migrate() in src/astra/db.py no longer has 12 copied 'if version < N' blocks plus two steps (v13, v14) that each opened their own transaction. It now has one MIGRATION_STEPS tuple, (1,_migrate_v1) through (14,_migrate_v14), and one loop (src/astra/db.py:96-100) that opens BEGIN IMMEDIATE, runs the step, writes PRAGMA user_version = N and commits, rolling back on any error. Step functions only run their SQL. The v14 duplicate-submission check still runs once before the loop and again at the start of the v14 step. v1-v12 SQL text is byte-identical to the old code. Two tests added to tests/test_db.py: a registry contiguity test and a step-only transaction test. No existing test changed."
review-gaps: "All low severity. 1. Moving the user_version bump outside the transaction is not caught by any test on this branch; 67T315's per-step fault tests (local commit 5b16f81 on claude/wip-67T315, not on origin at review time) catch it at every step 1-12, merge cleanly and pass on top of this change. 67T315 must land for this to be regression-protected. 2. The docstring of test_migration_steps_leave_transaction_and_user_version_to_migrate overclaims: a step that commits partway then re-opens BEGIN IMMEDIATE passes it (two existing fault tests catch that), and it never calls migrate(). 3. Pre-existing: removing the in-step _refuse_duplicate_submission_versions re-probe from _migrate_v14 passes every test, on old and new code. 4. CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 item 1 (line ~573) and the list near line ~262 still describe migrate() as repetitive version blocks. 5. Proofs cite db.py:96-99; the loop runs to line 100."
review-verdict: Approve — independent reviewer
review-check: "1. cd /workspace/project-astra (or the worktree) and run: /workspace/project-astra/.venv/bin/python tests/run.py — expect 287 tests, OK (reviewer run: 287 in 290s). 2. cd tests && PYTHONPATH=../src /workspace/project-astra/.venv/bin/python -m unittest -v test_db — expect test_migration_step_registry_is_contiguous_from_one_to_schema_version and test_migration_steps_leave_transaction_and_user_version_to_migrate to pass. 3. Open src/astra/db.py around lines 96-100 and 566: see one loop and the MIGRATION_STEPS tuple, no per-version if-blocks. 4. Reviewer's old-vs-new equivalence harness (execute/commit/rollback trace proxy, start versions 0-14, faults at every Nth execute and commit, duplicate-submission cases): 784 cases, 0 mismatches; moving the bump outside the transaction produced 653 mismatches, so the harness can fail. 5. git diff --check is clean; the diff touches only src/astra/db.py, tests/test_db.py and the ticket file. There is no UI path."
---

# Maintainability: replace the repeated migrate() version blocks with a step registry

## Definition of Done

- [x] migrate() runs steps from one ordered registry; each step's statements and user_version bump share one transaction by construction
  proof: src/astra/db.py:96-99 (the only migration transaction + user_version write) and :566 MIGRATION_STEPS; test_db.MigrationTests.test_migration_steps_leave_transaction_and_user_version_to_migrate
- [x] Fresh and legacy-upgrade catalog equivalence tests and all migration fault tests pass unchanged; full suite green
  proof: tests/run.py on shared tip 01975de + this change: Ran 287 tests OK (existing test_db tests unchanged); scratch equivalence run old vs new db.py: 15 start versions (0-14) and 616 injected CREATE denials give identical user_version, sqlite_master sql, exception and retry result
- [x] A test asserts the step registry is contiguous: versions exactly 1..SCHEMA_VERSION, in order, no gaps or duplicates
  proof: test_db.MigrationTests.test_migration_step_registry_is_contiguous_from_one_to_schema_version (tests/test_db.py:106)

## Options

- [x] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] write the registry-contiguity test against db.MIGRATION_STEPS and confirm it fails (attribute missing) before the refactor
- [x] capture a pre-refactor schema_signature for fresh and each legacy start version 0..13 as a byte-equality baseline
- [x] move v1-v12 SQL into _migrate_vN step functions that only apply statements; strip transaction()/user_version from _migrate_v13/_migrate_v14
- [x] add MIGRATION_STEPS tuple and one loop in migrate() owning BEGIN IMMEDIATE, the steps, PRAGMA user_version and commit/rollback; keep the pre-flight v14 refusal before the loop
- [x] run test_db, compare signatures with the baseline, then full suite, node --check, compileall, git diff --check
- [x] rebase onto the current shared branch (and onto 67T315 fault tests if landed) and rerun

## Progress
- **2026-09-23 16:34 · Claude** — Brainstorm. What the code shows: migrate() in src/astra/db.py has twelve hand-written 'if version < N: with transaction(): _execute_statements(SQL); PRAGMA user_version = N' blocks (v1-v12) plus _migrate_v13/_migrate_v14 which open their own transaction and bump user_version inside. Nothing is broken today; the risk is drift (a bump outside its transaction, a skipped number) and that the version list is not data a test can check. Options: (A) registry of (version, callable) where every callable only applies statements and the loop owns BEGIN IMMEDIATE + PRAGMA user_version + commit/rollback -- one control path, contiguity testable; v13/v14 bodies lose their own transaction() and bump. Cost: v13/v14 docstrings must move with the ownership. (B) registry of SQL strings only for v1-v12, keep v13/v14 as special calls -- smaller diff but leaves two control paths, which is the thing the ticket wants gone. (C) generic 'migration runner' class/framework -- overkill for 14 steps in a stdlib app. Choosing A: it gives the by-construction guarantee in DoD 1 with the smallest conceptual surface; the v14 pre-flight refusal before step 1 stays in migrate() unchanged, and the in-step re-probe stays as the first statement of the v14 step, inside the loop's transaction.
- **2026-09-23 16:34 · Claude** — Plan reasoning. Registry entries are (version, step) where step(connection) only applies statements; the loop does 'with transaction(): step(c); PRAGMA user_version = N'. That makes DoD 1 structural: a step cannot bump the version or escape the transaction because it never sees either. The v14 refusal stays exactly where it is: once in migrate() before the first step (so a sub-v13 DB is refused at its starting version) and again as the first action of the v14 step (under the write lock). transaction() rolls back on SchemaMigrationRefused like any other exception, which is the current behaviour. Byte-for-byte equality is checked by comparing sqlite_master sql for fresh and every legacy start version before vs after the refactor, not only by the existing fresh-vs-upgrade test (which compares two outputs of the same new code).
- **2026-09-23 16:53 · Claude** — Done in-progress. Not in the repo: (1) The SQL inside _migrate_v1.._migrate_v12 keeps its original 16-space indentation on purpose. SQLite stores CREATE text verbatim in sqlite_master.sql, so dedenting would make a fresh v14 DB's catalog text differ from one upgraded by older builds; a first attempt that dedented was reverted for that reason. (2) Byte-equality was checked outside the suite with a throwaway script that loads the pre-refactor db.py (git show 01975de~:src/astra/db.py, i.e. the parent tip) next to the new one: it builds a DB at each start version 0-14, then for every start version 0-13 denies each of the 44 CREATEs in turn; old and new agree on exception, user_version, sqlite_master and in_transaction before and after a retry (15 + 616 cases). (3) 67T315 (per-version fault tests) was still in backlog and not on origin at 01975de, so there was nothing to rebase onto; when it lands its tests should pass unchanged because every step still runs as one BEGIN IMMEDIATE ... user_version=N ... COMMIT. (4) The v14 pre-flight probe in migrate() still runs before the loop; the in-step re-probe is now the first statement of _migrate_v14, inside the loop's transaction, so SchemaMigrationRefused still rolls back via db.transaction().
- **2026-09-23 19:12 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
