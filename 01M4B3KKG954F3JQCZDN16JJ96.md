---
id: 01M4B3KKG954F3JQCZDN16JJ96
title: Allow owners to rename an entity without breaking project links
status: review
ready: true
creator: Codex
assignee: Codex
goal: Add an owner entity rename option with stable entity IDs and recorded old/new names.
context: Aly selected a separate Rupani group of Colleges entity for Rupani IB School on 2026-10-07 and requested the ability to rename it. Existing People and access has Add/Deactivate/Reactivate but no rename action. Preserve entity/project identities and current owner-only settings permissions.
definition-of-done: "Owner rename UI and HTTP/service path work; IDs and project filing stay unchanged; old/new/actor audit recorded; blanks, invalid names, duplicates and unauthorized roles refused without partial writes; browser, full suite, guard mutation and independent review pass."
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-07T11:57:29Z
updated-at: 2026-10-07T12:24:52Z
updated-by: Codex
claimed-by: X1CarbonPC-21680
claimed-at: 2026-10-07T12:02:00Z
outcome-what: "Owner entity rename with stable IDs, preserved filing, transactional audit and clear form feedback."
outcome-why: Aly requested a rename option and selected a separate entity.
outcome-resolves: "Service, HTTP roles and browser checks pass; full suite 745 OK."
review-summary: "Independent read-only review passed source, role boundaries, atomic audit, stable links and final feedback correction."
review-gaps: Windows symlink check skipped. Actual user-session re-login after local restart remains pending; synthetic browser workflow passed.
review-verdict: PASS
review-check: "Parent full suite 745 OK (skipped=1); independent focused 6 OK; three guard-removal probes caught; synthetic browser success, retained filing, audit and duplicate-error feedback verified."
---

# Allow owners to rename an entity without breaking project links

## Definition of Done

- [x] Owner rename UI and HTTP/service path work; IDs and project filing stay unchanged; old/new/actor audit recorded; blanks, invalid names, duplicates and unauthorized roles refused without partial writes; browser, full suite, guard mutation and independent review pass.
  proof: tests/test_entity_rename.py: 6 tests pass independently and in parent; full suite Ran 745 tests in 746.073s OK (skipped=1); 3 guard-removal probes caught. Synthetic browser rename/history/retained filing and success-then-duplicate feedback pass. Independent workplan_review final PASS. Actual local server activated; user re-login pending.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-07 12:16 · Codex** — Approved entity created and school project filed in real authenticated UI. Rename implementation independently reviewed; 6 focused tests and 3 guard-removal probes pass. Synthetic browser rename preserves checked filing and records history; success followed by duplicate refusal restores alert/error styling. Current live DB backed up before activation. Full suite still running; local server activation and push pending.
