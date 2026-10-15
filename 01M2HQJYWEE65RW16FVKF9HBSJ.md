---
id: 01M2HQJYWEE65RW16FVKF9HBSJ
title: Daily summary and notification policy
status: pre-process
ready: true
creator: Aly Jafferani
assignee: Codex
goal: Deliver an owner daily digest and configurable notification policy on top of the existing in-app inbox.
context: |-
  Astra tracker, section 11 gap "Daily summary: Missing". The durable in-app inbox exists (ticket Z24KVH); this adds the scheduled digest + policy on top.
  Section 7: default 09:00 owner tz, owner-only recipient control, automatic outbound email and escalation OFF by default.
  GATED on section 15 decisions: notification channel, any additional recipients, external email delivery, escalation rules, and a scheduler/host choice. Do not start until the owner supplies these. Related: Z24KVH (in-app inbox).
definition-of-done: "Owner daily summary at a saved time in the owner timezone (default 09:00, owner-editable); only the owner enables other recipients; digest covers overdue/due-today/upcoming bands/reviews/checkpoints/next action; disabling the digest does not remove dashboard or event records; unit + HTTP tests; existing tests green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:42Z
updated-at: 2026-10-15T16:46:39Z
updated-by: Codex
claimed-by: X1CarbonPC-18440
claimed-at: 2026-10-15T16:35:36Z
outcome-what: Recorded an implementation plan for the owner-only in-app daily summary and its test/review gates.
outcome-why: The policy choices are present in the decisions log; code design and delivery reliability need to be resolved before implementation.
outcome-resolves: Creates a scoped plan for the daily summary without modifying cloud infrastructure.
---

# Daily summary and notification policy

## Definition of Done

- [ ] App Owner-only daily in-app summary at a saved time in the App Owner timezone (default 09:00); first release has no external email, additional recipients, or escalation; digest covers overdue, due-today and upcoming bands, reviews, checkpoints and next action; disabling it does not remove dashboard or event records; service and HTTP tests pass with the existing suite.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reconcile the existing inbox, global Owner role and accepted notification policy with the code; confirm the saved time and timezone contract.
  proof: docs/handoff/DECISIONS_LOG.md:44-46; src/astra/service.py:list_notifications; src/astra/db.py:notifications migration
- [ ] Choose a reliable, idempotent delivery trigger that works with the single-process app and recovers after downtime without an external email service.
- [ ] Define the digest's overdue, due-today, upcoming, reviews, checkpoints and next-action content using existing task and review data.
- [ ] Implement App Owner-only digest settings and a daily in-app summary while preserving the underlying notifications and activity records.
- [ ] Add service and HTTP authorization/content/idempotency tests plus browser verification of the setting and inbox presentation.
- [ ] Run focused and full suites, review the diff independently, update handoff evidence, and move the ticket to human review.

## Progress
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): DO NOT START YET - gated on the App Owner section-15 decisions (notification channel, additional recipients, external email delivery, escalation rules, scheduler/host). Builds on Z24KVH (in-app inbox, done). See astra_project_tracker/CODEX_HANDOFF_2026-09-19.md sec 6.
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20 resolves the policy gate: in-app digest at 09:00 in the Owner timezone, Owner only. External email, additional recipients and escalation are off for the initial release.
