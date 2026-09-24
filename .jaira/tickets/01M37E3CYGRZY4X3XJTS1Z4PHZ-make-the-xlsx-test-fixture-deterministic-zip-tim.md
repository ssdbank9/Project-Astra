---
id: 01M37E3CYGRZY4X3XJTS1Z4PHZ
title: Make the xlsx test fixture deterministic (zip timestamps flake an import test)
status: done
ready: true
creator: Claude
assignee: Claude
goal: "tests/import_fixtures.py produces byte-identical workbooks for identical input, so no test depends on wall-clock time."
context: |-
  What is wrong: tests/import_fixtures.py workbook_bytes (~73-122) writes each part with archive.writestr(name, data). A plain name makes zipfile stamp the entry with the current local time (2-second resolution).
  So two filled_template() calls a couple of seconds apart give different bytes and a different sha256.
  Flaky test: tests/test_import.py test_commit_refuses_a_plan_that_changed_since_the_preview (~674-697). Line ~692 builds a fresh workbook for the second preview, but line ~695 commits the first 'data' with the second preview's sha256. Across a 2-second boundary the service refuses it at src/astra/service.py ~3193 ('The file changed since the preview').
  Seen about 1 in 10 loop runs during T8WHJR (IMP-8). Confirmed 2026-09-23: two filled_template() calls 2.1 s apart return different bytes.
  Found during the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Ruled out: product code. The service is right to refuse a changed file.
definition-of-done: "workbook_bytes writes every part with a zipfile.ZipInfo carrying a fixed date_time (and ZIP_DEFLATED), so identical input yields identical bytes"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:28:13Z
updated-at: 2026-09-23T19:51:00Z
updated-by: Aly Jafferani
claimed-by: vm-29298
claimed-at: 2026-09-23T15:41:51Z
outcome-what: "Independent review approved"
outcome-why: "No medium+ findings; four low gaps recorded"
outcome-resolves: "Review fields filled; ready for a person to sign off"
review-summary: "tests/import_fixtures.py now builds test workbooks through a small zipfile subclass (_DeterministicZip) that writes every part with a fixed date (1980-01-01) and DEFLATE compression instead of the current time, so the same input always gives the same bytes. The flaky test test_commit_refuses_a_plan_that_changed_since_the_preview now commits the workbook bytes that belong to the preview whose sha256 it passes, so it no longer depends on two builds matching. A new test (FixtureDeterminismTests) builds the same workbook at two different patched clock times and asserts the bytes are equal. Only test files and the ticket changed; no production code."
review-gaps: "No medium or higher problems. Low gaps: (1) no test catches removal of the ZIP_DEFLATED line in _DeterministicZip.writestr (tests/import_fixtures.py:82) - a mutation storing parts uncompressed still passes test_import and test_xlsx_reader; DoD 1 is met by inspection (every part compress_type 8, date_time 1980-01-01). (2) CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md:215-217, 259, 322 still call the test a known flake (about 1 in 10); stale once this merges. (3) The regression test uses mock.patch(\"time.time\"), process-wide while active; fine under the sequential TextTestRunner in tests/run.py, could affect other threads under a future parallel runner. (4) Branch had to be rebased on 2 newer shared-branch commits (DVS19Q); files do not overlap."
review-verdict: Approve — independent reviewer
review-check: "1. cd to the repo root on codex/migration-safety-remediation.  2. Run: cd tests && PYTHONPATH=../src ../.venv/bin/python -m unittest -v test_import  - expect \"Ran 68 tests ... OK\", including FixtureDeterminismTests and test_commit_refuses_a_plan_that_changed_since_the_preview.  3. Run it 20 times in a loop: for i in $(seq 20); do PYTHONPATH=../src ../.venv/bin/python -m unittest test_import 2>&1 | tail -1; done  - expect OK every time (before the fix about 1 in 10 failed).  4. Optional: revert tests/import_fixtures.py to its pre-1Z4PHZ version (git show 23cc15b^:tests/import_fixtures.py) and rerun FixtureDeterminismTests - it fails because the bytes differ in the ZIP DOS timestamp.  5. From the repo root run: .venv/bin/python tests/run.py  - expect Ran 270 tests, OK. Reviewer results: 25/25 targeted runs with a 2s-jumping clock, a start 30ms before a DOS 2s boundary, and the plain clock; 20/20 full test_import runs; mutations M1 (wall-clock date_time) and M2 (override disabled) caught, M3 (ZIP_DEFLATED removed) not caught."
---

# Make the xlsx test fixture deterministic (zip timestamps flake an import test)

## Definition of Done

- [x] workbook_bytes writes every part with a zipfile.ZipInfo carrying a fixed date_time (and ZIP_DEFLATED), so identical input yields identical bytes
  proof: tests/import_fixtures.py:77-87 _DeterministicZip.writestr wraps each str name in ZipInfo(date_time=FIXED_ZIP_DATE_TIME) with compress_type ZIP_DEFLATED; all workbook_bytes parts go through it
- [x] A fixture test builds the same workbook twice with a clock change between (patched time or a >2 s gap) and asserts equal bytes; the flaky test commits the bytes that belong to the preview it uses
  proof: test_import.FixtureDeterminismTests.test_same_workbook_built_across_a_clock_change_has_identical_bytes (patched time.time, +1 h 7 s; failed before the fix with differing header timestamp bytes); test_commit_refuses_a_plan_that_changed_since_the_preview now commits data_again with again['sha256'] (tests/test_import.py ~692-695). Also a real 2.1 s sleep between builds gives identical bytes
- [x] test_import passes 20 consecutive loop runs; full suite green
  proof: 20/20 parallel runs of 'python -m unittest test_import' each Ran 68 tests OK; 100/100 loop runs of the two targeted tests OK; tests/run.py Ran 270 tests OK; node --check app.js, compileall, git diff --check clean

## Options

- [x] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] reproduce: build filled_template twice across a 2 s boundary, bytes differ
- [x] regression test in test_import.py asserting identical bytes across a patched clock, confirm it fails
- [x] fixture: write each part through a ZipInfo with fixed date_time and ZIP_DEFLATED
- [x] flaky test commits the second preview's own bytes with its sha256
- [x] loop test_import 20 times, full suite, node --check, compileall, diff --check

## Progress
- **2026-09-23 15:42 · Claude** — Brainstorm. Wrong in code: tests/import_fixtures.py workbook_bytes calls archive.writestr(name, str); zipfile then builds a ZipInfo with time.localtime(), so the local-header and central-directory DOS timestamps follow the clock (2 s resolution). test_import.py test_commit_refuses_a_plan_that_changed_since_the_preview commits the first preview's bytes with the second preview's sha256. Options: (A) fixed ZipInfo date_time in workbook_bytes plus make the test commit the second preview's own bytes - fixes the root and the test's logic, cheap. (B) only fix the test (commit data_again) - removes this flake but leaves every other byte comparison clock-dependent. (C) patch time.localtime in the test - hides it, fragile. Take A: both halves, the test fix keeps its meaning even if the fixture ever changes again.
- **2026-09-23 15:42 · Claude** — Plan reasoning: a helper in workbook_bytes (part(name, data)) builds ZipInfo(name, date_time=(1980,1,1,0,0,0)) with compress_type=ZIP_DEFLATED, because writestr(ZipInfo) ignores the archive's default compression and would store parts uncompressed otherwise (would change what the reader tests exercise). 1980-01-01 is the earliest DOS date zipfile accepts. Regression test patches time.localtime used by zipfile rather than sleeping 2 s, so it is fast and certain; it also runs a real >2 s variant is unnecessary.
- **2026-09-23 15:52 · Claude** — Why a writestr-overriding ZipFile subclass and not editing each writestr call: workbook_bytes has 7 call sites, the override catches all of them and any added later, and leaves the call sites untouched. Tried nothing else. The DeterminismTest patches time.time, which is what zipfile.writestr reads (time.localtime(time.time())); a real 2 s sleep was checked by hand only, to keep the suite fast. tests/test_xlsx_reader.py still has its own ad-hoc zipfile.writestr archives (lines ~78-107); they are never compared by bytes or sha, so they were left alone. The flaky test would now pass even with the old 'data' (bytes are identical), but committing data_again keeps the test honest if the fixture ever changes.
- **2026-09-23 19:11 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
