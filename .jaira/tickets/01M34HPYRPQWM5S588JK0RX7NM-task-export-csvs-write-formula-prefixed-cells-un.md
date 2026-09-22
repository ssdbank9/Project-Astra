---
id: 01M34HPYRPQWM5S588JK0RX7NM
title: Task export CSVs write formula-prefixed cells unescaped (CSV formula injection)
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "The Owner can open /api/export?format=csv and /api/export/final-results?format=csv in Excel without any task-supplied text being evaluated as a formula: every cell starting with = + - @ is neutralised with the same csv_cell() helper the import CSVs already use, from one shared module."
context: |-
  The two task export CSVs the Owner downloads are open to CSV formula injection: a task title, project name, next action or entity starting with = + - @ is written into the file verbatim, and Excel evaluates it as a formula when the download is opened.
  src/astra/web.py on main cd59438e: _csv() (line 471) and _csv_final_results() (line 492), served by the /api/export?format=csv and /api/export/final-results?format=csv routes (lines 99-123); both write task.get(column) straight into csv.writer with no escaping.
  Found in the 2026-09-22 independent regression pass (fix-worker item SECURITY-2, low): the import branch's two CSVs had the same defect and were fixed in d295d78 on claude/excel-import; the pre-existing export routes on main were not in that fix's scope and are still unescaped.
  The fix to reuse: csv_cell() in src/astra/importer.py (line 352 on d295d78) normalises the value with normalize_text() and prefixes a leading = + - @ (FORMULA_PREFIXES) with a single quote so the spreadsheet shows the text instead of evaluating it; build_template_csv and ImportEngine.report_csv both call it.
  The export should call the same helper, not a copy. importer.py is only on the excel-import branch (PR #4); once PR #4 lands, move csv_cell() and FORMULA_PREFIXES into a shared module (for example src/astra/textutil.py) that both web.py and importer.py import. If this ticket is worked before PR #4 merges, put the helper in that shared module on top of the excel-import branch and have importer.py import it from there.
  How to reproduce: sign in as a Manager, create a task titled =HYPERLINK("http://example.org","x") or =cmd|' /C calc'!A0, then GET /api/export?format=csv as the Owner and open the file in Excel.
  Ruled out: the JSON export (/api/export without format=csv) is unaffected; the stored title is fine and must not be changed, only the CSV cell.
definition-of-done: "Both export routes (_csv and _csv_final_results in src/astra/web.py) pass every cell through csv_cell() so a value starting with = + - @ arrives in Excel as text, not a formula"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T12:33:36Z
updated-at: 2026-09-22T12:34:48Z
updated-by: Claude
---

# Task export CSVs write formula-prefixed cells unescaped (CSV formula injection)

## Definition of Done

- [ ] Both export routes (_csv and _csv_final_results in src/astra/web.py) pass every cell through csv_cell() so a value starting with = + - @ arrives in Excel as text, not a formula
- [ ] Test in tests/test_web.py: a task whose title starts with = (and one each for + - @) is exported through both CSV routes over HTTP and the cell in the response body begins with a single quote; a plain title is unchanged
- [ ] csv_cell() and FORMULA_PREFIXES live in one shared module imported by both src/astra/web.py and src/astra/importer.py; no second copy of the prefix check exists (grep FORMULA_PREFIXES finds one definition)
- [ ] Full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

