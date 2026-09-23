---
id: 01M3675JP3ADPB1KQ5R2A836XC
title: Make legacy SQLite migrations atomic and retry-safe
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Ensure every Astra schema migration either commits completely with its user_version update or rolls back completely, and can be retried after an injected failure without leaving partial DDL."
context: "The 2026-09-22 adversarial probe confirmed that migration steps 1-12 in src/astra/db.py use sqlite3.executescript inside a transaction helper. SQLite executescript commits an open transaction before running its script, so an injected error can persist earlier DDL while user_version remains old. Migration v13 already avoids this pattern by executing statements individually inside BEGIN IMMEDIATE. This ticket must harden the legacy migration path without changing the resulting v13 schema or production data semantics."
definition-of-done: Migrations 1-12 execute atomically without executescript transaction escape; an injected mid-migration failure leaves schema and user_version unchanged; reconnect/retry succeeds; fresh and representative legacy-version upgrades produce the expected v13 schema; the full suite and Git diff checks pass.
tags:
  - astra
blocked-by: []
related: []
follows: 01M3549XTPENM6MSYCG2SRFCZD
commits:
  - 3fd31ec0094798b867aadfa5e94a5de9fb9b7906
created-at: 2026-09-23T04:07:50Z
updated-at: 2026-09-23T04:33:25Z
updated-by: Aly Jafferani
claimed-by: X1CarbonPC-33252
claimed-at: 2026-09-23T04:17:12Z
outcome-what: "Replaced every v1-v12 sqlite3.executescript migration call with complete-statement execution through connection.execute inside the existing per-version BEGIN IMMEDIATE transaction; documented the contract and added rollback, retry, parser, legacy-upgrade, and schema-equivalence regressions."
outcome-why: "executescript committed the surrounding transaction before running, so a DDL failure could leave partial tables, columns, or indexes while user_version remained stale and future starts failed."
outcome-resolves: "Injected failures in v1, v5, and v12 now leave the prior schema and user_version intact, retries reach v13, legacy and fresh SQLite catalogs match, focused migration tests pass 8/8, and the complete suite passes 220/220 with syntax and diff checks clean."
executed-by: Codex
---

# Make legacy SQLite migrations atomic and retry-safe

## Definition of Done

- [x] Migrations 1-12 execute atomically without executescript transaction escape; an injected mid-migration failure leaves schema and user_version unchanged; reconnect/retry succeeds; fresh and representative legacy-version upgrades produce the expected v13 schema; the full suite and Git diff checks pass.
  proof: src/astra/db.py runs every v1-v12 statement via connection.execute inside the existing per-version BEGIN IMMEDIATE transaction; injected v1/v5/v12 failures prove schema and user_version rollback, retry, and fresh-schema equivalence; 220/220 full suite passes.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Inventory migration steps 1-12 and build a failing fault-injection regression that proves no schema or user_version changes survive a mid-step error.
  proof: tests/test_db.py fault injection denied CREATE TABLE tasks midway through v1; before implementation, users/sessions/entities/projects/project_entities/memberships persisted while user_version remained 0.
- [x] Replace executescript-based migration execution with explicit statements inside one BEGIN IMMEDIATE transaction, preserving statement order and final v13 schema.
  proof: src/astra/db.py _execute_statements feeds complete SQL statements through connection.execute while each legacy step remains inside transaction(BEGIN IMMEDIATE); no migration call uses executescript.
- [x] Cover fresh creation, representative legacy-version upgrades, rollback/retry, and schema equivalence against the current expected database.
  proof: tests/test_db.py now covers fresh v13 creation, v1 rollback/retry, v4-to-v13 ALTER rollback and schema-signature equality, v11/v12 table-index rollback/retry, and the existing v12/v13 interrupted-state recovery; 7/7 migration tests pass.
- [x] Run focused migration tests, the complete project suite, and Git diff checks; document the contract and review the exact diff.
  proof: Final focused migration suite 8/8; full tests/run.py 220/220 in 190.334s; py_compile and git diff --check pass; no executable .executescript call remains; README contract and exact diff reviewed.

## Progress
- **2026-09-23 04:32 · Aly Jafferani** — The first red v1 regression proved six tables persisted with user_version 0. Its initial failing assertion left the SQLite handle open and produced a secondary Windows cleanup error; the test now closes in finally so failures remain unambiguous. Jaira ticket creation also initially failed to record its coordination outbox under the sandbox, although the local ticket file was created; narrow permission to the project-specific .jaira state directory restored normal board writes.
