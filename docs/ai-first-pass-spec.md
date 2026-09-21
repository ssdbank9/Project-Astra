# AI first-pass — design spec

Settled through a grilling session on 2026-09-15. Terms in **bold** are defined in
[`CONTEXT.md`](../CONTEXT.md). This is the design for jaira ticket `KK400X`. It is design
only — building it stays gated on the App Owner explicitly turning the capability on for a
run (nothing reads the archive or calls a provider before that).

## Purpose

A provider-swappable **Assessor** reads normalized **Evidence** from EPO's archive and
produces **Proposals** — create-or-update Tasks — for the **App Owner** to review, correct,
and approve. Nothing touches the live board without approval; nothing leaves the machine
without per-run authorization.

## Flow

1. **Evidence source.** `_machine/` under `D:\DropBox\Self\Rupani`. The Assessor starts at
   `catalog.jsonl`, follows `thread.md` / `manifest.json`, and honors `scope.json`: reads only
   inside `_machine`, only `is_current` content, flags OCR-derived figures as unverified, and
   never opens the authoritative originals by default.

2. **Incremental by date.** An **Assessment run** reads only Evidence newer than that
   project's **watermark** (per-project, from the catalog `date`). Unchanged Evidence is never
   re-read.

3. **What it proposes.** Tasks with a suggested **Task Owner**, dates, dependencies,
   criticality, and entity/project filing — each **cited to its Evidence** (the `manifest`
   path). Given the project's **current open Tasks** as context, it also proposes **updates**
   to existing Tasks (moved deadline, cancellation, reopening, status change). It creates or
   changes nothing itself.

4. **Filing.** Reuse EPO's existing entity/project filing as the default Proposal; the App
   Owner can **refile/override** any Proposal at review. EPO's entity/project maps onto Astra's
   (new Astra projects created to match where missing); the App Owner confirms the mapping once.
   See [ADR-0002](adr/0002-reuse-epo-filing.md).

5. **Provider & transport.** One Assessor interface, three adapters: **Gemini (API key,
   default)**, **Claude (`claude -p`)**, **Codex (`codex exec`)**, selectable per run. The
   interface hides the transport. See [ADR-0001](adr/0001-assessor-mixed-transport.md).

6. **Review.** A dedicated **Proposals review screen**: Proposals sit in a *Proposed* state
   (off the live board), grouped by entity → project, each **approve / edit / refile /
   reject-with-reason**. Approval applies the create or update. Re-runs are idempotent — a
   Proposal is keyed to its Evidence, so the same record never yields a duplicate.

## Guardrails (handoff §8)

- Evidence text is **untrusted data**, never instructions to the Assessor.
- Uncertainty stays visible; missing owner/date/reason remains a review item.
- The tool learns only from the App Owner's attributable approvals/corrections.
- No auto-create, no auto-publish, no auto-close.
- Model, prompt, and version are recorded on each run.
- Content is sent to a provider only after the App Owner authorizes that run.

## Open dependencies (not part of this design, but gate the build)

- The Gemini API key / Claude / Codex CLIs must be present and authorized on the host.
- The EPO entity/project → Astra entity/project mapping is confirmed once by the App Owner.
