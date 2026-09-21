---
id: 01M2HQJZ0ZVRWGYNQ0QWTRPV3J
title: Backups and restore
status: backlog
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
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
updated-at: 2026-09-20T03:10:17Z
updated-by: Aly Jafferani
---

# Backups and restore

## Definition of Done

- [ ] A documented, scripted backup (consistent snapshot, not a live WAL copy) and a demonstrated restore from it; restore verified to reopen with data intact; procedure covers corruption recovery; no live archive touched; test/verification recorded.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20: zero-dollar backup policy = nightly encrypted SQLite-consistent backup to OCI Object Storage within the free allowance plus encrypted desktop recovery copy; RPO 24 hours; target RTO 4 hours; retain 7 daily, 4 weekly and 3 monthly copies; Owner controls restore credentials; prove both restore directions before go-live.
