# Pending additions to the canonical global mistakes log

Canonical target: `C:\Users\Aly Jafferani\.codex\mistakes.md`

## ASTRA-20261006-01 — remaining development was incorrectly described as blocked

- Date / project: 2026-10-06; Project-Astra continuation.
- Category / status: Confirmed communication omission corrected; Phase A3 CSV/search fixes verified and awaiting Aly's acceptance.
- Evidence / impact: Earlier responses inferred no development remained from agentic board lanes, although NEXT_STEPS.md Phase A3 lists unbuilt CSV-whitespace and literal-search repairs. They also asked for a hosting choice already recorded as Oracle Cloud, DuckDNS and Caddy.
- Cause / prevention: Board lane availability is not feature completion. Read the authoritative phase plan and accepted decisions before declaring all work gated; create scoped tickets for authorized, untracked work.
- Verification: Current source confirmed both defects; new regression run failed 11 cases, then four focused tests passed after repair. Full suite: Ran 722 tests in 873.981s, OK (skipped=1). Independent read-only a3_review passed with no blocking defect. Actual spreadsheet interpretation remains unverified.
- Tool corrections: Broad combined reads truncated output and an unrestricted file search encountered known inaccessible tmp directories. New Jaira tickets are ref-only until pulled; the ticket created under Codex required explicit self-takeover because the installed CLI identity differs. Use bounded reads, known directories and inspect CLI output before advancing. Git/Jaira writes required sandbox escalation; no existing work was discarded.
- Canonical log merge pending outside workspace write permissions.

- Final hygiene correction: The byte check found CRLF in web.py despite an earlier diff check passing. Scoped files were normalized to LF and rechecked; this changes no Python semantics. The normalization loop unnecessarily rewrote the CLI-owned ticket file with identical content; ticket fields were still written only through Jaira. Future byte normalization must exclude ticket paths and use the CLI for ticket mutations. An attempted Git stage was denied by the sandbox and was rerun with approved escalation.

## ASTRA-20261004-09 — approver development and launch-plan inspection corrections

- Date / project: 2026-10-04; Project-Astra Q1 development after the three published repairs.
- Category / status: Inspection and documentation mistakes corrected; selected approver-policy implementation is in progress.
- Evidence / impact: Two searches guessed nonexistent source/test paths (`src/astra/templates.py` and `tests/test_astra.py`). Combined log/source reads exceeded their output budgets again. The first progress update to the external launch plan left three stale clauses about authorization, the mixed-save repair and the importer ticket's assignee. Independent review identified them; they were corrected before use.
- Cause / correction: Discover file names with `rg --files`, bound both individual and combined output, and inspect full current cards after text substitutions. Preserve historical findings while updating every current-facing status. Missing evidence is reread before relying on it; no application data was changed by failed searches.
- Test/workflow corrections: The temporary regression runner was initially assumed to be under the repository's Temp directory; its actual location is the Windows temporary directory. The first red run used a guessed import-result key, designated a reviewer after task closure, and reused a revoked-access actor across red subtests. Inspect the actual result schema, add governance rows before closure, and give each race an independent actor. Preserve yielded shell session IDs and drain them before dependent mutations.
- Recurrences / review corrections on 2026-10-05: The independent reviewer also encountered truncated log/status output and an absent optional documentation path; narrow reads recovered the evidence. A status regex ending at `$` omitted CRLF ticket rows; `\r?$` verified 37 signoff / 5 human at 2f8f07. The reviewer identified missing HTTP write-lock access-change coverage in DoD 3; a focused four-case HTTP race now verifies 403 and complete SQLite equality after the concurrent authorization change. Import review-column fixtures must explicitly enable those optional columns. The browser exposed ambiguous existing acceptance-request confirmation text; it now explicitly says the submission is awaiting the App Owner's decision. The first background browser-tab creation took about ten minutes despite the normal tool timeout; later bounded interactions worked normally. No original account or user preview was changed.
- Prevention / verification: Use known source directories and small line ranges. The corrected plan records all three repairs as published and awaiting Aly's acceptance, with local selected development authorized and external execution separately gated; independent plan rereview passes. The Q1 extended 78-test run and two additional review regressions pass. Three disposable guard removals fail (15 action cases, four authorization races, one pending-state case). Final Q1 rereview/full-suite/browser evidence is in progress. Canonical log merge remains pending outside writable roots.

## ASTRA-20261004-08 — mixed-save boundary and inspection corrections

- Date / project: 2026-10-04; Project-Astra 1G7Q4C.
- Category / status: Confirmed lost-edit defect repaired, independently reviewed and published as 2f8f079aa3c93d2fdccdaef790842a1a1537cbee; Aly's acceptance pending.
- Evidence / impact: Fifty-four service field/transition cases and two HTTP cases reproduced silent discarded edits. The new guard initially exposed TypeError/OverflowError for unsupported progress values; two review regressions reproduced six service errors and four HTTP 500-versus-400 failures.
- Cause / correction: Protected status routing returned a request before the ordinary write. Compare actual normalized persisted values before both request routes, translate unsupported progress types to ValueError, and preserve unchanged full-form requests and earlier lifecycle refusals.
- Workflow lessons: A jaira lane JSON was incorrectly assumed to have a ticket property; inspecting its keys showed input and prompt instead. A root file inventory encountered pre-existing inaccessible tmp directories; target known paths or exclude tmp directories. An exact browser label lookup failed because the textarea's label included its current contents; inspecting form.elements exposed stable name attributes, which completed the retained-value check. A redundant claim renewal was refused because a new CLI process identity differed from this session's live original claim; no claim was stolen and the existing claimed work continued. Independent documentation review clarified that both request branches share one HTTP endpoint.
- Verification: Focused 25 tests and two progress-boundary tests pass; each route's guard removal fails (36 and 18 cases), independent rereview passes and the actual browser retains all entered fields. The default full Windows suite ran 700 tests in 368.566s, OK (skipped=1), with unchanged source/test hashes, no ResourceWarnings and no new tmp directories. No unrelated directory or original account was changed. Canonical log merge remains pending outside writable roots.

## ASTRA-20261004-06 — bounded reads and CSV contract ambiguity

- Date / project: 2026-10-04; Project-Astra importer repair continuation.
- Category / status: Output-budget mistake corrected; confirmed CSV round-trip defect remains open pending Aly's R2 decision.
- Evidence / impact: A broad regex over the importer tests produced 349 matching lines and truncated the output. Relevant tests were reread in small ranges. The existing export maps a formula-prefixed title and a literal apostrophe-prefixed title to the same CSV text, so blind unescaping or matching the stored task cannot distinguish a deliberate edit.
- Cause / prevention: Limit regex scope and select bounded source ranges before display. Do not treat older claims that no design decision is needed as authority to change the CSV contract.
- Correction / verification: A concrete reversible-format proposal and a format-preserving alternative are recorded in docs/handoff/CSV_ROUNDTRIP_DECISION_2026-10-04.md. Neither is implemented or owner-approved. Keep independently authorized repairs separate from this decision. Canonical log merge remains pending outside writable roots.

## ASTRA-20261004-07 — importer regression and cycle-review corrections

- Date / project: 2026-10-04; Project-Astra WYM776.
- Category / status: Test-authoring, workflow and implementation errors corrected and independently reviewed; published as dd5284c0004319bb6fea53f325224f6265980cd2, owner acceptance pending.
- Evidence / impact: A failing HTTP assertion included binary workbook bytes, producing oversized output. One new HTTP test called the SQLite connection as a context factory; corrected to query the existing service connection. A move to human was refused because the question and plan were absent; these were recorded through the CLI and the move then succeeded. No forced move was used.
- Cause / prevention: Keep binary response assertions to status, content type and length; inspect actual fixture connection ownership; inspect lane gates before moving a ticket. Capture red-run logs in Temp and display bounded summaries. Unfiltered jaira validation output recurred before publication; the filtered retry checked 72 tickets with errors=false. Filter validation fields before display.
- Publication-check correction: Overriding core.autocrlf before normalizing documentation exposed checkout CRLF as trailing-whitespace failures and oversized output. The first check's exit was not gated. Use the actual staged blobs for LF proof, preserve CLI-only ticket writes, normalize ordinary documentation, and stop on failed checks before publication. The test-preview process also ended after new input; a stale login link was corrected after a live HTTP check and the loopback helper was restarted hidden. Confirm the server before offering a usable login; rebind CUA after its runtime resets.
- Independent review: The first cycle-attribution implementation duplicated E_PARENT_CYCLE on a four-row cycle. A new exact-one-finding regression failed with 2 != 1; a duplicate guard corrected it, and independent rereview passed. Preserve the final graph to allow valid simultaneous reparenting; report the last changed edge, excluding unchanged parent rows.
- Verification: Eight initial regressions reproduced the remaining source defects; the focused reader/importer suite then ran 88 tests, OK. The extended two-cycle tests pass. Five removal mutations fail as required. The actual local task History displays Import key assigned. The default full suite ran 692 tests in 406.850 seconds, OK (skipped=1), with source hashes unchanged, no resource warnings and no new tmp directories. CSV serialization is unchanged; R2 and the sample workplan remain with Aly. A Windows rg wildcard path failed with error 123; the corrected directory plus -g search succeeded. The completed suite session expired after new input; its saved result was read instead of rerunning it. Canonical log merge remains pending outside writable roots.

## ASTRA-20260924-04 remediation — A0 Windows baseline

- Date / project: 2026-10-04; Project-Astra, ticket SFAZD7, starting SHA `10d0ff32f64b9ffd73299e9559976b60d6884db5`.
- Category / status: Confirmed baseline defects repaired and verified on the Windows runtime; owner acceptance pending.
- Evidence / impact: A focused default-locale run reproduced SQLite file cleanup errors, Node output decoding failure and two missing-database path assertions. The prior default full run was 583 tests with 12 failures and 26 errors; the UTF-8 diagnostic was 680 tests with 2 failures and 19 errors, with one platform skip in each.
- Cause: Implicit locale decoding of UTF-8 Node output; connection setup failed without closing its SQLite handle; unittest cleanup callbacks ran after fixture directory removal; CLI assertions compared short and resolved long Windows paths.
- Correction / prevention: Decode all five Node capture sites explicitly. Close unsuccessful database setup, including interruption. Register fixture directory and primary connection cleanup first, so later secondary connections close before them. Resolve the expected missing-database path while retaining exact refusal and noncreation checks.
- Verification: Four new regressions failed before the repair; 20 focused tests then passed. Removing connection cleanup makes all three closure regressions fail; removing UTF-8 decoding makes the locale regression fail. Independent static review passed. The documented default suite ran 684 tests in 429.070 seconds, OK (skipped=1), with no UTF-8 environment override, no resource warnings and no new temporary directories. The existing symlink test is skipped because symlinks are unavailable in this Windows environment; that check and hosted readiness remain unverified. Source files were unchanged during the run.
- Scope: No importer, mixed-save, role-policy, feature, schema, deployment or real-user change. Aly alone accepts A0. Canonical global-log merge remains pending outside writable roots.

## ASTRA-20261004-05 — A0 workflow and regression-authoring errors

- Date / project: 2026-10-04; Project-Astra A0.
- Category / status: Tooling and test-authoring errors; corrections recorded below. No private data loss.
- Evidence / impact: The required pull was blocked at FETCH_HEAD and succeeded with scoped escalation. A combined handoff refresh and an unfiltered jaira JSON list exceeded output budgets; relevant phase and ticket fields were reread narrowly. Plain module-qualified unittest imports missed the tests-only link_roots helper; the corrected invocation reproduces the real failures. The first Node regression missed its mock import; after correction it failed on the intended cp1252 decoding error. Entering pre-process was refused until the ticket's planning option was enabled.
- Cause / prevention: Account for tests/run.py discovery imports; use existing unittest.mock bindings; filter structured CLI output before display; inspect lane options; wait for every exec session to complete before starting another mutation.
- Mutation recurrence: Three sequential tool calls returned still-running shell sessions. Later calls then overlapped jaira writers, producing ref-conflict warnings. The sessions were drained; jaira fetch reconciled the refs and jaira resolve SFAZD7 reported no outstanding conflicts. The local checklist retained all completed/current steps. Await a shell session's exit before the next mutation; no force operation was used.
- Identity recurrence: A dry-run move omitted JAIRA_USER=Codex and was refused by the assignee gate; nothing was written. Supply the agent identity for gate checks as well as actual moves, without impersonating Aly.
- Verification: Required pull says already up to date; focused, regression-removal and default full-suite checks pass. Board validation has errors=false. Application source is restricted to db.connect cleanup; five test files carry baseline repairs. LF normalization and diff hygiene passed; independent final review verified zero CR characters. Owner acceptance and canonical global-log merge remain pending.

## ASTRA-20260920-10 - current authorization predates the latest Owner-only decisions

- Date / project: 2026-09-20; Astra cumulative handoff authorization cross-check.
- Category / status: Confirmed implementation/specification mismatch; open and gated before real-user access.
- Evidence / impact: `service.py` treats Chairman as a project manager for many mutations and allows non-Owner project managers to add attachment links and mark/unmark final results. The later approved UX/drag contracts reserve protected lifecycle actions and every file/final-result mutation for Aly Jafferani as App Owner. Real Chairman or Manager accounts could therefore exercise powers broader than the current decision register.
- Cause: The 102-test implementation reflects earlier ticket decisions; the consolidated Owner-only decisions were approved later during the UX/drag design pass and have not been applied to production code.
- Correction / prevention: Treat the later role matrix as authoritative, add a bounded authorization-reconciliation ticket before deployment, and test UI/API/service/automation/download paths. Until corrected, do not create a real Chairman account or share the app with Managers.
- Verification: `CODEX_HANDOFF_2026-09-20.md` now lists the mismatch as an explicit pre-sharing gate; no code or role behavior was changed during the documentation task.

## ASTRA-20260920-09 - one patch attempted delete and add on the same file

- Date / project: 2026-09-20; Astra cumulative handoff/start prompt.
- Category / status: Patch-construction error; recovered.
- Evidence / impact: One `apply_patch` call tried to delete and add `CODEX_START_PROMPT.md` in the same patch. The patch engine rejected multiple operations on one target before changing the file.
- Cause: Whole-file replacement was expressed as two operations in one patch rather than a supported update or two sequential operations.
- Correction / prevention: Replaced the file through two small, explicit apply-patch calls: delete the known exact file, then immediately add the complete current prompt. For whole-file replacement, use one update or separate delete/add calls.
- Verification: The current `CODEX_START_PROMPT.md` points to `CODEX_HANDOFF_2026-09-20.md`, contains the live board/test commands and no longer hard-codes the stale 2026-09-19 queue.

## ASTRA-20260920-08 - JavaScript check ran from the parent directory

- Date / project: 2026-09-20; Astra cumulative handoff verification.
- Category / status: Verification command error; recovered.
- Evidence / impact: `node --check src\astra\static\app.js` was invoked from the parent Git root, so Node looked for `New project\src\astra\static\app.js` and returned `MODULE_NOT_FOUND`. The application file was not missing or changed.
- Cause: A command copied from the Astra-local runbook was executed with the parent repository as its working directory.
- Correction / prevention: Run repository-relative verification from `astra_project_tracker`, or use the full `astra_project_tracker\src\...` path from the parent.
- Verification: Re-running from the Astra directory completed successfully with no syntax output; the 102-test Python suite also passed.

## ASTRA-20260920-07 - Markdown handoff failed the whitespace check

- Date / project: 2026-09-20; Astra Monday.com/Trello UX handoff.
- Category / status: Formatting check failure; corrected before commit.
- Evidence / impact: `git diff --cached --check` flagged metadata lines that used Markdown hard-break spaces and one extra blank line at end of file. Content was valid but the staged change did not meet the repository whitespace check.
- Cause: Metadata was formatted with two-space Markdown line breaks without checking the Git whitespace policy.
- Correction / prevention: Converted the baseline metadata to a list, separated research metadata with blank paragraphs, removed the extra end-of-file blank line, restaged and reran the check.
- Verification: The final staged `git diff --cached --check` completes without findings.

## ASTRA-20260920-06 - parent Git index was outside the write sandbox

- Date / project: 2026-09-20; Astra Monday.com/Trello UX handoff.
- Category / status: Environment permission failure; recovered with scoped approval.
- Evidence / impact: The first scoped `git add` could not create the parent repository's `.git/index.lock` because the workspace allowed reading but not writing that Git directory. The chained commit therefore also failed; no unrelated files were staged or changed.
- Cause: Astra is a subdirectory of the parent Git repository while the sandbox write root covered the Astra directory, not the parent's `.git` metadata.
- Correction / prevention: Re-ran the exact four-file staging operation with scoped permission for that command, then inspected the staged set before committing. Expect parent-repository Git mutations to need scoped approval in this workspace.
- Verification: The subsequent staging command completed with only line-ending warnings; final commit and clean scoped status are recorded in the task handoff.

## ASTRA-20260920-05 - human-lane move omitted its required question

- Date / project: 2026-09-20; Astra ticket `Z9JCZ6`.
- Category / status: Jaira workflow error; recovered.
- Evidence / impact: The first in-progress → human move was refused because the command supplied outcomes but omitted `--question`. The ticket remained in progress and no source file was affected.
- Cause: The lane's required human question was not included in the first command even though the project instructions identify human as a person-owned lane.
- Correction / prevention: Read the refusal and `jaira move --help`, then retried with a focused review question. Include the destination lane's required field in the command checklist before moving.
- Verification: `jaira move` reported `Z9JCZ6 → human`; the completed plan, proof and outcomes remain on the ticket.

## ASTRA-20260920-04 - automation wording weakened the cross-project boundary

- Date / project: 2026-09-20; Astra Monday.com/Trello UX baseline.
- Category / status: Documentation ambiguity; corrected before handoff.
- Evidence / impact: The inherited research report said automation could not mutate another project “without Owner approval.” That could be read as allowing an automation to execute an approved cross-project mutation even though the settled authority rule says only the App Owner executes cross-project Move / Copy / Link.
- Cause: A generic protected-action approval formulation was applied to the stricter cross-project rule.
- Correction / prevention: The report now says automation cannot mutate another project directly; where policy permits it may only stop and create an Owner request, which it cannot approve or execute. Cross-check strict prohibitions separately from approval-eligible actions.
- Verification: The repaired research wording matches `docs/design/astra-product-ux-baseline.md` and `docs/design/governed-drag-drop-contract.md`, both of which keep cross-project execution Owner-only.

## ASTRA-20260920-03 - Monday/Trello research worker reported exhausted credits

- Date / project: 2026-09-20; Astra Monday.com/Trello workflow research.
- Category / status: Environmental limitation and inaccurate initial handoff assumption; recovered through independent verification.
- Evidence / impact: The required background research agent reported that its workspace had no remaining credits. The first fallback note incorrectly said no research file had been created; inspection showed that the worker had left a comprehensive `docs/research/monday-trello-workflow-ux-research.md`. Treating the final status alone as authoritative could have caused duplicate work or loss of useful partial output.
- Cause: External agent-credit availability, not a source or repository failure.
- Correction / prevention: Inspect the workspace after any interrupted or failed worker before concluding that no artifact exists. The primary agent audited the inherited report, independently reopened representative official and Reddit sources, repaired its access-date and automation-health coverage, and converted it into the product UX baseline. Continue distinguishing official product facts from Reddit experience signals.
- Verification: `docs/research/monday-trello-workflow-ux-research.md` now records the 2026-09-20 refresh and limitations; `docs/design/astra-product-ux-baseline.md` traces the evidence into explicit Adopt / Adapt / Avoid and screen-level rules.

## ASTRA-20260920-02 - drag prototype verification exposed a What-if ordering defect

- Date / project: 2026-09-20; governed drag prototype `AX572Q`.
- Category / status: Confirmed prototype logic defect; corrected.
- Evidence / impact: The reducer scenario check expected a Manager's critical-task change in private What-if mode to update only simulation state, but it created an Owner approval before reaching the simulation branch. The prototype contradicted the approved rule that What-if experiments do not mutate live work or require approval until submitted.
- Cause: `SHIFT_GANTT` checked protected live impact before checking `state.mode === 'what-if'`.
- Correction / prevention: Handle authorized private simulation before live protected-impact approval. Retain the approval check for live Manager changes and submission of the simulation.
- Verification: The corrected reducer scenario confirms live start remains 2, simulated start becomes 5, and the complete protected/viewer/batch/lock/What-if/Undo scenario set passes.

## ASTRA-20260920-01 - prototype workflow and QA command assumptions

- Date / project: 2026-09-20; governed drag prototype `AX572Q`.
- Category / status: Workflow and read-only verification errors; recovered.
- Evidence / impact: The first move from Todo to pre-process was refused because the ticket's planning option was not ticked. A fixed-string `rg` command supplied multiple patterns as filenames instead of `-e` expressions. A parallel image-view request hit a transient sandbox ACL helper failure even though both screenshots existed. Source inspection also found a duplicate role-change listener that would have dispatched the same state change twice. No production file or live state was affected.
- Cause: Destination-lane options, `rg` multi-pattern syntax, parallel image-helper behavior, and delegated event coverage were not checked before their first use.
- Correction / prevention: Tick the planning option before moving; use `rg -F -e` per pattern; inspect local screenshots individually after a helper failure; keep one delegated change listener.
- Verification: `AX572Q` reached in-progress, the corrected marker search found every required scenario, both images were individually inspected, and the duplicate listener was removed before handoff.

### 2026-09-20 recurrence - oversized combined continuation read

- Evidence / impact: A continuation command combined the global mistakes head, repository status, research report head and pending-log tail; its output was truncated. No conclusion relied on the missing section and no file was changed by the read.
- Cause: The known bounded-read rule was not applied after context compaction.
- Correction / prevention: Follow-up inspection used focused `rg` and bounded file segments. Keep independent artifacts in separate reads even when resuming from a summary.
- Verification: The research comparison, source list, ticket state and pending entry were subsequently checked with targeted commands before editing.

## ASTRA-20260919-06 - Jaira note lock required scoped escalation

- Date / project: 2026-09-19; Astra UX decisions on `JQY55P`.
- Category / status: Environmental permission limitation; recovered.
- Evidence / impact: The first `jaira note` attempt could not create its lock under `C:\Users\Aly Jafferani\.jaira\state`; no ticket content changed in that attempt.
- Cause: Jaira's shared lock directory is outside the workspace write boundary even though the ticket itself belongs to this repository.
- Correction / prevention: Retry the identical bounded Jaira mutation with scoped escalation when the lock-path denial occurs; do not edit ticket Markdown directly.
- Verification: The escalated retry recorded the approved cross-project Move / Copy / Link decision on `JQY55P`.

### 2026-09-20 recurrence - cumulative handoff ticket plan

- Evidence / impact: Adding the `MTEDTM` plan, note and lane move again failed on the same external Jaira lock path; no ticket content changed in the failed attempt.
- Correction / prevention: The exact CLI mutations were rerun with scoped approval rather than editing the ticket file directly.
- Verification: `MTEDTM` now contains the six-step plan and is in `in-progress`.

## ASTRA-20260919-05 - repository index write required escalation

- Date / project: 2026-09-19; Astra native-HTML UX prototype `JQY55P`.
- Category / status: Environmental permission limitation; recovered.
- Evidence / impact: The first exact-path `git add` failed because the parent repository `.git/index.lock` was outside the workspace write boundary. No files were staged in that attempt and no user changes were overwritten.
- Cause: The task workspace is a subdirectory of a parent Git repository whose index is readable but not sandbox-writable.
- Correction / prevention: Request scoped escalation for the same exact-path staging command; never broaden the staged set to unrelated parent-workspace files.
- Verification: The escalated command staged only the prototype, its Jaira ticket, and the Astra pending mistakes log.

## ASTRA-20260919-04 - human-lane move omitted its required question

- Date / project: 2026-09-19; Astra native-HTML UX prototype `JQY55P`.
- Category / status: Workflow command omission; recovered.
- Evidence / impact: The first `jaira move JQY55P --to human` was refused because it did not include the human decision question. No lane or file state changed in the refused attempt.
- Cause: The completion outcome fields were supplied, but the destination lane's additional `--question` gate was not checked first.
- Correction / prevention: Run `jaira move --help` or a dry run before entering a human lane and include the exact decision needed from the owner.
- Verification: The retry included the production-direction question and moved `JQY55P` from `in-progress` to `human`.

## ASTRA-20260919-02 - headless browser screenshot paths were relative

- Date / project: 2026-09-19; Astra native-HTML UX prototype `JQY55P`.
- Category / status: Visual-QA tool path error; recovered.
- Evidence / impact: Parallel headless Chrome renders exited zero, but three reported that `tmp_visual_qa\\*.png` could not be written because Chrome did not resolve the relative output path against the requested shell working directory. The prototype was not changed; those screenshots were not produced.
- Cause: The screenshot target was passed as a relative path to an external browser process.
- Correction / prevention: Pass fully resolved absolute screenshot paths to external GUI/headless applications and verify each output exists before treating an exit code as success.
- Verification: Four explicit-path renders were produced and visually inspected at 1440px and 1024px widths. A final 1440px Variant A render also confirmed the corrected task drawer position.

## ASTRA-20260919-03 - drawer fix patch assumed reformatted CSS

- Date / project: 2026-09-19; Astra native-HTML UX prototype `JQY55P`.
- Category / status: Patch-context error; recovered.
- Evidence / impact: The first drawer-positioning patch failed because its expected `.board` rule differed from the prototype's compact one-line CSS. No file was changed by the failed patch.
- Cause: The patch was written from a remembered, reformatted rule instead of copying the exact current source context.
- Correction / prevention: Locate the exact stable line with `rg -F`, patch against its literal contents, and keep future visual prototypes reasonably formatted where iterative changes are likely.
- Verification: The exact-context patch applied, the document parsed successfully, and a new headless-browser render showed the drawer correctly anchored at the right edge.

## ASTRA-20260919-01 - prototype marker search regex was malformed

- Date / project: 2026-09-19; Astra native-HTML UX prototype `JQY55P`.
- Category / status: Read-only verification command error; recovered.
- Evidence / impact: The HTML parser completed and `node --check` returned clean, but the combined `rg` feature-marker regex ended with an unclosed group because the quoted `data-action` fragment was mangled by PowerShell transport. The marker search did not run; the prototype file was not changed by the failed search.
- Cause: A multi-alternative regex containing nested quotes was used where fixed-string searches were sufficient.
- Correction / prevention: Use separate `rg -F` fixed-string patterns for HTML attribute and feature-marker verification; keep JavaScript syntax validation independent.
- Verification: The marker search was rerun using fixed strings after this entry was recorded.

## GLOBAL-20260905-03 recurrence - design inventory globs and oversized HTML output

- Date / project: 2026-09-19; Astra UX and design-tool research.
- Category / status: Read-only inspection command errors; recovered.
- Evidence / impact: An `rg` command passed Windows wildcard paths (`design/*.html`, `design/*.json`) directly and reported invalid filename syntax. The corrected follow-up combined a search with reads of generated design HTML and produced truncated output because one HTML artifact contains a very large embedded application bundle. No file or application state changed, and no design conclusion relies on the truncated bundle.
- Cause: The command did not follow the existing Windows guidance to use `rg -g`, then requested generated HTML without first checking its size and structure.
- Correction / prevention: Use `rg -g '*.html' -g '*.json' design` and read only small source-backed design files or bounded line ranges; exclude the generated `astra-dashboard-directions.html` bundle from routine text inspection.
- Verification: The corrected search identified the design inventory, and targeted reads of `design/canvas.json`, `Shell.dc.html`, and `TaskDetail.dc.html` established the current v2 shell, view, and side-panel decisions.

## GLOBAL-20260905-03 recurrence - review-agent command assumptions

- Date / project: 2026-09-19; Astra ticket `6G89SJ` independent review.
- Category / status: Read-only command errors; recovered.
- Evidence / impact: The Specification reviewer searched a nonexistent `tests/test_http.py` path and assumed a nonexistent `.ticket` field in Jaira JSON. The Standards reviewer initially used incorrect unittest class names, producing five loader errors. No repository or ticket state changed, and no finding relied on those failed commands.
- Cause: File and JSON/test identifiers were assumed instead of being confirmed with `rg` and the returned schema first.
- Correction / prevention: Resolve test paths, class names, and JSON keys through narrow discovery commands before constructing review commands. Re-run the intended checks using confirmed names.
- Verification: The reviewers inspected `tests/test_web.py`, used `AstraCoreTests` and `AstraWebTests`, and the five focused attachment tests passed. The primary agent independently ran the complete project-environment suite: 102 tests passed.

## GLOBAL-20260905-03 recurrence - combined Jaira claim and review prompt

- Date / project: 2026-09-19; Astra ticket `6G89SJ` review.
- Category / status: Inspection workflow error; recovered through the prior targeted read and a narrow retry.
- Evidence / impact: A command combined the existing pending-log read, `jaira claim`, and the ticket's 116,722-character review diff. The output was truncated, and the claim itself failed because Jaira's live lock is outside the workspace write boundary. No ticket or application file changed.
- Cause: The claim was bundled with a known oversized ticket read even after the prior turn had established that the review diff must be inspected through targeted commands.
- Correction / prevention: Run Jaira mutations separately from ticket inspection; never request this ticket's full diff in the same call as another command; use focused source paths and tests for the review evidence.
- Verification: The earlier targeted `jaira show 6G89SJ --json` and source reads recovered the ticket decisions and implementation evidence. The claim will be retried as a standalone command with the required filesystem permission.

## GLOBAL-20260905-03 recurrence - oversized review read

- Date / project: 2026-09-14; Astra planning and Email Project Organizer review.
- Category / status: Inspection workflow error; recovered.
- Evidence / impact: The first combined mistakes, memory, specification, and workspace read truncated. No files changed and no conclusion relied on the truncated content.
- Cause: Too many independent sources were requested in one output despite the existing prevention rule.
- Correction / prevention: Re-read the specification in bounded sections and queried code, archive, and lessons separately. Keep independent reads bounded with explicit output headroom.
- Verification: The approved design, detailed decisions, current 0.8.26 source boundary, archive contract, and test baseline were subsequently inspected in targeted calls.

## ASTRA-20260914-01 - bootstrap patch was created in the archive workspace

- Date / project: 2026-09-14; Astra standalone tracker bootstrap.
- Category / status: Confirmed file-placement and patch-transport error; recovered.
- Evidence / impact: A nested bootstrap patch caused the new `src`, `tests`, `README.md`, and project content to appear temporarily under `D:\DropBox\Self\Rupani\_machine`; batch/direct multiline patch retries also failed before writing because the final patch marker was not preserved.
- Cause: The nested patch was interpreted as file edits by the patch engine, and Windows command/batch transport did not preserve the large multiline patch as intended.
- Correction / prevention: Verified the exact added paths and empty standalone target, moved only the Astra files to `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`, and removed all staging files. For external writable targets, use small patches or a verified one-file staging workflow; verify the target tree after every patch.
- Verification: The `_machine` root again contains only its original `entities`, `standalone`, `catalog.jsonl`, `README_FOR_LLM.md`, and `scope.json` entries. Astra has its own separate 14-file source/test tree.

## ASTRA-20260914-02 - threaded server reused a main-thread SQLite connection

- Date / project: 2026-09-14; Astra standalone tracker vertical slice.
- Category / status: Confirmed code defect; corrected and offline verified.
- Evidence / impact: Initial HTTP integration tests returned 500 because `ThreadingHTTPServer` handlers used the SQLite connection created on the main thread. Login and authenticated API requests could not operate.
- Cause: The first server scaffold stored one connection on the server object without accounting for request-handler threads.
- Correction / prevention: Each HTTP request now opens and closes its own configured SQLite connection; the main connection remains only for owner bootstrap/test setup. Keep concurrency tests in the required suite.
- Verification: Nine tests pass, including authenticated login, CSRF enforcement, project creation, dated critical-task creation, authorized task retrieval, static Gantt shell loading, access isolation, audit history, and schedule validation.

## ASTRA-20260914-03 - test command and discovery setup failures

- Date / project: 2026-09-14; Astra bootstrap verification.
- Category / status: Tool/setup errors; recovered.
- Evidence / impact: One JavaScript wrapper syntax error prevented Python from starting. The next unittest discovery run failed because `tests` lacked `__init__.py`. No application state changed.
- Cause: An invalid wrapper expression and an omitted test-package marker in the initial scaffold.
- Correction / prevention: Simplified the command wrapper, added `tests/__init__.py`, and retained standard discovery as the canonical test command.
- Verification: `python -m unittest discover -s tests -v` now discovers and passes all nine tests.

### 2026-09-14 recurrence - src-layout environment omitted

- Evidence / impact: Running the documented discovery command in a fresh shell failed to import `astra` because the package was neither installed in that interpreter nor exposed through `PYTHONPATH`. Both test modules failed before executing; this was not evidence of an application regression.
- Cause: The earlier verification result did not preserve or document the import-path prerequisite used by the test shell.
- Correction / prevention: Make the repository test command self-contained or explicitly use an installed project environment. Re-run with the repository `src` directory on the import path before relying on the application result.
- Status / verification: Corrected by adding `tests/run.py`, which supplies the repository `src` path without requiring installation. The runner subsequently executed all 13 tests successfully.

## GLOBAL-20260905-03 recurrence - combined context read

- Date / project: 2026-09-14; Astra continuation.
- Category / status: Inspection workflow error; recovered through targeted follow-up reads.
- Evidence / impact: A combined read of the approved planning documents, tests, and JavaScript produced truncated output. No file was changed and no conclusion relied on the missing tail.
- Cause: Several individually bounded reads were still combined into one aggregate result that exceeded the output allowance.
- Correction / prevention: Read the phased plan and final design in separate targeted calls; avoid aggregating large document and source reads even when each child command is bounded.
- Verification: The phase plan and clean approved baseline were subsequently read in separate bounded calls.

## ASTRA-20260914-04 - dependency capability was declared but not operable

- Date / project: 2026-09-14; Astra task-planning slice.
- Category / status: Confirmed feature gap; correction in progress.
- Evidence / impact: The database contained `task_dependencies` and the README claimed dependencies in the first vertical slice, but the service, API, UI, and tests provided no way to create, inspect, or validate a dependency. One `Get-Content` output appeared to show a malformed separator, but a UTF-8-aware `rg` read showed the source character was valid.
- Cause: The initial scaffold created the storage table before implementing its application behavior, and the README described schema presence as delivered capability; text was transported with an encoding artifact.
- Correction / prevention: Added project-safe finish-to-start dependency operations, cycle checks, blocked-state reporting, audit events, API/UI support, and tests. Verify user-visible claims against an operable path, not schema presence. Treat encoding as a display/tool issue unless the stored source bytes confirm corruption.
- Verification: Thirteen offline unit/HTTP tests pass, including creation, blocking/unblocking, cycle and cross-project rejection, reasoned removal, audit history, and API behavior. JavaScript syntax check passes. Live visual browser acceptance is still unverified.

## ASTRA-20260914-05 - handoff search command had an unterminated quote

- Date / project: 2026-09-14; Astra dependency-slice verification.
- Category / status: Tool-command error; recovered.
- Evidence / impact: One combined `rg` hygiene check did not run because PowerShell reported a missing string terminator. The parallel unit/HTTP and JavaScript checks completed; no application file or data was changed by the failed search.
- Cause: A double quote embedded in the regex pattern was over-escaped for JavaScript but still terminated the surrounding PowerShell argument.
- Correction / prevention: Use a single-quoted PowerShell regex argument for source hygiene searches and rerun the exact check before handoff.
- Verification: The search was rerun with a single-quoted regex and completed successfully. No stale debug branch or malformed separator was found.

### 2026-09-14 recurrence - inline UI-fixture command

- Evidence / impact: A long inline Python command intended to start the isolated browser fixture failed before execution with an unterminated string literal. No fixture database or application state was created by the failed command.
- Cause: Nested JavaScript, PowerShell and Python/SQL quoting made the inline command fragile, repeating the same command-composition class immediately after it was logged.
- Correction / prevention: Stop retrying nested inline commands. Put the bounded fixture launcher in a reviewable repository test helper and invoke that file directly.
- Status / verification: Recovered by `tests/ui_fixture_server.py`; the isolated server started and listened on `127.0.0.1:8766`. Browser acceptance remained blocked by the environment as recorded below.

## ASTRA-20260914-06 - browser surface unavailable for visual acceptance

- Date / project: 2026-09-14; Astra dependency-slice verification.
- Category / status: Environmental limitation; unresolved visual check, fixture cleaned up.
- Evidence / impact: Computer Use reported no available browser, and creating an in-app-browser tab also returned `Browser is not available: iab`. The task-form and blocked-Gantt visual behavior could not be proven through a live browser in this session.
- Cause: No browser surface was attached or available to the automation environment.
- Correction / prevention: Retain automated HTTP and JavaScript checks as structural evidence only, provide the isolated visual-fixture helper, and require a later manual or attached-browser acceptance pass before claiming visual compatibility.
- Verification: The local fixture server was confirmed listening on port 8766, then its exact process was stopped and `tmp_ui_accept` was removed. `Get-NetTCPConnection` itself returned access denied, so the exact listener PID was identified through read-only `netstat -ano` output instead.

## ASTRA-20260914-07 - dependency cycle check initially preceded the write lock

- Date / project: 2026-09-14; Astra dependency-slice handoff review.
- Category / status: Confirmed concurrency risk in the new implementation; corrected before handoff.
- Evidence / impact: The first implementation checked for duplicates and graph cycles before opening its `BEGIN IMMEDIATE` transaction. Two concurrent writers could theoretically both pass validation before either insert, weakening the cycle invariant.
- Cause: Read validation and mutation were initially split around the transactional boundary.
- Correction / prevention: Duplicate and recursive cycle checks now execute inside the same immediate write transaction as dependency insertion and its audit event. Keep invariant checks and dependent writes under one serialization boundary.
- Verification: Fourteen regression tests pass after the correction. A simultaneous opposite-edge writer test proves exactly one dependency is added and the other is rejected as a cycle.

## ASTRA-20260914-08 - handoff audit found vertical-slice gaps and build-sequence divergence

- Date / project: 2026-09-14; Astra complete-task handoff review.
- Category / status: Confirmed implementation gaps and unverified risks; open and disclosed in `CLAUDE_HANDOFF.md`.
- Evidence / impact: The standalone tracker implements an early portion of the approved multi-user/Gantt phase, while the approved integrated sequence required reconciliation of the existing Email Project Organizer first. Current source has no user/access-management UI or API, no task edit/history UI, no entity operations, no project closure/reopening workflow, no baseline-versus-pending schedule revisions, no notifications, no evidence ingestion/publication, and no recovery/backup workflow. Task updates do not revalidate a nonblank title; task assignment accepts any existing user ID without confirming project membership; due-state calculation uses the server's local date rather than each project's governing timezone; production HTTPS, secure cookies, login throttling, and consistent static-page security headers are not implemented.
- Impact: The current 14 passing tests prove a bounded local slice, not the approved end-to-end product, production safety, cross-role completeness, visual browser fidelity, or ingestion accuracy. Continuing only the tracker UI would deepen divergence from the approved source-first roadmap.
- Cause: The bootstrap intentionally delivered a small standalone tracker slice, but its scope and remaining distance from the integrated approved design were not yet captured in one builder-facing record.
- Correction / prevention: Use the new handoff's requirement matrix and phase gates. Reconcile Phase 0 and decide the integration boundary before broader build work; fix authorization/data-integrity defects before staff access; keep local/offline verification separate from live proof; require explicit approval for deployment, private-source processing, credentials, external delivery, and consequential automation.
- Verification: Source, schema, routes, tests, approved `FINAL_DESIGN.md`, phased `ASTRA_PLAN_AND_CONTEXT.md`, and current pending mistakes were inspected. No live deployment, mailbox, OCR, notification, backup restore, or browser visual acceptance was performed during this audit.

## ASTRA-20260914-09 - handoff reference-validation command did not parse

- Date / project: 2026-09-14; Claude handoff document verification.
- Category / status: Tool-command error; recovered.
- Evidence / impact: One PowerShell reference-existence check failed before execution with `An empty pipe element is not allowed`; the handoff file itself was already written and was not changed by this failed read-only check.
- Cause: A `foreach` statement was piped without wrapping its output expression correctly.
- Correction / prevention: Use `Get-Item` with an explicit literal-path list for the bounded reference check rather than a compound loop/pipeline expression.
- Verification: Targeted `Get-Item` validation confirmed that the global instructions/log, all three approved design references, and `CLAUDE_HANDOFF.md` exist and are readable.

### 2026-09-21 recurrence - handoff metrics loop was piped without grouping

- Evidence / impact: A read-only PowerShell check for the new Claude Code handoff's line, character and code-fence counts failed before execution with `An empty pipe element is not allowed`. The handoff files had already been written and were not changed by the failed check.
- Cause: A `foreach` statement was again piped directly instead of emitting or grouping its results, repeating the command-composition mistake recorded above.
- Correction / prevention: Avoid compound loop/pipeline validation commands. Read each bounded file into its own variable and print each metric directly.
- Status / verification: Recovered. Direct per-file metrics reported 610 lines and 10 balanced fence markers for `CLAUDE_CODE_HANDOFF_2026-09-21.md`, and 23 lines and 2 balanced fence markers for `CLAUDE_CODE_START_PROMPT.md`. Targeted heading/prompt searches also passed.

## ASTRA-20260921-01 - authorization code changed before all public wording was reconciled

- Date / project: 2026-09-21; Astra ticket `HS3JRY` Owner-only authorization reconciliation.
- Category / status: Confirmed documentation omission; open and explicitly handed off.
- Evidence / impact: The uncommitted service/API/UI/tests now route Manager and designated-Approver protected actions to the App Owner and remove Chairman's implicit mutation power, but `README.md` still says Manager, Chairman or a designated Approver may directly accept a submission, and `CONTEXT.md` still says an Approver may accept. A new agent or human could rely on those stale claims and misunderstand the current authority boundary.
- Cause: Implementation and authorization-matrix documentation were updated before the older overview/domain wording received the same reconciliation pass.
- Correction / prevention: Treat public/domain documentation as part of the authorization requirement matrix. Update `README.md` and `CONTEXT.md` before marking `HS3JRY` complete, then search all role/acceptance wording and rerun the full suite.
- Verification: The exact stale lines and required corrections are called out in `CLAUDE_CODE_HANDOFF_2026-09-21.md` section 6.3 and in the paste-ready Claude Code prompt. Ticket `HS3JRY` remains in progress; no final-completion claim was made.

## ASTRA-20260921-02 - first standalone Git export command used incompatible PowerShell parameters

- Date / project: 2026-09-21; Astra standalone GitHub export.
- Category / status: Tool-command error; recovered without changing the source workspace.
- Evidence / impact: The first packaging attempt stopped because this PowerShell environment rejected `New-Item -LiteralPath`; a later wildcard copy also could not be paired with `Copy-Item -LiteralPath`. The abandoned temporary target contains no usable export, and no source file was modified or deleted.
- Cause: The command assumed parameter support and combined wildcard expansion with a literal-path API.
- Correction / prevention: Build into a new, explicitly checked target; use `New-Item -Path` and `Copy-Item -Path` only where wildcard expansion is intended; verify the complete file inventory before initializing Git.
- Verification: The fresh `astra-project-tracker-cloud-export-20260921-v2` target was created from `git archive`, received only the intended current Astra files, and excluded local databases, virtual environments, caches, credentials and browser artifacts.

### 2026-09-21 recurrence - combined secret-scan regex was parsed as PowerShell code

- Evidence / impact: A read-only `rg` secret-pattern scan failed because nested quote characters ended the PowerShell string and caused part of the pattern to be parsed as a module name. No file or Git state changed.
- Correction / prevention: Run simple fixed-string credential markers as separate bounded searches instead of embedding quoted assignment patterns in one shell command. Treat a failed hygiene scan as no evidence and rerun it successfully before publishing.
- Status: Recovered workflow; the replacement scans and final result are recorded in the GitHub export verification.

## ASTRA-20260921-03 - repository visibility was not verified before the first push

- Date / project: 2026-09-21; Astra standalone GitHub publication.
- Category / status: Confirmed verification-process error; repository was observed as public only after both sanitized branches were pushed. Aly Jafferani subsequently instructed that it remain public for now, so no visibility correction is pending.
- Evidence / impact: The signed-in GitHub repository page labeled `ssdbank9/Project-Astra` a public repository. The uploaded payload contains Astra source, tests, design documents, Jaira records and product handoffs, but the pre-push hygiene checks found no database, virtual environment, credential file, private key or GitHub token marker.
- Cause: The empty repository was created and authenticated earlier, but its visibility was not read and confirmed before publishing.
- Correction / prevention: Verify visibility on the empty repository page before any first push and state the observed setting to the owner. For private work require an explicit private label, then verify again after publication. Repository visibility and external connector access remain separate permission decisions.
- Verification: Both branches and expected files are visible remotely. On 2026-09-21 Aly explicitly chose to keep `Project-Astra` public for now. Claude connector authorization remains separate and was not completed in that session.
