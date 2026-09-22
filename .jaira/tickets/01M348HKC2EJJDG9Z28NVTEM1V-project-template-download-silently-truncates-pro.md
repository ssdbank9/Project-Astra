---
id: 01M348HKC2EJJDG9Z28NVTEM1V
title: Project template download silently truncates projects with more than 2000 tasks
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "A project-scoped template download either refuses clearly above the sheet capacity, before any Import Key is assigned, or carries every task; and the CSV twin of a download can always be re-uploaded."
context: |-
  For a project with 2100 tasks, the .xlsx template download assigns Import Keys to all 2100 tasks (2100 import_key_assigned events) but the Tasks sheet holds only 2000 rows, with no warning anywhere. Re-uploading it unedited previews 2000 unchanged and 100 not_in_file. The CSV twin has all 2100 rows and is refused on upload: 'The CSV has more than 2000 data rows'.
  src/astra/service.py:2340-2450 (_template_project, _template_prefill) assigns keys before any size check; src/astra/importer.py:911 (task_rows) writes rows 2 to TEMPLATE_DATA_ROWS+1 only. TEMPLATE_DATA_ROWS = 2000 (importer.py:53) and MAX_ROWS = 2000 (importer.py:45).
  Reproduced 2026-09-22 on claude/excel-import 911e8c1 by creating 2100 tasks through the service and downloading both templates (probe_b: 'Tasks sheet data rows: 2000', 'keys assigned: 2100 of 2100').
  docs/design/excel-import.md about L89 promises the download 'already listing that project's tasks'; the 2000-row cap is documented for uploads (about L228), not downloads.
  From the 2026-09-22 adversarial review, finding XI3-04, medium (docs/reviews/2026-09-22-adversarial-review.md, section 2). Not covered by 3NT40T (import hardening follow-ups) or C9KPH6.
  Decision already taken: either (a) refuse the download above TEMPLATE_DATA_ROWS with a 400 before assigning keys, or (b) size the sheet to len(tasks)+200 and let an upload of existing keys exceed MAX_ROWS. Both are acceptable; (a) is the smaller change.
definition-of-done: "Downloading a project template above the row capacity either returns 400 with a clear message before any Import Key is assigned, or produces a workbook whose Tasks sheet holds every task; a test creates 2001 tasks and asserts the chosen behaviour"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T09:53:23Z
updated-at: 2026-09-22T09:56:29Z
updated-by: Claude
---

# Project template download silently truncates projects with more than 2000 tasks

## Definition of Done

- [ ] Downloading a project template above the row capacity either returns 400 with a clear message before any Import Key is assigned, or produces a workbook whose Tasks sheet holds every task; a test creates 2001 tasks and asserts the chosen behaviour
- [ ] The CSV twin of a project download can always be re-uploaded (same limit on both sides, or MAX_ROWS lifted for rows carrying existing keys); tested
- [ ] docs/design/excel-import.md states the download limit next to the upload limit (about L89 and L228)
- [ ] Full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

