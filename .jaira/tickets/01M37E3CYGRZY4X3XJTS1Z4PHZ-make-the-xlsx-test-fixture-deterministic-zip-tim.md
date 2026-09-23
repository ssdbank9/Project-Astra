---
id: 01M37E3CYGRZY4X3XJTS1Z4PHZ
title: Make the xlsx test fixture deterministic (zip timestamps flake an import test)
status: review
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
updated-at: 2026-09-23T16:13:31Z
updated-by: Claude
claimed-by: vm-29298
claimed-at: 2026-09-23T15:41:51Z
outcome-what: "tests/import_fixtures.py: workbook_bytes now writes through _DeterministicZip, whose writestr stamps every part with FIXED_ZIP_DATE_TIME (1980-01-01) and ZIP_DEFLATED. tests/test_import.py: new FixtureDeterminismTests regression test; test_commit_refuses_a_plan_that_changed_since_the_preview commits the second preview's own bytes (data_again) with its sha256."
outcome-why: "zipfile.writestr with a bare name stamps the wall clock, so two builds seconds apart differed in bytes and sha256, and the test committed one build's bytes with another build's sha256 - it failed about 1 in 10 runs across a 2 s boundary."
outcome-resolves: "DoD 1: fixed ZipInfo date_time + ZIP_DEFLATED on every part. DoD 2: FixtureDeterminismTests asserts equal bytes across a patched clock (failed before the fix); flaky test uses its own workbook. DoD 3: test_import 20/20 green, full suite 270 OK."
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
