---
id: 01M4SZPK6T1VMB9YTFGE2FREQ9
title: Notify App Owners and Chairman when deadlines move later
status: human
ready: true
creator: Codex
assignee: Codex
goal: Committed deadline extensions create durable in-app notices for active App Owners and Chairman without changing approval authority.
context: "Aly requested increased deadlines go to Owner and Chairman and selected in-app notification on 2026-10-13, retaining existing approval rules. Current generic notices omit Chairman and suppress the acting App Owner; calculated project finish can extend while agreed deadline stays unchanged. Cover task due-date extensions through edits, timeline movement, approved revisions, reopening and re-import, plus explicit project target extensions. Notices show old/new dates and project context; unchanged, earlier, initial, rejected and rolled-back dates create no extension notice. Use disposable data; do not send email or alter Chairman approval powers."
definition-of-done: "Failing recipient/date regressions pass after repair; active primary/secondary Owners and Chairman including an acting Owner receive in-app extension notices with old/new dates and project context; committed edit/timeline/revision/reopen/import and project-target paths covered; no notice for initial/earlier/unchanged/preview/refused/rolled-back dates, duplicates prevented; service/HTTP recipient isolation and unchanged authority verified; actual Chairman Inbox check, full suite, independent review and scoped handoff/publication pass."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-13T06:37:49Z
updated-at: 2026-10-13T07:47:19Z
updated-by: Codex
claimed-by: X1CarbonPC-17880
claimed-at: 2026-10-13T06:45:32Z
outcome-what: "Durable deadline notices for active App Owners and Chairman; complete composed-operation project finish snapshots."
outcome-why: Aly selected in-app notification; generic routing omitted Chairman and acting Owner.
outcome-resolves: "Focused10 and full807 OK(skip1); independent source/guard/bulk/Undo/handoff review; Chrome Chairman Inbox and read-reload verified. Publication receipt follows normal push."
question: Aly accepted 2FREQ9 on 2026-10-13. Acceptance is complete; only the Aly-only Done board transition remains. Do not request repeat acceptance.
---

# Notify App Owners and Chairman when deadlines move later

## Definition of Done

- [x] Failing recipient/date regressions pass after repair; active primary/secondary Owners and Chairman including an acting Owner receive in-app extension notices with old/new dates and project context; committed edit/timeline/revision/reopen/import and project-target paths covered; no notice for initial/earlier/unchanged/preview/refused/rolled-back dates, duplicates prevented; service/HTTP recipient isolation and unchanged authority verified; actual Chairman Inbox check, full suite, independent review and scoped handoff/publication pass.
  proof: tests/test_deadline_notifications.py focused10 OK; tests/run.py Ran807 in525.988s OK(skip1); independent guard-removal and bulk/Undo checks pass; actual Chrome Chairman Inbox and read/reload; scoped normal push79a1f881ca5451646249616a27dd41b8484545d8; no authority/deployment change

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Read recipient, event, transaction and importer contracts; retain existing permission checks.
  proof: service.py _event/_project_event/import_apply and existing notification uniqueness
- [x] Add failing recipient, saved-date, rollback, import and HTTP regressions.
  proof: 10 regressions: 8 product failures before repair; corrected fixture errors; focused final receipt
- [x] Route deadline notices and compare complete project finish snapshots inside composed transactions.
  proof: Dedicated active recipient helper plus composed write transaction range snapshots
- [x] Verify a disposable Chairman Inbox, independent diff review and full suite; publish scoped handoff.
  proof: Published79a1f881ca5451646249616a27dd41b8484545d8; handoff DEADLINE_NOTICES_2026-10-13.md; full807 OK skip1; Chairman browser and independent source/bulk/Undo/handoff pass

## Progress
- **2026-10-13 06:46 · Codex** — Use a dedicated deadline recipient helper, not a global expansion of private Owner notices. Watch complete before/after project ranges once per composed transaction so linked moves and multi-row imports do not report intermediate finishes. Initial dates with no previous deadline are not extensions. Notification is explicitly selected by Aly; Chairman decision authority stays unchanged.
- **2026-10-13 07:09 · Codex** — All 807 tests pass (existing one symlink skip). Chairman browser Inbox verified: saved task and project finish 10 to 14 October; individual mark-read survives reload. Source/test independent review passes with guard-removal proof. Supplemental bulk/Undo and handoff review is being run separately; reviewer capacity failures were tooling only. Preserve all unrelated dirty Owner Done transitions.
- **2026-10-13 07:11 · Codex** — Independent supplemental bulk+Undo and handoff/screenshot review passed. Full suite807 OK skip1. Publication receipt will be ticked only after the normal push; human lane does not imply acceptance.
- **2026-10-13 07:22 · Codex** — Aly explicitly accepted 2FREQ9 in chat on 2026-10-13: I accept 2FREQ9. Accepted published receipt e9a15f42c83c514dab64cc6cf8556a436806836b, implementation79a1f881ca5451646249616a27dd41b8484545d8. Do not ask Aly to repeat acceptance. Human lane remains unchanged under AGENTS.md; only Aly performs its Done transition. Acceptance does not authorize deployment, accounts or external delivery.
