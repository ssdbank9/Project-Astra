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
updated-at: 2026-09-24T05:31:07Z
updated-by: Claude
outcome-what: "Replaced the single-longest-chain heuristic with full CPM (forward/backward pass, zero-slack) in _critical_path_nodes; marks ALL parallel critical paths; scoped to the dependency network so isolated tasks are never marked; cycle-guard returns no path."
outcome-why: "Owner wanted proper zero-slack CPM that can mark multiple parallel critical paths, not just one longest chain."
question: "Accept, or send back? Two calls to confirm: (1) critical path = single LONGEST chain by duration (not full CPM zero-slack, which can mark several parallel paths). (2) I left the mockup's connector ARROWS between critical bars out of v1 (highlight + label instead) — want those added as a follow-up?"
outcome-resolves: "New multiple-parallel-paths test passes; existing CP tests (linear, longer-branch, isolated, cancelled) still pass; full suite green."
review-summary: |-
  The code at 1c45904 does what the outcome says. In src/astra/service.py, list_tasks calls _add_critical_path after the access checks, so every task gets is_critical_path (False by default). _add_critical_path loads the dependency edges between visible tasks, drops edges that cross projects, and runs _critical_path_nodes once per project. _critical_path_nodes:
  - leaves out cancelled and abandoned tasks
  - keeps only tasks that have at least one active edge (the dependency network)
  - sorts that network topologically (Kahn) and returns nothing if it finds a cycle
  - runs a forward pass and a backward pass using _duration_days (due minus start plus 1, minimum 1, 1 when a date is missing)
  - flags every task with zero slack. This is all longest chains, so two equal parallel chains are both flagged.
  The flag also reaches the CSV export (web.py:571) and the schedule table.

  In static/app.js, renderGantt:
  - draws weekly axis ticks from the start of the chart range
  - adds a "Today" flag in the header and a teal today-line on every row
  - styles critical bars with the "critical" class (crimson #a01f2b, style.css:87 and :284) and critical steps with "crit"
  - adds "On critical path" to the meta column
  index.html:57 has a "Critical path" legend entry. Each row's meta column shows that row's own owner_name, and steps show their owner's initials.

  Tests: test_core has 5 critical-path tests (linear, longer branch wins, isolated, multiple parallel paths, cancelled node). All pass. node --check app.js is clean. The full suite ran 335 tests, all OK.
review-gaps: |-
  1. MEDIUM, test coverage: the isolated-task test does not test the isolated-task rule.
  - test_critical_path_ignores_isolated_tasks builds a project with no dependencies at all.
  - So _critical_path_nodes returns early at `if not has_edge` and never reaches the line that keeps isolated tasks out: `network = {tid for tid in active if preds[tid] or succ[tid]}` (service.py:941).
  - Mutation: in a scratch copy I changed that line to `network = set(active)`. All 5 critical-path tests still passed.
  - A probe then showed what goes wrong. Project with chain A->B (4 days) plus an unlinked 60-day task X: the mutant flags only X and un-flags A and B. The real code flags A and B, not X, which is correct.
  - The definition of done asks for a no-false-positive test on isolated tasks. The only test for it cannot catch the false positive it is named after.
  - Fix: add an isolated task longer than the chain to a project that has a chain, and assert it is not flagged while the chain is.

  2. LOW, tests: no test has a task whose slack is exactly 1 day. Changing the zero-slack check to `<= 1` also passed all tests. A test with a one-day-shorter parallel tail would pin the threshold.

  3. LOW, ticket text is stale:
  - The definition of done still says "longest finish-to-start chain", but the owner decision (2026-09-15) changed the method to full CPM. On a single project the CPM set equals the union of all longest chains, so they agree, but the wording should say so.
  - The `question` field still asks whether to keep the single-longest-chain method, which the rework has already replaced.
  - The DoD proof names service._critical_path/_longest_chain, which no longer exist, and says "62 pass".

  4. LOW, front end:
  - Bars use Date.parse('YYYY-MM-DD'), which gives UTC midnight. The Today line and axis ticks use local midnight. Outside UTC, bars sit up to about half a day off the axis and the Today line.
  - Ticks step by a fixed 7*86400000 ms, so after a daylight-saving change their labels can shift by one day.
  - Ticks start at the chart's start date minus 3 days, not on a week boundary.
  - stateClass gives "critical" priority over blocked and overdue, so a critical bar that is overdue or blocked loses that colour. The meta column still says "Blocked by", but it does not say the task is overdue.
  - No automated test checks the axis, the Today marker or the legend (test_web only checks that today-line has pointer-events: none). No browser pass is recorded.

  5. Known deferral, not a defect: the mockup's connector arrows between critical bars are left out. Critical bars are highlighted and labelled instead.

  Checked with no problem found:
  - Access control is unchanged. The project check and membership filter run before the calculation, and a member's view of a project shows the same flags as the owner's (probe).
  - A cycle returns no critical path instead of raising an error.
  - Edges that cross projects are ignored.
review-verdict: "Send back. The critical-path method is correct, the Gantt changes match the definition of done, node --check is clean and all 335 tests pass. One thing is missing: a test that actually checks isolated tasks are never flagged. The existing isolated-task test never reaches the line that enforces the rule, and a mutation removing that line passed every test. Fix: add one test with an isolated task longer than a dependency chain in the same project, assert the isolated task is not flagged and the chain is, and refresh the stale DoD wording and question field. With that test added I would approve. I am confident about the gap; the front-end findings are low severity and only need a decision on whether to fix now or later."
review-check: "1. cd /workspace/project-astra\n2. node --check src/astra/static/app.js. You should see no output (clean).\n3. .venv/bin/python -m unittest tests.test_core -k critical_path -v. You should see 5 tests, all \"ok\".\n4. Show the gap:\n   a. Copy src and tests to a scratch folder.\n   b. In the copy's src/astra/service.py, change `network = {tid for tid in active if preds[tid] or succ[tid]}` to `network = set(active)`.\n   c. Rerun step 3 with PYTHONPATH pointing at the copy's src. All 5 still pass, which means isolated tasks are not really tested.\n5. Behaviour by hand:\n   a. .venv/bin/python -m astra (or however the app starts locally) and log in as owner.\n   b. Create project P with task A (Sep 1-2), then task B (Sep 3-4) that depends on A, then task X (Sep 1 - Oct 30) with no dependency.\n   c. GET /api/tasks?project_id=<P>. You should see is_critical_path true for A and B, and false for X.\n6. Open the dashboard in a browser for P:\n   a. The header row shows weekly date ticks (day number plus month) and a teal \"Today\" flag if today is in range.\n   b. A teal vertical line crosses every row at today.\n   c. The bars for A and B are crimson, and their meta column says \"On critical path\".\n   d. The legend above the chart includes \"Critical path\".\n   e. Each row's meta column shows that task's own owner (or \"Unassigned\").\n7. Full suite: .venv/bin/python tests/run.py. It should end with \"OK\" (335 tests, about 4 minutes)."
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
- **2026-09-24 05:31 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: isolated-task test never reaches the isolation rule (mutant network=set(active) passes); DoD wording/question/proof are stale. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name AYW0QC.
