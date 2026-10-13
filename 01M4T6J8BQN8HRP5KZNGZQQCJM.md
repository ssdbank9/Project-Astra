---
id: 01M4T6J8BQN8HRP5KZNGZQQCJM
title: B1 security review and verified HTTP hardening
status: in-progress
ready: true
creator: Codex
assignee: Codex
goal: Review the complete current app against B1 and repair reproduced security defects before hosting.
context: "Aly accepted deadline notices2FREQ9 and explicitly said start B1 on2026-10-13. Socket inactivity repairAY5EZ0 is accepted, but whole-app authentication, route authorization, request framing, response headers and proxy policy remain outstanding. Audit current source/tests, not the historical handoff status. Use disposable data; preserve approved no-lockout, Owner/Chairman permissions and standard-library stack. Parent deployment6BXYJZ belongs to Aly; do not claim it or deploy/create accounts/notify externally. Record verified defects separately from hosted or policy limits."
definition-of-done: "Full suite, independent final diff review, LF/scoped hygiene and short security handoff pass; ticket waits for Aly acceptance."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-13T08:37:47Z
updated-at: 2026-10-13T10:58:00Z
updated-by: Codex
claimed-by: X1CarbonPC-29860
claimed-at: 2026-10-13T08:39:42Z
---

# B1 security review and verified HTTP hardening

## Definition of Done

- [ ] Full suite, independent final diff review, LF/scoped hygiene and short security handoff pass; ticket waits for Aly acceptance.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Inventory all B1 requirements and independently audit authentication, route roles and input/output boundaries on disposable fixtures.
  proof: Independent authentication23tests; AST93routebranches,92signedout/65CSRF; role14+21tests; disposable XML/account/task/assignee probes
- [x] Add reproducible failing real-socket framing/header and XLSX XML/archive rejection tests.
  proof: Initial17 tests48failingconditions plus actor/assignee/foreignlogin RED regressions; tests/test_http_security.py
- [x] Implement bounded parser/framing and common-response protections without permission or login-policy changes.
  proof: Current web.py/xlsx_reader.py/service.py guards; independent diff and guard removal receipts
- [ ] Verify focused/full suites and guard removals; independently review repairs; record approved proxy policy, residual launch gates and scoped publication.

## Progress
- **2026-10-13 08:41 · Codex** — Aly selected Caddy access logs for real client IPs; keep Astra peer address and do not trust forwarded headers. Independent review reproduced XML entity expansion and archive error classification gaps; parent identified HTTP length/type and response-header omissions. Create regressions before repairs, not a broad readiness claim.
- **2026-10-13 08:52 · Codex** — Aly selected on2026-10-13: keep former importers own old reports accessible; closed project must reopen before new tasks; agreed project deadline changes Owner-only in both project date screen and linked scheduling. Record these accepted decisions; do not remove retained own-report access. Independent role-drift regressions reproduced Manager-to-Viewer task writes and revoked Owner account writes; add under-lock rechecks.
