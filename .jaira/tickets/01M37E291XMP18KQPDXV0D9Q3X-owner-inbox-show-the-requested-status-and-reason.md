---
id: 01M37E291XMP18KQPDXV0D9Q3X
title: "Owner inbox: show the requested status and reason, and reload the task after a 409"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "The Owner can decide a request from the inbox without opening the task, and a 409 conflict anywhere in the task dialog reloads the current task so the user sees the new state."
context: |-
  What is wrong 1: src/astra/static/app.js renderInbox (~496-503) shows only the action name, requester, task title and time. For update_task_status the requested target status (payload status, from_status) and the Manager's reason are not shown, so the Owner approves blind.
  What is wrong 2: after a 409 the UI shows or alerts the message but keeps the stale form (submitDetailEdit ~886-896, request decision ~515). The user must close and reopen the task to see the change. Called SVC-5 in the 03G8EH review.
  Found again in the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Related: handoff 7.1 asks whether a terminal-source request should offer 'Review and reopen' instead of a generic Approve that returns an error.
  The API already returns payload_json and reason on each request (GET /api/owner-action-requests), so no server change is expected.
definition-of-done: "Each inbox request shows the target status (and from status when present) and the requester's reason, escaped"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:27:36Z
updated-at: 2026-09-23T16:51:39Z
updated-by: Claude
claimed-by: vm-19186
claimed-at: 2026-09-23T16:39:03Z
outcome-what: "Inbox requests show target/from status, reason and an Open task link; a 409 from task edit, lifecycle actions or an inbox decision reloads the task/inbox and says it changed since it was opened; inbox errors inline"
outcome-why: "Owner approved requests blind and users kept editing stale revisions after a 409"
outcome-resolves: "DoD 1: requestDetail in renderInbox; DoD 2: api() err.status + reloadTaskAfterConflict + decideOwnerRequest 409 branch; DoD 3: 6 node-driven tests, 290 tests OK, node --check clean"
---

# Owner inbox: show the requested status and reason, and reload the task after a 409

## Definition of Done

- [x] Each inbox request shows the target status (and from status when present) and the requester's reason, escaped
  proof: src/astra/static/app.js requestDetail() + renderInbox owner-request row; tests/test_web.py test_inbox_request_shows_target_status_from_status_and_reason_escaped; browser 0D9Q3X-after-inbox.png
- [x] A 409 from the task edit, submit or request decision reloads the task (and the inbox) and keeps the conflict message visible
  proof: app.js api() sets err.status; reloadTaskAfterConflict() used by submitDetailEdit and lifecycleAction; decideOwnerRequest 409 branch; tests test_a_conflicting_save/submit/inbox_decision_reloads_*; browser 0D9Q3X-after-edit-409.png, -inbox-409.png, -edit-409-task-closed.png
- [x] Static JS tests cover both; node --check clean; full suite green
  proof: tests/test_web.py AstraDetailDialogWiringTests (6 new tests); node --check clean; tests/run.py Ran 290 tests OK

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing node-driven tests: inbox row shows target status, from status and reason escaped; a 409 from task edit, lifecycle submit and inbox decision reloads and keeps a conflict message
- [x] api(): tag the thrown Error with the HTTP status (err.status) so callers can tell a 409 apart; no other behaviour change
- [x] renderInbox: add a status line (From -> To, via statusLabel) and a Reason line to each request; add an inline inbox message area instead of alert()
- [x] on 409: submitDetailEdit and lifecycleAction reload list + task, then show the conflict line on the re-rendered form (fallback: a note at the top of the dialog) and move focus to it
- [x] on 409: decideOwnerRequest reloads the list and inbox and shows the conflict line in the inbox
- [x] browser check with Playwright on the fixture server (before/after screenshots), node --check, focused tests, full suite, compileall, diff --check
- [x] README/docs note on the inbox and conflict behaviour

## Progress
- **2026-09-23 16:40 · Claude** — Brainstorm. What the code shows: GET /api/owner-action-requests (service.list_owner_action_requests) already returns reason and a parsed payload (payload.status, payload.from_status for update_task_status), so this is UI-only; renderInbox (app.js ~502) prints only action, requester, task title, time. api() (app.js line 2) throws a plain Error with no HTTP status, so no caller can tell a 409 from any other refusal; submitDetailEdit, lifecycleAction and decideOwnerRequest just print/alert the message and keep the stale form. Options: (A) show status+reason in the inbox row and, on 409 only, reload task/inbox and show a plain conflict line - small, keeps other errors as today. (B) always reload after any error - simpler but wipes what the user typed on ordinary validation errors (e.g. missing reason), which is worse. (C) add a server-side 'current revision' to the 409 body and diff it for the user - more informative, but a server change the ticket does not need. Choice: A. Tag the Error with response.status in api(), reload only on 409.
- **2026-09-23 16:40 · Claude** — Plan reasoning: reload only on 409, not on every error, so a missing-reason 400 keeps what the user typed. After a reload the form is re-rendered, so the message must be written after openDetail() into the new element, not the captured one (the captured #detail-edit-error node is detached by then). A task can become closed during the conflict, in which case #detail-edit may not exist; hence a fallback note at the top of #detail-body. Focus moves to the message because the submit button that had focus is destroyed by the re-render. Other task-dialog forms (criticality, schedule, dependencies, reviewers) are out of scope for this ticket.
- **2026-09-23 16:51 · Claude** — Implementation notes. (1) The WIRING_DRIVER stub in tests/test_web.py now re-renders on the stubbed openDetail and resets both dialog bodies per scenario; without the re-render a message written to the pre-reload node would pass the test but vanish in a browser. The stub only resolves #id selectors, so a lifecycle form is found with submitAt=[attr,value]. Its insertAdjacentHTML is a no-op, so the fallback note (#detail-conflict, used when the reload removes the form because the task closed meanwhile) is verified only in the browser (0D9Q3X-after-edit-409-task-closed.png). (2) Only 409 reloads; a 400 keeps the typed values and the server's message. The reload discards the user's unsaved edits on purpose: merging over a changed revision would hide the other change. (3) Inbox errors are now inline (#inbox-error, role=alert) instead of alert(); prompt() for the decision note is unchanged. (4) Out of scope, same stale-form pattern still there: criticality, schedule proposal, parent, dependency and reviewer forms in the task dialog show a 409 message without reloading. (5) Handoff 7.1 'Review and reopen' for terminal-source requests not done; the new Open task link in each request is the route to the task for now. (6) The API already returned payload and reason; no server change.
