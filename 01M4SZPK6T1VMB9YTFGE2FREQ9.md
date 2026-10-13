---
id: 01M4SZPK6T1VMB9YTFGE2FREQ9
title: Notify App Owners and Chairman when deadlines move later
status: in-progress
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
updated-at: 2026-10-13T06:46:33Z
updated-by: Codex
claimed-by: X1CarbonPC-17880
claimed-at: 2026-10-13T06:45:32Z
---

# Notify App Owners and Chairman when deadlines move later

## Definition of Done

- [ ] Failing recipient/date regressions pass after repair; active primary/secondary Owners and Chairman including an acting Owner receive in-app extension notices with old/new dates and project context; committed edit/timeline/revision/reopen/import and project-target paths covered; no notice for initial/earlier/unchanged/preview/refused/rolled-back dates, duplicates prevented; service/HTTP recipient isolation and unchanged authority verified; actual Chairman Inbox check, full suite, independent review and scoped handoff/publication pass.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [ ] Read recipient, event, transaction and importer contracts; retain existing permission checks.
- [ ] Add failing recipient, saved-date, rollback, import and HTTP regressions.
- [ ] Route deadline notices and compare complete project finish snapshots inside composed transactions.
- [ ] Verify a disposable Chairman Inbox, independent diff review and full suite; publish scoped handoff.

## Progress
- **2026-10-13 06:46 · Codex** — Use a dedicated deadline recipient helper, not a global expansion of private Owner notices. Watch complete before/after project ranges once per composed transaction so linked moves and multi-row imports do not report intermediate finishes. Initial dates with no previous deadline are not extensions. Notification is explicitly selected by Aly; Chairman decision authority stays unchanged.
