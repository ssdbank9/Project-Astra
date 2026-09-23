---
id: 01M37DZWCWD295ABSYPNDVS19Q
title: db.transaction() leaves the connection inside an open transaction when COMMIT fails
status: backlog
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
updated-at: 2026-09-23T15:26:33Z
updated-by: Claude
---

# db.transaction() leaves the connection inside an open transaction when COMMIT fails

## Definition of Done

- [ ] transaction() rolls back (ignoring a secondary rollback error) and re-raises when connection.commit() raises; the connection ends with in_transaction False
- [ ] Regression test in tests/test_db.py: a deferred foreign-key violation makes COMMIT fail; the test asserts the original error is raised, in_transaction is False, no row persisted, and a following transaction() on the same connection succeeds
- [ ] Full suite green (.venv/bin/python tests/run.py) and git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

