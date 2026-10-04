---
id: 01M42BMWMFBR1WSTTCRJSFAZD7
title: "A0: restore the Windows test baseline"
status: signoff
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
updated-at: 2026-10-04T08:14:30Z
updated-by: Codex
claimed-by: X1CarbonPC-26304
claimed-at: 2026-10-04T02:26:57Z
outcome-what: Closed unsuccessful SQLite setup; ordered fixture cleanup; decoded all Node capture sites as UTF-8; resolved expected missing-database paths; added four regressions and A0 evidence.
outcome-why: "Default Windows tests failed on locale decoding, leaked handles and equivalent short/long paths."
outcome-resolves: "Default full suite Ran 684 tests in 429.070s, OK (skipped=1); focused20 tests OK; closure/encoding removal regressions caught; no resource warnings or new temp residue; independent review passed. Owner acceptance remains pending."
review-summary: Independent agent read the A0 diff and final evidence. Failed setup closes without changing successful connection ownership; all Node captures use UTF-8; fixture callbacks close secondary handles first; CLI refusal remains strict. No material correctness or scope finding.
review-gaps: One existing symlink test cannot run in this Windows environment; Linux and hosted readiness are unverified. No unresolved A0 code finding. Initial LF wording finding corrected.
review-verdict: "PASS: A0 criteria are supported by source, focused/removal checks and the documented default full-suite result; Aly alone accepts."
review-check: "1. In the Project-Astra checkout run .venv\\Scripts\\python.exe tests\\run.py. Expect 684 tests and OK (skipped=1) on the verified Windows environment, with only the symlink availability skip. 2. Read docs/handoff/A0_2026-10-04.md for changes, removal-check evidence and remaining limits. 3. Compare the SFAZD7 commit to 10d0ff32f64b9ffd73299e9559976b60d6884db5. Expect only A0 connection/test reliability and its ticket/evidence files. 4. Aly accepts or sends back this ticket; no deployment or next repair slice is included."
---

# A0: restore the Windows test baseline

## Definition of Done

- [x] Node driver output is decoded explicitly as UTF-8 and the normal Windows run loads every intended UI class.
  proof: tests/test_web.py: all five subprocess capture sites use encoding=utf-8; AstraNodeEncodingTests passes and encoding-removal mutation fails; default full run executes UI classes.
- [x] Failed database connection setup closes the connection without modifying refused migration data; a regression fails when cleanup is removed.
  proof: src/astra/db.py connect cleanup; ConnectionSetupTests real SQLite refusal/data, PRAGMA and interruption checks; all3 fail when close is removed.
- [x] Secondary test connections close before temporary directory removal; the affected interleaving and refusal tests pass without WinError 32.
  proof: tests/test_core.py, test_state_integrity.py and test_update_task_contract.py LIFO cleanup; full 684-test run has no WinError32, resource warning or new tmp directories.
- [x] Recovery commands still refuse missing databases without creating files; path assertions use resolved identity.
  proof: ServerCommandCliTests.test_recovery_commands_refuse_a_missing_database_without_creating_one passes with exact resolved-path messages and absent missing directory.
- [x] The documented full suite passes with exact count and explained skips; independent review and LF/diff checks pass; Aly alone accepts the result.
  proof: docs/handoff/A0_2026-10-04.md: default Windows Ran 684 tests in 429.070s, OK (skipped=1); symlink skip explained; independent review PASS, mutations caught, LF/diff checks pass. Aly acceptance remains separate.

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
