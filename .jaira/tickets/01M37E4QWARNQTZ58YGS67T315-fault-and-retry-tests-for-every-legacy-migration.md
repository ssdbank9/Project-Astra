---
id: 01M37E4QWARNQTZ58YGS67T315
title: Fault and retry tests for every legacy migration step v1-v12
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Every migration step 1-12 in src/astra/db.py has a committed test that injects a failure mid-step, re-reads user_version and the schema, and proves the step rolled back and the retry reaches the fresh schema."
context: |-
  What is wrong: A836XC made migration steps 1-12 atomic, but the committed fault tests in tests/test_db.py cover only v1, v5 and v12.
  Putting executescript() back into v2, v3, v4 or v6-v11, or moving the v3 or v8 'PRAGMA user_version' bump outside its transaction, leaves tests.test_db green (A836XC review gap 1).
  The behaviour itself was verified by hand during that review (148 injected faults and 26 hard kills, all rolled back and retried to a catalog identical to fresh); what is missing is a committed test that fails when it regresses.
  Found in the A836XC review and carried into the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Overlap, do not duplicate: ticket T81ZV6 on branch claude/review-report-2026-09-22 ('Schema migrations are not atomic: executescript() commits the BEGIN IMMEDIATE', lane todo) covers re-reading user_version inside the lock, a two-connection concurrent-migration test, and completing databases half-applied by the old code. Its atomicity work is already done here by A836XC. It does not cover per-version fault tests. Reconcile T81ZV6 when that branch is merged.
  Also seen: four tests in tests/test_db.py leave SQLite handles open when an assertion fails (A836XC gap 4); fix with addCleanup while in the file.
definition-of-done: "tests/test_db.py has a parameterised test that, for each version N in 1-12, starts from a database at N-1, injects a failure after the step's first statement, and asserts user_version is still N-1 and sqlite_master is unchanged"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:28:57Z
updated-at: 2026-09-23T17:16:59Z
updated-by: Claude
claimed-by: vm-22489
claimed-at: 2026-09-23T16:46:25Z
outcome-what: "Added tests/test_db.py test_every_legacy_step_rolls_back_a_mid_step_failure_and_retries_to_the_fresh_schema: for each legacy step v1-v12 (24 subTests) it builds a database at N-1, injects a fault after the step's first statement or at its PRAGMA user_version = N, asserts user_version N-1, an unchanged sqlite_master and no open transaction, then retries to v14 with a catalog equal to a fresh database. Helpers: full_catalog, deny_version_bump, stop_before_step, first_statement_then_fail. Test-only; src/ unchanged."
outcome-why: "A836XC made steps v1-v12 atomic but only v1, v5 and v12 had committed fault tests. Restoring executescript() in 9 of the steps, or moving any step's version bump outside its transaction, left the suite green (21 of 24 such mutants passed)."
outcome-resolves: "DoD 1-2: the new test. DoD 3: 24 mutants (executescript() per step, bump dedented per step) all fail at exactly their step, against 3/24 for the pre-ticket file; matrix in the notes. DoD 4: full suite 286 tests OK, git diff --check clean. No real defect found."
---

# Fault and retry tests for every legacy migration step v1-v12

## Definition of Done

- [x] tests/test_db.py has a parameterised test that, for each version N in 1-12, starts from a database at N-1, injects a failure after the step's first statement, and asserts user_version is still N-1 and sqlite_master is unchanged
  proof: tests/test_db.py test_every_legacy_step_rolls_back_a_mid_step_failure_and_retries_to_the_fresh_schema: subTest step=1..12, fault 'after the first statement' (first_statement_then_fail) and 'at the user_version bump' (deny_version_bump); start db built by stopped_before_step(connection, N) on a db.connect()-configured (WAL) connection; asserts user_version N-1, full sqlite_master unchanged, not in_transaction
- [x] The same test re-opens and migrates again and asserts the final user_version is SCHEMA_VERSION and the catalog equals a fresh database's
  proof: tests/test_db.py test_every_legacy_step_rolls_back_a_mid_step_failure_and_retries_to_the_fresh_schema: after the fault asserts, connection.close(); connection = db.connect(path) (the real startup path: row_factory, WAL, busy_timeout, migrate); asserts user_version == db.SCHEMA_VERSION, full_catalog == fresh db.connect() catalog, integrity_check ok; 24 subTests, test_db OK 3/3 runs
- [x] Mutation check recorded in the ticket: executescript() restored in any one step, or that step's user_version bump moved outside its transaction, makes the test fail
  proof: 24 mutants (executescript() in step N, bump N dedented out of transaction, N=1..12): new test fails at exactly step N for all 24; pre-ticket tests/test_db.py caught 3/24 (exec v1,v5,v12). Matrix in jaira note
- [x] Full suite green and git diff --check clean
  proof: tests/run.py: Ran 286 tests, OK (exit 0) after review fixes; test_db 16 OK x3; node --check app.js ok; compileall ok; git diff --check against merge-base clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] helpers: deny_version_bump(N) authorizer and first-statement-then-fail patch of db._execute_statements
- [x] database at N-1: fresh file migrated under stop_before_step(N), which refuses every write after the N-1 bump (does not rely on step N being atomic)
- [x] subTest loop N=1..12 x two faults: assert version N-1, catalog unchanged, not in_transaction; retry; assert v14 and catalog == fresh
- [x] mutation check: executescript() in one step, bump moved outside its transaction; record failing output
- [x] focused tests, full suite, node --check, compileall, git diff --check

## Progress
- **2026-09-23 16:47 · Claude** — Brainstorm. What the code shows: src/astra/db.py migrate() runs steps v1-v12 each as 'with transaction(connection): _execute_statements(...); PRAGMA user_version = N'. tests/test_db.py fault-tests only v1 (deny CREATE TABLE tasks), v5 (deny task_schedule_proposals) and v12 (deny owner_action_requests / its index). v2-v4 and v6-v11 have no fault test, and no test fails if a bump moves out of its transaction.
Option A: one hand-written test per version with a step-specific authorizer. Explicit, but 12 near-copies, and v7/v11 are ALTER-only so an authorizer cannot pick one column out.
Option B: one subTest loop over 1-12 with two generic faults: (1) patch db._execute_statements so step N runs only its first statement then raises; (2) an authorizer that denies 'PRAGMA user_version = N' (SQLite passes the value as arg2, checked), i.e. failure after every statement of the step. The same bump-denying authorizer also builds the N-1 database. Generic, no per-step knowledge, catches both mutations named in DoD 3.
Option C: kill a subprocess mid-step. Closest to a real crash, but slow and timing-dependent; A836XC already did this by hand.
Choice: B. Fault 2 alone catches executescript() restored and the bump moved outside the transaction; fault 1 is the DoD's literal 'after the first statement'. T81ZV6 items (re-read inside lock, concurrent migrators, half-applied old databases) stay out.
- **2026-09-23 16:53 · Claude** — Implementation notes (67T315).
Dead end 1: building the N-1 start database by denying 'PRAGMA user_version = N' relies on the atomicity under test. Under a mutant step N commits its DDL during setup, and the test then errors with 'table X already exists' instead of failing on the assertion.
Dead end 2: denying the BEGIN of step N via the authorizer does not work. 'BEGIN IMMEDIATE' is the same SQL string every step, so sqlite3's statement cache reuses the prepared statement and the authorizer is never asked. Steps 7, 8 and 12 went through unrefused.
Used instead: stop_before_step(N) denies every CREATE/ALTER/INSERT/UPDATE/DELETE once 'user_version = N-1' has been authorized. Each bump string is unique per connection, so it is always prepared fresh and the authorizer sees it.
Mutation matrix, run against copies of src/ (not committed): executescript() restored in step N, and 'PRAGMA user_version = N' dedented out of its with-transaction block, for N=1..12, 24 mutants in all. New test: 24/24 fail, each at exactly step=N. Pre-ticket tests/test_db.py: 3/24 fail (executescript in v1, v5, v12); the other 21, including all 12 bump moves, stay green.
Not done, out of plan scope: A836XC gap 4 (four older tests in tests/test_db.py close SQLite handles without try/finally). The new test closes its connections in finally. Left for a separate change so this diff stays test-additive.
- **2026-09-23 17:16 · Claude** — Review round 1 fixes (reviewer: 1 medium, 2 low).
Medium (DoD 2 said re-opens, test retried on the same raw connection): the retry now closes and re-opens through db.connect(path), which migrates. So the retry goes through startup and reads what is on disk.
Low 3 (bare sqlite3.connect, no WAL): the test connection now comes from open_without_migrating(path) = db.connect(path) with db.migrate patched to a no-op. Same settings as production with no copied pragma list to drift; the test asserts journal_mode is wal. The faults now run in WAL.
Low 2 (stop_before_step assumed the N-1 bump was that step's last statement): replaced by the stopped_before_step(connection, N) context manager. A trace callback watches for 'PRAGMA user_version = N-1' and then the next 'BEGIN IMMEDIATE' (step N opening); only then does the authorizer refuse writes. Trace, not authorizer, because the cached BEGIN is never re-authorized.
Dead end: first I armed on the COMMIT after the bump. That made the executescript/dedent mutants fail at N and at N+1: a non-atomic step N never sends a COMMIT with an open transaction (Python commit() is a no-op outside a transaction), so the N+1 setup never stopped. Arming on the next BEGIN makes setup independent of how step N-1 commits.
Mutation re-run (scratch script, db.py mutants): executescript() in step N -> fails at exactly step N, N=1..12; bump N dedented out of transaction -> exactly step N, N=1..12; bump moved to the top of its transaction (bumpfirst, still atomic) -> passes, N=1..12 (before this fix it failed at N+1).
Not rebased: origin/codex/migration-safety-remediation gained 7c0fb9e refactor(39DNZT) (migrate step registry) after this branch was cut. Compatibility with it is checked separately below.
- **2026-09-23 17:16 · Claude** — Compatibility with origin 7c0fb9e/8ef8fd8 (39DNZT migrate step registry): a scratch merge of e473b6e onto origin/codex/migration-safety-remediation auto-merges with no conflicts, and test_db passes there (18 tests OK). Mutation matrix not re-run on the registry form (the mutant script finds steps by the old inline layout). Branch not pushed; the ticket stays in review.
