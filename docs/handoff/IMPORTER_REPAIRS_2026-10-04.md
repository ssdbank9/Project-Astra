# Importer repairs — 2026-10-04

Aly authorized fixes followed by development on 2026-10-04 and then said go.
Branch: `codex/migration-safety-remediation`.
Starting SHA: `10fcccdfde6a52b77805f013480b38b4116aee23`.
Repair ticket: **WYM776**, in signoff, scoped from **3NT40T**. Aly alone accepts work.

## Verified repairs

| Requirement | Change and evidence |
| --- | --- |
| Corrupt workbook parts produce an upload error | Translate BadZipFile, zlib.error, EOFError and OSError at the shared archive-read boundary. Actual bad-CRC and invalid-deflate fixtures return XlsxError; HTTP preview and commit return 400 for both App Owner and Manager, with no tasks written. |
| Closed-project downloads write nothing | Refuse filled templates for both App Owner and Manager. Recheck authorization and status under BEGIN IMMEDIATE before key assignment. Service snapshots stay identical; CSV/XLSX HTTP checks include Owner, Manager, viewer and Chairman. |
| Cycle findings identify the closing change | Preserve the final proposed parent graph; attribute a cycle to its last changed file edge, excluding unchanged parent rows. Two-node mixed/new/existing and four-node cases verify one cycle finding and invalid related rows. Existing absent tasks, forward references and simultaneous reparenting remain covered. |
| Import-key assignment has a readable history label | Task History displays **Import key assigned**, verified in the actual local browser with synthetic data. Node syntax check passes. |
| Documentation describes actual import behavior | Numeric Excel 0.45 scales to 45; text 0.45 is refused. An unchanged upload can warn when a named person loses access. Closed-template rules and the current CSV limitation are explicit. |
| Preserve protection already present | Existing XML-illegal-character and CSV formula-neutralisation regressions pass. CSV serialization is unchanged. |

## Verification

- Eight new tests reproduced the original defects before the repair.
- Focused reader/importer run: **Ran 88 tests in 94.560s, OK**. A subsequently
  extended four-task cycle case caught a duplicate finding; after correction,
  both cycle tests passed and independent rereview passed.
- Five removal checks in disposable copies failed as required: archive error
  translation, closed-template refusal, transactional recheck, cycle attribution
  and duplicate suppression. The real workspace was not mutated by these checks.
- Independent code review and correction rereview: **PASS**.
- Default Windows command: `.venv\Scripts\python.exe tests\run.py`.
  **Ran 692 tests in 406.850s, OK (skipped=1)**, without PYTHONUTF8 override.
- The skip is the existing attachment symlink test: symlinks are unavailable here.
  That platform check remains **unverified**.
- The full run left the seven changed code/test files unchanged, produced no
  ResourceWarnings and left no new tmp directories. All 14 staged files match
  the exact scope; their blobs and diff contain no CR characters, and
  `git diff --cached --check` passes. Source hashes match the full test run.

## Remaining work and owner gates

**3NT40T remains in human** for the exact CSV round-trip decision R2; agents
must not move it out. Aly asked that the workflow suit people with basic Excel
and offered a sample project workplan. The recommendation is XLSX as the primary
editing workflow. Review that sample locally before finalizing the CSV contract;
no versioned CSV format has been approved or implemented. See
[the concrete options](CSV_ROUNDTRIP_DECISION_2026-10-04.md).

Next repair: **1G7Q4C**, mixed Manager saves. Apply the selected atomic-refusal
policy with retained form values and service, HTTP and browser evidence. Then
continue the selected product development slices toward private hosted launch.

A0/SFAZD7 and this repair require Aly's acceptance. Hosted readiness, Linux
verification, real-device acceptance, sample-workplan compatibility and real-user
pilot results remain **unverified**. No deployment, account, credential, merge,
release, external notification or real-user action follows from this repair.
