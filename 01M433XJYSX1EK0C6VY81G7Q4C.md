---
id: 01M433XJYSX1EK0C6VY81G7Q4C
title: Prevent mixed Manager saves from silently dropping edits
status: pre-process
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
updated-at: 2026-10-04T15:07:35Z
updated-by: Codex
claimed-by: X1CarbonPC-53068
claimed-at: 2026-10-04T15:07:35Z
---

# Prevent mixed Manager saves from silently dropping edits

## Definition of Done

- [ ] A Manager save that combines an actual ordinary edit with a protected status request fails atomically with a clear error; task, revision, events, requests and notifications remain unchanged.
- [ ] Service tests cover all persisted ordinary fields, entering and leaving protected statuses, normalized unchanged form values, ordinary Manager edits and direct App Owner edits; read-only roles remain refused.
- [ ] HTTP tests prove status 400 and no partial writes or requests; browser verification proves the entered form values remain available after refusal.
- [ ] Removing the service guard makes the regression fail; focused and full Windows suite, LF and diff hygiene and independent review pass before publication.

## Options

- [ ] brainstorm
- [x] planning

## Plan

- [ ] Reproduce discarded edits with failing service and HTTP tests; inspect existing form error handling.
- [ ] Compare normalized persisted fields before either protected-request route; refuse mixed saves without writing.
- [ ] Verify retained fields in a synthetic local browser and preserve dedicated lifecycle routes.
- [ ] Obtain independent review, run guard-removal and full checks, document evidence and move to signoff with the scoped commit.

## Progress
