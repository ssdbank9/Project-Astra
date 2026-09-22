---
id: 01M343BZ654VN11E38293NT40T
title: Excel import hardening follow-ups
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "Close the low-severity gaps the round-2 independent review left open on the Excel/CSV importer (src/astra/xlsx_reader.py, importer.py, service.py, static/app.js, docs/design/excel-import.md) without changing any behaviour reviewed and accepted in C9KPH6."
context: |-
  Seven LOW findings from independent review round 2 of C9KPH6 (2026-09-22, report scratchpad/excel-import/review/review-probes-round2.md, probes R6d/R6e/R7b/R13a/R5b/R8b/R15/R13c/R2b) are open. None violates the C9KPH6 definition of done; the review verdict was go and C9KPH6 sits in signoff.
  1. A corrupt or truncated zip part in an uploaded .xlsx escapes as HTTP 500: src/astra/xlsx_reader.py ~L226-230 calls archive.read without catching zipfile.BadZipFile (Bad CRC-32), zlib.error, EOFError or OSError. Wrap that read and raise XlsxError so the client gets a 400 with a message.
  2. A Manager can download the pre-filled template of a CLOSED project, which assigns Import Keys into it: src/astra/service.py ~L2332 (_template_project) lacks the closed-project check that _import_authorize applies to uploads.
  3. XML-illegal control characters (\x0b, \x0c) in a task title or notes break the generated workbook: src/astra/importer.py ~L361-368 (_xml/_xml_text) escapes markup but does not strip them; Excel and read_workbook refuse the file. Strip or replace them.
  4. docs/design/excel-import.md overstates two behaviours: ~L201 says text 0.45 is accepted as 45% (only a numeric 0.45 cell is scaled; text 0.45 is E_PROGRESS_INVALID); ~L116 says an unedited re-upload is warning-free (it warns W_PERSON_NOT_ELIGIBLE when a task owner has no project access).
  5. src/astra/static/app.js ~L301 EVENT_LABELS has no entry for import_key_assigned, so task history shows the raw kind.
  6. Pre-existing pattern: the CSV template and the CSV export write cells beginning with = (also +, -, @) bare, a formula-injection risk when opened in Excel. Prefix with an apostrophe or space.
  7. Cosmetic: a parent cycle mixing new and existing rows is reported on the new row (E_PARENT_CYCLE) while the existing row gets E_PARENT_INVALID; the stable choice is to report it on the row whose parent closes the loop.
  Ruled out: none of these needs a design decision from Aly; keep the C9KPH6 template, preview and commit behaviour unchanged and keep the 170-test suite green.
definition-of-done: "xlsx_reader.py: corrupt/truncated zip parts (BadZipFile, zlib.error, EOFError, OSError around archive.read) raise XlsxError and reach the client as 400, with a test for a bad-CRC part and a corrupt-deflate part"
tags:
  - astra
blocked-by: []
related:
  - 01M33VD86SS216CCQEDVC9KPH6
follows: 01M33VD86SS216CCQEDVC9KPH6
commits: []
created-at: 2026-09-22T08:22:56Z
updated-at: 2026-09-22T08:23:33Z
updated-by: Claude
---

# Excel import hardening follow-ups

## Definition of Done

- [ ] xlsx_reader.py: corrupt/truncated zip parts (BadZipFile, zlib.error, EOFError, OSError around archive.read) raise XlsxError and reach the client as 400, with a test for a bad-CRC part and a corrupt-deflate part
- [ ] service.py _template_project: template download for a closed project is refused for Managers exactly like an upload (as _import_authorize does) and assigns no Import Keys; tested
- [ ] importer.py _xml/_xml_text strip XML-illegal control characters so a task with \x0b or \x0c in title or notes yields a workbook read_workbook parses; tested
- [ ] docs/design/excel-import.md corrected at ~L116 (W_PERSON_NOT_ELIGIBLE on unedited re-upload) and ~L201 (only numeric 0.45 cells scale; text 0.45 is refused)
- [ ] app.js EVENT_LABELS gains import_key_assigned with a human label; node --check clean
- [ ] CSV template and CSV export neutralise cells starting with =, +, -, @ (leading apostrophe or space); tested; existing CSV re-upload still round-trips unchanged
- [ ] Mixed new/existing parent cycle is reported on the row whose parent closes the loop, consistently with the pure-existing case; probe R2b updated
- [ ] Full suite green (.venv/bin/python tests/run.py), git diff --check clean, no behaviour change to anything in the C9KPH6 definition of done

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

