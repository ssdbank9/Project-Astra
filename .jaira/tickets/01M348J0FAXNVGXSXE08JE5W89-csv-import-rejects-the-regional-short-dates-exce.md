---
id: 01M348J0FAXNVGXSXE08JE5W89
title: CSV import rejects the regional short dates Excel writes on save
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "A CSV template edited and saved in Excel imports its dates: slash- and dot-separated day-first dates are read, ambiguous ones carry a warning or a clear pointer to the .xlsx template, and the docs and dialog say what is accepted."
context: |-
  Excel rewrites every date cell to the regional short format when it saves a CSV (9/4/2026 in en-US, 04/09/2026 in en-GB, 01.09.2026 in de-DE). The importer accepts only dd-mm-yyyy and ISO text, so every dated row of an Excel-edited CSV fails with E_DATE_INVALID and the row advice 'Enter a real date (dd-mm-yyyy ...)' cannot be followed without retyping each cell.
  src/astra/importer.py:60-61 (ISO_DATE, DMY_DATE with '-' only) and the text branch of the date parser at importer.py:1655-1672 on claude/excel-import.
  Reproduced 2026-09-22 on claude/excel-import 911e8c1 with CSV rows using 9/4/2026, 04/09/2026 and 01.09.2026 (the last ;-delimited): all E_DATE_INVALID; ISO with a time part and dd-mm-yyyy pass (probe_a 'XI3-06 CSV locale dates').
  The dialog offers 'Download template (.csv)' and 'Drop your .xlsx or .csv here' with no hint that Excel rewrites CSV dates on save; docs/design/excel-import.md about L197 and L239 promise only the '-' forms, so this is a documented limitation but wrong behaviour on realistic input.
  From the 2026-09-22 adversarial review, finding XI3-06, medium (docs/reviews/2026-09-22-adversarial-review.md, section 2).
  Decision already taken: read slash and dot dates day-first (Astra shows dd-mm-yyyy everywhere); when day and month are both 12 or less and differ, either accept day-first with a new W_DATE_ASSUMED_DMY warning or refuse with a pointer to the .xlsx template. Do not touch the .xlsx path, where dates are numeric cells.
definition-of-done: "DMY_DATE accepts the separators -, / and . ; 04/09/2026 and 01.09.2026 parse as 4 September and 1 September 2026; tests cover the en-US m/d, en-GB dd/mm and de-DE dd.mm forms"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T09:53:37Z
updated-at: 2026-09-22T09:56:37Z
updated-by: Claude
---

# CSV import rejects the regional short dates Excel writes on save

## Definition of Done

- [ ] DMY_DATE accepts the separators -, / and . ; 04/09/2026 and 01.09.2026 parse as 4 September and 1 September 2026; tests cover the en-US m/d, en-GB dd/mm and de-DE dd.mm forms
- [ ] Ambiguous slash or dot dates (day and month both 12 or less and different) either carry W_DATE_ASSUMED_DMY on the row or fail with a row error that points at the .xlsx template; the choice is documented
- [ ] docs/design/excel-import.md (about L197 and L239) and the import dialog's help text list the accepted date formats and warn that Excel rewrites CSV dates on save
- [ ] Full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

