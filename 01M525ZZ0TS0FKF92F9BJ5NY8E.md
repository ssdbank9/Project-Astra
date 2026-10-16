---
id: 01M525ZZ0TS0FKF92F9BJ5NY8E
title: Fix stale digest test clock and Waitress test thread leak
status: in-progress
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
updated-at: 2026-10-16T11:02:42Z
updated-by: Claude
claimed-by: X1CarbonPC-41964
claimed-at: 2026-10-16T11:02:05Z
---

# Fix stale digest test clock and Waitress test thread leak

## Definition of Done

- [ ] The digest test passes regardless of the current date, verified by freezing the clock at another date; repeated runs of AstraWaitressIntegrationTests leave no waitress-* threads and tearDown asserts the run thread and workers exited; the full suite passes; no application code changed.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

