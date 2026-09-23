---
id: 01M37E3CYGRZY4X3XJTS1Z4PHZ
title: Make the xlsx test fixture deterministic (zip timestamps flake an import test)
status: backlog
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
updated-at: 2026-09-23T15:28:46Z
updated-by: Claude
---

# Make the xlsx test fixture deterministic (zip timestamps flake an import test)

## Definition of Done

- [ ] workbook_bytes writes every part with a zipfile.ZipInfo carrying a fixed date_time (and ZIP_DEFLATED), so identical input yields identical bytes
- [ ] A fixture test builds the same workbook twice with a clock change between (patched time or a >2 s gap) and asserts equal bytes; the flaky test commits the bytes that belong to the preview it uses
- [ ] test_import passes 20 consecutive loop runs; full suite green

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

