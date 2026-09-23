---
id: 01M37E8AHKJM0V50JS55EXEZPM
title: "Maintainability: pass the Owner decision context explicitly instead of _active_owner_request_id"
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "The approval being executed travels through the call stack as an explicit argument or context object, not as mutable AstraService instance state."
context: |-
  Maintainability, not a demonstrated defect.
  src/astra/service.py decide_owner_action_request (~1398-1404) sets self._active_owner_request_id and self._active_owner_decision_reason, runs the action, then clears them in finally.
  _assert_active_request_revision (~1338), _resolve_pending_requests (~1286) and code near ~2375-2390 read them with getattr.
  Safe today because the HTTP layer builds a fresh AstraService per request. It breaks if one instance is shared by threads, a background worker, or re-entrant calls.
  Suggested in Codex's handoff CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 item 2; re-listed by the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Constraint: the six approve-vs-reject race tests in tests/test_state_integrity.py must keep failing when a guard is moved outside its transaction.
definition-of-done: No _active_owner_request_id or _active_owner_decision_reason attribute remains; governed actions receive the decision context explicitly
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:30:54Z
updated-at: 2026-09-23T15:31:28Z
updated-by: Claude
---

# Maintainability: pass the Owner decision context explicitly instead of _active_owner_request_id

## Definition of Done

- [ ] No _active_owner_request_id or _active_owner_decision_reason attribute remains; governed actions receive the decision context explicitly
- [ ] All test_state_integrity race and flag-reset tests pass unchanged (or with only signature updates); full suite green

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

