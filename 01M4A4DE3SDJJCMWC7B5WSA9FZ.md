---
id: 01M4A4DE3SDJJCMWC7B5WSA9FZ
title: Consolidate local Astra data under the main checkout
status: pre-process
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
updated-at: 2026-10-07T03:13:10Z
updated-by: Codex
---

# Consolidate local Astra data under the main checkout

## Definition of Done

- [ ] SQLite backup, integrity and logical contents verified before and after relocation; old folder relocated with all companions; data directory ignored by Git; explicit loopback launcher and local instructions verified; independent read-only review passes.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

