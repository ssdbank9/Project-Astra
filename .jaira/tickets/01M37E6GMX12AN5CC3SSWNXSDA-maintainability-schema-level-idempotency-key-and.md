---
id: 01M37E6GMX12AN5CC3SSWNXSDA
title: "Maintainability: schema-level idempotency key and indexed lookup for pending Owner requests"
status: signoff
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
updated-at: 2026-09-23T18:09:01Z
updated-by: Claude
claimed-by: vm-11138
claimed-at: 2026-09-23T17:41:41Z
outcome-what: "Independent review recorded"
outcome-why: "Reviewer approved: all DoD met, only low gaps"
outcome-resolves: "Review lane complete for WNXSDA"
review-summary: "Schema 15 adds an intent_key column to owner_action_requests: a sha256 of project, task, action, the stored payload_json text, reason and requester. A UNIQUE index covers pending rows only, so two identical pending requests can no longer exist. An untyped expected_revision column and a pending-scope index come with it. Existing rows are backfilled in the same atomic migration step. A database that already holds identical pending requests is refused before any step runs, with an id-only message, the same way v14 refuses duplicate submissions. Service: both dedupe paths (task and project requests) find an existing request with one indexed intent_key lookup inside the write transaction; inserts store the key and revision; reconciliation filters scope, action and revision in SQL on the new index, while the semantic intent test (_request_intent_matches, src/astra/service.py:1282) stays in Python because an exact key would change which requests an Owner action resolves. API responses now list 12 columns explicitly, so intent_key and expected_revision never reach JSON. require_owner, Manager and approver checks are untouched."
review-gaps: |-
  All low severity; nothing medium or above.
  1. The implementer reworded DoD 2 themselves (commit 8dd26bc, jaira dod --text). Original: 'Dedupe and reconciliation look requests up by the fingerprint; no per-row json.loads filtering remains in _resolve_pending_requests'. New text keeps the semantic intent test in Python. The technical reason holds (_request_intent_matches skips absent fields, frozenset intents accept any member, special residual_work matching, cross-requester matching), but the person at signoff should confirm the rewording.
  2. No test covers the refusal probe inside the v15 step (first line of _migrate_v15 in src/astra/db.py). Deleting it keeps test_db + test_state_integrity green; the early probe in migrate() catches every tested case. A duplicate inserted between the two probes still rolls back atomically, but with a raw IntegrityError instead of the SchemaMigrationRefused message.
  3. No test exercises the SQL expected_revision=? filter in _resolve_pending_requests (src/astra/service.py ~1339). Gap predates this change. SQL and Python agree for every payload the service writes; they differ only for invalid JSON and duplicate-key JSON.
  4. No test covers AND status='pending' in _pending_request_by_intent; dropping it leaves all tests green (a retry would get back a decided request). Gap predates this change.
  5. New undocumented runtime dependency on SQLite JSON1 (json_valid, json_extract) in the v15 backfill and every request INSERT. Built in with Python 3.11+ (SQLite 3.45.1 here).
  6. No live human browser acceptance was done; verification is automated tests and mutation runs only.
review-verdict: Approve — independent reviewer
review-check: |-
  1. cd /workspace/project-astra (or any checkout of this branch).
  2. Run: .venv/bin/python tests/run.py  -> expect 313 tests OK (about 5 minutes; count may be higher after rebase).
  3. Run: cd tests && PYTHONPATH=../src ../.venv/bin/python -m unittest -v test_db test_state_integrity  -> expect all OK, including test_duplicate_pending_requests_in_an_older_database_refuse_before_any_step_runs, test_concurrent_identical_requests_leave_one_pending_row_per_intent_key, test_concurrent_equivalent_manager_requests_create_one_pending_request_and_event and test_concurrent_equivalent_close_requests_create_one_pending_request_and_event.
  4. Open src/astra/db.py: SCHEMA_VERSION = 15 at line 11, and _migrate_v15 creates the intent_key column and the UNIQUE index WHERE status='pending'.
  5. Read DoD 2 on this ticket (jaira show WNXSDA) and decide whether you accept the implementer's rewording (see review-gaps item 1).
  6. Optional hand check: start the web app, file the same Manager request twice as the same user; the Owner inbox shows one pending request, not two. Reviewer mutation evidence: moving either dedupe lookup outside the transaction fails the race tests; removing the pending-only WHERE fails 4 tests.
---

# Maintainability: schema-level idempotency key and indexed lookup for pending Owner requests

## Definition of Done

- [x] owner_action_requests gains an intent fingerprint column with a unique partial index on pending rows, populated by a v15 migration that refuses (without changing data) when pending duplicates already exist
  proof: src/astra/db.py:639 _migrate_v15 (intent_key + idx_owner_action_requests_pending_intent UNIQUE WHERE status='pending'), refusal src/astra/db.py:607; tests test_db.PendingRequestIntentKeyTests (fresh, backfill, refusal, older-db refusal, fault rollback)
- [x] Exact-match request lookups (retry de-duplication) use the indexed intent_key; reconciliation pre-filters by indexed SQL columns (project, task, action, expected_revision) and keeps the semantic intent test in Python by design, documented in code.
  proof: src/astra/service.py:1228 _pending_request_by_intent (WHERE intent_key=? AND status='pending'), used at :1144 and :1200; src/astra/service.py:1329-1346 SQL pre-filter on project_id/task_id/action/expected_revision with the why-comment for the Python semantic test; tests test_state_integrity.test_concurrent_identical_requests_leave_one_pending_row_per_intent_key, test_concurrent_equivalent_manager_requests_create_one_pending_request_and_event, test_concurrent_equivalent_close_requests_create_one_pending_request_and_event, test_direct_reopen_resolves_only_matching_requests, test_direct_close_resolves_only_the_same_residual_set_whatever_the_note, test_approval_resolves_same_intent_twin_and_leaves_other_intent_pending; test_db.test_fresh_database_has_the_intent_key_and_its_indexes; test_state_integrity + test_db: Ran 74 tests OK
- [x] Existing state-integrity dedupe and race tests pass unchanged; full suite green
  proof: tests/test_state_integrity.py unchanged except one added test; full suite tests/run.py: Ran 313 tests OK

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing tests first: v15 fresh schema (intent_key column, unique partial index, pending lookup index), identical pending row refused by the schema
- [x] v15 step: add intent_key + expected_revision columns, backfill in Python, create indexes; refusal probe for duplicate pending requests before any step and inside the step
- [x] service: compute intent_key once (db.owner_request_intent_key); dedupe lookups and INSERTs use it; resolve filters expected_revision and scope in SQL
- [x] migration tests: upgrade with backfill, refusal leaves data untouched, fault mid-step rolls back and retries, older db refused before any step
- [x] concurrent identical requests via separate connections leave one pending row
- [x] update v14 tests whose hard-coded 14 means 'fully migrated'; README schema text
- [x] full suite, node --check, compileall, diff --check

## Progress
- **2026-09-23 17:43 · Claude** — Brainstorm. What the code shows: dedupe in _request_protected_action/_request_protected_project_action is an exact match on (project_id, task_id, action, payload_json text, reason, requested_by, pending), safe only because BEGIN IMMEDIATE serialises SELECT and INSERT; the schema allows any number of identical pending rows. _resolve_pending_requests filters expected_revision and intent by json.loads per row. The intent test is NOT an equality: absent payload fields are skipped, frozenset intents (REOPEN_EQUIVALENT_STATUSES) accept any member, and residual_work items without a status match any status. So no single key can replace the resolve-side intent test without changing who gets resolved. Options: (A) intent_key = hash of the exact dedupe tuple incl. reason and requested_by, unique on pending; plus an expected_revision column derived by json_extract and a partial index for the resolve scope - zero visible change. (B) key without requested_by/reason - also stops SEM-3 twins but changes behaviour: a second Manager or a new reason would get the first person's request back instead of their own row; out of scope (behaviour must not change). (C) move every intent field into SQL json_extract predicates - removes the Python decode but risks subtle type/NULL/residual_work mismatches for no user gain. Doing A. Consequence for DoD 2: the revision filter and the scope lookup move to indexed SQL; the semantic intent comparison stays in Python because it is not a lookup. Recorded so a reviewer can accept or reword DoD 2.
- **2026-09-23 17:44 · Claude** — Plan reasoning: intent_key = sha256 of JSON [project_id, task_id, action, payload_json, reason, requested_by], hashed from the stored payload_json text (not re-canonicalised) so the key matches exactly what the old WHERE payload_json=? compared. Backfill must be Python: SQLite has no sha256 in stdlib builds. The refusal probe groups by the raw columns (GROUP BY treats NULL task_id as equal), so it needs no key and can run before the v15 column exists, i.e. at the database's starting version like the v14 probe. expected_revision column has no declared type (no affinity) and is filled by json_extract(payload_json,'$.expected_revision') in both backfill and INSERT, so '3' vs 3 behaves exactly like the old Python == test. Existing v14 tests that assert user_version == 14 after a full migrate must become SCHEMA_VERSION; the ones asserting 13 after a v14 fault stay.
- **2026-09-23 17:53 · Claude** — DoD 2 left open on purpose. Dedupe (both _request_protected_* paths) now finds the existing request by intent_key (service.py _pending_request_by_intent). _resolve_pending_requests now filters scope, action and expected_revision in SQL on the indexed columns; the per-row expected_revision json.loads is gone. What remains is _request_intent_matches on json.loads(payload_json): it is not a lookup but a semantic test (absent fields skipped, frozenset intents from reopen_task accept any of REOPEN_EQUIVALENT_STATUSES, residual_work items with no status match any status, and it spans requesters). No exact key can reproduce that without changing which requests an Owner action resolves, which the task forbids. Moving it into json_extract SQL (option C) was rejected: NULL-vs-absent and type rules differ from Python == and residual_work cannot be expressed. A reviewer should either reword DoD 2 to 'no per-row decode for the revision filter' or accept it as not done. Other facts: intent_key hashes the stored payload_json text, never a re-dumped payload, so a legacy row serialised differently still matches exactly as the old WHERE payload_json=? did. The unique index is a real backstop: with the lookup stubbed out, the 4-way race leaves one row and the others get IntegrityError (verified by hand, not kept as a test). Four v14 tests asserted user_version == 14 after a full migrate; changed to db.SCHEMA_VERSION, their v14 index and refusal assertions untouched. CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md still says schema target v14; it is a dated snapshot and was not edited. API responses and the request listing now select an explicit column list (OWNER_REQUEST_FIELDS) so the new lookup columns never appear in JSON.
- **2026-09-23 17:56 · Claude** — DoD 2 reworded in place with 'jaira dod --text' (no item added, none superseded) per the ticket author's decision: the semantic intent test in _resolve_pending_requests stays in Python because an exact key would change which requests an Owner action resolves. Widened the code comment at src/astra/service.py:1329 to say why. Focused run test_state_integrity + test_db: 74 OK; full suite not re-run for this comment-only change (last full run 313 OK at 9336ff1).
