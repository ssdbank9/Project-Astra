---
id: 01M37DZWCWD295ABSYPNDVS19Q
title: db.transaction() leaves the connection inside an open transaction when COMMIT fails
status: review
ready: true
creator: Claude
assignee: Claude
goal: "A failed COMMIT inside astra.db.transaction() rolls back and re-raises, so the connection is never left in an open transaction."
context: |-
  What is wrong: src/astra/db.py:42-50 transaction() runs BEGIN IMMEDIATE, yields, then calls connection.commit() in the else branch. If commit() itself raises, nothing rolls back.
  Result: the connection stays in_transaction=True and keeps the write lock; the next transaction() on that connection fails with 'cannot start a transaction within a transaction'.
  Reproduced 2026-09-23 (in-memory SQLite, foreign_keys=ON, a DEFERRABLE INITIALLY DEFERRED foreign key violated inside the block): COMMIT raised IntegrityError, in_transaction stayed True, the next transaction() raised OperationalError.
  Other ways COMMIT can fail in production: SQLITE_BUSY at commit, disk full, I/O error.
  Found as MIG-7 in the 03G8EH review and confirmed again in the 2026-09-23 adversarial review of branch codex/migration-safety-remediation. It predates that branch.
  Every service write and every migration step goes through this helper, so the fix is one place.
  Ruled out: the rollback-on-exception branch is correct; only the commit path is unguarded.
definition-of-done: transaction() rolls back (ignoring a secondary rollback error) and re-raises when connection.commit() raises; the connection ends with in_transaction False
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:26:18Z
updated-at: 2026-09-23T15:47:53Z
updated-by: Claude
claimed-by: vm-28526
claimed-at: 2026-09-23T15:40:32Z
outcome-what: "db.transaction() now rolls back (suppressing a secondary sqlite3.Error) and re-raises when connection.commit() fails; regression test with a deferred FK violation; README migration note extended"
outcome-why: "A failed COMMIT left the connection in an open transaction holding the write lock, so the next transaction() raised 'cannot start a transaction within a transaction'"
outcome-resolves: "DoD 1: src/astra/db.py transaction(); DoD 2: tests/test_db.py test_failed_commit_rolls_back_and_leaves_the_connection_reusable, failed before fix; DoD 3: 270 tests OK, diff --check clean"
---

# db.transaction() leaves the connection inside an open transaction when COMMIT fails

## Definition of Done

- [x] transaction() rolls back (ignoring a secondary rollback error) and re-raises when connection.commit() raises; the connection ends with in_transaction False
  proof: src/astra/db.py:52-57 transaction(): try commit / except rollback under suppress(sqlite3.Error) / raise
- [x] Regression test in tests/test_db.py: a deferred foreign-key violation makes COMMIT fail; the test asserts the original error is raised, in_transaction is False, no row persisted, and a following transaction() on the same connection succeeds
  proof: tests/test_db.py test_failed_commit_rolls_back_and_leaves_the_connection_reusable (failed before fix: in_transaction True)
- [x] Full suite green (.venv/bin/python tests/run.py) and git diff --check clean
  proof: tests/run.py: Ran 270 tests OK; git diff --check origin/codex/migration-safety-remediation clean; node --check and compileall clean

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] reproduce: failing regression test in tests/test_db.py using a DEFERRABLE INITIALLY DEFERRED FK violated inside transaction()
- [x] confirm the test fails against current code for the right reason (in_transaction True / next transaction() raises)
- [x] guard connection.commit() in db.transaction(): on exception roll back, suppress a secondary sqlite3.Error, re-raise the original
- [x] run test_db, then full suite, node --check, compileall, git diff --check
- [x] update docs if they describe transaction() behaviour

## Progress
- **2026-09-23 15:41 · Claude** — Brainstorm. Code confirms the note: src/astra/db.py transaction() calls connection.commit() in the try/else branch with no guard; the except branch only covers exceptions raised by the with-body. With isolation_level=None, a failed COMMIT (deferred FK violation -> IntegrityError) leaves the SQLite transaction open. Options: (A) wrap commit() in try/except, rollback (suppressing a secondary sqlite3.Error from rollback), re-raise the original - one place, keeps call sites unchanged. (B) replace the context manager with a savepoint-based helper - larger change, alters nesting semantics used by migrations, no benefit here. (C) fix at call sites - dozens of sites, easy to miss one. Choosing A: smallest, covers every service write and migration step. Secondary rollback error is suppressed so the caller sees the COMMIT error, which is the real cause.
- **2026-09-23 15:41 · Claude** — Plan reasoning: the test uses a raw connection (MigrationTests.raw pattern, file-backed temp DB, foreign_keys=ON, isolation_level=None) with a throwaway parent/child schema, not the app schema, so it isolates transaction() from migrations. A deferred FK is the only deterministic, stdlib-only way to make COMMIT itself fail; SQLITE_BUSY or disk-full are not reproducible in a unit test without mocks. Rollback error is suppressed with contextlib.suppress(sqlite3.Error) rather than bare Exception so programming errors still surface.
- **2026-09-23 15:47 · Claude** — Findings: (1) BaseException that is not Exception (KeyboardInterrupt, GeneratorExit) raised in the with-body still skips rollback - pre-existing, out of scope, not changed. (2) Rollback after a failed COMMIT is wrapped in suppress(sqlite3.Error) because on some failures (e.g. SQLite already auto-rolled back on I/O error) rollback() is a no-op or raises; the COMMIT error is the useful one. (3) Suite count is 270, not the 220 in CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md - the handoff doc is stale on that number. (4) No service-level test hits this path; the helper test covers every caller since they all go through db.transaction().
