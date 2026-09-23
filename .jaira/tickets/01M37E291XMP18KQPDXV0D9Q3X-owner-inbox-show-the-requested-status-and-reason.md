---
id: 01M37E291XMP18KQPDXV0D9Q3X
title: "Owner inbox: show the requested status and reason, and reload the task after a 409"
status: signoff
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
updated-at: 2026-09-23T19:11:24Z
updated-by: Claude
claimed-by: vm-19186
claimed-at: 2026-09-23T16:39:03Z
outcome-what: "Independent review approved 0D9Q3X"
outcome-why: "Diff meets the definition of done; all findings low"
outcome-resolves: "review fields set; awaiting human signoff"
review-summary: "The Owner inbox now shows each request as '<Action> · <task or project>' with the requested status change using readable labels (e.g. 'Change status from Cancelled to In progress'), the requester's reason (escaped, or a muted 'No reason given.'), who asked and when, and an Open task link for task requests. api() now attaches the HTTP status to the error it throws. On a 409 from the Edit form or a lifecycle form (submit, accept, request changes, reopen, hold) the page reloads the task list and the task, says 'This task changed since you opened it, so nothing was saved' plus what happens next, shows the server's reason in smaller grey text, and moves focus to that message. On a 409 from an inbox decision it reloads the inbox and says the request can no longer be approved (reject or cancel it) or was already decided elsewhere. Inbox errors appear inline with role=alert instead of alert() pop-ups. A 400 keeps what the user typed. Only src/astra/static/app.js, style.css, README.md and tests/test_web.py changed; no server, database or permission code changed, so the server remains the authority."
review-gaps: "All low severity. (1) The escaping of the server's reason inside the conflict note (showConflict, <small class=conflict-detail>) is not covered by a test; removing escapeHtml there survives the AstraDetailDialogWiringTests. (2) Focus falls to <body> after Open task -> save -> Close, because the close listener re-renders the inbox and destroys the Open task button. (3) A close-project conflict shows two instructions: 'reject or cancel' on the first line and the server's 'review and decide again' under it. (4) Only Edit, lifecycle forms and inbox decisions reload on a 409; the criticality, schedule-proposal, parent, dependency and reviewer forms still show the raw 409 and keep the stale form, which is narrower than the goal's 'anywhere in the task dialog' (DoD is scoped to edit, submit, decision) - follow-up ticket recommended. (5) README says every inbox request shows an Open task link; project-level requests (Close project) have none. (6) Two pending requests with the same action and task cannot be told apart in the stale-request message, and the failed row is not marked. (7) No live human browser acceptance yet: browser checks were Playwright runs on synthetic data by the builder and the reviewer."
review-verdict: Approve — independent reviewer
review-check: "1. cd /workspace/project-astra && git checkout codex/migration-safety-remediation && git pull --ff-only  2. .venv/bin/python tests/run.py  -> ends with OK (all tests pass)  3. cd tests && PYTHONPATH=../src ../.venv/bin/python -m unittest -v test_web  -> OK, including the 0D9Q3X AstraDetailDialogWiringTests  4. Start Astra bound to 127.0.0.1 with a throwaway database, sign in as a Manager and request a status change on a task with a reason  5. Sign in as the Owner and open the inbox: the row reads bold '<Action> · <task title>', then 'Change status from X to Y', the reason in italics, and 'Requested by ... · Open task'  6. In a second browser tab change that task so the request is stale, then Approve in the first tab: the inbox reloads and says the request can no longer be approved and to reject or cancel it, with the server reason in small grey text, and keyboard focus is on that message  7. Open a task's Edit form in two tabs, save in one, then save in the other: 'This task changed since you opened it, so nothing was saved' appears at the top, the form shows the latest version, and nothing you typed was saved  8. Submit the Edit form with an invalid value (400): your typed values stay and the server message shows"
---

# Owner inbox: show the requested status and reason, and reload the task after a 409

## Definition of Done

- [x] Each inbox request shows the target status (and from status when present) and the requester's reason, escaped
  proof: app.js requestTitle()/requestDetail() in renderInbox; style.css '.owner-request .request-detail p.muted' keeps 'No reason given.' muted; tests/test_web.py test_inbox_request_shows_target_status_from_status_and_reason_escaped, test_no_reason_given_is_muted_inside_a_request; browser 0D9Q3X-after-r2-inbox-no-reason.png (computed colour #667085)
- [x] A 409 from the task edit, submit or request decision reloads the task (and the inbox) and keeps the conflict message visible
  proof: app.js api() err.status; reloadTaskAfterConflict() + showConflict() keep the server's reason under the plain line; requestConflictText() says 'can no longer be approved ... Reject or cancel it' when the request is still listed; tests test_a_conflict_keeps_the_servers_reason_under_the_plain_line, test_a_stale_request_still_listed_says_reject_or_cancel_it, test_a_project_close_conflict_keeps_its_reason_and_does_not_mention_a_task, test_a_request_decided_elsewhere_says_nothing_was_decided, test_a_conflict_that_leaves_the_task_read_only_does_not_say_try_again, test_a_conflict_whose_reload_fails_does_not_claim_the_latest_is_shown, test_api_puts_the_http_status_on_a_thrown_error; browser 0D9Q3X-after-r2-*.png
- [x] Static JS tests cover both; node --check clean; full suite green
  proof: tests/test_web.py AstraDetailDialogWiringTests 20 tests; node --check clean; tests/run.py Ran 299 tests OK; git diff --check and compileall clean

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
- **2026-09-23 17:14 · Claude** — Round 2 (review sent it back). (1) 409 copy: kept a plain first line and put the server's own reason under it in a quieter <small class=conflict-detail> (escaped via escapeHtml, so markup from the server is inert). Tried textContent with white-space:pre-line first; it worked but both lines were the same red, so the technical line competed with the plain one. (2) Inbox: after the reload, if the request is still in state.ownerRequests and the decision was approve, it says the request can no longer be approved and to reject or cancel it: a pending request keeps its expected_revision / residual-work snapshot, so an approve that 409s once always will (service.decide_owner_action_request, close_project ~2406-2413). Wording names the request by its inbox title ('Close project · Harbour works'), so it fits project requests with no task. (3) openDetail now returns the task (or null on failure); the conflict note uses it: closed task -> 'It is now Cancelled; this is the latest version.' (no 'try again'), failed reload -> 'It could not be reloaded.' (4) Open task stacking kept (Close returns to the inbox); the inbox re-renders on the task dialog's close event only if load() ran meanwhile (state.loads vs state.inboxLoads), so a conflict note is not wiped when nothing was saved. (5) api() err.status is pinned by a probe that runs the real api() against a fake fetch; removing err.status fails test_api_puts_the_http_status_on_a_thrown_error (checked). (6) Still out of scope: criticality, schedule, parent, dependency and reviewer forms show the raw 409 without reloading.
- **2026-09-23 19:11 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
