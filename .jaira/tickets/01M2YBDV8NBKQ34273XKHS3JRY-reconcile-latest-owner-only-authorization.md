---
id: 01M2YBDV8NBKQ34273XKHS3JRY
title: Reconcile latest Owner-only authorization
status: backlog
ready: false
creator: Aly Jafferani
goal: Make every application path enforce the latest rule that protected lifecycle and all file/final-result mutations are App Owner-only while Managers retain only approved ordinary project operations.
context: "The 102-test implementation predates the 2026-09-19/20 UX and drag decisions. src/astra/service.py currently treats Chairman as a project manager for many mutations and lets project managers add attachment links and mark/unmark final results. The approved current role matrix reserves accept/reject/complete/close/reopen/override and every file/final-result mutation for Aly Jafferani as App Owner; Manager protected attempts create requests rather than direct mutations. Reconcile service, API, UI, automation/offline paths and tests before creating real Chairman/Manager accounts or sharing Astra."
definition-of-done: "Chairman behavior matches the current role matrix; Managers can perform only approved ordinary internal actions; protected lifecycle attempts create Owner requests and do not mutate accepted state; add/remove/open/publish/version/permanent-link/final-result file mutations are Owner-only except authorized read/download; blocked attachment-removal attempts notify the Owner; service/API/UI/automation/offline paths cannot bypass the rules; authorization matrix tests cover Owner, Chairman, Manager and Viewer; all existing tests remain green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-20T02:48:19Z
updated-at: 2026-09-20T02:50:51Z
updated-by: Aly Jafferani
---

# Reconcile latest Owner-only authorization

## Definition of Done

- [ ] Chairman behavior matches the current role matrix; Managers can perform only approved ordinary internal actions; protected lifecycle attempts create Owner requests and do not mutate accepted state; add/remove/open/publish/version/permanent-link/final-result file mutations are Owner-only except authorized read/download; blocked attachment-removal attempts notify the Owner; service/API/UI/automation/offline paths cannot bypass the rules; authorization matrix tests cover Owner, Chairman, Manager and Viewer; all existing tests remain green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-20 02:50 · Aly Jafferani** — Captured during the 2026-09-20 cumulative handoff audit as a mandatory pre-sharing authorization gate. No code change was made; the next implementation agent must drive this ticket through normal lanes before creating real Chairman or Manager accounts.
