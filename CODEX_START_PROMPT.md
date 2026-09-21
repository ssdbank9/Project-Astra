# Codex or Claude start prompt — Astra project tracker

Paste the block below to the next implementation agent. The cumulative brief is
`CODEX_HANDOFF_2026-09-20.md`; older dated handoffs are historical snapshots.

---

You are taking over the **Astra project tracker**. Work only in
`C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`
unless the owner explicitly expands scope.

Read these completely before changing anything:

1. `CODEX_HANDOFF_2026-09-20.md` — current implementation, all settled decisions,
   runtime/sharing model, production gates and exact next sequence.
2. The active `AGENTS.md` instructions — especially the Jaira lane rules.
3. `C:\Users\Aly Jafferani\.codex\mistakes.md` and
   `pending-global-mistakes.md` — prevention rules and unresolved synchronization.
4. `docs/design/astra-product-ux-baseline.md` — product surface and UX contract.
5. `docs/design/governed-drag-drop-contract.md` — mutation, locks, files,
   schedule and recovery contract.

Then report, before editing:

```powershell
jaira next --per-lane --json
jaira resume
.venv\Scripts\python.exe tests\run.py
node --check src\astra\static\app.js
git status --short
```

The verified handoff baseline is 102 passing Python tests plus a clean JavaScript
syntax check, but you must recheck the live workspace. Current code, approved
target behavior and production readiness are three different things.

Follow Jaira lane ownership. Claim the selected ticket, use its lane prompt,
record evidence on its checklists and commit its ticket file with the relevant
changes. An agent may move work into `human` or `signoff` but never move it out.

Do not expose the current development server, deploy, create real users, ingest
private sources, configure external AI/providers, send external notifications or
publish real files without explicit owner authorization. Keep private evidence
processing on the owner's machine and expose only authorized shared records.

Start by reading the cumulative handoff, running the live board/test commands and
reporting what you find before making changes.
