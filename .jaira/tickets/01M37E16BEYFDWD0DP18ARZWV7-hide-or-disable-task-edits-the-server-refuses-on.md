---
id: 01M37E16BEYFDWD0DP18ARZWV7
title: Hide or disable task edits the server refuses on closed and submitted tasks
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "The task detail dialog only offers edits the server will accept for the task's current status, and tells the user to reopen first on a closed task; the server stays the authority."
context: |-
  What is wrong: src/astra/static/app.js renderDetail (~567-570) builds the Status select from STATUSES minus GOVERNED. On a completed/cancelled/abandoned task it still offers cancelled, abandoned and changes_requested, which the server now refuses with 400 (SRFCZD R6).
  On a submitted task it offers in_progress and others; the server refuses leaving review outside accept/request changes (SRFCZD R5).
  The Edit form (#detail-edit ~614), the criticality form, add-predecessor and reviewer forms are still shown on closed tasks; T8WHJR made the server refuse all of those with 400 'reopen the task first'.
  So the user fills a form and only then sees an error.
  Found in the 2026-09-23 adversarial review of codex/migration-safety-remediation (SRFCZD and T8WHJR review gaps).
  Allowed on a closed task: attachments and final-result marking, and the reopen action.
  Ruled out: changing server rules. Keep the server checks exactly as they are; this is UI only.
definition-of-done: "On completed, cancelled and abandoned tasks renderDetail hides or disables the Edit, criticality, dependency and reviewer forms and shows a line saying to reopen the task first; attachments, final-result marking and reopen stay available"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:27:00Z
updated-at: 2026-09-23T15:27:29Z
updated-by: Claude
---

# Hide or disable task edits the server refuses on closed and submitted tasks

## Definition of Done

- [ ] On completed, cancelled and abandoned tasks renderDetail hides or disables the Edit, criticality, dependency and reviewer forms and shows a line saying to reopen the task first; attachments, final-result marking and reopen stay available
- [ ] On a submitted task the Status select is locked; the dialog points to accept / request changes
- [ ] On a terminal task a Manager's Status select offers only statuses that can become a request (back to ordinary work), never cancelled, abandoned or changes_requested
- [ ] Static JS test in tests/ covers the rendered markup for each case; node --check src/astra/static/app.js clean; full suite green

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

