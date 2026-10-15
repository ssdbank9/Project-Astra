---
id: 01M2HQJYWEE65RW16FVKF9HBSJ
title: Daily summary and notification policy
status: in-progress
ready: true
creator: Aly Jafferani
assignee: Codex
goal: Deliver an owner daily digest and configurable notification policy on top of the existing in-app inbox.
context: "Astra tracker, section 11 gap Daily summary: Missing. The durable in-app inbox exists (ticket Z24KVH); this adds an owner-only daily digest on top of it. The accepted policy is in-app at 09:00 in the Owner timezone, with no email, extra recipients or escalation for the first release (docs/handoff/DECISIONS_LOG.md). Aly approved Codex taking the ticket and selected the free app-hosted scheduler on 2026-10-15, rejecting minute-by-minute polling. Implement an Astra scheduler that sleeps until the next saved Owner-local delivery time, deduplicates by Owner-local date and catches up after restart. Test public service methods with a controlled clock, the local command on disposable SQLite, and the authenticated Owner-only HTTP/browser flow. No cloud, account, hosting or deployment changes are in scope."
definition-of-done: "App Owner-only daily in-app summary at an Owner-selected local time (default 09:00) and IANA time zone; no external email, additional recipients, or escalation in the first release; covers overdue, due-today and upcoming bands, reviews, open checkpoints due soon or overdue, and next actions; disabling it does not remove dashboard or event records; service, HTTP, browser and existing-suite tests pass."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:42Z
updated-at: 2026-10-15T17:33:48Z
updated-by: Codex
claimed-by: X1CarbonPC-18440
claimed-at: 2026-10-15T16:35:36Z
outcome-what: "Resolved the accepted notification policy, selected a no-extra-service sleeping scheduler with daily idempotency and restart catch-up, defined digest sections, and recorded the test seams."
outcome-why: "Aly selected the free app-hosted option and rejected a per-minute trigger; the ticket's old scheduler gate is resolved."
outcome-resolves: Provides an implementation-ready plan for the owner-only in-app digest without cloud work.
---

# Daily summary and notification policy

## Definition of Done

- [ ] App Owner-only daily in-app summary at an Owner-selected local time (default 09:00) and IANA time zone; no external email, additional recipients, or escalation in the first release; covers overdue, due-today and upcoming bands, reviews, open checkpoints due soon or overdue, and next actions; disabling it does not remove dashboard or event records; service, HTTP, browser and existing-suite tests pass.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reconcile the existing inbox, global Owner role and accepted notification policy with the code; confirm the saved time and timezone contract.
  proof: docs/handoff/DECISIONS_LOG.md:44-46; src/astra/service.py:list_notifications; src/astra/db.py:notifications migration
- [x] Choose a reliable, idempotent delivery trigger that works with the single-process app and recovers after downtime without an external email service.
  proof: Aly's 2026-10-15 decision: no per-minute checks; use the free app-hosted scheduler.
- [x] Define the digest's overdue, due-today, upcoming, reviews, checkpoints and next-action content using existing task and review data.
  proof: Existing list_tasks computes due_state/days_to_due per project timezone; export_tasks supports 7/30-day bands; _next_action derives task next action; task_submissions holds submitted reviews; task_checkpoints has checkpoint_date/resolved.
- [~] Implement App Owner-only digest settings and a daily in-app summary while preserving the underlying notifications and activity records.
- [ ] Add service and HTTP authorization/content/idempotency tests plus browser verification of the setting and inbox presentation.
- [ ] Run focused and full suites, review the diff independently, update handoff evidence, and move the ticket to human review.

## Progress
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): DO NOT START YET - gated on the App Owner section-15 decisions (notification channel, additional recipients, external email delivery, escalation rules, scheduler/host). Builds on Z24KVH (in-app inbox, done). See astra_project_tracker/CODEX_HANDOFF_2026-09-19.md sec 6.
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20 resolves the policy gate: in-app digest at 09:00 in the Owner timezone, Owner only. External email, additional recipients and escalation are off for the initial release.
- **2026-10-15 16:47 · Codex** — I took over F9HBSJ after Aly's approval, reconciled the first-release policy with DECISIONS_LOG.md, and aligned the DoD to owner-only in-app delivery (no email, extra recipients or escalation). Existing inbox storage and listing are in service.py:list_notifications and db.py's notifications table. The delivery trigger is still a design choice: an Astra-owned single-process clock loop with once-per-owner/local-day dedupe and startup catch-up avoids cloud or OS scheduler setup; a server-stop means today's digest is produced on restart after the saved time. Proposed test seams are the public AstraService digest/settings methods with a controlled clock, then authenticated Owner-only HTTP settings/inbox and browser rendering. I have not written tests or source yet; awaiting Aly's confirmation of this delivery behavior and test seams per the TDD workflow.
- **2026-10-15 16:51 · Codex** — Aly clarified on 2026-10-15 that a per-minute trigger is too much for the free plan and selected the free option. Use Astra's own scheduler thread, sleeping until the next saved Owner-local delivery time, rather than polling every minute or adding Cloudflare/OCI job services. Because the app time is editable, a settings change must wake/recalculate the scheduler; a unique per-owner local-day digest key must prevent duplicates across restarts or multiple starts. At startup, check whether today's saved time has passed and create the digest once if so. Test the public AstraService digest/settings methods with a controlled clock, the local command against disposable SQLite, and the Owner-only authenticated HTTP/settings/inbox and browser flow. No cloud, account, or deployment changes are part of this ticket.
- **2026-10-15 16:53 · Codex** — Digest content plan: use the existing Owner-wide task list and each project's own date timezone. Group open tasks as overdue, due today, due in 1-7 days, and due in 8-30 days, matching the existing portfolio filters; include submitted tasks awaiting acceptance, unresolved checkpoints due within the next 7 days, and the stored/derived next action for each listed task. Show a concise count-first digest with task/project labels and a link to the relevant task. Do not alter task/event records when the digest is disabled. The first release has no Chairman or member recipients, outbound email, or escalation per DECISIONS_LOG.md.
- **2026-10-15 17:28 · Codex** — F9HBSJ implementation now includes a primary-owner-controlled daily summary time and IANA time zone. The scheduler sleeps until that local due time, checks once at process start for restart catch-up, and stores a unique owner/date snapshot with its Inbox notice. No cloud job is needed. Independent review caught the fixed-zone gap and a settings-history label gap; both are corrected. Review also showed v21/v22 backup tests hard-coded schema numbers and the v20 fixture retained v22 tables; update those fixtures alongside schema migrations. Focused service and HTTP/UI tests pass; the full suite is running after those corrections. Browser check uses only the disposable AstraDailyDigestBrowserCheck database.
