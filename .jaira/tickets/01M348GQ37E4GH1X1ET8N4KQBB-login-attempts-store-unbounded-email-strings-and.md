---
id: 01M348GQ37E4GH1X1ET8N4KQBB
title: Login attempts store unbounded email strings and are never pruned
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "_login rejects malformed or oversized emails before writing anything, and the login_attempts table stays bounded: hashed email, capped length, rows older than the throttle window pruned."
context: |-
  Any unauthenticated POST to the login route with an arbitrary 'email' string stores that string verbatim in login_attempts. A 900,006-character email came back 401 and LENGTH(email)=900006 in the table: about 1 MB of database growth per request, limited only by the 1 MB request cap.
  src/astra/web.py:453-463 (_login) does no length or shape check on the email; src/astra/service.py:81-87 (record_login_attempt) inserts it and deletes rows only on a successful login for that exact email. Nothing prunes rows by age.
  Reproduced 2026-09-22 with an HTTP probe on main cd59438e, PR #2 7858c7f and PR #4 911e8c1 (probe verify-auth-security AS-4: http=401, max_len=900006, rows=1).
  From the 2026-09-22 adversarial review, finding AS-4, medium (docs/reviews/2026-09-22-adversarial-review.md, section 2).
  Not blocking any merge. Must land before the public deployment planned in HQJZ6K (Production security and deployment).
  Ruled out: the request-size cap works; the gap is per-row storage and retention. Pair with the AS-3 ticket (throttle key): both change the same two functions.
definition-of-done: "_login validates the email (normalised, at most 254 characters, plausible shape) and answers 400 without writing a login_attempts row when validation fails"
tags:
  - astra
blocked-by: []
related:
  - 01M2HQJZ6KSPH67PP6746BXYJZ
  - 01M348FVY3X24MGYTBVNEBSJ4J
commits: []
created-at: 2026-09-22T09:52:54Z
updated-at: 2026-09-22T09:56:07Z
updated-by: Claude
---

# Login attempts store unbounded email strings and are never pruned

## Definition of Done

- [ ] _login validates the email (normalised, at most 254 characters, plausible shape) and answers 400 without writing a login_attempts row when validation fails
- [ ] login_attempts stores a SHA-256 of the normalised email instead of the raw string and the throttle lookup uses the same hash; the schema change is a migration step tested against an existing populated database
- [ ] Rows older than LOGIN_WINDOW_SECONDS are pruned on each attempt or in the same cleanup that removes expired sessions; tested
- [ ] HTTP test: a 900 KB email answers 400 and login_attempts stays empty; full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

