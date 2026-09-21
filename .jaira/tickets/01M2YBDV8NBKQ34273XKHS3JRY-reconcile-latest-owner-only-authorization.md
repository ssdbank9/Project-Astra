---
id: 01M2YBDV8NBKQ34273XKHS3JRY
title: Reconcile latest Owner-only authorization
status: in-progress
ready: true
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
updated-at: 2026-09-21T07:30:30Z
updated-by: Aly Jafferani
claimed-by: X1CarbonPC-50572
claimed-at: 2026-09-20T09:47:28Z
assignee: Aly Jafferani
---

# Reconcile latest Owner-only authorization

## Definition of Done

- [ ] Chairman behavior matches the current role matrix; Managers can perform only approved ordinary internal actions; protected lifecycle attempts create Owner requests and do not mutate accepted state; add/remove/open/publish/version/permanent-link/final-result file mutations are Owner-only except authorized read/download; blocked attachment-removal attempts notify the Owner; service/API/UI/automation/offline paths cannot bypass the rules; authorization matrix tests cover Owner, Chairman, Manager and Viewer; all existing tests remain green.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [ ] Run the validated venv baseline and inventory every current mutation seam that depends on can_manage_project or lifecycle/file authorization.
- [ ] Add an append-only owner-action-request persistence seam that audits and notifies the App Owner without mutating live state.
- [~] Write failing service matrix tests for App Owner, Chairman, Manager and Viewer across ordinary work, protected lifecycle and attachment/final-result actions.
- [ ] Make Chairman read-only by default, route Manager protected lifecycle attempts to Owner requests, and enforce Owner-only attachment/final-result mutations at the service boundary.
- [ ] Add failing and then passing HTTP/UI tests so routes and controls expose the same authorization outcomes without a bypass.
- [ ] Run the full suite, inspect automation/offline call paths for alternate mutation seams, update the authority documentation, and record proof for every acceptance criterion.

## Progress
- **2026-09-20 02:50 · Aly Jafferani** — Captured during the 2026-09-20 cumulative handoff audit as a mandatory pre-sharing authorization gate. No code change was made; the next implementation agent must drive this ticket through normal lanes before creating real Chairman or Manager accounts.
- **2026-09-20 09:50 · Aly Jafferani** — Planning conclusion: keep Chairman organization-wide read visibility through can_view_project/list/search, but remove Chairman from can_manage_project so it has no implicit mutation authority. Use one append-only owner_action_requests table and service helper for protected attempts; this preserves intended action, actor, target and payload, emits an audit event/Owner notification, and returns without mutating live state. Current file implementation is link-only (add/remove/list) and final-results mark/unmark; enforce Owner-only on all four existing mutation seams while retaining project-authorized list/read. No automation or offline replay subsystem exists yet, so their non-bypass proof is that all current HTTP/UI paths call the same service methods; future systems must enter through this seam.
- **2026-09-21 07:30 · Aly Jafferani** — PAUSE/HANDOFF 2026-09-21: implementation is present but uncommitted. Schema v12 adds owner_action_requests; Chairman is read-only by global role, Managers/Approvers create audited Owner requests for supported protected lifecycle actions without changing live state, and attachment/final-result mutations are Owner-only. Service and HTTP authorization matrix coverage is in tests/test_core.py and tests/test_web.py. Final verification after the last code edit: .venv\Scripts\python.exe tests\run.py = 110 passed in 75.217s; node --check src\astra\static\app.js passed. Browser check: Owner task controls/request inbox rendered with clean console; Manager UI was not separately visually logged in; legacy dashboard has pre-existing horizontal overflow at 1280x720. Remaining before review: reconcile stale README.md and CONTEXT.md Approver/Chairman acceptance wording, decide/review whether generic request decision buttons belong in this ticket, complete Jaira plan/DoD proof, and inspect/stage the exact diff. Full continuation, settled decisions, file list and paste-ready Claude prompt are in astra_project_tracker/CLAUDE_CODE_HANDOFF_2026-09-21.md and CLAUDE_CODE_START_PROMPT.md. No deployment, real users, private-source ingestion, external AI, external notification or publication occurred.
