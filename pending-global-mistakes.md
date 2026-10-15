# Pending additions to the canonical global mistakes log

Canonical target: `C:\Users\Aly Jafferani\.codex\mistakes.md`

## ASTRA-20261009-01 - continuation tooling and context recovery

- Date / project: 2026-10-09; Astra JM7CFP continuation.
- Category / status: Tooling and inspection errors recovered; browser verification remains pending. Global log update staged here because its canonical path is outside the writable roots.
- Evidence / impact: Ordinary shell startup repeatedly returned os error 2; Node REPL rejected sandboxCwd. Scoped escalated execution restored Git and the existing Windows Python environment. The initial backslash Python command was interpreted by bash and exited 127; node and jaira were absent from bash PATH. A guessed test_ui_drivers.py read failed; the actual drivers are in tests/test_web.py. Combined log reads exceeded output limits. No live tasks were changed by these failures.
- Cause / correction: Shell/path assumptions and insufficiently bounded output. Use forward slashes for the existing .venv/Scripts/python.exe under bash, verified bundled node.exe and installed go/bin/jaira.exe; inventory files before referring to them. Keep large command output in a file or summarize complete tool output before returning it.
- Prevention / verification: Recovered the current JM7CFP ticket and latest chat before continuing; the older memory-described CSV draft was superseded by the local Excel implementation. Pull returned Already up to date. Bundled Node syntax and scoped LF/whitespace checks passed. The pre-repair fresh full suite ran 764 tests in 532.432s, OK (skipped=1); corrected-code results and completed independent review are below. Do not infer browser acceptance or owner approval from these checks.
- Focused-check correction: A direct unittest package invocation could not import link_roots; a bash PYTHONPATH assignment was not visible as intended to the Windows interpreter and the next invocation could not import test_core. No test body ran in those two attempts. Supply source and test helper paths explicitly in the Windows interpreter, or use the canonical runner. The corrected isolated symlink check ran one test and confirmed OK (skipped=1), reason symlinks are not available here. The full-suite result above remains a separate successful run.
- Independent-review correction: The reviewer's Git diff call stalled; a captured exact scoped diff packet and separate bounded rg reads recovered the review after another oversized combined output. It found a real workbook defect: dropdown references used raw task-title whitespace, while the parser indexed collapsed whitespace. A new isolated regression failed with one preview error before correction. The parser now normalizes index labels and selected references through the same helper, retaining exactly-one-match ambiguity checks. The new regression checks both Related task and Part of, persisted grouping and the dependency edge. Corrected focused run: Ran 20 tests in 14.030s, OK. Independent static review of the repair and scoped ignore rule passed. Corrected-code full suite: Ran 765 tests in 557.349s, OK (skipped=1), exit 0. The earlier 764-test result does not cover the repair. Browser and desktop Excel behavior remain unverified; no owner acceptance or release readiness is claimed.
- Artifact-hygiene correction: This continuation initially described Temp logs as ignored without checking .gitignore. Current .gitignore lacked /Temp/ and the starting status listed Temp/ as untracked. Added the scoped /Temp/ ignore so local generated logs, review packets and existing browser/sample artifacts stay outside normal staging. No artifacts were staged or published. Verify the effective ignore rule rather than inferring it from the directory's name.
- Ticket-attribution correction: The first continuation note was appended through the CLI, but its inherited local identity recorded the author as Aly Jafferani. It was an automated progress note, not an owner decision or acceptance; the ticket remained in-progress. The final note supplied JAIRA_USER=Codex explicitly to the Windows CLI subprocess and appended the attribution correction while preserving earlier history. Reread confirmed its author is Codex and ticket status is still in-progress. Never edit ticket files by hand.
- Owner acceptance follow-up: Aly explicitly stated Approved JM7CFP in this chat on 2026-10-09. Record that actual owner decision in the handoff, decisions log and CLI ticket history; retain browser/desktop checks as unverified. The agent may place the ticket in signoff but may not leave that human lane. A combined approval-start context read again exceeded the aggregate output budget; bounded ticket and rule reads recovered the required evidence before mutation.
- Recurrence 2026-10-10: The how-to-check context lookup again combined overly broad memory and global-log searches, truncating output. No product change resulted. Recovered the exact workflow from bounded owner instructions, local launcher documentation and UI labels. Limit context searches to the named entry or file and budget the aggregate output before batching.
- Publication environment limitation: The Linux Git push of the accepted local commit failed before authentication with could not read Username for https://github.com: No such device or address. Read-only inspection confirmed the installed Windows Git has the manager credential helper. Use the existing Windows Git credential setup for the retry; never print credentials or infer remote publication from a local commit. The same Linux-versus-Windows authentication distinction was already recorded in the global log, so check it before future pushes.

## ASTRA-20261006-03 — minimal owner CSV draft limits and verification correction

- Date / project: 2026-10-06; Rupani Academy owner CSV preparation.
- Category / status: Draft artifacts prepared; live project/entity binding is unverified, not an implemented feature.
- Evidence / impact: Default Astra database path does not exist. Current CSV parser skips lines before the task header and does not verify embedded project/entity IDs. Entities belong to projects, not individual tasks. Do not fabricate identifiers or call a metadata-only CSV bound to a project.
- Correction / prevention: Request the real app/project location and clarify project-level versus task-level entity allocation. Keep nine task columns; leave exact dates and unapproved predecessors blank. Verify selected import configuration before operational use; Full recognizes the draft headers whereas Simple does not enable all of them.
- Tool correction: An overcomplicated inline Python verification command failed with shell-quoting SyntaxError. Replaced it with one small reusable checker; do not embed nested exec strings in PowerShell commands.
- Verification: Three CSV drafts parse with Full configuration; 115 private and 124 charter titles, unique keys and parent links match the workbook. No real project, task, entity, account or application configuration was changed. Operational end-to-end upload, exact IDs and milestone reconciliation remain pending. Global log synchronized on 2026-10-07.

## ASTRA-20261006-02 — sample-workplan inspection corrections

- Date / project: 2026-10-06; Astra planning against Aly's Gantt workbook.
- Category / status: Inspection mistakes corrected; no workbook or application changes.
- Evidence / impact: Initial combined skill/memory reads truncated output. A source search guessed nonexistent gantt.js and scheduling.py paths. Relevant rules were reread in bounded chunks; rg --files identified app.js and service.py as the actual implementation paths.
- Cause / prevention: Repeated oversized reads and guessed module names. Inventory known source directories first and budget combined output below the tool limit.
- Verification: Read both workplan sheets, numbered rows, date formats, milestones, empty owner/status cells and current importer columns. Planning distinguishes source month targets from exact dates, existing capabilities from proposed changes, and source regulatory notes from verified legal claims. Global log synchronized on 2026-10-07.
- Preview corrections: The bundled Playwright browser was absent; verified installed Chrome was used successfully. The standalone preview wrapper refused replacement until its explicit overwrite flag was supplied; stale-wrapper checks were discarded and repeated. Browser inspection found clipped labels, corrected with short labels and full detail on selection; an overbroad label replacement briefly changed one task title and was corrected against the workbook. Calendar-day CPM checks show three days float on the occupancy branch and a 17-day selected-chain delay after adding 20 days there. The dependency network and dates are illustrative, not the full project's accepted critical path.

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

## ASTRA-20261007-01 - workplan implementation and verification corrections

- Date / project: 2026-10-06 to 2026-10-07; Astra W6ZSGA single-project owner CSV.
- Category / status: Confirmed defects in uncommitted implementation, corrected; final suite Ran 739 tests in 812.249s; OK (skipped=1). Global log synchronized on 2026-10-07.
- Evidence / impact: Independent probes found partial imports could retain one old plan while applying an incompatible related plan; unkeyed native tasks were absent from plan checks; raw comma/marker detection mishandled stripped semicolon files, intact quoted files and legacy CR line endings. Separate downloads initially reused spare keys. No real data was used or changed.
- Cause: Graph validation used one prospective snapshot and keyed nodes only; identity detection relied on serialized text; spare keys were computed solely from current tasks.
- Correction / prevention: Fixed-point validation with retained plans and persistent task IDs; structural CSV detection with explicit newline handling; transactionally reserve WP keys in project history. Cover hostile partial imports and files produced through alternative serialization, including positive legacy cases.
- Verification: Sixteen focused tests and one HTTP role-matrix test passed in parent and independent reviewer runs; eleven disposable guard-removal experiments each caused its regression to fail. Synthetic Chrome download/fill/upload/preview/commit and desktop/phone plan selection passed.
- Tool failures / correction: Repeated existing-file apply_patch context failures required inspecting every target for partial application; switched to UTF-8 source edits with exact occurrence assertions. One inspection used implicit cp1252, one test referenced a nonexistent file and another used the wrong create_task signature; corrected encoding, discovered the actual module and checked the actual signature. An undefined JS esc helper was corrected to escapeHtml; plan changes now use refreshGantt to preserve project navigation. Sandbox GitHub access failed and was retried through escalation.

## ASTRA-20261011-02 - first timeline reorder changes unrelated row positions

- Date / project: 2026-10-11; Astra task-handle browser verification after compaction.
- Category / status: Confirmed ordering defect, open. Confirmed layout shift; later-row drag cancellation reproduced but its cause remains unverified. Pending synchronization to the global log because it is outside the writable workspace.
- Evidence / impact: Chrome showed Build foundation, Open classrooms, Prepare site, Inspect foundation. Dropping Build foundation below Open classrooms saved Prepare site, Inspect foundation, Open classrooms, Build foundation; dates and links remained intact. Later-row Open classrooms drag starts twice emitted dragstart then immediate dragend. First-row date, below, after and concurrent drops saved successfully; above preview and cancellation worked.
- Cause: First backend reorder starts from created_at/id order while the visible timeline initially follows the task-list order. Exposing drop controls also moved the first date target about 63 pixels; its causal role in the later-row cancellations is unverified.
- Correction / prevention: Preserve visible order when initializing persisted ranks; cover actual first reorder, filtering/grouping and order/revision conflicts. Isolate later-row cancellation with browser event evidence before changing it. Keep drop targets stable during gestures. No source fix made in this verification task.
- Verification: docs/handoff/TIMELINE_DRAG_VERIFICATION_2026-10-11.md records browser results, persistence, critical-path changes and limits. Synthetic screenshots remain ignored under Temp; temporary event listeners were removed by reload. No owner records or deployment changed.
- Tool/communication recurrence: A raw Input.setInterceptDrags command was unsupported; Input.dispatchMouseEvent worked. Initial target geometry was read before drag controls appeared; fresh state and a second movement inside the live target produced a real drop. Unbounded jaira list JSON output was truncated; subsequent listing projected only handle/status/assignee/title. Git status could not enumerate unrelated old temporary directories; tracked changes were visible and preserved. Use bounded outputs and never equate a failed gesture with an app defect.

### ASTRA-20261011-02 repair follow-up (2026-10-12, ZFP6ET)

- Status: Local ordering and row-layout corrections independently reviewed; final publication and full-suite receipt pending. Global synchronization pending outside the writable workspace.
- Cause / evidence: Initial order came from creation order. Displaying in-flow drop controls expanded rows and caused later-row drag cancellation; hiding controls and then replacing them with absolute overlays each restored dragstart. Final Chrome measurements showed unchanged row/target geometry, and actual later-row Above, Below, date, After and Concurrent drops saved. Cancellation and reload preserved dates, order and links.
- Additional omission / correction: The first complete-snapshot implementation missed portfolio filters that hide a parent and promote its children into task-list order. Independent review caught this before publication. Actual-function Node regression failed before DOM sibling-order merging and passed afterward, retaining hidden slots, collapsed children and foreign-project isolation. Focused suite: Ran 24 tests, OK in parent and independent runs. Extra filtered-parent browser check is currently unverified because Chrome became unavailable; do not describe the whole feature as accepted.
- Tool failures / prevention: Initial Jaira ticket existed only on its ref; claim/move needed `jaira pull`. The installed CLI requires planning options and uses `dod --plan`, not a `plan` command. Initial creation inherited the existing CLI creator identity; subsequent writes explicitly use `JAIRA_USER=Codex`. Git pull needed escalation for FETCH_HEAD; no history rewrite. Repeated broad log output was truncated; use bounded sections. Early offscreen/before-paint drag probes were invalid and replaced by fresh in-bounds geometry. Browser recovery used documented troubleshooting and retained the selected binding; no security changes or owner records changed.
- Verification completion: Chrome had reconnected as a different browser instance; documented surface inventory recovered it. Actual filtered-parent drop changed Other,A,C,B to Other,C,A,B and reload retained it. This supersedes the temporary browser-unverified limitation above. A semantic Project label did not resolve; the observed DOM ID worked. An old drag-helper closure retained the disconnected binding; direct input through the current binding completed the gesture. Rebind closures as well as tabs after genuine reconnection, and do not confuse stale-tool handles with app failures.
- Final checks: Ran 770 tests in 508.309s, OK (skipped=1), exit 0. The skip is the attachment symlink rejection test because symlinks are unavailable here. An initial draft inferred a different platform skip; checking the exact receipt corrected the draft before publication. Independent code review and actual desktop Chrome cases pass. Owner acceptance and touch/narrow-screen dragging remain unverified. A sandbox Jaira note write was denied by its outside-workspace lock path; authorized elevated CLI write recovered it.
- Publication tooling: Sandbox remote lookup could not connect; elevated read confirmed unchanged origin. Initial partial-log patch slicing matched a hunk's closing marker and was rejected without staging; anchor hunk matches to line starts. Git index writes require escalation in this workspace. Preserve unrelated log edits by staging only the task's addition hunk.

## ASTRA-20261012-01 - automatic schedule preview identity and verification corrections

- Date / project: 2026-10-12; SXAWHN automatic linked scheduling, uncommitted implementation.
- Category / evidence: Independent review found preview fingerprints omitted the source task ID from the request path. A preview for A could apply to B with equal revisions. A dedicated regression failed before adding the source ID to the fingerprint. No owner data or deployment changed.
- Correction / prevention: Bind the full action identity, actor, source, project, tasks, links and order to preview acceptance. Commit recomputes the fingerprint inside the transaction; regress reuse across sources as well as stale descendants, project deadlines, graph and task-list changes. Correction implemented; focused and final verification pending.
- Test/tool errors: A completed-task test expected Forbidden rather than the existing ValueError contract. A plan fixture passed an unsupported create_task plan_option key, so it did not create alternatives. Use the persisted import metadata contract. Broad combined reads again exceeded output budgets; use single bounded reads. These are verification errors, not product defects.
- Review clarification: A Shared task may shift multiple alternatives. An agreed project deadline must be previewed against the overall project range, while alternative forecasts remain separately visible; do not silently use only Shared work's finish as the full project finish.
- Global synchronization: Pending outside the writable workspace.
- Implementation check: Adding the overall schedule `bounds()` helper exposed a local list with the same name in the graph solver, causing fifteen focused errors. Renamed the local list to `required_starts`; Ran 16 tests in 4.125s, OK. Re-run affected tests after extracting helpers and avoid shadowing callable names. The source-ID regression is now green; final HTTP/browser/full-suite checks remain pending.
- Verification completion: Parent focused 17 tests in 7.611s OK; independent focused 17 in 8.665s OK. Removing the source-ID binding or fingerprint check in memory makes the respective regression fail. Full suite Ran 787 tests in 561.770s, OK (skipped=1), existing unavailable-symlink skip. Actual Chrome Below/Above/date/Concurrent and accessible After flows update links, chains, critical indicators and project schedule; both deadline choices, unchanged owners, cancellation and reload pass. Preview readability was corrected (checkbox layout and separated schedule ranges); final static review pending. Initial post-navigation screenshot showed the prior frame; fresh capture verified the actual Overview before saving proof. No real data or deployment changed.
- Final review / synchronization: Independent final static and handoff review passed. Canonical global log was reread and missing ASTRA-20261011-02 and ASTRA-20261012-01 sections appended on 2026-10-12; both IDs verified present and existing entries preserved. This supersedes the pending-global limitation above. Publication and App Owner acceptance remain separate.

## ASTRA-20261012-02 - scheduling actions missing from phone and List views

- Date / project: 2026-10-12; 827Q51 launch QA after accepted SXAWHN.
- Category / evidence: Confirmed UI feature gap. The same synthetic owner had four Move task controls in desktop Gantt, zero DOM controls at 390px, and zero in desktop List. Small widths automatically render the schedule table; that renderer omitted movement actions, and the click handler was registered only on Gantt.
- Impact / cause: The new linked scheduling preview was unreachable through its own task movement controls in table views. This was rendering/event wiring, not hidden CSS or different permissions. Existing service guards remained intact.
- Correction / prevention: Actual-function Node regressions for eligible task/subtask table rendering and shared click-to-review dispatch failed before repair (Ran 2 tests, failures=2). Add one eligible action per task/step, share the handler, and consistently hide actions for fixed tasks/closed projects/non-managers. Run responsive/table QA for every control introduced only on a Gantt path. Focused tests pass; browser/full/independent verification pending.
- Tool recurrence: An inspection search found no matching variable name, so bounded source lines identified the real name. One stale completed exec session was accidentally polled and rejected; use only the returned live session ID. Combined context reads again exceeded output budgets; use bounded single-purpose reads. No real data, accepted ticket status or deployment changed.
- Global synchronization: Pending outside the writable workspace.

- Independent-review omission: Table entry points initially reused the Gantt-only snapshot query. Hidden-parent filters then lost the table sibling sequence. Actual renderer/grouping/snapshot regression failed before table row IDs and a combined selector, then passed; parent focused Ran 4 tests in 0.230s and independent Ran 4 in 0.251s, OK. Removing table capture in memory fails the regression.
- Additional tool lessons: A guessed test module path and absent handoff filename failed; use rg --files before reads. PowerShell rg with Temp/*.py failed glob expansion; use -g with a directory. Direct unittest imports needed tests on PYTHONPATH, then passed. Reviewer discarded a guessed-name loader error and reran the exact mutation regression. A semantic label selector did not resolve the browser form; observed select names worked. Zoom shortcuts had no effect; actual 200 percent zoom remains unverified, distinct from reduced-viewport checks.
- Browser completion: Actual Chrome table controls, 390px cancellation, 320px keyboard apply/reload, desktop List and reduced viewport pass using disposable fixtures. Filtered-parent table Above saved Other,C,A,B and C to A dependency; reload retained them. Owners remained unchanged and unchecked deadline choice retained the agreed deadline. Final full suite pending; no hosted or physical-device acceptance.

- Final verification: Ran 790 tests in 602.540s, OK (skipped=1), exit 0. Existing unavailable-symlink skip. Final Node syntax/focused tests and independent review pass. Earlier 789-test receipt is superseded. Combined definition of done remains unticked because actual browser zoom is unverified; handoff discloses it. Synthetic fixtures on different localhost ports share cookie scope: bootstrap the fixture session when switching ports; do not mistake the resulting sign-in page for a broken app. Initial evidence frame was discarded and recaptured after fresh DOM confirmation. Sandbox remote lookup failed; elevated lookup verified origin unchanged.

- Global synchronization completed: ASTRA-20261012-02 appended after rereading canonical mistakes.md; prior entries preserved. Independent final handoff review passes with the stated zoom limitation.


## ASTRA-20261013-01 - stalled HTTP connections and verification corrections

- Date / project: 2026-10-13; AY5EZ0 launch hardening, NEXT_STEPS B1.
- Confirmed defect / evidence: Actual loopback tests reproduced idle connections, incomplete headers and JSON/raw request bodies remaining open past the test deadline. AstraHandler inherits timeout=None; installed StreamRequestHandler.setup applies a timeout only when configured. Production has no finite socket inactivity policy.
- Scope / impact: Stalled clients hold request threads; body reads also hold per-request SQLite connections. This repair covers inactivity, not an absolute total request duration, continuous trickle clients, concurrency caps, proxy rate limiting or deployed security.
- Test correction: Initial red run had five timeout failures plus a Windows temporary-database cleanup error. Closing the client was not followed by waiting for the observed request handler to finish; synchronize cleanup before removing files. Treat harness cleanup errors separately from product repro.
- Tool recurrence: Combined context/search output was truncated; bound each result and inspect exact references. PowerShell rg with literal filename globs failed again; use -g and directory arguments. Jaira planning option was initially omitted, so pre-process move was refused; enable planning before moving. One elevated ticket pull hit temporary GitHub DNS failure; retry succeeded without changing configuration or taking over another ticket.
- Status / prevention: Production correction and final verification pending. Keep real socket regressions and guard-removal checks; shorten only a valid positive policy so tests do not install the missing guard themselves. No real data or deployment changed. Canonical global synchronization pending.

- Reproduction/fix verification: Corrected the test cleanup race; pre-fix Ran7 in8.872s failed5 (no cleanup errors). Setting timeout alone released idle/header sockets but three body tests returned500. Wrapped only socket body-read timeouts in RequestBodyTimeout and returned408 with Connection close, preserving finally cleanup. Focused Ran7 in4.026s OK. Full and independent verification pending.

- Independent verification: Ran7 in4.192s OK; timeout=None mutation fails idle release, and removing body-timeout classification fails with500 versus408. Independent scope/source review passes. Evidence is socket inactivity only; final full suite and publication pending.

- Hygiene scope: A broad core.autocrlf=false working-diff check exposed pre-existing CR line endings in unrelated dirty ticket files and produced oversized output. Preserve those owner edits; run scoped and staged checks on this repair. Scoped source, tests, handoff and own ticket contain no CR bytes.

- Handoff review correction: README initially said all incomplete bodies return408, which was too broad; only timed-out body reads use this path. Revised that wording. EOF/truncated framing remains separate; do not describe timeout evidence as a full request-framing repair. Detailed handoff/source scope review otherwise passed.

- Final verification: Ran797 in419.228s OK (skipped=1), exit0; existing unavailable-symlink skip. Independent focused/source review passed. An unmodified production-policy probe measured idle/header closure and JSON/raw408 at30.007-30.023 seconds, with normalstatic200; no timeout patch. Tests and default-probe receipts are ignored. Publication and App Owner acceptance remain separate.

- Canonical synchronization completed: ASTRA-20261013-01 appended after rereading mistakes.md; earlier pending-log/verification lines are superseded. Final independent receipt and handoff review passed. Publication remains the next step.


## ASTRA-20261013-02 - actual browser zoom verification completed

- Date / project: 2026-10-13; 827Q51 outstanding zoom check, explicitly requested by Aly.
- Status / evidence: Earlier browser automation shortcuts changed neither zoom nor DPR. Native Windows computer-use controls now visibly set Chrome to200 percent. Without viewport override, document width/DPR changed1251/1.5 to625/3; native200 popup and reachable preview buttons are saved in ignored Temp/827Q51-native-200-preview.png.
- Verification: At actual200 percent, keyboard Move task, linked preview, deadline checkbox, Cancel, Apply/reload and Timeline automatic table4controls/0Ganttrows passed on fresh disposable data. Build15-17, Open19-21 and Inspect22-23 persisted; Taylor Example ownership and unchecked agreed deadline16 remained; scheduledfinish23. After dependency preview also passed and cancelled. Restored original100 percent and1251/1.5.
- Tool prevention: Native Chrome capture initially combined stale Google AX text with fresh Astra pixels. Reobserved matching Astra title/address before zoom input or index actions. Use native browser controls when page-level shortcuts do not affect browser zoom; distinguish actual zoom from viewport emulation and never act on mixed stale/fresh captures.
- Independent review: Screenshot and handoff inspected; remaining zoom criterion is proven. Prior accepted functional repair is unchanged. Physical-phone/touch/screen-reader/hosting remain unverified. No owner data, credentials or deployment changed; no repeat acceptance required. Canonical synchronization pending.

- Canonical synchronization completed; older zoom-unverified status is superseded. Independent screenshot/handoff review passed and owner Done move dry-run is allowed. Human lane is unchanged.


## ASTRA-20261013-03 - deadline extension routing clarification

- Date / project: 2026-10-13; Aly requested that increased deadlines go to Owner and Chairman.
- Verified current gap: timeline_schedule_apply notifies responsible task owners, while generic task/project notices go to other active App Owners. Neither generic recipient helper includes Chairman. A linked project's calculated finish can move later without changing its agreed target date.
- Scope / decision: Aly selected in-app notification on 2026-10-13, retaining existing approval rules. Do not interpret Chairman notification as new protected-change approval authority or enable external delivery.
- Tool recurrence: Initial searches guessed three nonexistent test filenames; corrected by rg --files and searches over the tests directory. Use actual module names before file arguments. No app behavior, data or ticket lane changed; global synchronization pending.

- Reproduction / correction: Initial focused run exposed eight product failures; separate test errors guessed a nonexistent authenticate API and PATCH/PUT instead of the actual POST task route. An initial-date fixture retained a start date, which correctly already contributes a project finish; removed both dates for the true no-prior-range case. Final focused Ran10 in11.164s OK. Task event IDs are reused for extension notices; a dedicated active Owner/Chairman recipient helper leaves other private routing unchanged. Whole-operation transaction snapshots avoid intermediate project finishes for composed changes.
- Verification: Independent source review passed; focused Ran10 in8.469s OK; in-memory extension-detection removal fails the regression. Actual Chrome Owner save/confirmation and Chairman Inbox show task/project old/new dates; Chairman read status persists after reload. Initial browser Inbox selector missed its new unread-count accessible name; refreshed DOM and used the observed name. Synthetic data only; full suite and publication pending.
- Tool limitations: Combined reads again exceeded output budgets; use bounded reads. Two supplemental reviewer turns failed at model capacity after the successful independent source/test review; this is a tooling limitation, not a code defect. No other model selected or external delivery enabled. Canonical global synchronization pending.

- Full verification: Ran807 in525.988s OK (skipped=1), exit0, existing unavailable-symlink skip. Source unchanged since independent review and browser check. Supplemental handoff/bulk verification and scoped publication remain pending; no real data, accounts or deployment changed.

- Supplemental verification: Independent +3-day bulk/Undo and -3-day bulk/restoring Undo passed. One original-to-final project finish notice per recipient; earlier changes emit none. Handoff and saved Chairman screenshot independently reviewed, no blocking findings. Screenshot proves initial two unread; later one-unread reload was separately observed by browser. Publication remains pending.

- Canonical synchronization completed after rereading mistakes.md; earlier pending synchronization lines are superseded. Prior global entries preserved.

- Board/tool correction: First move to human omitted the required --question field and was refused without mutation; read CLI help and supplied the owner acceptance question. Validation has no errors and existing unrelated warnings; do not regenerate agent instructions or repair unrelated board entries. Publication criterion remains unticked until the normal push completes.

- Scoped staging correction: Refreshing the own-fragment patch against HEAD failed because those fragments were already staged. Generate the incremental patch against the current index while constructing the desired scope from HEAD plus only this task's content; preserve unrelated working edits and avoid resetting the index.

## ASTRA-20261013-04 - B1 security review, parser budgets and authority drift

- Date / project: 2026-10-13; ZQQCJM, Aly-authorized B1 whole-app review. Category: confirmed input/authorization defects repaired locally; final full/publication pending, hosted operation unverified.
- Evidence / cause: Real sockets reproduced negative/duplicate length acceptance, incomplete-body dispatch and non-object input. Independent workbook probes expanded a small DTD into a million-character cell, duplicated a sheet target to multiply allocation, and surfaced unclassified archive errors. Early account/task/assignee validation trusted snapshots that could predate revocation, deactivation or membership loss.
- Correction / prevention: Reject ambiguous/unsupported framing and incomplete/non-object bodies before dispatch; common header protection covers framework errors and downloads. Parser-level DTD refusal handles encodings; worksheet targets unique; archive properties/errors refused. Re-read current account/project authority and new assignee eligibility under write locks, preserving unchanged legacy assignments and Chairman assignment-only rights. Foreign-Origin and form-type login now refused; no browser exploit claim.
- Owner decisions: Caddy logs real IPs; keep former importers' own reports; reopen closed projects before any new task; agreed deadlines Owner-only on both paths. Do not remove the deliberate own-report exception or broaden approval authority. No deployments/accounts/real data or external notifications.
- Test/tool corrections: An early send_error implementation placed Cache-Control before the status line; focused BadStatusLine failures exposed it. Send framework cache header at end_headers instead. A shared assignee red fixture contaminated later subtests after failed writes; use one task per case. Initial broad reads again truncated; bound output. Latest eligibility fix superseded an in-progress full run; positively identified this checkout's exact run.py launcher/server, used native process termination (PowerShell Stop-Process has a recorded failure), then restarted final suite. Child had already exited, not an unrelated-process failure.
- Verification: Initial 17 new tests failed48 conditions, no setup errors. Final focused44 in27.512s OK; independent parser43, account30 and finalassignment29/18 pass. Required guards fail when removed in memory. Independent source review passes; full suite/browser/handoff/publication pending. Scope includes static all-route guard inspection and92 signed-out/65 CSRF probes, not a newly executed valid-role matrix for every endpoint or hosted assurance.
- Hosting research: Current official Oracle docs specify2OCPU/12GB A1, not old4/24 claims. Google free compute still charges ordinary public IPv4; Render Free loses SQLite on restarts; AWS is time-limited. Preserve free-only/account gates and check actual console eligibility/capacity before provisioning. Canonical global sync pending.

- Browser verification: Actual Chrome Owner form saved target20to23October; reloadpersisteddeadline/notice. ClosedOverview hidAddtask/Import; reasonedreopeningrestored controls. Manager hasnoOwneradministrationentry, so do not describe the readonlyManager form branch as browser-tested; HTTPguard tests prove denial. Reload screenshot initiallyshowedtransientHome despiteprojectDOM; discarded/replacedaftersettledDOM. Prior stale-frame prevention applies. No realdataorcredentialchanges.

- Full-suite correction: Ran832 in1054.252s, FAILED(failures=1,errors=8,skipped=1). Historical v13/v14 fixtures called today's create_task, whose current-user reload needs a v16 column; write historical task rows directly, as existing legacy_user already does, without weakening production authorization. The locked revision recheck changed an established late-write conflict message; preserve that message while retaining the permission check. Corrected migration48 in9.388s OK; independent delta review and final full rerun pending. Focused success did not prove full compatibility.

- Independent delta:81 in57.770s OK; parent contract24 in33.742s OK. CLI note first refused local-state lock access under sandbox, then succeeded through escalation. Process inventory likewise needs approved read access. A guessed backup test filename was absent; locate files with rg before targeted reads. These are tool/inspection limitations, not application defects.

- Canonical synchronization completed after rereading mistakes.md; prior entries preserved. Exact owned browser tab closed and disposable fixture PID30928 stopped after fresh command-line verification. GitHub branch lookup failed under sandbox networking, then approved read-only retry confirmed origin unchanged at e9a15f4. Board validation errors=false with existing warnings; no instruction regeneration or unrelated ticket edits.

- Hygiene inspection correction: A whole-working-tree diff with core.autocrlf=false treated existing CRLF ticket content as trailing whitespace and produced oversized output. Preserve those unrelated working edits; assess only normalized scoped staged blobs/diff for publication. Independent final handoff/hosting review found no blocker and retained the failed full run rather than hiding it.

- Superseding verification: Full suite Ran832 in976.020s, OK(skipped=1); Node/UI tests ran, unavailable Windows symlink case unverified. Independent final source/delta/document review passed; required guards fail when removed. Browser and canonical log sync complete; publication pending. Earlier pending verification statements are superseded; failed run retained.

- Scoped publication verification:13 intended files; staged blobs/diff LF, cached diff check passes, private/database/browser files excluded. Unrelated working changes retained. ZQQCJM moved into human through CLI; only Aly accepts or moves it out. No deployed result claimed.

## ASTRA-20261013-05 - release planning, board and handoff drift

- Date/project:2026-10-13, TV43F1; Aly requested planning, independent-LLM package and complete safe publication, not new implementation/deployment.
- Confirmed documentation drift: September counts and several current-worded acceptance/browser claims persisted. Current board85:25done/39signoff/7human/14backlog; JM7CFP and3NT40T declared DoD incomplete despite later child evidence, and accepted W6ZSGA/JM7CFP/2FREQ9 not Done. First-login/self password, backup/version CLI, CI and hosted gates remain gaps. Added current plan/board/prompt, dated entry-point notices and decision sources; remove historical force-command advice conflicting with AGENTS. No inferred acceptance or ticket closure.
- Prevention: Recount all CLI tickets and reconcile lanes, ticked criteria, actual proof and owner acceptance separately. All Done is not hosted readiness; superseded/deferred tickets need explicit owner disposition. Distinguish local gates from drills requiring an authorized staging VM. Other LLM reviews are unverified until actual reports exist. Keep draft checkbox data distinct from owner decisions.
- Inspection/tool recurrence: Early batched broad reads again truncated; bounded rereads recovered skill and source context. Guessed cli.py/deployment/CI paths absent; use rg --files before naming them. Windows literal docs/handoff/*.md failed; use rg -g '*.md' on the directory. Unsupported jaira plan/option help resolved to root help; dod --help documents --plan --add and --option. Inaccessible tmp directories remain unverified/excluded. Do not infer their contents or delete them. No product source changed.
- Verification/publication: fresh full suite and independent package review pending; explicit tracked scope will include inspected pre-existing Aly Done transitions and safe notes, excluding private XLSX/PDF/data/Temp/keys/environments. Canonical global synchronization pending.

- Independent completeness correction: Reviewer found WCAG2.2AA was implied rather than named, and F1 incident/offline guide and F3 Owner/scoped user-data exports were not explicit. Added each to preparation and review criteria; read the full F phase and distinguish later monthly/quarterly operating evidence from pre-launch proof. An initial combined patch included a board-text context in the plan file and failed atomically; reread exact targets and apply only matching hunks. No source changes or partial patch.
- Fresh verification: Ran832 in1011.192s, OK(skipped=1), exit0; Node drivers ran, unavailable Windows symlink case unverified. All86 unique local ticket rows and28 handoff docs/link targets checked; app/tests/package source unchanged from da1b3fd. jaira validation checked86, errors=false,40 existing warnings. Independent final review and scoped publication pending.

- Final package reviews: independent content/metadata and source/factual reviewers pass after completeness corrections.20 exact safe staged files, LF/cached diff check pass; no application/test/private artifact staged. Own TV43F1 criteria clarify commit-readiness versus post-push Git proof; the actual publication requirement is retained and verified/reported after execution. An initial staging call followed a still-running multi-command CLI session; waited for completion and refreshed final ticket/audit before commit. Always finish dependent CLI sessions before staging their output. Publication/canonical synchronization next; hosted/external-LLM reviews unverified.

## ASTRA-20261013-06 - critical built-work and UI UX review

- Date/project:2026-10-13,26ZF8D; Aly requested critical self-review and said go. Scope review/evidence, not product fixes, acceptance or deployment; synthetic fixtures only.
- Confirmed independent actual-JS probes: Out-of-order task details render A while global save target remains B; failed/slow assignee lookup resets selected owner to empty before save; notification fetch failure silently substitutes empty/unread0; owner-only assignment history displays No field changes. Browser/server reproduction pending. Do not claim live user data was affected; the workspace source remains unchanged.
- Tool/inspection recurrence: broad initial batching again truncated; narrowed code-review skill/rule reads. The code-review skill is a fixed-diff workflow, whereas this request is whole-product review, so use the frozen current source and whole-ticket criteria without inventing a comparison ref. Windows literal wildcard path failed again; pass a directory with rg -g. One independent backend reviewer failed at workspace credits; another source/spec reviewer completed. Continue meaningful direct verification and disclose the unavailable independent backend pass, not an invented success. Native/physical-device quality remains unverified.
- Prevention: preserve task identity through asynchronous loading and mutation, retain existing assignment until eligible options load, show recoverable partial/error state rather than empty success, and render readable assignment changes. Classify known scope/deferred features separately from defects in built work. Fresh full/browser/coverage review and canonical log synchronization pending.

- Superseding verification: Current-source synthetic Chrome fixture reproduced persisted wrong-task save (A displayed; POST/B revision2; A unchanged), title-only save clearing owner after HTTP500 lookup, owner-only History saying No field changes, required-field validation blocking Cancel in New project/Capture, Viewer creation form reaching a correct403, unnamed reviewer selects, non-navigable project search result and global unread6 becoming0 on lookup failure. Inbox itself displays the failure paragraph; correct the earlier broader empty-Inbox risk to a badge/cache defect. No owner records changed and no product fix claimed.
- Fresh positives/limits: Full Ran832 in568.186s OK(skipped=1), Node drivers ran; unavailable Windows symlink remains unverified. Phone-size later-row Move/After preview saved a dependency/date/project finish change, retained target, survived reload and produced Chairman old/new extension notices. Pointer/touch, all-role and physical-device/AT checks not exhaustive.38 feature records139 criteria plus5 contextual records12 criteria enumerated without accepting tickets.
- Tool/corrected assumptions: JSON ticket id is full identity; handle is the short key. Initial lane/key filters failed/read the wrong count; corrected to status/handle and asserted38/139 before artifact generation. Viewport handle was not defined after compaction; read capability docs before instantiating. Browser screenshots immediately after navigation/resize can show a previous frame; use settled observations and label limitations. Native template prompt blocked focus/screenshot calls; prompt dismissal succeeded via documented API but subsequent browser exploration timed out. No completed template apply claimed.
- Repeated inspection/patch failures: An rg call guessed a nonexistent prototypes directory; use rg --files root first. A combined patch included an invented prompt-file context and failed atomically; reread the actual file and apply matching hunks. Do not use placeholder contexts. Current review report/criteria and independent-review prompt prepared; report review, safe publication and canonical log synchronization pending.

- Independent report correction: All43 sections151 verbatim criteria and resolved links verified; corrected a generic nonexistent prototype path and wording that could imply a fresh research/prototype suite. Main report passed bounded independent review with backend completeness, physical-device/AT and hosted readiness explicitly unverified. Reviewer confirmed screenshots are supplemental, not standalone wrong-task/owner persistence proof. Browser tab closed and viewport override reset; exact fixture processes verified before targeted cleanup. No product changes.
- CLI environment: first plan/note writes were denied by the sandbox's outside-workspace jaira lock folder, then succeeded through escalation. Finish the entire CLI session before staging; do not confuse a yielded shell session with completion. Safe documentation publication and canonical synchronization remain pending.

- Canonical synchronization completed after rereading mistakes.md; all earlier bytes preserved. Own browser tab closed and verified fixture launcher/child terminated, leaving other servers untouched.26ZF8D handed to human through CLI; no existing human/signoff/Done ticket moved. Sandbox GitHub lookup failed, approved retry confirmed unchanged origin5f379c9. Publication checks next; application remains unchanged and not ready.

## ASTRA-20261013-07 - critical frontend repairs

- Date/project:2026-10-13,WMW428; Aly authorized Fix all the issues. Scope all nine confirmed review findings plus duplicate-name/token/navigation debt. No deployment, real records or existing acceptance transitions. Private Capture versus project quick-add is a conflicting product specification; asked Aly while independent repairs continue.
- Evidence/prevention: Current-source regression13 failed before fixes; preserve rendered task identity through delayed/same-task/close responses and capture mutation IDs before awaits. Keep stored owner selected while people load; disabled failed controls never serialize Unassigned, and show Retry. Preserve stale notification snapshot rather than fake zero; readable ownership audit and role-aware creation cues. Full/browser/independent verification pending; do not call repaired source ready merely because focused tests pass.
- CLI/tool corrections: New jaira create lived only on its ref, so first claim/move failed until pull. Checklist --add accepts no item number; read help and corrected. Broad reads again truncated; bounded follow-ups. A failing source assertion printed whole JS/CSS; changed to bounded symptoms. Colour-token keyword substitution accidentally changed white-space properties; caught by inspection and restored before browser/full checks. Future transforms must target property values rather than arbitrary words. No such CSS shipped.

- October14 decision: Aly chose direct project-task creation named Add a task. Updated source and authoritative design/decision documents; private drafts remain future scope. No acceptance or deployment inferred.
- Regression/review corrections: The original13 tests failed before repair. Intermediate web187 failed3/errors2; repaired the accidental white-space transform, updated DOM stubs for select readiness/option clearing and token contrast resolution, and corrected a stale Member creation expectation to match unchanged service authority. Test-fixture missing generated nodes were harness errors, not product defects. Independent review found focus restoration, numeric inactive accounts, bulk picker readiness, final-result selection refresh and feedback-tone gaps; fixed and added coverage.17 integrity and221 web pass; five guard removals in disposable copies each fail their regression.
- Patch/tool recurrence: Three combined patch attempts failed atomically when their source hunks were ordered incorrectly; ascending matching hunks succeeded. Browser bindings reset and the historical ID5 disappeared; fresh inventory identified Chrome4. An earlier owned fixture ended, so restarted only the synthetic fixture; one browser-policy request failure was resolved by documented retry. SQLite inspection used a file URI and approved read access to the temporary DB. Screenshots can show a previous frame: separately inspected final task-dialog image; do not label the earlier Home image as a dialog.
- Final verification: Ran849 in583.910s OK(skipped=1), exit0; Node drivers ran. Independent source delta PASS with17 independently run and syntax check, not an independent full-suite/browser rerun. Synthetic Chrome checks prove correct-task save, owner retention, assignment history, blank Cancel, Viewer controls, named template creation/search and notification Retry; read-only SQLite supports the principal persistence checks. Phone viewport is a browser approximation; physical devices/AT and hosted release gates remain unverified.
- Handoff recurrence: An unfiltered jaira list again produced oversized/truncated output. Filter structured CLI output to count/lane/proof before printing; fresh bounded validation is required, not inference from truncated text. Publication and canonical log synchronization are pending until verified below. Do not mistake local pass for owner acceptance or all-ticket closure.

- Final handoff: independent documentation PASS; WMW428 moved to human through CLI after all dependent commands completed. Board88:25Done/39signoff/10human/14backlog; validation errors=false,44 warnings and generated-note drift disclosed, no unrelated board edits. Browser viewport reset and owned tab closed; freshly verified fixture launcher35776/child28848 stopped, leaving user servers untouched. Canonical global entry07 appended after rereading latest bytes; all prior bytes preserved. Scoped publication verification follows.

- Publication preflight: sandbox staging denied index.lock access and GitHub lookup could not connect; approved retries succeeded, with origin still9a509ed. Exact13 intended staged files verified; all staged blobs/diff LF and cached diff check pass. Private XLSX/PDF/database/browser artifacts excluded. These were environmental permission/network limitations, not application test failures. Complete dependent CLI writes before staging and never infer publication from local commit alone.

- October14 acceptance follow-up: Aly's Ticket accepted refers to WMW428 and the supplied4d92bbd repair receipt. Record chat acceptance promptly and remove stale awaiting-acceptance wording without asking again, while preserving the human lane because AGENTS forbids agent transitions out. Acceptance does not authorize hosting or close other tickets. A combined118-plus-line rule/log read again truncated; narrow rereads recovered the missing rules. Use smaller bounded outputs before handoff. Documentation/CLI-only scope; new full pre-push receipt and independent metadata review pending.

## ASTRA-20261014-09 - review guard repairs

- Scope/authority: Aly said fix these after the Claude-review reconciliation. MJ5Q35 tracks closed-project template/dependency guards and stale actor/membership/eligibility writes, plus Owner-only project reopen aligned with Z72D79's dated October5 note. Aly explicitly selected Keep ordinary edits allowed during review; no submitted freeze. Earlier WMW428 acceptance remains recorded; no existing protected lane, real database, account or deployment changes.
- Proven negatives before repair: new15 service/HTTP tests yielded19 failures with no errors after harness corrections. The first run had17 failures/3 errors because a shared dependency fixture created a cycle/deleted the row, and it tried to deactivate a secondary owner without revoking ownership; isolated writes with rollback and used reachable member deactivation. The earlier reconciliation's primary-demotion constraint is a harness error, not proof the stale-secondary issue is impossible.
- Prevention/repair: validate the current active/global role after the write lock, preserve specialized primary-owner sentinels/audits, and recheck project permissions and target eligibility under that lock. Global-role freshness alone does not cover manager-to-viewer membership changes. Keep cleanup actor-independent. Templates are captured atomically; copying a historical template stays allowed, destination instantiation/dependency changes require an open project. Session revocation does not cancel in-flight requests.
- Intermediate corrections: automated transaction replacement over-restricted former primary owners and generic manage permission would block Chairman assignment. Core181 initially failed4/errors1(skip1); removed blanket primary-flag rejection, retained the existing primary-specific audited guards and password-reset refusal semantics, and used view permission for the shared schedule context with action checks inside callers. Core181 then OK(skip1); Assignment26 OK; focused26 OK before two additional cases. A matrix fixture omitted lock kind and was corrected. No failing implementation claimed ready.
- Tool lessons recurrence: UTF8 omitted in an AST source read caused Windows cp1252 decoding failure; explicit encoding fixed it. A patch guessed an untyped field context and failed atomically; reread exact lines before retry. A guessed workplan_csv.py path was absent; source discovery identified workplan.py/workplan_excel.py. Combined reads again truncated; smaller bounded reads recovered the needed context. jaira pre-process move required the planning option; a refusal was retained and the specified plan drove in-progress without force. Finish yielded CLI commands before staging.
- Current verification: focused28 and final independent/full/browser checks pending until their receipts below. Rejection audits and bulk cleanup need regression coverage; not just business-row protection. Outstanding password/recovery/CI/hosted gates are separate release work, not silently marked complete by this repair.

- Independent review corrections: blindly wrapping audit-only _audit_board_block rejected the stale actor again and lost the rejection record. Separately guarding board-rank bookkeeping after a delegated committed move could return Forbidden after a successful mutation. Restored audit-only transaction and added one outer transaction for move/rank/response; SQL rank-storage fault now rolls back status/revision/history. Restored specialized account guards to retain their existing audited primary-owner sentinels; global role/active freshness does not remove a former primary's valid secondary project rights. Independent final source32 in50.304s OK/PASS; parent32 in52.677s OK. Six distinct guard removals detected in memory with source preserved.
- Browser/tool verification: synthetic Chrome confirms Chairman lacks Reopen and App Owner reasoned reopen saves Active plus an Activity record; screenshots separately inspected, owned tab closed. An unscoped Reopen button matched two controls; refreshed state and scoped to observed submit ID. Several small output budgets again truncated combined results; use fewer reads and adequate per-result space. One retry patch included a nonexistent truncated audit-helper signature and failed atomically; reran only exact scoped hunks. Main server/data unchanged; physical/device/hosted state unverified.
- Test/publication correction: focused Board76 failed1 solely on changed permission-denial wording; preserved the original role-specific message while retaining locked recheck. The already-started outdated full process was verified and stopped, its partial log retained, then final full was restarted against the corrected source. Never count an interrupted run as a pass. Handoff now corrects the supplied report's arithmetic:88 minus25 is63 notDone, not60; neither number is an unaccepted-launch-blocker count. Final full/canonical synchronization/publication remain pending until confirmed.

- Historical-schema correction: a generic get_user call in the new guard read is_primary_owner before older migration fixtures had that column; DB48 failed8 errors. Narrow authority SQL now reads id/global_role/active only; DB48 in12.729s OK and final-source focused32 in54.087s OK. The second partial full run was stopped and retained, not called a pass. Final full Ran881 in830.547s OK(skipped=1), exit0; Node/UI drivers ran, unavailable Windows symlink unverified. Independent tiny source-delta PASS retains locked authorization and original board denial wording.
- Evidence/cleanup correction: qualify dependency HTTP coverage as addition only; removal has service and write-boundary race checks, not a separate HTTP receipt. Actual submitted responsible-person change remained submitted/revision3. Browser tab closed; freshly verified synthetic launcher45032/child39476 and its subprocess tree stopped. CIM process inspection required escalation; do not infer cleanup from a denied inspection. Main server/data remain unchanged and its loaded backend is unverified. Publication, final metadata review and canonical synchronization follow.
- Final board/tool correction: CLI session completed before staging; own MJ5Q35 moved to human, no existing protected lanes changed. Board89:25Done/39signoff/11human/14backlog; validation89 errors=false/44 problems, existing AGENTS/CLAUDE generated-note drift. First JSON aggregation incorrectly treated list envelope as ticket rows and guessed validation property names, returning a meaningless count1/null; inspected exact keys and counted tickets/problems correctly. Never publish guessed structured-field counts. Exact scoped publication and canonical synchronization remain to verify.
- Final handoff verification: independent documentation/metadata PASS confirmed the actual full receipt, source-delta approval, policy, coverage limits and board counts. Canonical global entry09 appended after reading latest bytes, preserving all prior content. Application/tests unchanged after the final full run. Only11 intended source/test/handoff/ticket files will be staged; unrelated .commandcode, private XLSX/PDF and inaccessible temporary directories remain excluded. Normal publication and its SHA are verified separately after execution.
- Publication environment recurrence: sandbox staging could not create .git/index.lock; approved escalation is required. This is a filesystem permission limitation, not a failing application check. No unrelated content is included by the retry.

## ASTRA-20261014-10 - reviewer follow-up and next password gate

- Date/project:2026-10-14, Project Astra; Aly said proceed after the strengthened c13c7de recheck.
- Confirmed corrections: Current DECISIONS_LOG already records Aly's October14 ordinary-submitted-edits rule, despite the review's drift note. At89 total/25 Done, non-Done is64 (39 signoff+11 human+14 backlog), not63. Do not call all open tickets launch blockers. Exact scratchpad database-copy path from the review returned NOT_FOUND under approved elevated check; no file was deleted and current/other locations remain unverified.
- Next-gate discovery: NEXT_STEPS A5 specifies forced change of owner-created/reset temporary passwords, signed-in self-service change requiring current password, 8-character minimum, user_events audit, revoke other sessions, preserve no-lockout. No open A5 ticket exists; existing matches are unrelated password-reset CLI signoff and completed basic reset/lockout protections. Capturing the separately specified release gate is authorized by Aly's continue-to-launch instruction.
- Tool correction: A first parallel read used an abbreviated nonexistent C:\Users\Aly path instead of the exact user profile path; it failed with file-not-found. A read-only git merge-tree attempt used local branch main, absent from this single-branch checkout, so mergeability was not established. Use exact supplied paths and inspect available refs before claiming local merge proof.
- Jaira capture attempt: PowerShell parsed an apostrophe inside the single-quoted --dod value as a string terminator, so ticket creation did not run. Retry with safely quoted arguments after recording the failure; confirm ticket identity before any claim.
- Jaira filesystem boundary: safely quoted ticket creation was denied writing the user's outside-workspace .jaira outbox. No ticket was created. Retry only through approved elevation, preserving the canonical board configuration.
- Jaira ref claim mismatch: ticket creation succeeded with --mine and reports assignee Codex, but pull refused because the ticket is not considered this ref's owner and suggested --steal. Did not use --steal; inspect ticket ownership/CLI contract before changing it.
- Jaira pull recurrence cause: the shell that created the ticket set JAIRA_USER=Codex, but the later independent PowerShell process did not inherit it. The refusal reported Codex as claimant; retry with the project-required identity set explicitly before considering steal. Do not take over another actor's ticket to compensate for a missing environment setting.
- JRNDC8 planning gate: moving todo directly to pre-process was refused because its planning option was unchecked. Record the authorized planning option through the CLI, then retry the move; never use --force.
- Skill lookup error: a tdd SKILL.md path was guessed under the unrelated work-pets plugin. The available-skill catalog identifies r9/.agents/skills/tdd/SKILL.md; use the declared root instead of deriving from a plugin name.
- TDD discovery pass: an unrestricted rg --files scan hit the known inaccessible tmp* directories and exited with access-denied errors. Context.md was available and read; avoid scanning those directories by constraining file discovery to src/tests and the known docs paths.
- JRNDC8 first red run: 4 service tests ran before implementation and all errored as expected for the missing flag/method; one test also called reset_user_password with the CLI signature instead of the service signature, causing an extra AttributeError. Correct the fixture call to (actor, user_id, password), then rerun to establish a clean expected-red receipt before implementation.
- Migration-test placement error: the new schema21 test class was inserted before the end of TaskLockMigrationTests, unintentionally inheriting its two v18 tests; focused run showed those errors plus the expected schema-version failure. Move the new class to module end before interpreting the result or changing migration code.
- A5 implementation correction: the board contains two same-title password-gate tickets; JRNDC8 is the active claimed in-progress ticket, while 01M4XH87 is an unclaimed backlog duplicate. Do not edit either ticket file directly or move/delete the duplicate outside the jaira CLI. A focused `python -m unittest tests.test_web...` invocation failed importing `link_roots` because this repository's runner adds `tests` to `sys.path`; use `tests/run.py` or set the test import path. Also, the first HTML patch used an absent closing-markup context and failed atomically; reread the actual file boundary and apply separate context-specific patches.
- A5 current verification: v21 migration plus four service tests pass in 1.675s. HTTP tests and full suite remain pending; no live database or user account was touched. `git pull --ff-only` was denied inside the sandbox, then approved escalation confirmed the branch already up to date at c13c7de.
- A5 first full suite completed: Ran891 in502.302s; FAILED (failures=71, errors=11, skipped=1). The confirmed common cause is legacy HTTP tests directly authenticating newly owner-created fixture users without the required password change, so later protected requests correctly get403. Update non-A5 HTTP test login helpers to complete first sign-in on disposable fixtures; keep dedicated A5 cases raw so they continue to prove gating. Preserve this failed full receipt; only a later full rerun can establish success.
- A5 rerun and UI verification: Updated only disposable test fixtures to clear the forced-change flag for tests exercising unrelated established-user features; dedicated A5 HTTP cases retain the real change-only state. Focused regression run passed30 tests in58.555s. Full suite then passed: Ran891 in698.337s, OK (skipped=1). `node --check` passed. Isolated Chrome on a temporary database exposed a script-order defect: the password dialog markup followed the app.js tag, so an early null event binding stopped the rest of app initialization. Moved the markup before the script; forced sign-in and self-service dialog then rendered, and the normal shell loaded for an established synthetic account. Correction: Chrome did not submit a password change; only service and HTTP tests verify the successful change transition. Main Astra DB and real accounts were not used. Independent review and owner acceptance remain pending.
- A5 handoff verification: A guard-removal check temporarily disabled the server-side password gate; the dedicated HTTP test then failed on its expected 403 (actual 200). Restored the guard and reran the test: 1 test in1.204s, OK. Two PowerShell/Python line-ending audit commands initially failed (one had a Python bracket SyntaxError, and the earlier count expression escaped newline bytes incorrectly). Replaced the count expression with explicit byte values, confirmed the A5 file set, normalized intended files to LF, and will check staged blobs before commit. One broad Astra search in the global mistakes log produced truncated output; the relevant Astra entries were already reviewed in this task. No source or user data lost.
- Staged-blob newline check command: a Python one-liner had a repeated unmatched-parenthesis SyntaxError, so staged blob line endings were not yet verified by that command. Correct the expression and rerun before commit; no staged content was changed by the failed check.
- Staged-blob newline verification: corrected the PowerShell quoting and list expression; every one of the 16 intended index blobs contains zero carriage-return bytes. `git diff --cached --check` passes after removing Markdown trailing spaces. The current local commit is ready for review; untracked duplicate/backlog ticket, private reference documents, and `.commandcode` remain excluded.
- Staging boundary: two ordinary `git add` attempts were denied creating `.git/index.lock` in the sandbox. The exact intended paths were staged successfully after approved elevation. No unrelated files were staged; do not repeat a sandbox retry for Git index writes when this path restriction recurs.
- Independent A5 review follow-up: Standards review found unqualified "owner-created" wording against CONTEXT.md; docs, migration comment and JRNDC8 frontmatter/checklist/outcome now say App Owner, using `jaira set`/`jaira dod`. The first CLI update command had a PowerShell ParserError because a single-quoted argument contained an apostrophe; retry with apostrophe-free wording succeeded. Spec review found no functional defect but confirmed the password-change transition was not submitted in Chrome; report that browser behavior as unverified and leave the ticket DoD open until separately verified or Aly accepts the limitation. Reviewer recheck is pending.
- Documentation patch correction: one apply_patch attempt used a README sentence that did not match the current line wrapping and failed atomically. Read the exact A5 paragraphs and applied the updated terminology/review status to the matching context; no partial edit occurred.
- Staged newline audit retry: deriving blob paths dynamically from `git diff --cached --name-only` returned exit 1 without output in PowerShell; cause was not established. A second read-only check used the six explicit staged paths and confirmed zero carriage-return bytes in each. No file content was affected.
- Final A5 verification on 2026-10-15: after the wording updates, the full suite completed with `Ran 891 tests in 659.923s; OK (skipped=1)`. `node --check src/astra/static/app.js` and `git diff --check` passed. Standards recheck found two remaining unqualified-owner references; `NEXT_STEPS.md` now says App Owner, while the older ticket progress note is explicitly identified as historical via the jaira CLI. Successful password change in Chrome remains unverified, so JRNDC8 stays in-progress. The test run used test fixtures and the earlier browser check used an isolated temporary database; no live accounts or primary Astra data were changed.
- Browser continuation corrections (2026-10-15): The first Windows skill lookup omitted the repository `.agents/skills` root; recovered from the declared skill catalog. Initial Chrome window lookup/activation calls used the wrong argument shape and a minimized tab, then succeeded after querying by integer window ID and activating with the returned window object. `Get-NetTCPConnection` returned Access denied for the test port; verified the isolated server through a local HTTP 200 instead. The first read-only audit query assumed `user_events.user_id`; actual schema is `target_user_id`, discovered via PRAGMA and queried correctly. A combined PowerShell/Python audit one-liner hit ParserError; replaced with a simpler isolated query. These were tooling/query errors, not app defects; no live data was accessed. The isolated Chrome checks then verified invalid forced/voluntary inputs, protected-route gating, successful forced and voluntary password changes, cleared flags, one secret-free audit event each, and continued active sessions. Full-suite rerun remains in progress; reviewer recheck pending.
- A5 handoff correction (2026-10-15): A documentation patch attempt used mismatched context and failed without changing files. The affected paragraphs were reread and corrected. The Jaira ticket is still in `in-progress`; the handoff had briefly stated that owner signoff was already pending before the lane was moved. Corrected README wording to report the actual lane. Follow-up full suite and browser verification completed successfully; reviewer findings are recorded in the ticket workflow. No source-code regression was introduced by the failed patch.
- A5 standards recheck (2026-10-15): The independent document recheck caught a stale sentence in the initial-smoke section that still called successful browser changes unverified, despite the later follow-up section recording both successful flows. Reworded it as the historical result of the initial smoke and pointed to the later verification. Appended the new browser evidence and clarified historical wording on JRNDC8 through the Jaira CLI, then moved it to the human-review lane. Prevention: scan the entire handoff for present-tense status claims after adding a newer dated verification section.
- Commit preparation (2026-10-15): Initial Git staging was denied when the sandbox could not create `.git/index.lock`; no staging occurred in that attempt. Retried via the repository's approved escalation path, staging only the five named handoff, ticket and log files. Leave the separate untracked user files untouched.
- Handoff status drift (2026-10-15): After Aly accepted A5 and JRNDC8 moved to Done, the current handoff index and NEXT_STEPS still said acceptance was pending. Corrected both from the live Jaira record. Prevention: after an owner acceptance, search current handoff pages for stale present-tense lane/approval claims and update them; keep dated review packages as historical snapshots. The same-title 0RHNMG backlog item remains unverified as a duplicate and is not closed.
- Jaira ownership (2026-10-15): I created B2A1AX with `--mine`, but this machine's configured Jaira identity is Aly, so the ticket landed assigned to her. Aly explicitly authorized transfer; Jaira then required the ticket to be pulled from its ref before assignment could be updated. Prevention: create agent-owned tickets with explicit `--assignee Codex`, pull ref-only tickets before writing, and verify assignee before progressing lanes. Resolved; ticket is assigned to Codex.
