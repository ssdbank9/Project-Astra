---
id: 01M4NTRVWHP8QEZ18GB5VZ1ENJ
title: Show person names in workplan change preview
status: in-progress
ready: true
creator: Codex
assignee: Codex
goal: Show readable old and new responsible person names in import previews without changing stored user IDs.
context: "Native Chrome verification of an Excel-saved workplan showed Unassigned followed by a raw user UUID in the Owner change column. The assignment itself succeeded. src/astra/importer.py _display returns owner_user_id verbatim. JM7CFP remains in signoff, so this is a separate defect follow-up."
definition-of-done: "Regression proves assignment and reassignment previews use person names and blank fields preserve assignment; browser preview shows a name and saved assignment persists; focused and full tests pass; independent diff review completed"
tags: []
blocked-by: []
related: []
follows: 01M4BY5B6YP69JMFMVCQJM7CFP
commits: []
created-at: 2026-10-11T15:54:43Z
updated-at: 2026-10-11T16:16:44Z
updated-by: Codex
---

# Show person names in workplan change preview

## Definition of Done

- [ ] Regression proves assignment and reassignment previews use person names and blank fields preserve assignment; browser preview shows a name and saved assignment persists; focused and full tests pass; independent diff review completed

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-11 15:57 · Codex** — Native verification found raw owner IDs only in preview labels; follow-up created separately because JM7CFP is in signoff. Ticket creation saved locally but outbox write was denied; this successful follow-up records the ticket through the CLI.
- **2026-10-11 16:16 · Codex** — Corrected full suite Ran 766 tests in 875.619s, OK (skipped=1), exit 0. Focused 21 OK. Independent read-only review passed and old-behavior restoration failed the regression. Native Chrome preview displays the user name and saved owner persisted. Native Excel dropdown/save/upload and named dependency import verified on synthetic data. Pointer drag produced no dialog, so pointer acceptance remains unverified.
