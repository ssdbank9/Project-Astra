---
id: 01M4A4DE3SDJJCMWC7B5WSA9FZ
title: Consolidate local Astra data under the main checkout
status: signoff
ready: true
creator: Aly Jafferani
assignee: Codex
goal: Use Project-Astra/data as the single local application data location.
context: "Aly requested moving Documents/AstraTest into the main Project-Astra folder on 2026-10-07 because separate folders are hard to track. Source contains SQLite DB and WAL/SHM companions. Preserve all records, prevent Git publication, and provide a launcher that refuses missing data."
definition-of-done: "SQLite backup, integrity and logical contents verified before and after relocation; old folder relocated with all companions; data directory ignored by Git; explicit loopback launcher and local instructions verified; independent read-only review passes."
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-07T02:52:21Z
updated-at: 2026-10-07T08:13:51Z
updated-by: Codex
claimed-by: X1CarbonPC-38872
claimed-at: 2026-10-07T03:16:32Z
outcome-what: "Independently reviewed local data consolidation."
outcome-why: Aly requested one main folder.
outcome-resolves: Verified existing DB preserved and explicit launcher documented.
review-summary: "Independent workplan_review passed relocation audit, launcher, Git exclusion and final handoff."
review-gaps: "Actual app startup, login and earlier browser database unverified. Full suite not rerun for local move; no push."
review-verdict: PASS for local consolidation
review-check: SQLite consistent backup and every-table comparison; -Check path checks; both guard-removal regressions fail; Git ignore and diff checks pass.
---

# Consolidate local Astra data under the main checkout

## Definition of Done

- [x] SQLite backup, integrity and logical contents verified before and after relocation; old folder relocated with all companions; data directory ignored by Git; explicit loopback launcher and local instructions verified; independent read-only review passes.
  proof: Temp/check_astra_data_move.py before/after: SQLite integrity, foreign keys, schema and every table record unchanged; consistent backup matches. Start-Astra.ps1 -Check passed. Temp/check_astra_launcher_guards.ps1 passed both refusals and guard-removal checks. git check-ignore -v data/* and independent workplan_review passed.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-07 03:16 · Codex** — Source database held 1 user and no projects/tasks. SQLite backup and table hashes match after relocation. No startup, migration, login or real import performed. Missing database/Python checks pass; removing each guard fails its regression. Independent review passed. Earlier browser database unverified.
