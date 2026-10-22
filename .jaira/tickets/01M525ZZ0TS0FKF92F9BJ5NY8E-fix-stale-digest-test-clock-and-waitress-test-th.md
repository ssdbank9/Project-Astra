---
id: 01M525ZZ0TS0FKF92F9BJ5NY8E
title: Fix stale digest test clock and Waitress test thread leak
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: Make the daily digest test date-independent and make the Waitress integration test tearDown stop the server and its worker threads cleanly. Test-only change.
context: |-
  The 2026-10-16 independent review of HEAD 66a0c0e ran the full suite: 927 tests, FAILED (failures=1).
  The failure is tests/test_daily_digest.py test_digest_groups_dates_reviews_checkpoints_and_next_actions.
  It calls build_daily_digest(owner, digest_date="2026-10-15") with no now, so the service buckets tasks relative to the real clock. It only passes on 2026-10-15 (Asia/Karachi).
  A probe freezing astra.service.datetime at 2026-10-15T04:00Z made it pass: stale test clock, not an app defect.
  Second problem: tests/test_web.py AstraWaitressIntegrationTests.tearDown calls server.close() but never shuts down server.task_dispatcher. Each test leaks 4 waitress-N worker threads (200 threads after 10 runs of the class).
  A previous review saw one WinError 10038 from the server thread at shutdown (not reproduced in 50 runs); it fits closing the socket while run() is still in select().
  Open question for Aly (not blocking): should public build_daily_digest derive now from digest_date, or refuse a mismatch? Only this test calls it with a digest_date; the scheduler path is consistent. No app code changes unless Aly decides.
definition-of-done: "The digest test passes regardless of the current date, verified by freezing the clock at another date; repeated runs of AstraWaitressIntegrationTests leave no waitress-* threads and tearDown asserts the run thread and workers exited; the full suite passes; no application code changed."
tags:
  - astra
blocked-by: []
related:
  - 01M2HQJZ6KSPH67PP6746BXYJZ
follows: 01M2HQJYWEE65RW16FVKF9HBSJ
commits: []
created-at: 2026-10-16T11:01:43Z
updated-at: 2026-10-22T14:37:55Z
updated-by: Claude
claimed-by: X1CarbonPC-41964
claimed-at: 2026-10-16T11:02:05Z
outcome-what: "Digest test passes a fixed timezone-aware now (2026-10-15 09:00 Karachi). Waitress tests stop the asyncore loop from its own thread via a trigger thunk, shut down the task dispatcher, join this server's workers and assert they exited; setUp cleans up if it fails after create_server."
outcome-why: "The digest test failed on every day but 2026-10-15, and the Waitress tests leaked 4 worker threads per test and could close a socket under select() (WinError 10038)."
outcome-resolves: "Date-independent digest test verified with a frozen clock at two other dates; no waitress-* threads left after 50 runs; guard fails when dispatcher shutdown is removed; full suite 963 OK (skipped=1); no app code changed."
review-summary: "Test-only. tests/test_daily_digest.py passes now=2026-10-15T04:00Z to build_daily_digest, so the buckets no longer follow the real clock. tests/test_web.py AstraWaitressIntegrationTests: setUp records only the waitress-* workers create_server started; stop_server closes all sockets on the loop thread (trigger thunk running wasyncore.close_all), joins the run thread, calls task_dispatcher.shutdown(), joins the workers and asserts all exited; setUp stops the server if it fails after creation."
review-gaps: "none blocking. Uses private server._map (no public map on TcpWSGIServer, Waitress pinned 3.0.2). Open product question for Aly: should public build_daily_digest derive now from digest_date or refuse a mismatch? Today it labels with digest_date but buckets against now; only this test passes digest_date."
review-verdict: "Independent read-only review (separate subagent) found no defects; its two low findings (generic worker-name match, setUp-failure leak) were fixed before commit 8b2554f. DoD met."
review-check: "1. In the repo run: .venv\\Scripts\\python.exe tests\\run.py — expect Ran 963 tests, OK (skipped=1) (count includes other uncommitted test files on disk).  2. Run only the digest test on any date: set PYTHONPATH=src;tests then .venv\\Scripts\\python.exe -m unittest test_daily_digest — all pass even though today is not 2026-10-15.  3. Run test_web.AstraWaitressIntegrationTests several times — each tearDown asserts the Waitress loop thread and its 4 waitress-N workers exited, so a leak shows as a failure."
question: "Ready to accept per the 2026-10-22 consensus (no app change; build_daily_digest keeps labelling by digest_date and bucketing by now, which callers pass explicitly). Only Aly's board move to done remains."
---

# Fix stale digest test clock and Waitress test thread leak

## Definition of Done

- [x] The digest test passes regardless of the current date, verified by freezing the clock at another date; repeated runs of AstraWaitressIntegrationTests leave no waitress-* threads and tearDown asserts the run thread and workers exited; the full suite passes; no application code changed.
  proof: tests/test_daily_digest.py:70 passes with astra.service.datetime frozen at 2027-03-01 and 2025-01-01 (HEAD version fails both); tests/test_web.py AstraWaitressIntegrationTests.stop_server asserts loop+workers exited, 10x class = 50 OK with 0 waitress threads; full suite Ran 963 tests OK (skipped=1); only tests/ changed

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-16 11:06 · Claude** — Waitress shutdown: server.run() is wasyncore.loop over server._map and exits when the map is empty. tearDown now runs wasyncore.close_all(server._map) as a trigger thunk on the loop thread, so no socket is closed under select() (the WinError 10038 theory), then task_dispatcher.shutdown() and joins waitress-* workers. Probe: 10x the class = 50 tests OK, 0 waitress threads left, 1 thread total. Old tearDown never called task_dispatcher.shutdown, so workers stayed blocked on queue_cv forever.
- **2026-10-16 11:11 · Claude** — Applied independent review (general-purpose subagent, no edits): workers are now snapshotted in setUp as only the threads create_server started; setUp failure after create_server now stops the server and runs base tearDown, since unittest skips tearDown then. Proof: digest test passes with astra.service.datetime frozen at 2027-03-01 and 2025-01-01; HEAD version fails at both. Waitress: 10x class = 50 OK, 0 waitress threads, 1 thread total; with ThreadedTaskDispatcher.shutdown stubbed out, all 5 tests fail on the leftover-worker assertion. Not done: Aly's call on whether build_daily_digest should derive now from digest_date.
- **2026-10-22 14:37 · Claude** — Sign-off consensus 2026-10-22 (Claude assessment, Codex review; full suite 1102 OK at 2661bf7; every proof's named tests exist): ACCEPT. Answer: no app change; build_daily_digest keeps labelling by digest_date and bucketing by now, which callers pass explicitly.
