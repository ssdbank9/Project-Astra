---
id: 01M2HQJYWEE65RW16FVKF9HBSJ
title: Daily summary and notification policy
status: backlog
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
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
updated-at: 2026-09-20T03:10:15Z
updated-by: Aly Jafferani
---

# Daily summary and notification policy

## Definition of Done

- [ ] Owner daily summary at a saved time in the owner timezone (default 09:00, owner-editable); only the owner enables other recipients; digest covers overdue/due-today/upcoming bands/reviews/checkpoints/next action; disabling the digest does not remove dashboard or event records; unit + HTTP tests; existing tests green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): DO NOT START YET - gated on the App Owner section-15 decisions (notification channel, additional recipients, external email delivery, escalation rules, scheduler/host). Builds on Z24KVH (in-app inbox, done). See astra_project_tracker/CODEX_HANDOFF_2026-09-19.md sec 6.
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20 resolves the policy gate: in-app digest at 09:00 in the Owner timezone, Owner only. External email, additional recipients and escalation are off for the initial release.
