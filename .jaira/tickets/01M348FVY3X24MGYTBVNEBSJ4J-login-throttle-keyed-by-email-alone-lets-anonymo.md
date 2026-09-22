---
id: 01M348FVY3X24MGYTBVNEBSJ4J
title: Login throttle keyed by email alone lets anonymous callers lock out the Owner
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "Failed sign-in throttling cannot be used by an anonymous caller to lock a legitimate account out: attempts are keyed by (normalised email, client IP) with a per-IP back-off, and the client IP is read from the trusted proxy header when Astra runs behind Caddy."
context: |-
  Five wrong passwords for the Owner's email from any client lock the Owner out: the Owner's own correct password then returns 429 for 15 minutes, and repeating the five attempts keeps the lockout going indefinitely. Casing and whitespace variants of the email all normalise to the same key.
  src/astra/service.py:72-87 (login_is_throttled, record_login_attempt) count failures by normalised email only; src/astra/web.py:456 (_login) passes the peer address but it is not part of the key.
  Reproduced 2026-09-22 with an HTTP probe on main cd59438e, PR #2 7858c7f and PR #4 911e8c1: five 401s for owner@example.org, then the correct password gave 429 'Too many failed sign-in attempts'.
  From the 2026-09-22 adversarial review, finding AS-3, medium (docs/reviews/2026-09-22-adversarial-review.md, section 2).
  Not blocking any merge. Must land before the public deployment planned in HQJZ6K (Production security and deployment), which puts the login route on the internet behind Caddy with individual accounts.
  Ruled out: the throttle and its 429 message work; the gap is only the key. Behind Caddy the socket peer is always the proxy, so an IP key must read X-Forwarded-For from a configured trusted proxy only, or it degrades to one global throttle.
  Pair with the AS-4 ticket (login_attempts growth): both change the same two functions.
definition-of-done: "login_is_throttled and record_login_attempt key failed attempts by (normalised email, client IP) and additionally per client IP with back-off; five failures from one address no longer block the same email from another address"
tags:
  - astra
blocked-by: []
related:
  - 01M2HQJZ6KSPH67PP6746BXYJZ
  - 01M348GQ37E4GH1X1ET8N4KQBB
commits: []
created-at: 2026-09-22T09:52:27Z
updated-at: 2026-09-22T09:56:00Z
updated-by: Claude
---

# Login throttle keyed by email alone lets anonymous callers lock out the Owner

## Definition of Done

- [ ] login_is_throttled and record_login_attempt key failed attempts by (normalised email, client IP) and additionally per client IP with back-off; five failures from one address no longer block the same email from another address
- [ ] Behind a reverse proxy the client IP is taken from X-Forwarded-For only when the socket peer is a configured trusted proxy; otherwise the socket peer address is used; the setting is documented
- [ ] Service and HTTP tests: lockout of one address while the same email still signs in from another; per-IP back-off; trusted versus untrusted forwarded header
- [ ] Full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

