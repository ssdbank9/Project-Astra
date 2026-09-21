---
id: 01M2JHKHPFGHBYXK2FFDX8FNA5
title: Cohesive UX shell + feature interoperability
status: backlog
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Turn Astra from a dense board + modal-pile into one cohesive app: a persistent nav shell with switchable views over one shared filter/selection context, features that cross-link, and low-friction in-place actions."
context: "Owner's guiding bar (2026-09-15): Astra is judged on UI/ease-of-use/INTEROPERABILITY, not feature count. Current app = one board + ~8 modals; features work in isolation. This is a FRONT-END rebuild toward a nav shell (backend endpoints already exist). PRIORITY over the 9 Asana feature tickets — Sections/Board/My Work/Calendar should be built INTO this shell, not as standalone screens. Design-first: extend the Option-A design canvas (artifact METAtTHJSL4xSuNrAXXPsR) with the shell + interconnected views + a click-through map, align, then rebuild incrementally. Design ref: astra_project_tracker/design/."
definition-of-done: "Persistent left nav + view tabs (Board / Timeline / Calendar / My Work / Portfolio); switching a view keeps the current filter/selection context; task detail is a docked SIDE PANEL, not a blocking modal; cross-links wired (portfolio card->filtered board, notification/search/critical-path bar->task panel, My Work item->its project); in-place actions (drag card between sections, drag Gantt bar->schedule proposal, inline edit, quick-add); one consistent visual system (Option A palette); responsive; existing tests green; new UI covered where testable."
tags:
  - astra
  - asana
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T12:45:25Z
updated-at: 2026-09-15T13:06:32Z
updated-by: Aly Jafferani
---

# Cohesive UX shell + feature interoperability

## Definition of Done

- [ ] Persistent left nav + view tabs (Board / Timeline / Calendar / My Work / Portfolio); switching a view keeps the current filter/selection context; task detail is a docked SIDE PANEL, not a blocking modal; cross-links wired (portfolio card->filtered board, notification/search/critical-path bar->task panel, My Work item->its project); in-place actions (drag card between sections, drag Gantt bar->schedule proposal, inline edit, quick-add); one consistent visual system (Option A palette); responsive; existing tests green; new UI covered where testable.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-15 13:06 · Aly Jafferani** — DESIGN APPROVED by owner (2026-09-15). Canvas artifact METAtTHJSL4xSuNrAXXPsR v4. Shell = Option A palette + left nav (Views: Board/Timeline/Calendar/My Work/Portfolio; Entities>Projects) + view tabs + DOCKED side panel (not modal). Interoperability map captured (portfolio card->filtered board; notification/search/critical-bar->task panel; My Work->its project; drag card between sections; drag Gantt bar->schedule proposal; inline edit; quick-add). TIMELINE VIEW must be a DETAILED SWIMLANE Gantt (per owner's reference sketch): swimlanes grouped by workstream/owner with the accountable owner highlighted; month->week grid; a duration bar per workstream + per-SUBTASK bars across weeks, each bar labelled with dates AND carrying that subtask's OWN owner avatar (subtask owners can differ from workstream owner); critical-path bars highlighted crimson; legend for critical-path + owner-per-task. Working files: astra_project_tracker/design/Shell.dc.html + ShellTimeline.dc.html. Next: front-end rebuild incrementally toward this (backend endpoints exist).
