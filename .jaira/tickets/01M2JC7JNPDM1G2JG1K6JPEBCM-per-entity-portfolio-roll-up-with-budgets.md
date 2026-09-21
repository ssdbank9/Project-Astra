---
id: 01M2JC7JNPDM1G2JG1K6JPEBCM
title: Per-entity portfolio roll-up with budgets
status: signoff
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Give each entity a portfolio view that rolls up its projects — task health (open/overdue/critical) and BUDGET — where each project carries a budget that sums into one entity budget, without double-counting cross-entity projects."
context: |-
  Astra tracker. From the Asana-forum review + owner request (2026-09-15): add a per-entity portfolio roll-up (my earlier suggestion #3) AND project budgets that roll up into one entity budget.
  Astra already has Entities -> Projects -> Tasks, so grouping exists; this adds budget as a new concept + an entity-level summary.
  Buildable now, no section 15 gate. OPEN DESIGN DECISIONS (being settled with owner before build): (1) cross-entity double-count — a project can belong to several entities (section 4); section 7 forbids duplicated totals, so a shared project budget must count once; (2) currency — entities span USD (Rupani USA) and PKR (Pakistan), so no blind blended total; (3) planned budget only vs planned+actual/spent.
definition-of-done: "A project has a budget (amount + currency); each entity shows a portfolio roll-up (open/overdue/critical task counts + budget totals); a cross-entity project's budget counts ONCE (never double, per section 7); budgets owner-editable; roll-up hides nothing silently; unit + HTTP tests incl. the cross-entity no-double-count case; existing tests green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T11:11:29Z
updated-at: 2026-09-20T03:10:12Z
claimed-by: X1CarbonPC-37316
claimed-at: 2026-09-15T11:56:49Z
updated-by: Aly Jafferani
outcome-what: Per-entity portfolio roll-up (open/overdue/critical + per-currency budget totals) with project budgets (amount+currency) and a primary-entity flag so cross-entity projects count once; Portfolio dialog + budget controls; 4 new tests (76 total).
outcome-why: Owner asked (from Asana-forum review) for a per-entity portfolio roll-up with budgets summing into one entity budget.
question: "Accept, or send back? (1) A multi-entity project with NO primary set lands in an 'Unassigned' bucket (shown, not counted) until you pick a primary — OK, or default it to the first-listed entity? (2) Budget is planned-only; want actual/spent as the next slice?"
outcome-resolves: "DoD met: project budget (amount+currency), per-entity roll-up with per-currency totals, cross-entity counted once via primary entity, owner-only edits, scope-limited, unit+HTTP incl. no-double-count case, existing tests green."
review-summary: "Per-entity portfolio roll-up with planned budgets, correct against all three accepted calls. portfolio_rollup iterates each project once and assigns it to a single entity via _rollup_entity_id: primary_entity_id if set, else the sole linked entity, else None -> Unassigned bucket (shown, never summed). Genuine no-double-count. Budgets stored per-currency in a dict, never blended; currency upper-cased at write (default PKR); null budgets skipped (not summed as 0). Scope respected: list_projects/list_tasks are authz-filtered; list_entities used only as a name lookup. Planned-only budget. Owner-only edits (set_project_budget/set_primary_entity via require_owner; set_primary_entity validates the entity is linked). Meets the accepted DoD."
review-gaps: "One real MEDIUM gap + two minor. (1) MEDIUM: set_project_entities deletes/re-inserts a project's entity links but never reconciles primary_entity_id; if the owner sets a primary then re-files the project to an entity set that drops that primary, primary_entity_id remains and the project rolls up (once) to an entity it is no longer linked to - a silent mis-attribution (not a double-count). Matches the ticket's own 'primary not among linked entities' hint. (2) MINOR: a body of currency=null yields str(None).upper()='NONE' as currency (empty string handled -> PKR, None not); UI never sends this. (3) TEST GAP: the no-primary multi-entity -> Unassigned 'shown, not counted' case the DoD proof claims has no test."
review-verdict: pass-with-notes
review-check: "Read set_project_budget, set_primary_entity, _rollup_entity_id, portfolio_rollup, list_projects, list_tasks, _due_state, set_project_entities, _attach_entities; web portfolio/budget/primary-entity endpoints; app.js portfolio+budget UI. Ran test_core.test_budget_rollup_counts_cross_entity_once_and_sums_per_currency, test_primary_entity_must_be_a_linked_entity, test_portfolio_is_scope_limited, test_web.test_portfolio_and_budget_over_http -> all pass. No full suite, no edits. No real-browser pass (yolo-chrome down)."
---

# Per-entity portfolio roll-up with budgets

## Definition of Done

- [x] A project has a budget (amount + currency); each entity shows a portfolio roll-up (open/overdue/critical task counts + budget totals); a cross-entity project's budget counts ONCE (never double, per section 7); budgets owner-editable; roll-up hides nothing silently; unit + HTTP tests incl. the cross-entity no-double-count case; existing tests green.
  proof: schema v7 (projects.budget_amount/budget_currency/primary_entity_id); service set_project_budget/set_primary_entity/portfolio_rollup (per-currency, primary-entity single-count, Unassigned bucket, scoped); GET /api/portfolio + POST /budget + /primary-entity; Portfolio dialog + budget/primary controls in People filing; tests test_core.test_budget_rollup_counts_cross_entity_once_and_sums_per_currency/test_primary_entity_must_be_a_linked_entity/test_portfolio_is_scope_limited, test_web.test_portfolio_and_budget_over_http; 76 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v7: projects.budget_amount, budget_currency (default PKR), primary_entity_id
- [x] Service: set_project_budget + set_primary_entity (owner-only, primary must be a linked entity); portfolio_rollup (per-entity task health + per-currency budget, each project counted once via primary/single entity, Unassigned bucket, scope-limited)
- [x] API: GET /api/portfolio; POST /api/projects/{id}/budget; POST /api/projects/{id}/primary-entity
- [x] UI: Portfolio button -> per-entity roll-up dialog; budget + primary-entity controls in People project-filing
- [x] Tests: budget sums per currency, cross-entity project counted once (toward primary), portfolio scope-limited

## Progress
- **2026-09-15 12:02 · Aly Jafferani** — Per owner's 3 approved calls: (1) cross-entity NO double-count — each project counts once via its primary_entity_id (or its sole linked entity; multi-entity with no primary -> Unassigned bucket, shown not counted); (2) currency per project (default PKR, upper-cased), entity roll-up shows per-currency subtotals, NEVER blended; (3) planned budget only (no actual/spent yet). portfolio_rollup is scope-limited (uses list_projects/list_tasks authz). Task health per entity = open/overdue/critical of that entity's roll-up projects. UI: Portfolio toolbar button -> per-entity cards; budget amount+currency+primary-entity controls in the People project-filing section. No real-browser visual pass (no browser in session).
- **2026-09-15 18:32 · Aly Jafferani** — OWNER ACCEPTED (2026-09-15): no-primary multi-entity project -> Unassigned bucket (shown, not counted); planned-only budget; per-currency subtotals never blended. Proceeding to model review.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. PARKED in signoff - waiting on the App Owner. Verdict: pass-with-notes. Owner question: multi-entity project with no primary -> Unassigned bucket (shown, not counted) - OK, or default to first-listed entity? Budget planned-only - want actual/spent next?
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20: keep a multi-entity project with no primary entity in a visible Unassigned bucket; never default to the first-listed entity. Production budgets include planned, committed and actual/spent amounts with explicit variance; never blend currencies.
