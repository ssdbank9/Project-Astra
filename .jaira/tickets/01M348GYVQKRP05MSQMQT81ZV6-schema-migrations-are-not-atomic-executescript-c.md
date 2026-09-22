---
id: 01M348GYVQKRP05MSQMQT81ZV6
title: "Schema migrations are not atomic: executescript() commits the BEGIN IMMEDIATE"
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "Each schema migration step runs inside one write transaction, so a failing or interrupted step leaves the database at the previous version with its schema untouched, and two processes migrating the same file at once cannot interleave."
context: |-
  A migration step that fails or is interrupted halfway leaves a database file no Astra build can open: part of the new tables exist but user_version is still the old number, so the old build sees unknown tables and the new build's CREATE TABLE fails.
  Cause: src/astra/db.py:37-46 transaction() opens BEGIN IMMEDIATE, but every step in migrate() calls connection.executescript(). Python's sqlite3 executescript() issues COMMIT for any pending transaction before running the script (documented behaviour), so the statements run one by one in autocommit and the rollback in transaction() has nothing to undo.
  Also, migrate() reads PRAGMA user_version at db.py:49 outside any lock, so two processes starting together both run the same step.
  Demonstrated 2026-09-22 on Python 3.11: inside 'with transaction(c)', executescript('CREATE TABLE a(x); CREATE TABLE a(x);') raises, table a survives the rollback, in_transaction is False, and a second connection can write meanwhile. Killing the process mid-step reproduced the unopenable file.
  Affects the v12 step on main cd59438e (db.py about 354-376) and the v13 step on claude/excel-import (db.py:378-408); the pattern goes back to the v1 step.
  From the 2026-09-22 adversarial review, finding DI-1, medium (docs/reviews/2026-09-22-adversarial-review.md, section 2). Own ticket against main; land before the next schema bump.
  Ruled out: WAL and busy_timeout are set correctly, and the migration content is right (a populated v11 database reaches v12 and v13 with no data loss).
definition-of-done: "migrate() takes BEGIN IMMEDIATE first, reads and re-checks user_version inside the lock, runs each step's statements with execute() from a list (no executescript), sets user_version in the same transaction and commits once per step"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T09:53:02Z
updated-at: 2026-09-22T09:56:15Z
updated-by: Claude
---

# Schema migrations are not atomic: executescript() commits the BEGIN IMMEDIATE

## Definition of Done

- [ ] migrate() takes BEGIN IMMEDIATE first, reads and re-checks user_version inside the lock, runs each step's statements with execute() from a list (no executescript), sets user_version in the same transaction and commits once per step
- [ ] Test: a step whose statement fails leaves sqlite_master and user_version exactly as before the step
- [ ] Test: two connections migrating the same file concurrently end with the migration applied once and no error
- [ ] The existing populated v11-to-current migration test still passes; full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

