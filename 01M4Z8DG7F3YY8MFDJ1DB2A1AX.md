---
id: 01M4Z8DG7F3YY8MFDJ1DB2A1AX
title: Run Astra real-device and accessibility acceptance
status: in-progress
ready: true
creator: Aly Jafferani
assignee: Codex
goal: "Prepare a concise, repeatable manual checklist for Aly to check Astra on real mobile, tablet, screen-reader and zoom environments before launch."
context: "The release plan in docs/handoff/NEXT_STEPS.md A7 requires real-device and screen-reader checks. The plan says Aly will run the checks with an agent-written 20-minute checklist covering mobile task flows, tablet Board drag, Windows NVDA and 200% desktop zoom. No reusable checklist exists in docs. Keep this as an owner-run acceptance check; do not claim device or assistive-technology verification until Aly reports results."
definition-of-done: Add a plain-language checklist under docs/handoff that fits the planned 20-minute session; names the required devices/apps and exact Astra flows; includes pass/fail observations and a place to record unavailable devices; preserves the approved Add a task wording; does not claim WCAG conformance; independent read-only review and documentation checks pass; transition ticket to human for Aly to run.
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-15T07:46:21Z
updated-at: 2026-10-15T07:58:31Z
updated-by: Codex
outcome-what: "Wrote the 20-minute owner-run real-device and accessibility checklist, linked it from the live handoff, and passed independent review."
outcome-why: "Aly needs a safe, bounded manual acceptance run for mobile, timeline movement, NVDA and desktop zoom."
outcome-resolves: The checklist is ready for Aly to execute; device results remain unverified until she reports them.
claimed-by: X1CarbonPC-46496
claimed-at: 2026-10-15T07:49:11Z
---

# Run Astra real-device and accessibility acceptance

## Definition of Done

- [ ] Add a plain-language checklist under docs/handoff that fits the planned 20-minute session; names the required devices/apps and exact Astra flows; includes pass/fail observations and a place to record unavailable devices; preserves the approved Add a task wording; does not claim WCAG conformance; independent read-only review and documentation checks pass; transition ticket to human for Aly to run.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Read the current A7 requirements and verify the relevant page names and approved task wording in the app and handoff.
  proof: docs/handoff/NEXT_STEPS.md:A7; src/astra/static/index.html:Home, Add a task; src/astra/static/app.js:Board and Move to labels
- [x] Design a timed 20-minute pass/fail checklist for mobile, tablet drag, NVDA and desktop 200% zoom, with explicit evidence and unavailable-device fields.
  proof: Checklist timeboxes sum to 20 minutes including optional iPhone; 17 without it. See docs/handoff/REAL_DEVICE_ACCESSIBILITY_CHECKLIST_2026-10-15.md.
- [x] Write the owner-facing checklist in docs/handoff and link it from the current handoff index and A7.
  proof: docs/handoff/REAL_DEVICE_ACCESSIBILITY_CHECKLIST_2026-10-15.md; linked from docs/handoff/README.md and docs/handoff/NEXT_STEPS.md A7.
- [x] Review the steps for plain language, feasible timing, accessibility evidence limits and consistency; then move the finished checklist to Aly for execution.
  proof: Independent read-only review: no confirmed defects; 20 minutes with optional iPhone, 17 without; row drag and safe-demo instructions verified.

## Progress

