---
id: 01M433XJYSX1EK0C6VY81G7Q4C
title: Prevent mixed Manager saves from silently dropping edits
status: in-progress
ready: true
creator: Codex
assignee: Codex
goal: Apply Aly R1 atomic-rejection decision so status requests never silently discard ordinary task edits.
context: "A Manager who edits Title and requests cancellation receives success, but Title is silently discarded. update_task returns the protected-status request before the ordinary write. Aly selected atomic rejection with retained form values in the launch decisions and authorized fixes then development on 2026-10-04. Compare actual normalized field changes; echoed unchanged form fields must still allow a status-only request. Preserve dedicated reopen and submission actions."
definition-of-done: Mixed ordinary edits and protected Manager status requests are refused atomically and form values are retained.
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-04T09:29:01Z
updated-at: 2026-10-04T18:18:16Z
updated-by: Codex
claimed-by: X1CarbonPC-53068
claimed-at: 2026-10-04T15:07:35Z
outcome-what: "Planned failing service and HTTP regressions, persisted-field comparison and browser retention verification."
outcome-why: Aly selected R1 atomic refusal and authorized fixes followed by development.
outcome-resolves: A bounded method for preventing silent discarded edits without changing lifecycle policy.
---

# Prevent mixed Manager saves from silently dropping edits

## Definition of Done

- [x] A Manager save that combines an actual ordinary edit with a protected status request fails atomically with a clear error; task, revision, events, requests and notifications remain unchanged.
  proof: UpdateTaskContractTests.test_manager_mixed_status_request_refuses_without_any_database_write covers six fields and nine transitions with complete SQLite dump comparison.
- [x] Service tests cover all persisted ordinary fields, entering and leaving protected statuses, normalized unchanged form values, ordinary Manager edits and direct App Owner edits; read-only roles remain refused.
  proof: UpdateTaskContractTests normalized-form, ordinary-Manager/direct-Owner and read-only-role controls; existing lifecycle/revision characterization tests pass.
- [x] HTTP tests prove status 400 and no partial writes or requests; browser verification proves the entered form values remain available after refusal.
  proof: AstraWebTests.test_manager_mixed_status_save_is_400_without_any_database_write and role controls; synthetic browser retained every entered field after HTTP400, screenshot outside repo.
- [x] Removing the service guard makes the regression fail; focused and full Windows suite, LF and diff hygiene and independent review pass before publication.
  proof: Both guard-removal regressions fail; 25 focused tests and two progress tests pass; full suite Ran 700 tests in 368.566s, OK (skipped=1); independent code and documentation review PASS; seven staged LF blobs/diff and full-suite hashes verified.

## Options

- [ ] brainstorm
- [x] planning

## Plan

- [x] Reproduce discarded edits with failing service and HTTP tests; inspect existing form error handling.
- [x] Compare normalized persisted fields before either protected-request route; refuse mixed saves without writing.
- [x] Verify retained fields in a synthetic local browser and preserve dedicated lifecycle routes.
- [x] Obtain independent review, run guard-removal and full checks, document evidence and move to signoff with the scoped commit.

## Progress
- **2026-10-04 15:09 · Codex** — Use the existing update_task service seam and compare normalized persisted fields before both protected-request routes. A full form with unchanged fields remains a status-only request. Return ValueError so the existing HTTP 400 form error handling retains inputs. Preserve dedicated lifecycle actions and direct App Owner writes. No schema or UI redesign is required.
- **2026-10-04 15:41 · Codex** — Independent review caught unsupported progress types at the new normalization boundary. Lists, objects and infinity are translated to ValueError locally; ordinary and Owner-save normalization is unchanged. The textarea label includes its contents, so browser verification used observed form name attributes. No UI source change was needed. Default full suite: 700 tests in 368.566s, OK (skipped=1); source hashes unchanged, no new tmp dirs or ResourceWarnings.
