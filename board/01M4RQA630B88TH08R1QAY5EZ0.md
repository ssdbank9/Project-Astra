---
id: 01M4RQA630B88TH08R1QAY5EZ0
title: Bound stalled HTTP requests before launch
status: done
ready: true
creator: Codex
assignee: Codex
goal: Stalled incomplete headers or bodies release their Astra request thread after a finite socket inactivity timeout.
context: "docs/handoff/NEXT_STEPS.md B1 flags a missing server timeout. AstraHandler in src/astra/web.py has no finite socket timeout, while _body waits for Content-Length bytes. Reproduce using disposable loopback sockets, then apply a finite I/O timeout and verify clean resource release and ordinary requests. This is application hardening, not proxy rate limiting or deployment; do not take over Aly-assigned 6BXYJZ."
definition-of-done: Actual incomplete-header and body regressions fail before repair and pass after; finite timeout is applied to real sockets; timed-out bodies do not reach login or mutation handlers and close request database connections; normal requests and completed chunked arrival within timeout still work; guard-removal tests catch missing timeout; full suite and independent review pass; handoff states limits and no deployment; ticket and source publish together.
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-12T18:51:59Z
updated-at: 2026-10-13T06:13:36Z
updated-by: Aly Jafferani
claimed-by: X1CarbonPC-46676
claimed-at: 2026-10-12T19:07:14Z
question: Aly accepted the published inactivity-timeout repair in chat. Human lane remains unchanged under AGENTS.md; broader security review and hosted operation remain separate. No repeat acceptance requested.
outcome-what: Added a 30-second accepted-socket inactivity policy and explicit body-timeout 408 handling with connection closure.
outcome-why: Stalled clients could hold request threads and SQLite connections indefinitely; body timeout initially fell through to500.
outcome-resolves: "Actual socket cleanup, valid requests, two guard-removal checks, independent review and the full 797-test suite passed. The unmodified production policy released four stalled cases around 30 seconds. Source and ticket were published at 6010ca6401aff36e7822e26fb00d626a8daf7440; Aly accepted AY5EZ0 in chat on 2026-10-13. Broader launch gates remain separate."
---

# Bound stalled HTTP requests before launch

## Definition of Done

- [x] Actual incomplete-header and body regressions fail before repair and pass after; finite timeout is applied to real sockets; timed-out bodies do not reach login or mutation handlers and close request database connections; normal requests and completed chunked arrival within timeout still work; guard-removal tests catch missing timeout; full suite and independent review pass; handoff states limits and no deployment; ticket and source publish together.
  proof: tests/test_http_timeout.py real sockets; guard mutations fail; full797 in419.228s OK skipped1; independent review; production idle/header30.007s and body40830.007-30.023s; handoff and scoped ticket/source publication.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reproduce stalled headers and JSON/raw bodies with actual loopback sockets and track request cleanup.
  proof: tests/test_http_timeout.py; Temp/AY5EZ0-red.txt: Ran7, failures5; actual socket stalls and cleanup tracked.
- [x] Apply a finite socket inactivity timeout and return an explicit request timeout for stalled bodies; preserve all authority and body-size limits.
  proof: src/astra/web.py AstraHandler.timeout and RequestBodyTimeout; timeout-only3failures reduced to Ran7 in4.026s OK.
- [x] Verify positive requests, guard-removal regressions, full suite, independent review and scoped handoff; publish with no deployment.
  proof: docs/handoff/HTTP_TIMEOUT_2026-10-13.md; focused7, independent7, two mutants, default30s socket probe; full797 in419.228s OK skipped1; scoped publication prepared.

## Progress
- **2026-10-13 04:23 · Codex** — Installed Python StreamRequestHandler.setup applies self.timeout directly to the accepted socket before header reads. Use a finite socket inactivity timeout, with explicit 408 for stalled bodies and existing finally database cleanup. This is not an absolute request-duration limit: a client continuously sending bytes is a proxy hardening concern, still unverified. Tests shorten only a valid positive policy to exercise actual sockets quickly; they must fail when the production policy is removed.
- **2026-10-13 04:31 · Codex** — Socket tests shorten only a valid existing positive timeout; timeout=None retains the real missing-policy behavior and fails. Timeout-only probe separated release from response classification: headers/idle pass, stalled bodies returned500 until RequestBodyTimeout handling. Independent source/socket review passes, including two guard-removal mutations. Broader framing and proxy/trickle review stays outside this slice. Full suite is running; no owner-server restart.
- **2026-10-13 05:15 · Codex** — Aly Jafferani explicitly accepted AY5EZ0 in this conversation: Accept AY5EZ0. Accepted implementation SHA: 6010ca6401aff36e7822e26fb00d626a8daf7440. Acceptance covers the published 30-second socket inactivity repair and its disclosed limits. Broader security review, actual browser zoom, physical-device checks and hosted operation remain separate. Human lane is unchanged under AGENTS.md; no deployment or owner-server restart authorized.
