---
id: 01M34HSDG69WCXNZ1NZXDBZ2WM
title: xlsx_reader does not decode Excel _xHHHH_ escapes; control characters arrive as literal _x0007_ text
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "A workbook Excel saved with control characters in a cell imports the same as a CSV with the raw characters: the reader decodes _xHHHH_ and _x005F_ escapes in shared and inline strings and the decoded control characters are dropped by the importer's illegal-character cleaning, so no _x0007_ literal reaches a task title."
context: |-
  src/astra/xlsx_reader.py does not decode Excel's _xHHHH_ escape sequences, so a cell that Excel saved with a control character reaches the importer as the literal seven-character text _x0007_ instead of being cleaned out.
  Background: OOXML forbids most control characters in XML text, so Excel writes them in sharedStrings.xml and inline strings as _xHHHH_ (four hex digits, for example _x0007_ for U+0007, _x000D_ for CR) and escapes a literal underscore run that would look like one as _x005F_ (so the text "_x0007_" typed by a user is stored as _x005F_x0007_). A conforming reader decodes these; ours takes the <t> text as-is.
  Where: _text_of() in src/astra/xlsx_reader.py (line 190 on claude/excel-import e76eb52) joins the <t> runs verbatim; _cell_value() (line 388) returns shared strings and inlineStr text from it unchanged.
  Found in the 2026-09-22 independent regression pass while re-checking SECURITY-3. Severity low: only a real Excel-authored workbook containing control characters triggers it, and the outcome is a wrong visible title (_x0007_ in the text), not a crash or an unreadable download.
  What is already fixed: c295bb7 on claude/excel-import added clean_text() and ILLEGAL_TEXT in src/astra/importer.py (line 388-394), applied in normalize_text() to every imported cell and in _xml_text() to every written cell, so a raw control character in a cell is dropped and the pre-filled template stays readable. That cleaning never sees the escaped form because the reader hands over the literal text.
  How to reproduce: build a workbook whose sharedStrings.xml has <t>Bad_x0007_title</t>, upload it through the import preview; the title shows as Bad_x0007_title. Hand-built test workbooks already exist in tests/test_core.py for the reader.
  Decode order matters: replace _xHHHH_ (case-insensitive hex, exactly four digits) with the code point first, then _x005F_ with a literal underscore, or do both in one regex pass left to right so _x005F_x0007_ becomes the literal text _x0007_ and not U+0007. Then run the decoded string through the same illegal-character cleaning as the importer (clean_text) so a decoded control character is dropped like a raw one.
  Ruled out: xml.etree already decodes standard XML entities (&amp;#7; is illegal XML anyway); the CSV import path is unaffected because CSV has no such escape.
definition-of-done: "_text_of() in src/astra/xlsx_reader.py decodes _xHHHH_ (four hex digits, any case) to the code point and _x005F_ to a literal underscore, in one left-to-right pass so _x005F_x0007_ yields the literal text _x0007_, for shared strings and inlineStr cells alike"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T12:34:57Z
updated-at: 2026-09-22T12:36:03Z
updated-by: Claude
---

# xlsx_reader does not decode Excel _xHHHH_ escapes; control characters arrive as literal _x0007_ text

## Definition of Done

- [ ] _text_of() in src/astra/xlsx_reader.py decodes _xHHHH_ (four hex digits, any case) to the code point and _x005F_ to a literal underscore, in one left-to-right pass so _x005F_x0007_ yields the literal text _x0007_, for shared strings and inlineStr cells alike
- [ ] The decoded text passes through the importer's illegal-character cleaning (clean_text / ILLEGAL_TEXT from c295bb7) so a decoded U+0007 is dropped exactly like a raw one; the decode happens in one place used by both shared-string and inline-string paths
- [ ] Tests with a hand-built workbook (sharedStrings.xml and an inlineStr cell): _x0007_ inside a title imports as the title with the character removed; _x005F_x0007_ imports as the literal text _x0007_; _x000D_ and lowercase _x000d_ both decode; a plain title with an underscore is unchanged
- [ ] Full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

