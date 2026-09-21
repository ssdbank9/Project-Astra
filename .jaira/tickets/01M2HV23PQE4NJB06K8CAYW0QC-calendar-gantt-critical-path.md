---
id: 01M2HV23PQE4NJB06K8CAYW0QC
title: Calendar Gantt + critical path
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Bring the approved Option-A dashboard to life: give the Gantt a real calendar/date axis with a Today line, and derive + highlight each project's critical path (the driving dependency chain), showing each subtask's own owner."
context: |-
  Astra tracker. Owner approved Option A design (Artifact METAtTHJSL4xSuNrAXXPsR) and asked to build the calendar Gantt + critical path into the real app; cloud hosting deferred.
  Today app.js renderGantt positions bars by date over a computed span but has NO date axis, NO today line, and NO critical path. Dependencies already exist (task_dependencies, FS-only, cycle-safe) so critical-path derivation is real, not mocked.
  Critical path = longest FS dependency chain by summed task duration, per project (duration = due-start+1 days, min 1; missing dates -> 1). Mark is_critical_path in list_tasks; front-end styles bars crimson (#a01f2b) per the design and adds a legend + Today line + weekly axis.
  Remember (owner req, see 9R7A87): each subtask has its OWN owner along the path — show per-row owner. Files: astra_project_tracker/src/astra/service.py (list_tasks), static/app.js (renderGantt), static/style.css. Design ref: astra_project_tracker/design/Main.dc.html.
definition-of-done: "list_tasks returns is_critical_path per task, computed per project as the longest finish-to-start dependency chain by duration (cancelled/abandoned excluded, isolated tasks never flagged); the Gantt renders a weekly calendar axis, a Today marker, and critical-path bars styled distinctly with a legend entry; each row shows its own owner; unit tests cover a linear chain, a branch where the longer chain wins, and no-false-positive on isolated tasks; node --check clean; existing tests green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T06:11:25Z
updated-at: 2026-09-19T06:14:43Z
updated-by: Aly Jafferani
outcome-what: "Replaced the single-longest-chain heuristic with full CPM (forward/backward pass, zero-slack) in _critical_path_nodes; marks ALL parallel critical paths; scoped to the dependency network so isolated tasks are never marked; cycle-guard returns no path."
outcome-why: "Owner wanted proper zero-slack CPM that can mark multiple parallel critical paths, not just one longest chain."
question: "Accept, or send back? Two calls to confirm: (1) critical path = single LONGEST chain by duration (not full CPM zero-slack, which can mark several parallel paths). (2) I left the mockup's connector ARROWS between critical bars out of v1 (highlight + label instead) — want those added as a follow-up?"
outcome-resolves: "New multiple-parallel-paths test passes; existing CP tests (linear, longer-branch, isolated, cancelled) still pass; full suite green."
---

# Calendar Gantt + critical path

## Definition of Done

- [x] list_tasks returns is_critical_path per task, computed per project as the longest finish-to-start dependency chain by duration (cancelled/abandoned excluded, isolated tasks never flagged); the Gantt renders a weekly calendar axis, a Today marker, and critical-path bars styled distinctly with a legend entry; each row shows its own owner; unit tests cover a linear chain, a branch where the longer chain wins, and no-false-positive on isolated tasks; node --check clean; existing tests green.
  proof: service._critical_path/_longest_chain + is_critical_path in list_tasks; app.js renderGantt (weekly axis + Today line + critical bars); style.css .bar.critical/.today-line/.axis-tick; tests test_core.test_critical_path_linear_chain/_longer_branch_wins/_ignores_isolated_tasks/_excludes_cancelled_node; 62 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Service: _duration_days + _critical_path longest-chain (per project, topo/DP), set is_critical_path in list_tasks
- [x] Front-end: weekly calendar axis header + Today line in renderGantt
- [x] Front-end: critical-path bar styling + legend entry; keep per-row owner visible
- [x] Tests: linear chain, longer-branch wins, isolated tasks not flagged

## Progress
- **2026-09-15 06:15 · Aly Jafferani** — Critical path = longest FS dependency chain by summed duration, computed PER PROJECT (topo + DP over the acyclic dep graph). Rules: cancelled/abandoned nodes excluded (a cancelled mid-node breaks the chain), isolated tasks never flagged, needs >=2 nodes. Front-end: weekly calendar axis header + teal Today line + crimson critical bars (#a01f2b) matching the design; each row keeps its own owner (per owner req on 9R7A87). Deliberately NOT included yet: inter-bar connector arrows from the mockup (row-based layout makes cross-row SVG connectors a separate polish) — bars are highlighted + labeled 'On critical path' instead. No real-browser visual pass (no browser in session).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): replace single-longest-chain critical path with full CPM (forward+backward pass, zero-slack) that can mark MULTIPLE parallel critical paths. Sent back to reimplement the algorithm.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (full CPM forward/backward zero-slack in _critical_path_nodes; marks multiple parallel critical paths; isolated tasks never flagged; cycle-safe). Known deferral: mockup connector ARROWS still omitted (highlight+label instead) - note in review-gaps. In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
