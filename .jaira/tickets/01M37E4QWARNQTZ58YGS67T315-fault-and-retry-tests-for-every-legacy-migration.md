---
id: 01M37E4QWARNQTZ58YGS67T315
title: Fault and retry tests for every legacy migration step v1-v12
status: backlog
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
updated-at: 2026-09-23T15:29:40Z
updated-by: Claude
---

# Fault and retry tests for every legacy migration step v1-v12

## Definition of Done

- [ ] tests/test_db.py has a parameterised test that, for each version N in 1-12, starts from a database at N-1, injects a failure after the step's first statement, and asserts user_version is still N-1 and sqlite_master is unchanged
- [ ] The same test re-opens and migrates again and asserts the final user_version is SCHEMA_VERSION and the catalog equals a fresh database's
- [ ] Mutation check recorded in the ticket: executescript() restored in any one step, or that step's user_version bump moved outside its transaction, makes the test fail
- [ ] Full suite green and git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

