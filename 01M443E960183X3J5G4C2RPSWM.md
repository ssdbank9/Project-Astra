---
id: 01M443E960183X3J5G4C2RPSWM
title: Limit designated approvers to acceptance requests
status: signoff
ready: true
creator: Codex
assignee: Codex
goal: Apply Aly selected Q1 rule without widening task assignment or project Manager powers.
context: "Task approver designation currently permits every protected task request, including holds, reopens and schedule decisions. Aly selected keeping Chairman and viewers eligible for reviewer/approver oversight while limiting designation to acceptance recommendations. After A0, importer and mixed-save repairs, Aly authorized fixing then selected development and confirmed login/go. Enforce the rule in service.py, separate acceptance from general protected-request UI permissions, and verify every affected role. Existing protected requests remain historical records; final acceptance stays with App Owners."
definition-of-done: "Designation permits acceptance requests only, verified at service, HTTP and browser layers with Manager and Owner powers preserved."
tags: []
blocked-by: []
related: []
commits:
  - bb07b6ca844a43dfdc11d3f83dca462822f6608f
created-at: 2026-10-04T18:39:54Z
updated-at: 2026-10-05T14:14:36Z
updated-by: Codex
claimed-by: X1CarbonPC-55344
claimed-at: 2026-10-04T18:40:24Z
outcome-what: "Q1 approver permissions are narrowed to acceptance recommendations, with service lock revalidation, separate UI capability, importer eligibility preservation and role-specific HTTP/browser coverage."
outcome-why: "Designated approvers previously inherited every protected request. Aly selected acceptance-only authority for Chairman and viewers while preserving Manager and App Owner powers."
outcome-resolves: "The authorized Q1 policy is implemented and independently reviewed. The ticket is ready for Aly signoff; no deployment, account creation or merge was performed."
review-summary: "Independent review PASS on authority scope, service seam, UI controls and eligibility; final review additions cover HTTP revalidation and pending submission state."
review-gaps: "No remaining Q1 defect found. Windows symlink check remains unverified; hosted, real-user, load, backup and assistive-device checks remain outside this ticket."
review-verdict: PASS
review-check: Reviewer read the diff without editing. Three guard removals fail as required. Full suite and actual synthetic browser pass. Plan artifact rereview passes.
---

# Limit designated approvers to acceptance requests

## Definition of Done

- [x] Chairman and project viewers remain selectable as reviewers and approvers; assignment and collaborator restrictions remain unchanged.
  proof: tests/test_approver_permissions.py; tests/test_web.py Q1 dialog and HTTP cases
- [x] Designation as a task approver permits requesting acceptance of pending submitted work only. It grants no hold, reopen, return-for-changes, schedule-decision or other protected-action right; independent Manager authority and final App Owner decisions remain intact.
  proof: src/astra/service.py:_can_request_protected_action and locked recheck; tests/test_approver_permissions.py
- [x] Service and HTTP tests cover affected roles, duplicate acceptance requests, removed designation/access, and authorization revalidation inside the write transaction without a partial request.
  proof: tests/test_approver_permissions.py; tests/test_web.py; tests/test_import.py; tests/test_state_integrity.py
- [x] The task dialog offers only permitted actions and explains the acceptance recommendation accurately; Node render tests and an actual synthetic browser check pass.
  proof: tests/test_web.py AstraDetailDialogStatusGateTests; synthetic viewer and Chairman browser
- [x] Guard-removal checks, independent read-only review, the full Windows suite and staged LF/diff hygiene pass; update the authorization documentation and handoff before publication and leave acceptance to Aly.
  proof: Temp/astra-q1-full-20261005-result.json; Temp/astra-q1-mutations-20261004-result.json; independent read-only review

## Options

- [ ] brainstorm
- [x] planning

## Plan

- [x] Pin the selected Q1 permission contract with failing service, HTTP and dialog regressions; preserve legacy request-execution tests as historical fixtures.
- [x] Narrow the common service request seam and recheck authority under the write lock; split acceptance permission from general protected requests in the dialog.
- [x] Verify reviewer/importer/template eligibility, transaction races, Manager and Owner controls, guard removal and actual browser behavior.
- [x] Obtain independent review, run the full suite, update exact evidence and publish the scoped code/ticket/documentation commit to signoff.

## Progress

- **2026-10-04 18:41 · Codex** — Use one action-aware permission check in service.py before the request and again under the write lock. General protected-request UI permission becomes Manager-only; a separate acceptance flag includes designated approvers. Existing historical hold requests remain decidable; no pending request is deleted or migrated. Preserve Chairman assignment and collaborator restrictions.
