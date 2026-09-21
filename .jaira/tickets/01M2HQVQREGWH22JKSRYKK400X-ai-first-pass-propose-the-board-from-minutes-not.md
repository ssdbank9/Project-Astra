---
id: 01M2HQVQREGWH22JKSRYKK400X
title: "AI first-pass: propose the board from minutes, notes, and emails"
status: backlog
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Let a selected AI assessor (Claude, Codex, or Gemini — provider-swappable) do a FIRST PASS over meeting minutes, notes, and emails and PROPOSE the project-management board: projects, tasks, owners, dates, dependencies, criticality — for the owner to review, correct, approve, or reject. Nothing is created or published automatically."
context: |-
  Astra tracker. New owner requirement (2026-09-15): an AI should review the minutes, the notes, and the emails and produce a FIRST-PASS project-management board for the owner to refine.
  Maps to handoff section 3 (suggest filing via local matching + selected AI assessor; owner reviews/approves) and section 8 (AI outputs are evidence-backed PROPOSALS; uncertainty visible; cite evidence per field; detect quoted-old requests, duplicates, conflicting dates, cancellations; no auto-publication on confidence). This is Phase 5 (evidence-backed task extraction pilot) in section 12.
  DEPENDS ON evidence being in the system: the standalone tracker does not yet ingest minutes/notes/emails. Either point the assessor at existing files (opt-in import) or wait for ingestion. The existing Email Project Organizer already uses Gemini as an assessor — reuse that pattern, keep it provider-swappable.
  GATED on section 15 decisions: which AI provider + its data-handling terms, model/prompt/version policy, spending limits. Section 8 rule: human visibility of content does NOT authorize sending it to an external AI provider — get explicit authorization first.
  Start when unblocked: define an Assessor interface (claude|codex|gemini), a proposals table (evidence-cited, status pending/approved/rejected/corrected), and an owner review surface; do not mutate the live board from a proposal.
definition-of-done: "Assessor is selectable (claude|codex|gemini) behind one interface; every proposal cites its evidence (source + locator) independently for action, owner, date, and status; proposals land as review items, never as live board changes; owner can approve/reject/correct each; uncertainty and missing owner/date/reason stay visible; source text is treated as untrusted data, never as instructions; no external-provider upload and no model switch/extra spend without explicit authorization; learning only from attributable human approvals/corrections, reversible; model/prompt/version recorded; owner-reviewed evaluation sample measures misses and false positives; unit tests for the proposal/review path with a stubbed assessor."
tags:
  - astra
  - ai
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:15:30Z
updated-at: 2026-09-20T03:10:18Z
updated-by: Aly Jafferani
---

# AI first-pass: propose the board from minutes, notes, and emails

## Definition of Done

- [ ] Assessor is selectable (claude|codex|gemini) behind one interface; every proposal cites its evidence (source + locator) independently for action, owner, date, and status; proposals land as review items, never as live board changes; owner can approve/reject/correct each; uncertainty and missing owner/date/reason stay visible; source text is treated as untrusted data, never as instructions; no external-provider upload and no model switch/extra spend without explicit authorization; learning only from attributable human approvals/corrections, reversible; model/prompt/version recorded; owner-reviewed evaluation sample measures misses and false positives; unit tests for the proposal/review path with a stubbed assessor.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-15 07:45 · Aly Jafferani** — DESIGN SETTLED (grilling session 2026-09-15). Full spec: astra_project_tracker/docs/ai-first-pass-spec.md. Vocabulary: astra_project_tracker/CONTEXT.md (Assessor, Evidence, Proposal, Assessment run + the App Owner / Task Owner / Project Owner distinction). Two ADRs: 0001 mixed Assessor transport (Gemini=API key, Claude/Codex=subscription CLI), 0002 reuse EPO filing. Key decisions: reads _machine/ per scope.json incrementally by per-project date watermark; proposes create-AND-update Tasks cited to Evidence; feeds the Assessor the project's current open Tasks so it can propose updates; reuse EPO entity/project filing with App-Owner refile override; dedicated Proposals review screen (approve/edit/refile/reject, idempotent); provider-swappable default Gemini. STILL GATED: build only after App Owner turns a run on (content leaves machine only with per-run authorization) + confirms EPO->Astra entity/project mapping.
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20: external AI is disabled for the initial release. A future assessor must be zero-cost, provider-swappable and preferably local on the Owner desktop. Sending private content to any external provider requires separate explicit authorization.
