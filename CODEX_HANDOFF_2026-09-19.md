# Astra — Codex handoff log (2026-09-19)

Prepared for: **Codex**, to continue Astra while Claude's usage limit resets.
Workspace: `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`
App version: `0.1.0`  ·  DB schema: **v9**  ·  Test suite: **102 tests, all green** (`python tests/run.py`, ~55s)

> This is a *status + next-actions* handoff. For product intent, roles, entities, and the
> approved design, read the existing docs (do not re-litigate settled product questions):
> - `CLAUDE_HANDOFF.md` — full architectural/product handoff (note: its "14 tests" line is stale; we're at 102).
> - `CONTEXT.md` — domain glossary (App Owner vs Task Owner vs Project Owner, Assessor, Budget, Proposal…).
> - `README.md` — run instructions.
> - `../CLAUDE.md` (project root) — the **jaira** board rules and lane definitions. **Read this before touching the board.**

---

## 1. TL;DR — where things stand

- The work is tracked on a **jaira** board at `../.jaira/` (25 tickets). Nothing moves itself; a session drives each ticket lane by lane.
- **Baseline is green: 102 unit/HTTP tests pass.** Keep it green — run `python tests/run.py` before and after any change.
- **No ticket has had a real-browser visual pass** — the `yolo-chrome` MCP has been down every session. All UI is code-verified only. This is a known, accepted gap flagged on every ticket.
- The outer git repo has Astra **entirely untracked** (`?? astra_project_tracker/`). The jaira board has **not been shared** (`.jaira/` is gitignored, ticket files untracked). Consequence: the *only* thing tying a commit to a ticket is the **handle in the commit message** — e.g. `fix(QY0WG2): …`. Omit it and `jaira move` refuses the step because the commit list can't be derived.

### Board at a glance

| Lane | Count | Who works it | State |
|---|---|---|---|
| **review** | 7 | **agent (you)** | Reworks are **already done**; each needs the model **review pass** → then move to `signoff`. |
| **signoff** | 5 | **person only** | Waiting on the **App Owner** to accept or send back. You may NOT move these out. |
| **backlog** | 13 | agent (via brainstorm→…) | Not started. `F9HBSJ` is **gated** on owner section-15 decisions. |

⚠️ The claims on the review/signoff tickets are **abandoned** (last renewed ~90h ago). **Re-claim before working** (`jaira claim <id>`).

---

## 2. How to run

```powershell
# from astra_project_tracker/
python tests\run.py            # 102 tests, ~55s, must stay green. Runner injects src/ on sys.path.

# app (optional, local only):
python -m venv .venv
.venv\Scripts\python -m pip install -e .
python -m astra                # serves locally; data home %LOCALAPPDATA%\AstraProjectTracker
                               # override data dir for testing with env ASTRA_HOME
```

Stdlib-only app (only runtime dep is `tzdata` on Windows, data-only). Do **not** add dependencies without a reason.

### Source map (`src/astra/`)
- `db.py` — SQLite schema + **migrations (currently through v9)**. Schema is versioned; add a new `vN` migration, never edit an old one.
- `service.py` — all business logic + authorization at the service boundary (the big file: tasks, criticality, subtasks, notifications, schedule proposals, templates, attachments, portfolio, search/export, critical path).
- `web.py` — HTTP routes (auth + CSRF on mutations, `_require_user` / `_require_owner`).
- `auth.py` — sessions, login, sign-out-everywhere.
- `static/{index.html, app.js, style.css}` — the single-page UI.
- `__main__.py` — entrypoint (`python -m astra`).

---

## 3. The jaira workflow you must follow (per ticket)

Read `../CLAUDE.md` "This board's lanes" first. In short, for a `review`-lane ticket:

```bash
jaira claim <id>                                  # take it (claims are stale — re-claim)
jaira show <id> --for-lane review --json          # get the lane prompt + the diff to judge
# ... do the model review pass: read the diff, run the tests, judge Standards + Spec ...
jaira move <id> --to signoff \
  --review-summary "<what the change does>" \
  --review-gaps "<material gaps / notes, or 'none'>" \
  --review-verdict "pass | pass-with-notes | fail" \
  --review-check "<what you actually read/ran to verify>"
```

Then **commit the ticket file with the code** in one commit, message naming the handle:
`review(<HANDLE>): model review pass → signoff`. (Board unshared → the handle in the message is what makes the commit list derivable.)

You **cannot** move `signoff`/`human` tickets onward — those are the App Owner's. You may only move work *into* them.

---

## 4. REVIEW lane — 7 tickets ready for the review pass (your main queue)

Each of these was **sent back by the owner, reworked, and the rework is complete** (see each `outcome-what`). They now sit in `review` awaiting the model review pass, then `move --to signoff`. Verify the rework against the owner decision, run the suite, write the review outputs.

1. **`QY0WG2` — Criticality: sorting + confirmation workflow**
   - Owner decision: don't hard-code criticality-primary; provide **both** sort modes, user-selectable.
   - Rework done: `list_tasks(sort='criticality'|'due_date')` with two ORDER BY branches; `/api/tasks?sort=` + Export CSV sort param; a "Sort by" toolbar dropdown; default stays criticality. `confirm_criticality` writes a dedicated `criticality_changed` audit event (actor/old/new/reason); `update_task` can't change criticality directly.
   - Review must confirm: both orderings correct, Unrated conspicuous (not hidden), unknown-mode fallback, audit record shape, tests cover both orders + HTTP `?sort=`.

2. **`Y3WC71` — Exports and search**
   - Owner decision: **drop** the leading `# Astra export — as of …` comment row; header row must be first for clean Excel/parser import.
   - Rework done: comment row removed from both CSV exports (tasks + final results); header now first; as-of date moved into the download **filename** via `_as_of_slug`.
   - Review must confirm: CSV header-first, dated filename, scope-isolation still enforced (search + export via authz'd `list_tasks`), HTTP test asserts header-first.

3. **`AYW0QC` — Calendar Gantt + critical path**
   - Owner decision: replace single-longest-chain heuristic with **full CPM** (forward/backward pass, zero-slack) that can mark **multiple parallel** critical paths.
   - Rework done: `_critical_path_nodes` now full CPM; marks all parallel critical paths; scoped to the dependency network (isolated tasks never flagged); cycle-guard returns no path; cancelled/abandoned excluded.
   - Review must confirm: CPM correctness (parallel paths, zero-slack), isolated-node handling, cycle safety. **Known deferral:** mockup connector *arrows* between critical bars still omitted (highlight + "On critical path" label instead) — call this out in review-gaps.

4. **`8B9NBH` — Project & task templates**
   - Owner decision: templates should carry a **suggested owner** (role/name-based), not always unassigned.
   - Rework done: templates capture a suggested owner (by display name); instantiation pre-fills that owner if still an assignable project member, else leaves unassigned. Depends on `6G89SJ` (task attachments) which is also in review.
   - Review must confirm: suggested-owner carry + graceful fallback; structure-only snapshot still excludes history/evidence (status→draft, progress reset); attachment links carried; offsets reapplied; owner-only.

5. **`6G89SJ` — Attachments on tasks**
   - Latest change: attachment **deletion gated to App Owner only** (`require_owner` in `remove_task_attachment`); Remove control hidden from non-owners; adding still allowed for project managers.
   - Review must confirm the deletion authz reading and that the http-served UI "open" = copy-path/download (can't open `file://`). This ticket **unblocks `8B9NBH` and `CS93C6`** — review it early.

6. **`CS93C6` — Final results repository (deliverables database)**
   - Owner decision: every final result is an **explicit manual mark** (removed auto-add of accepted submissions).
   - Rework done: auto-add on acceptance removed; manual submission/attachment mark only; tests + UI text updated.
   - Review must confirm: no auto-on-accept path remains; unmark works; attachments must be marked explicitly.

7. **`5WZ4A8` — Project schedule dates with change history**
   - Latest change: project **start/target markers** added to the Gantt timeline (dashed lines + labels + legend), scaled to range, single- vs multi-project labelling.
   - Review must confirm: project schedule edit lives in People/admin config with audit log; markers render from the config.

---

## 5. SIGNOFF lane — 5 tickets waiting on the **App Owner** (Codex cannot move these)

Each passed model review and needs **the owner to accept or send back** by answering its question. Surface these to the owner; do not attempt to advance them.

- **`9R7A87` Parent/subtask hierarchy + roll-up** (verdict: pass) — Q: roll-up counts only **direct** children, "completed" = accepted lifecycle state — is that the granularity wanted?
- **`Z24KVH` Durable in-app notification inbox** (verdict: pass-with-notes) — Q: confirm owner is **not** self-notified of own actions; in-app only, outbound email deferred to section 15. (Note: idempotency guard is defensive-only — event_id never actually reused; not a bug.)
- **`JZACMP` Schedule model baseline/current/pending** (verdict: pass) — Q: OK that direct date edits still change "current" immediately (propose/approve is the governed *alternative*, not the only path)? Baseline captured once, never editable — intended?
- **`XDA2JR` Project calendar: workweeks + holidays** (verdict: pass-with-notes) — Q: confirm the **permissive default** (all 7 days working, no holidays, nothing blocked); mechanism ready if a project later restricts its calendar.
- **`JPEBCM` Per-entity portfolio roll-up with budgets** (verdict: pass-with-notes) — Q: multi-entity project with no primary → "Unassigned" bucket (shown, not counted) — OK, or default to first-listed entity? Budget is planned-only — want actual/spent next?

---

## 6. BACKLOG — 13 tickets, not started

Work these via the full route (backlog→brainstorm→todo→pre-process→in-progress→review). Pick with `jaira next --json` / `jaira list --actionable --json`.

- **`F9HBSJ` Daily summary + notification policy** — ⚠️ **GATED**: needs owner **section-15 decisions** (notification channel, additional recipients, external email delivery, escalation rules, scheduler/host). Do **not** start until the owner supplies these. Builds on `Z24KVH` (in-app inbox, done).
- `TRPV3J` Backups and restore
- `6BXYJZ` Production security and deployment
- `KK400X` AI first-pass: propose the board from minutes/notes/emails (the Assessor/Proposal flow — see CONTEXT.md)
- `C86ZMY` Sections: group tasks within a project
- `A48JEX` Board (Kanban) view: sections as columns
- `RWMRKM` My Work: personal cross-project task view
- `2Z8AH5` Custom fields on tasks
- `4G3NY0` Task calendar (month) view
- `PRJAD8` Goals with progress roll-up
- `S1C6PN` Workload / capacity view
- `386TA6` Project status updates
- `X8FNA5` Cohesive UX shell + feature interoperability (the point-and-click shell that replaces current `prompt()`-based flows, e.g. template instantiation)

---

## 7. Cross-cutting rules & caveats (don't relearn these the hard way)

- **Authorization at the service boundary**, not just routes: scope checks (project membership / `can_view_project` / `can_manage_project`) live in `service.py`; `web.py` adds auth + CSRF. New endpoints must enforce scope in the service, and tests must include a **scope-isolation** case.
- **Never invent facts/percentages.** Roll-ups report accepted/total separately from declared progress; the Assessor only *proposes*, the owner applies.
- **Schema migrations are append-only.** Add `vN`; never mutate a shipped migration. Baseline schedule columns are single-writer (`_ensure_baseline`) — snapshot once, never overwrite.
- **Commit the ticket file in the same commit as the code, with the handle in the message** — required for the board and (board being unshared) required for the commit list to derive at all.
- **Do not** connect accounts, ingest private data, upload sources to any AI provider, send email/notifications externally, expose the server to a network, touch the Email Project Organizer, move archive files, or deploy — without explicit owner authorization (per `CLAUDE_HANDOFF.md` §1).
- **Real-browser acceptance is unverified everywhere.** If `yolo-chrome` comes back up, a visual pass on the Gantt/critical-path (`AYW0QC`), portfolio (`JPEBCM`), and inbox (`Z24KVH`) would close the biggest verification gap.

---

## 8. Suggested order for Codex

1. Re-claim and run the **review pass** on the 7 review tickets, `6G89SJ` first (it unblocks `8B9NBH` + `CS93C6`), moving each to `signoff`. Keep the suite at 102+ green.
2. Leave the 5 `signoff` tickets for the App Owner; present their questions (§5) so the owner can accept/send-back.
3. Only then start backlog work — and **not** `F9HBSJ` until the owner answers the section-15 questions.
