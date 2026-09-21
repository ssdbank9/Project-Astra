---
id: 01M2X47YF0DA7QCQV4QGAX572Q
title: Prototype governed Astra drag-and-drop
status: human
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: Validate the complete approved drag-and-drop state model and A-hybrid interaction before production integration.
context: "Astra's existing design/astra-shell-prototype.html shows the chosen shell direction but does not exercise real drag state. The App Owner approved the recommended A-hybrid and the complete governed drag package recorded on JQY55P: Kanban, Gantt, dependencies, critical path/What-if, files/folders, owner-only cross-project and file actions, Manager operational permissions, locks, bulk actions, Undo/restoration, notifications, responsive fallbacks, and audit behavior. Stop asking further design questions. Build a throwaway in-memory prototype plus a durable production contract. Do not call live APIs or modify production routes/database."
definition-of-done: "A durable Markdown interaction contract enumerates the approved roles, invariants, operation lifecycle, file/batch limits, locks, audit/notification rules, accessibility fallbacks, and a small deep-module interface for later implementation; a self-contained native-HTML A-hybrid logic prototype visibly exposes state, supports free-play and guided happy/conflict/blocked/What-if scenarios across Kanban, Gantt, dependencies, files, cross-project actions, bulk locks, Undo/restoration, and critical-path recalculation without persistence or live mutations; HTML and JavaScript syntax checks pass; desktop and 1024px visual renders are inspected and material defects corrected; limitations and the separate production implementation boundary are explicit."
tags:
  - astra
  - asana
blocked-by: []
related: []
follows: 01M2WNN5PQXBBCD0XTZGJQY55P
commits: []
created-at: 2026-09-19T15:23:32Z
updated-at: 2026-09-20T02:01:27Z
claimed-by: X1CarbonPC-47456
claimed-at: 2026-09-19T15:24:31Z
updated-by: Aly Jafferani
outcome-what: "Created a durable governed drag-and-drop contract and a self-contained A-hybrid native-HTML logic prototype with real Kanban/timeline/dependency/file drop targets, free-play controls, six guided scenarios, visible locks/approvals/notices/audit state, What-if isolation, bulk atomicity, Undo and responsive layouts."
outcome-why: "The approved drag package crosses authorization, scheduling, storage, locking and audit concerns; validating one coherent state model before production work reduces hidden contradictions and implementation rework."
outcome-resolves: "Every approved decision is traceable in one production contract and can be exercised safely in-memory without modifying Astra's live routes, database, files or notifications."
question: "Please open the governed drag prototype and confirm whether the visible state, guided edge cases, and A-hybrid interaction feel right before production implementation is split into test-first tickets."
---

# Prototype governed Astra drag-and-drop

## Definition of Done

- [x] A durable Markdown interaction contract enumerates the approved roles, invariants, operation lifecycle, file/batch limits, locks, audit/notification rules, accessibility fallbacks, and a small deep-module interface for later implementation; a self-contained native-HTML A-hybrid logic prototype visibly exposes state, supports free-play and guided happy/conflict/blocked/What-if scenarios across Kanban, Gantt, dependencies, files, cross-project actions, bulk locks, Undo/restoration, and critical-path recalculation without persistence or live mutations; HTML and JavaScript syntax checks pass; desktop and 1024px visual renders are inspected and material defects corrected; limitations and the separate production implementation boundary are explicit.
  proof: docs/design/governed-drag-drop-contract.md and design/astra-drag-drop-prototype.html; reducer scenario check and 1440/1024 visual QA complete

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Consolidate every approved JQY55P decision into explicit roles, operations, invariants, and prototype scenarios.
  proof: JQY55P decision record consolidated into docs/design/governed-drag-drop-contract.md role/operation/invariant sections
- [x] Write docs/design/governed-drag-drop-contract.md with the lifecycle, small DragCoordinator interface, validation/locking/transaction seams, audit and notification outcomes, accessibility fallbacks, and production boundaries.
  proof: docs/design/governed-drag-drop-contract.md: approved authority matrix, lifecycle, DragCoordinator interface, domain rules, audit/accessibility/production gates
- [x] Build design/astra-drag-drop-prototype.html as an A-hybrid single-file logic prototype with a pure reducer, visible current state, free-play actions, and guided walkthroughs.
  proof: design/astra-drag-drop-prototype.html: A-hybrid single-file shell with pure DragModel reducer, visible state, free-play controls and guided cases
- [x] Exercise Kanban, Gantt, dependency, critical-path/What-if, files/folders, cross-project Owner-only, bulk-lock, conflict, Undo/restoration, and approval outcomes in the prototype.
  proof: Reducer scenarios pass for protected Kanban, Viewer rejection, 250MB batch rejection, atomic lock conflict, private What-if and Undo; UI includes dependency, cross-project, file and bulk paths
- [x] Run HTML parsing and JavaScript syntax checks, then verify required scenario and decision markers.
  proof: HTMLParser OK; embedded JavaScript compiled with new Function; rg -F -e verified reducer and six required guided scenarios
- [x] Render and inspect desktop and 1024px layouts, correct material visual defects, and record the separate production implementation boundary.
  proof: Headless Chrome renders visually inspected: Kanban at 1440x1000 and 1024x900, Timeline at 1440x1000, Guided cases at 1440x1000; production boundary visible in prototype and contract

## Progress
- **2026-09-19 15:24 · Aly Jafferani** — BRAINSTORM: The current shell prototype shows layout and read-only controls but cannot answer whether the approved drag rules remain understandable when locks, approvals, dependency effects, owner-only actions, bulk atomicity, file limits, Undo, and What-if state interact. Option 1 is to add cosmetic dragging to the shell; cheap, but it would hide business-state failures. Option 2 is a separate plain state-machine demo; clearer logically, but divorced from the chosen A-hybrid experience. Option 3 is recommended: write one durable production contract, then build a self-contained A-hybrid logic prototype around a pure in-memory reducer with visible state, free play, and guided edge cases. This costs more prototype code but validates both the governed interaction and its presentation without touching production data.
- **2026-09-19 15:26 · Aly Jafferani** — PRE-PROCESS DESIGN: use a new design/astra-drag-drop-prototype.html rather than overloading the visual-comparison file. The page will reuse the approved A-hybrid language but answer a different question: whether the governed state model is understandable under awkward cases. Its pure reducer is the prototype's portable logic; the durable production seam is a deep DragCoordinator interface with preview, commit, cancel, and restore operations hiding authorization, graph, lock, storage, audit, and notification implementation. The HTML remains throwaway and disconnected from live routes.
- **2026-09-20 02:01 · Aly Jafferani** — VERIFICATION FINDING: the first reducer exercise found that a Manager's critical-task change in private What-if mode was being routed to live Owner approval before simulation logic. The branch order was corrected so the simulation changes only private state and approval begins only when the revision is submitted. The full reducer scenario set then passed. Visual inspection found the A-hybrid Kanban, Timeline and guided-case layouts readable at 1440px; the 1024px layout intentionally moves the state inspector below the main surface and keeps the board horizontally scrollable.
