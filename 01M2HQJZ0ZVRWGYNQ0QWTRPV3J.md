---
id: 01M2HQJZ0ZVRWGYNQ0QWTRPV3J
title: Backups and restore
status: in-progress
ready: true
creator: Aly Jafferani
assignee: Codex
goal: Provide a tested backup and restore procedure for the SQLite state so the tracker can recover from loss or corruption.
context: |-
  Astra tracker, section 11 gap "Backups and recovery: Missing" — WAL is not a tested backup strategy.
  Section 4 warns against a Dropbox-synced live SQLite DB as a shared backend.
  GATED on section 15 decisions: backup destination, retention, recovery-point objective (RPO), recovery-time objective (RTO), and restoration procedure. Do not start until the owner supplies these.
definition-of-done: "A documented, scripted backup (consistent snapshot, not a live WAL copy) and a demonstrated restore from it; restore verified to reopen with data intact; procedure covers corruption recovery; no live archive touched; test/verification recorded."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:42Z
updated-at: 2026-10-15T09:45:18Z
updated-by: Codex
claimed-by: X1CarbonPC-49508
claimed-at: 2026-10-15T09:41:41Z
---

# Backups and restore

## Definition of Done

- [ ] A documented, scripted backup (consistent snapshot, not a live WAL copy) and a demonstrated restore from it; restore verified to reopen with data intact; procedure covers corruption recovery; no live archive touched; test/verification recorded.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Implement astra backup using SQLite online backup from a read-only source; refuse overwrite/same-file targets, verify integrity, and remove incomplete outputs.
  proof: src/astra/backup.py:create_backup; tests.test_backup.BackupCliTests.test_backup_command_writes_an_integral_sqlite_snapshot
- [ ] Implement safe restore to a new target database only; validate before publishing, preserve the existing destination, and verify reopening/migration in disposable ASTRA_HOME.
- [ ] Add public CLI tests for a consistent snapshot during writes, intact restore, corrupt backup refusal, overwrite refusal, and recovery after reopening.
- [ ] Update deployment and operator docs to use the CLI while retaining age encryption, 7/4/3 retention, and the explicit cloud/desktop restore gates.
- [ ] Run focused and full suites; get independent read-only review; record proven local results and keep cloud, real-key, live-data, and deployment outcomes unverified.

## Progress
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20: zero-dollar backup policy = nightly encrypted SQLite-consistent backup to OCI Object Storage within the free allowance plus encrypted desktop recovery copy; RPO 24 hours; target RTO 4 hours; retain 7 daily, 4 weekly and 3 monthly copies; Owner controls restore credentials; prove both restore directions before go-live.
