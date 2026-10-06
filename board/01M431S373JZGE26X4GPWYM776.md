---
id: 01M431S373JZGE26X4GPWYM776
title: Repair independent importer defects before launch development
status: signoff
ready: true
creator: Codex
assignee: Codex
goal: "Repair the independently specified workbook, closed-template, cycle and history-label defects; verify existing XML protection and correct inaccurate importer documentation."
context: Corrupt XLSX members cause HTTP 500. Closed project template downloads assign Import Keys. Parent cycle errors name the earlier row. History displays import_key_assigned literally. Aly authorized repairs on 2026-10-04. CSV policy R2 remains on parent 3NT40T awaiting a sample workplan; this ticket changes no CSV format.
definition-of-done: Actual corrupt CRC and deflate XLSX members return XlsxError and HTTP 400 on preview and commit without task writes; all specified archive read exceptions are translated.
tags: []
blocked-by: []
parent: 01M343BZ654VN11E38293NT40T
related:
  - 01M343BZ654VN11E38293NT40T
commits: []
created-at: 2026-10-04T08:51:36Z
updated-at: 2026-10-04T14:49:56Z
updated-by: Codex
claimed-by: codex-astra-fixes-20261004
claimed-at: 2026-10-04T08:59:39Z
outcome-what: "Scoped importer repair independently reviewed and verified"
outcome-why: Ready for Aly review before acceptance
outcome-resolves: All six criteria proven; exact CSV policy remains separate and incomplete
review-summary: "Corrupt workbook member reads become XlsxError and HTTP 400. Filled-template downloads refuse closed projects and recheck under the write lock. Parent cycles identify the last changed edge once. History uses a readable import-key label and importer documentation reflects actual behavior. Independent review and correction rereview pass."
review-gaps: "CSV contract R2 remains on parent 3NT40T in human. Existing Windows symlink check is skipped and unverified. Owner acceptance, Linux, hosted readiness and sample compatibility remain unverified."
review-verdict: PASS
review-check: "1. Run .venv\\Scripts\\python.exe tests\\run.py at this repair commit; expect 692 tests OK skipped=1. 2. ImportHttpTests.test_corrupt_workbook_members_return_400_without_writes and test_closed_project_templates_return_400_without_keys prove the HTTP refusals. 3. ImportServiceTests.test_parent_cycle_error_identifies_the_closing_changed_row proves one error on the closing row. 4. In a synthetic active project, download a filled template and open task History; expect Import key assigned. 5. Run git diff --cached --check before publication; expect no findings."
---

# Repair independent importer defects before launch development

## Definition of Done

- [x] Actual corrupt CRC and deflate XLSX members return XlsxError and HTTP 400 on preview and commit without task writes; all specified archive read exceptions are translated.
  proof: XlsxReaderTests.test_corrupt_zip_members_are_refused and test_truncated_or_unreadable_zip_members_are_refused; ImportHttpTests.test_corrupt_workbook_members_return_400_without_writes; archive_translation mutation fails
- [x] Closed project filled-template downloads refuse Owner and Managers before any key or audit write; service and HTTP role tests pass.
  proof: ImportServiceTests.test_closed_project_template_downloads_write_nothing and test_template_download_rechecks_project_before_key_assignment; ImportHttpTests.test_closed_project_templates_return_400_without_keys; closed_template and template_recheck removal failures
- [x] Parent cycle errors identify the closing file row in new, existing and mixed graphs; invalid related rows cannot commit.
  proof: ImportServiceTests.test_parent_cycle_error_identifies_the_closing_changed_row and test_parent_cycle_does_not_blame_a_later_unchanged_parent; cycle_attribution and cycle_duplicate_guard mutations fail; independent forward-reference and simultaneous-reparenting probes pass
- [x] Existing XML-illegal character protection passes, and numeric-versus-text progress and eligibility warnings are documented accurately.
  proof: ImportServiceTests existing XML control and CSV protection tests in 88-test focused run; docs/design/excel-import.md matches numeric progress and eligibility behavior
- [x] Task history shows Import key assigned in a browser; JavaScript syntax passes.
  proof: Actual local browser task History shows Import key assigned; node --check src/astra/static/app.js passes; docs/handoff/IMPORTER_REPAIRS_2026-10-04.md
- [x] CSV format remains unchanged; full Windows suite, removal checks, independent review, LF and diff checks pass; publication is prepared under the branch rules.
  proof: Full default Windows run: Ran 692 tests in 406.850s, OK (skipped=1); five removal checks; independent rereview PASS; git diff --check; CSV code unchanged

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Add minimal failing reader, service and HTTP regressions for corrupt members, closed templates and cycle attribution
- [x] Translate archive member errors and enforce closed-template guard inside the key-assignment transaction
- [x] Attribute cycles in the final proposed parent graph to the last changed edge; preserve simultaneous reparenting and forward references
- [x] Correct verified documentation claims, label import-key history, and inspect that label in the browser
- [x] Run targeted, guard-removal and full Windows checks; obtain independent diff review
- [x] Prepare the scoped ticket and evidence for signoff and normal publication; report actual SHA and tests after push

## Progress
- **2026-10-04 09:30 · Codex** — 88 focused tests passed. Independent review found duplicate four-row cycle findings; an exact-count regression failed, then passed after the guard. Rereview PASS; valid simultaneous reparenting and forward references preserved. Actual browser History label verified. Five guard-removal mutations fail as required. Full default-locale Windows suite running; CSV unchanged and R2 remains with Aly in human.
