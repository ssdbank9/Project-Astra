---
id: 01M4NTRVWHP8QEZ18GB5VZ1ENJ
title: Show person names in workplan change preview
status: done
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
updated-at: 2026-10-11T16:30:36Z
updated-by: Aly Jafferani
review-summary: Independent owner_preview_review read only scoped importer and regression diff; no blocking findings. Focused regression passed; restoring old UUID behavior in memory made it fail.
review-gaps: Full app and phone/touch/pointer acceptance not established by this display-only fix.
review-verdict: Pass - independent review
review-check: Full Windows suite 766 OK skipped1; focused21 OK; native corrected preview and saved assignment verified on synthetic project.
outcome-what: Owner-name preview defect fixed and verified.
outcome-why: Independent review and actual Chrome checks passed.
outcome-resolves: "Readability correction complete; no role, storage or import-policy change; awaiting Aly acceptance."
---

# Show person names in workplan change preview

## Definition of Done

- [x] Regression proves assignment and reassignment previews use person names and blank fields preserve assignment; browser preview shows a name and saved assignment persists; focused and full tests pass; independent diff review completed
  proof: tests/test_import.py:test_owner_changes_preview_names_and_commit_keeps_user_ids; docs/handoff/DESKTOP_VERIFICATION_2026-10-11.md; full766 OK skipped1; focused21 OK; independent review pass; native Chrome owner preview and save verified

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-11 15:57 · Codex** — Native verification found raw owner IDs only in preview labels; follow-up created separately because JM7CFP is in signoff. Ticket creation saved locally but outbox write was denied; this successful follow-up records the ticket through the CLI.
- **2026-10-11 16:16 · Codex** — Corrected full suite Ran 766 tests in 875.619s, OK (skipped=1), exit 0. Focused 21 OK. Independent read-only review passed and old-behavior restoration failed the regression. Native Chrome preview displays the user name and saved owner persisted. Native Excel dropdown/save/upload and named dependency import verified on synthetic data. Pointer drag produced no dialog, so pointer acceptance remains unverified.
- **2026-10-11 16:25 · Codex** — Aly Jafferani explicitly accepted VZ1ENJ in this chat on 2026-10-11: accept VZ1ENJ. Published implementation SHA 2100f90b26e3ff7e03be50067f62e269dc02e640; full suite Ran766 tests OK skipped1; focused21 OK; independent review and native corrected preview passed. Acceptance is recorded; the signoff-to-done transition remains human-only under AGENTS.md. No deployment or real-data import authorized by this acceptance.
