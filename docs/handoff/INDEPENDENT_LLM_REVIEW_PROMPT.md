# Copyable independent review prompt — Astra before deployment

Paste the following into each repository-enabled LLM separately. Supply the
published review-package SHA with it. Use the same target for every reviewer.

---

I am Aly Jafferani, App Owner and sole decision maker for Project Astra.
Review the complete app and ALL handoff documents independently before deployment.
Treat existing claims and checked ticket boxes as evidence to test, not as proof.

Repository: https://github.com/ssdbank9/Project-Astra.git
Working branch: codex/migration-safety-remediation
Review-package SHA: USE THE EXACT SHA I SUPPLIED WITH THIS PROMPT.
App-source baseline: da1b3fd21ed0d4357669f0e727369fda02640672.

Your task is REVIEW ONLY. Make no source, document, board, real account,
credential, deployment, live database or real-user changes. Return findings
in your response. Synthetic users and test credentials may be created only
inside disposable fixtures; existing owner accounts/data remain untouched.
Use a fresh full disposable checkout of the branch; pull first, record HEAD,
and verify the exact requested package commit before reviewing. If origin has
moved, review the supplied commit in the disposable checkout and report both
SHAs. Do not switch or mutate Aly's canonical working checkout. Do not force,
rebase, amend, merge/push, create accounts or expose a server. Repository rules
in AGENTS.md govern; reviewer read-only scope is the tighter current instruction.
Tests and loopback browser fixtures may write disposable data only. Disable
jaira ref/snapshot synchronization in a disposable container as AGENTS.md directs;
read the board without claims or mutations.

1. **Establish scope and rules.** Read root AGENTS.md, pending-global-mistakes.md
   (and Aly's canonical global log only if actually available), then
   docs/handoff/README.md, PRE_DEPLOYMENT_REVIEW_2026-10-13.md and
   BOARD_AUDIT_2026-10-13.md. Inventory every tracked docs/handoff file from git;
   read all of them, including AGENT_START_PROMPT, HANDOFF_2026-09-26,
   NEXT_STEPS, OPEN_QUESTIONS, DECISIONS_LOG and DEPLOYMENT_RUNBOOK. Read the
   accepted root handoffs named by AGENTS.md, root README/CONTEXT and linked
   design/authorization documents as relevant. List every file reviewed or not
   accessible. Later dated decisions override historical status/defaults; a
   draft/not-submitted checkbox artifact does not authorize a decision.
   Completion: full document coverage register and source/assumption hierarchy.

2. **Rebuild requirements independently.** Turn accepted product rules and all
   phases A–F into atomic criteria. Map every criterion to service/HTTP/UI/test
   evidence or a missing/partial/unverified gate. Inspect every board ticket,
   including Done; check lane, declared DoD, proof, child repairs, recorded owner
   acceptance and remaining work. Distinguish superseded/deferred tickets from
   missing release requirements. Do not propose mass closure or infer acceptance.
   Completion: reconciled matrix and exact counts matching the frozen package.

3. **Review code and behavior.** Inspect authentication/session/CSRF/role paths,
   permission changes between checks and writes, closed-project rules, approvers,
   Chairman/Viewer boundaries, primary/secondary Owners, imports/exports,
   XML/ZIP/body budgets, CSV formulas, output headers and sensitive-data exposure.
   Check authorization in service.py, not merely UI visibility. Respect Aly's
   selected own historical import-report access after revocation. Check all
   response types and rejected requests for side effects.
   Review SQLite transactions, concurrent writes, idempotence, lease/revision
   conflicts, migrations/fault/retry and backup/restore/rollback feasibility.
   Completion: reproducible findings or explicitly bounded proof, with affected roles.

4. **Verify the defining workflows.** With disposable fixtures, test project/entity
   identity and rename; one project-bound XLSX with four main fields and optional
   explicit relationships; owner dropdown/basic-Excel save/upload; wrong binding,
   ambiguity, import preview/commit/replay, grouping and alternative plans.
   Test task-row timeline/date and vertical movement, later-row and filtered-parent
   ordering; Above predecessor, Below/After successor, Concurrent parallel;
   affected-chain dates/duration/calendar; independent critical paths; project
   scheduled bounds versus agreed deadline; unchanged assignees and approved
   baselines; Owner-only deadline revision and extension notices to App Owners
   and Chairman. Dates that overlap alone do not prove a dependency. Check cycle,
   access, revision and closed-project refusals, stale previews and Undo.
   Use real browser/native Excel only if tools are actually available. Inspect
   current DOM/UI before actions. A JS harness is not an actual pointer/touch test.
   Completion: persisted results and negative cases; unavailable checks unverified.

5. **Run verification.** Use .venv/Scripts/python.exe tests/run.py on Windows or
   .venv/bin/python tests/run.py on Linux/macOS; install editable package in the
   disposable environment if needed. Node must be on PATH. Run node --check
   src/astra/static/app.js and read-only jaira validate/list. Record Python/Node,
   OS, exact command, test count, failures/errors/skips and duration. Prior receipt
   was 832 OK with one unavailable Windows symlink skip; obtain your own result.
   For critical guards, remove them only in memory or a disposable copy and
   demonstrate that the relevant regression fails; preserve reviewed source.
   Completion: actual receipts, not 'should pass'; list unavailable environments.

6. **Assess launch operations.** Separate local readiness before server setup
   from staged-host proof before real-user invitations. Check first-login and
   self-service password change, dependencies, CI, version/tag/merge flow,
   realistic load, WCAG 2.2 AA/device evidence, safe error/logging, support/privacy,
   incident response/offline recovery guide, Owner export-everything and scoped
   user-data export/privacy requests, operating/maintenance cadence,
   encrypted consistent backups, off-host retention, timed two-direction restore,
   real HTTPS/Secure cookies, loopback isolation, host limits, SSH/firewall,
   restart/reboot, monitoring and cost boundaries. These may be missing; identify
   them rather than assuming runbook examples were executed. Refresh changing
   vendor facts against primary official sources if assessing them. No account
   signup/provisioning or credentials are authorized. One free VM is not multi-region
   resilience; budget alerts are not assumed spending caps. Completion: explicit
   prerequisites and unverified live checks, with no generic hosted-readiness claim.

Return:

- Model/version, review date, package SHA, app baseline, environment and coverage.
- Atomic requirement matrix: Proven / Partial / Missing / Unverified /
  Not applicable with reason; link repository file and exact line/test evidence.
- Findings sorted by severity. Each must have ID, category (confirmed defect,
  feature gap, documentation drift, unverified risk or environment limitation),
  trigger, expected/actual behavior, impact, file/line, reproduction command or
  browser steps, affected roles, and suggested fix plus regression.
- Every-ticket reconciliation with exact lane/DoD totals and accepted-but-open,
  superseded, deferred and launch-blocking items. Separate owner action from code.
- Exact tests/guard/browser/native/device receipts and all limitations.
- Review of every numbered gate in the pre-deployment plan, including anything
  obvious it missed, with responsible person and completion evidence.
- Separate GO/NO-GO for local preparation, staging deployment, and real-user
  invitations, with specific blockers and decisions Aly must make.

Do not claim checks you did not run, invent credentials/acceptance, treat a
historical test receipt as current proof, or apply fixes during this review.
If repository/tool access is unavailable, state that scope is unverified and
ask for the tracked export at the supplied SHA rather than guessing.

---
