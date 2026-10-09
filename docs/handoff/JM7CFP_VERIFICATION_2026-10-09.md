# JM7CFP continuation verification - 2026-10-09

This record covers the accepted Excel workplan and task-row timeline changes
against local HEAD `1d4fbb5e5ed5cc0cff6a099d9f3ec98df29e9d0e` on
`codex/migration-safety-remediation`. The required pull returned
`Already up to date`. Aly previously instructed continuation apart from Chrome,
then explicitly approved JM7CFP in this chat on 2026-10-09. Owner acceptance
and evidence of browser/desktop Excel behavior are recorded separately.

## Requirement checklist

| Requirement and source | Evidence or remaining check | Status |
| --- | --- | --- |
| Continue JM7CFP without changing live Rupani tasks (Aly; ticket context) | Tests use their disposable fixtures; no production import or server restart | Preserved |
| Four visible Excel fields, managed identifiers, dropdowns and grouped optional fields (ticket) | `workplan_excel.py`; `OwnerExcelTests` | Source/tests passed; desktop Excel unverified |
| Project/entity binding checked on preview and commit (ticket) | `test_project_entity_binding_rechecked_on_commit`; stripped-identity regression | Fresh suite passed |
| Explicit named relationships; no inferred links from overlap (ticket) | Named relationship, ambiguous-reference and concurrent graph tests | Fresh suite passed |
| Service authorization, revisions, leases, rollback and dependency/date checks (AGENTS.md; ticket) | `TimelineTaskDropTests`; `TimelineTaskHttpTests` | Fresh suite passed |
| Critical path recalculation and persistent sibling ordering (ticket) | Atomic dates/link/critical-path and order persistence tests | Fresh suite passed |
| Independent review by someone who did not write the implementation (AGENTS.md) | Read-only `excel_review` agent; complete scoped diff and repaired workbook/test inspected | Static pass; browser/desktop acceptance unverified |
| Full suite and JavaScript syntax (AGENTS.md) | `.venv/Scripts/python.exe tests/run.py`; bundled Node `--check` | Ran 765 tests in 557.349s; OK (skipped=1); focused 20 OK; syntax passed |
| LF and scoped diff hygiene (AGENTS.md) | Carriage-return search across authored source/tests returned no matches; scoped whitespace check passed | Passed |
| Real Excel upload, pointer/touch/keyboard dialogs and timeline behavior (AGENTS.md; ticket) | Prior browser connection failure; Aly instructed continuation without Chrome | Unverified |
| Owner acceptance, deployment, accounts and credentials (AGENTS.md) | Aly's direct message: "Approved JM7CFP" on 2026-10-09 | Feature accepted; deployment/account steps retain their separate approval gates |
| Preserve existing CSV compatibility (ticket context) | CSV download/upload controls remain; preceding Excel-only suggestion was a recommendation | Preserved |
| Scoped commit/push, ticket with code, remote race check (AGENTS.md) | Accepted feature and CLI-updated ticket saved together; remote checked before normal push | See working-branch history and the final chat push receipt |

## Confirmed defect and correction

The independent reviewer found that Excel's dropdown formula includes raw title
whitespace, while the parser indexed titles with collapsed whitespace. Selecting
`Shared:   Build  classroom  ` therefore failed to resolve the workbook's own
task name for a relationship or grouping.

The new `test_generated_relationship_labels_with_extra_whitespace_resolve`
failed before correction with one preview error. `reference_label()` now applies
the same whitespace normalization to lookup labels, selected references and
single-versus-multiline predecessor detection. Exactly-one-match validation is
retained, so duplicate normalized labels remain ambiguous. This normalizes
reference matching; it does not rewrite stored titles, plans or task IDs.

The regression checks preview success and the actual saved parent and dependency
IDs. The corrected focused run completed `Ran 20 tests in 14.030s`, `OK`.
The independent reviewer reread the repair and regression and returned a bounded
static pass with no remaining actionable finding established. It did not run
tests or claim browser/desktop Excel acceptance.

## Verification notes

- Jaira validation completed with `checked: 78` and `errors: false`.
  It also reported undeclared-dependency warnings and stale generated agent notes.
  Those warnings were not silently changed as part of JM7CFP.
- The bundled Node executable passed JavaScript syntax validation. Bash PATH did
  not expose Node or Jaira; explicit verified executable paths were used.
- The pre-repair fresh full run exited 0:
  `Ran 764 tests in 532.432s`, `OK (skipped=1)`.
  The corrected-code full run exited 0:
  `Ran 765 tests in 557.349s`, `OK (skipped=1)`. Its durable log is
  `Temp/jm7cfp-full-suite-20261009.txt` (ignored by Git); it includes the
  passing new regression and the explicit symlink-skip reason.
  A fresh isolated check confirmed
  `test_attachment_symlink_out_of_an_allowed_folder_is_rejected` is skipped
  with reason `symlinks are not available here`. The environment cannot create
  the symbolic link needed to exercise attachment escape protection.
  Two preliminary focused invocations failed during module discovery before
  any test ran; explicit source/test helper paths corrected that setup. Those
  discovery failures are separate from the successful full suite.
- The saved prior `Temp/owner-excel-guards.txt` records ten guard-removal
  regressions, including project/entity identity, task revisions and leases,
  dependency dates, order version, nested rollback and concurrency graph checks.
  Those disposable mutations were not repeated in this continuation.
- Unrelated board and line-ending changes are outside this review's scope.
  Private source workbooks, bindings, data and browser files remain outside
  public Git staging.
- `.gitignore` now excludes the root `Temp/` directory. It previously appeared
  as untracked, contrary to this continuation's initial assumption that it was
  already ignored. The scoped rule protects local generated logs/review packets
  and existing browser/sample artifacts; no artifact was staged or published.

## Readiness

The corrected-code full suite, focused regressions and independent static review
passed. Aly's message "Approved JM7CFP" records App Owner acceptance of the
feature. Browser uploads, timeline interaction and desktop Excel behavior remain
unverified; acceptance does not turn those into verified results.

The agent places the ticket in signoff, with the direct owner approval in its
CLI-written history. AGENTS.md reserves leaving signoff for a human, so the
agent does not move it to done or mark unperformed checks as passed. Working-
branch publication keeps this distinction. No deployment, server restart,
real-account creation or live-task import is authorized by this feature approval.
