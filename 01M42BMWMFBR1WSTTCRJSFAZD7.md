---
id: 01M42BMWMFBR1WSTTCRJSFAZD7
title: "A0: restore the Windows test baseline"
status: in-progress
ready: true
creator: Codex
assignee: Codex
goal: "Make the documented Windows test command run the intended suite without decoding, SQLite cleanup or path-identity failures."
context: |-
  Windows verification at 10d0ff32 fails before launch acceptance.
  Node UTF-8 output is decoded as cp1252; database setup/refusal and late test cleanups leave SQLite files open; missing-database CLI assertions compare short and long Windows paths.
  Aly authorized Start A0 on 2026-10-04. Focused tests reproduced all three failures.
  Scope is these baseline repairs only. Importer, mixed-save behavior, features, deployment, real users and owner acceptance remain separate.
definition-of-done: |-
  - [ ] Node driver output is decoded explicitly as UTF-8 and the normal Windows run loads every intended UI class.
  - [ ] Failed database connection setup closes the connection without modifying refused migration data; a regression fails when cleanup is removed.
  - [ ] Secondary test connections close before temporary directory removal; the affected interleaving and refusal tests pass without WinError 32.
  - [ ] Recovery commands still refuse missing databases without creating files; path assertions use resolved identity.
  - [ ] The documented full suite passes with exact count and explained skips; independent review and LF/diff checks pass; Aly alone accepts the result.
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-04T02:24:50Z
updated-at: 2026-10-04T08:08:45Z
updated-by: Codex
claimed-by: X1CarbonPC-26304
claimed-at: 2026-10-04T02:26:57Z
---

# A0: restore the Windows test baseline

## Definition of Done

- [ ] Node driver output is decoded explicitly as UTF-8 and the normal Windows run loads every intended UI class.
- [ ] Failed database connection setup closes the connection without modifying refused migration data; a regression fails when cleanup is removed.
- [ ] Secondary test connections close before temporary directory removal; the affected interleaving and refusal tests pass without WinError 32.
- [ ] Recovery commands still refuse missing databases without creating files; path assertions use resolved identity.
- [ ] The documented full suite passes with exact count and explained skips; independent review and LF/diff checks pass; Aly alone accepts the result.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reproduce the default-locale driver failure, migration-refusal leak, interleaving cleanup and missing-database path assertions.
- [x] Add real SQLite setup/refusal closure and locale-independent Node output regressions; observe failures before changing code.
- [x] Close unsuccessful database setup, decode Node output explicitly, order fixture cleanups and normalize the expected CLI path.
- [x] Run focused checks, cleanup-removal mutations and the documented full Windows suite; record skips and residue.
- [x] Obtain read-only independent review and prepare the scoped LF-only code, tests, evidence and ticket for a normal branch commit and push; Aly alone accepts A0.

## Progress
- **2026-10-04 04:03 · Codex** — The focused test command needs tests/ on sys.path because test_core/test_web import link_roots directly; plain module-qualified unittest import is not the documented discovery setup. The corrected focused loop reproduced all three A0 symptoms. New closure and cp1252 Node regressions went red before the fix, then focused20 tests passed. Fixture cleanup uses unittest LIFO callbacks so later secondary connections close before the initial connection and temporary directory, including setup failures. New ticket creation is ref-only in this CLI; jaira pull materializes it for the code commit. Planning must be ticked in Options before entering pre-process. Full suite is running with PYTHONUTF8 unset and utf8_mode=0; no product feature repairs included.
