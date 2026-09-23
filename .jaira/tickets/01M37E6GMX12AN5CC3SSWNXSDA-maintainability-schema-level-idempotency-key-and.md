---
id: 01M37E6GMX12AN5CC3SSWNXSDA
title: "Maintainability: schema-level idempotency key and indexed lookup for pending Owner requests"
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "Equivalent pending Owner requests are enforced unique by the schema and found by an indexed key, instead of by serialised lookup-then-insert and Python-side JSON decoding."
context: |-
  Maintainability, not a demonstrated defect.
  Today dedupe of equivalent pending requests in src/astra/service.py _request_protected_action (~1119-1127) relies only on BEGIN IMMEDIATE serialising the SELECT and the INSERT; nothing in the schema (owner_action_requests, src/astra/db.py ~386-404) enforces it.
  _resolve_pending_requests (~1266-1316) loads every pending row for the task and action, then json.loads each payload_json in Python to filter by expected_revision and intent.
  Suggested in Codex's handoff CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 items 3 and 4; re-listed by the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Decide first whether the key includes requested_by: without it, it also prevents the SEM-3 twin-request case (see that ticket).
  Needs a schema bump (next is v15) with the same atomic migration pattern and a pre-existing-duplicates refusal like v14's.
definition-of-done: "owner_action_requests gains an intent fingerprint column with a unique partial index on pending rows, populated by a v15 migration that refuses (without changing data) when pending duplicates already exist"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:29:55Z
updated-at: 2026-09-23T15:30:42Z
updated-by: Claude
---

# Maintainability: schema-level idempotency key and indexed lookup for pending Owner requests

## Definition of Done

- [ ] owner_action_requests gains an intent fingerprint column with a unique partial index on pending rows, populated by a v15 migration that refuses (without changing data) when pending duplicates already exist
- [ ] Dedupe and reconciliation look requests up by the fingerprint; no per-row json.loads filtering remains in _resolve_pending_requests
- [ ] Existing state-integrity dedupe and race tests pass unchanged; full suite green

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

