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
updated-at: 2026-09-22T12:33:09Z
updated-by: Claude
---

# Schema migrations are not atomic: executescript() commits the BEGIN IMMEDIATE

## Definition of Done

- [ ] migrate() takes BEGIN IMMEDIATE first, reads and re-checks user_version inside the lock, runs each step's statements with execute() from a list (no executescript), sets user_version in the same transaction and commits once per step
- [ ] Test: a step whose statement fails leaves sqlite_master and user_version exactly as before the step
- [ ] Test: two connections migrating the same file concurrently end with the migration applied once and no error
- [ ] The existing populated v11-to-current migration test still passes; full suite green (.venv/bin/python tests/run.py); git diff --check clean
- [ ] Migration steps 1-12 in src/astra/db.py follow the _migrate_v13() pattern from e76eb52: statements run with execute() from a list inside one transaction(), guarded so a half-applied database from the old executescript code completes on the next start, user_version set last in the same transaction; no executescript() call remains in migrate()

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-22 12:33 · Claude** — 2026-09-22 independent regression pass (fix worker, MIGRATION-1): the v13 step is already fixed on claude/excel-import in e76eb52 with _migrate_v13() in src/astra/db.py: PRAGMA table_info guard before each ALTER, IF NOT EXISTS on each CREATE, every statement run with execute() inside one BEGIN IMMEDIATE via transaction(), and PRAGMA user_version = 13 as the last statement of that same transaction. Use it as the pattern for this ticket. Steps 1-12 (db.py lines 54-377 on e76eb52, same on main cd59438e) still call connection.executescript(), which commits the surrounding BEGIN IMMEDIATE before it runs. Probe evidence: killing main mid-v12 step (after CREATE TABLE owner_action_requests, before CREATE INDEX idx_owner_action_requests_status) leaves user_version 11 with owner_action_requests present; the next connect() dies with 'table owner_action_requests already exists'. The same probe against e76eb52's v13 step rolled back cleanly and the next start completed the step.
