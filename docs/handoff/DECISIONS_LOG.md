# Astra decisions log

Every decision by Aly Jafferani (App Owner and the only decider) that we could
find, oldest first, with where it is recorded and the rule that follows from
it. Part 2 lists default calls Claude recorded that Aly has not overruled.

Sources:

- "Slack ts" means a message in `#astra-builder` (channel `C0C43N1CE00`). Most
  are in thread `1790256175.671249`; earlier threads are `1790003172.924309`
  (2026-09-21 to 2026-09-23) and `1790160392.461299` (2026-09-23 to
  2026-09-24).
- "Ticket X" means a note by Aly on that jaira ticket in `.jaira/tickets/`.
- "Memory" means the channel memory notes. Those entries could not be checked
  against Slack in this handoff and are marked as such where the Slack message
  was not re-read.
- Times are UTC. Aly works in UTC+5.

---

## Part 1 — Aly's decisions

### 2026-09-15

| Decision | Source | Rule |
| --- | --- | --- |
| Shell design approved: left navigation, view tabs, docked side panel, detailed swimlane Gantt | Ticket X8FNA5 note, 2026-09-15 13:06 | Build toward the A-hybrid shell with a docked panel, not modals. Built as Gate 2 slices 1-7. |
| AI first-pass design settled (Assessor, Evidence, Proposal) | Ticket KK400X note, 2026-09-15 07:45; `docs/ai-first-pass-spec.md` | AI only proposes; nothing is created automatically. Gated on Aly turning a run on. |

### 2026-09-19 (ticket JQY55P notes)

| Decision | Source | Rule |
| --- | --- | --- |
| Internal dependency authority, option 3 | JQY55P, 15:18 | Managers change project-local dependencies only without protected impact; material changes need the Owner; removal needs a reason; viewers cannot change dependencies; cross-project dependencies are Owner-only. |
| File management is Owner-only | JQY55P, 15:19 | Only the App Owner adds, removes or organises files and links and marks final results; others only open what they may see. |
| Protected Kanban status authority, option 3; stop item-by-item questions; apply recommended defaults; adopt A-hybrid | JQY55P, 15:22 | Managers move work through Draft, Ready, In progress, Blocked, Submitted; only the Owner accepts, completes, closes, reopens or overrides; protected drops create requests. |

### 2026-09-20 (the accepted decision package)

| Decision | Source | Rule |
| --- | --- | --- |
| Deployment: Oracle Always Free VM, free DuckDNS name, Caddy HTTPS; no Tailscale for users; individual Astra accounts; no paid resource or silent upgrade | Ticket 6BXYJZ note, 03:11; `CODEX_HANDOFF_2026-09-20.md` section 1 | The pilot costs nothing and fails safe before a free allowance is exceeded. |
| Backup policy: nightly encrypted SQLite-consistent backup to OCI Object Storage plus an encrypted desktop copy; RPO 24 h; RTO 4 h; keep 7 daily, 4 weekly, 3 monthly; Owner controls restore credentials; prove both restore directions before go-live | Ticket TRPV3J note, 03:10 | See `DEPLOYMENT_RUNBOOK.md` stage 11. |
| Daily digest: in-app at 09:00 in the Owner's timezone, Owner only; no external email, extra recipients or escalation in the first release | Ticket F9HBSJ note, 03:10 | Notifications stay in-app. |
| External AI disabled for the first release; a future assessor must be zero-cost, swappable and preferably local | Ticket KK400X note, 03:10 | No private content goes to an external provider without separate authorisation. |
| The research-derived UX baseline is the production specification | Ticket Z9JCZ6 note, 03:10 | `docs/design/astra-product-ux-baseline.md` governs UX. |
| A-hybrid Command Center reconfirmed | Ticket JQY55P note, 03:10 | Command Center density, Focus Workspace typography, Executive Cockpit health strip. |
| Remaining recommended package accepted; hosting deferral replaced by the Oracle selection | Ticket MTEDTM note, 03:10 | `CODEX_HANDOFF_2026-09-20.md` is the cumulative decision record. |

### 2026-09-21

| Decision | Source | Rule |
| --- | --- | --- |
| Keep the GitHub repository public for now | Commit `027f9ac`; `pending-global-mistakes.md` ASTRA-20260921-03 | Never commit anything secret. Do not change visibility without a new instruction. |
| jaira board rules: never init, never regenerate lanes, never hand-edit tickets; CLI from `BeMuCa/jaira` v0.2.0 | Slack ts 1790004678.014639 (memory) | Section 4.3 of the master handoff. |
| HS3JRY accepted ("yes i approve it and you update the jaira as well"); PR #1 merged as `cd59438` | Slack ts 1790008823.829579 (memory); ticket HS3JRY note | HS3JRY stays in signoff until Aly moves it. |
| Gantt steps: steps are subtasks, collapsed inside the parent bar, Okabe-Ito colours, owner initials chip, click opens the step, a schedule-table twin | Offered 2026-09-21, no objection (memory) | Built as D73AQW. |
| Visual direction: "make the dashboard look and feel immaculate" using Claude design | Memory (thread 1790003172.924309) | Real design effort on every screen. |

### 2026-09-22

| Decision | Source | Rule |
| --- | --- | --- |
| Excel import: locked template, dd-mm-yyyy dates, Owner-only template settings, managers import into managed projects, only the Owner creates a project from a file, re-import by Import Key, no third-party libraries | Memory (thread 1790003172.924309) | `docs/design/excel-import.md`. |
| Simplify the template to nine columns; full set behind Owner settings | Memory | User-facing forms carry only what Astra needs. |
| An adversarial review is required before any PR is marked ready; merge order PR #3, #2, #4; agents mark ready, Aly merges | Memory | Section 4.4 and 4.5 of the master handoff. |

### 2026-09-23

| Decision | Source | Rule |
| --- | --- | --- |
| PR #3 and PR #2 merged (as `c5ac1c0` and `c841526`); PR #4 held for more work | Memory; `CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md` | Merge order: PR #4, then this branch. |
| Hosting on Oracle Cloud confirmed | Slack ts 1790163810.341529 (memory) | Standing requirement. |
| All fifteen remediation tickets accepted | Slack ts 1790190457.194569 (memory); commit `60ab463` | Moved to done in `1c45904`. |
| WNXSDA and 5GK6SB definition-of-done readings accepted | Memory | Settled; do not reopen. |

### 2026-09-24

| Decision | Source | Rule |
| --- | --- | --- |
| Six review-lane tickets may be reworked | Slack ts 1790228901.999149 (memory) | Done; in signoff. |
| ZSZ9T2: non-managers see only `project_schedule_changed` and `project_closed` in project history | Slack ts 1790241586.565819 (memory) | Later widened by K62ZAP. |
| Branch rule: only `codex/migration-safety-remediation`, pull first, push, report the SHA, no force-push | Slack ts 1790242085.686589 (memory) | Section 4.1. |
| Exclusive write lock protocol | Slack ts 1790242691.717659 (memory) | Retired on 2026-09-26 (see that date). |
| No redundant files or commits | Slack ts 1790243107.569629 (memory) | Keep commits scoped. |
| K62ZAP: Owner, Chairman and project managers see full history; others see ordinary kinds plus their own rows | Slack ts 1790245384.787859 and 1790245584.314119 (memory) | Built. |
| GTEYTG: Aly is the primary owner; only the primary grants or removes secondary owners; secondaries cannot act against the primary or each other; every change recorded | Slack ts 1790245584.314119; defaults ts 1790245630.918199 (memory) | Built. |
| Option list 1-8 for this thread | Slack ts 1790256238.445899 | Options 1-5 and 7 done; 6 and 8 open. |
| "yes update as per your recommendation": notify the acting owner of attachment and final-result events; reword 6G89SJ to the link model | Slack ts 1790268694.030539 | Built in KBWY86 and 6G89SJ. "Update as per your recommendation" means accept Claude's recommended defaults. |
| Server command `reset-password` works for any active user | Slack ts 1790272847.843239 ("any active user go with that.") | Built in PDDS2D. |
| No record or notice for reviewer, approver and collaborator changes; notify owners on project close and date changes; no template-deletion record; secondaries may keep editing Aly's tasks; settings history and project reopen go on a separate ticket | Slack ts 1790276936.363329 | Built XX9RFM; filed Z72D79. |
| Secondary owners have the same rights as the primary for project actions, including closing a project with open work; "project owners" (managers) are a different role | Slack ts 1790277044.283429 | Primary-only powers: owner-access management, the server commands and the primary's password. |
| Sign-in never locks anyone out or signs anyone out; just say the password is incorrect; owners reset forgotten passwords | Slack ts 1790279102.044719 | Built in 3M2AYA. |
| Secondary owners may reset anyone's password except the primary's | Slack ts 1790279285.796099 | Built. |
| Minimum password length is 8 | Slack ts 1790279350.477049 | `auth.MIN_PASSWORD_LENGTH = 8`. |
| No per-IP throttle inside Astra; hosted rate limiting belongs to 6BXYJZ | `CLAUDE_HANDOFF_2026-09-24.md` section 6 item 5 | Rate limiting, if any, is at the proxy (`OPEN_QUESTIONS.md` Q11). |
| Only project closes and date changes gain owner notices (option 4); no other guard for tasks of the primary | `CLAUDE_HANDOFF_2026-09-24.md` section 6 item 4 | As built. |

### 2026-09-25

| Decision | Source | Rule |
| --- | --- | --- |
| Option 6 (PR #4 extra work and merge) skipped for now, to come back later | Slack ts 1790303433.881399 | Still open. |
| Study monday.com, Trello and Asana; easier UI; Claude design for looks; three slices per lock; build the UI and the whole app first, then move to the server | Slack ts 1790310312.798809 | Phase order in `NEXT_STEPS.md`. |
| Use community feedback (Reddit); nothing over the top; it is a free app | Slack ts 1790310494.822249 | Keep-it-lean rules. |
| Build drag and drop, Undo, bulk select, WIP limits, swimlanes and the calendar month view; drop the workload view | Slack ts 1790312361.199859 and 1790312435.066959 | Workload (S1C6PN) is not built. |
| Lock #10 scope: Approve and Reject stay live on Home; swimlanes and calendar in; drag, Undo, bulk, WIP later | `CLAUDE_HANDOFF_2026-09-24.md` section 6 item 7 | As built. |
| "Checked lets proceed" is not the lock grant; the exact phrase is required | Memory (write-lock note) | Moot since the protocol was retired on 2026-09-26. |
| Managers may put tasks on hold directly, with a reason; leaving hold stays an Owner request | Slack ts 1790342529.695749 | Built in lock #12. |

### 2026-09-26

| Decision | Source | Rule |
| --- | --- | --- |
| Project managers and the Chairman can assign tasks and subtasks to others | Slack ts 1790386228.535829 | `can_assign` = owner, the project's manager, or the Chairman (assignee only). |
| No task is ever assigned to the Chairman; project viewers can be given subtasks | Slack ts 1790386492.402489 | Built in 3FQEKB. |
| Lock #13 granted | Slack ts 1790386688.768309 | Released at `0b90ceb`. |
| Prepare a detailed handoff for Codex covering development to deployment to distribution; commit everything and push the files | Slack ts 1790401671.573199 | This pack. |
| Lock #14 granted, and the exclusive write lock protocol retired ("remove this exclusive code granted guard rail as well a we are moving on") | Slack ts 1790403410.978849 | The exclusive write lock protocol was retired by Aly on 2026-09-26 (Slack ts 1790403410.978849). Lock #14 was the last. Pulling first, checking origin before a push (if it moved: pull, merge, re-run the tests, push normally), normal pushes only and reporting the final SHA and tests stay in force (`HANDOFF_2026-09-26.md` section 4.2). |

### Standing preferences (memory note `astra-aly-preferences`)

- Show a live baseline (git status, tests, board) before building, and wait for
  the go-ahead.
- "Design masterpiece" visuals.
- Give PowerShell steps one line at a time.
- Tickets assigned to Aly go to an agent only after asking each time.
- User-facing templates and forms carry only the fields Astra needs;
  comprehensive options go behind Owner settings (2026-09-22).
- "Astra" is also the name of Aly's ChatGPT assistant; "run this by Astra"
  means a handoff file in git, not the app.

---

## Part 2 — Claude's recorded default calls (not overruled by Aly)

These are choices Claude made and reported; Aly has not overruled them. They
are not Aly's decisions. Codex may keep them, or raise any of them with Aly.

### Lock #12 (from the lock #12 plan and writer report)

1. An ordinary board or Gantt move records a system reason
   ("Board move: In progress → Ready", "Gantt drag: …") and applies at once;
   moves that need a human reason (on hold, closed, reopen) ask for one.
2. Board targets reuse existing actions: Draft, Ready, In progress set the
   status; Blocked puts on hold; Submitted submits; Accepted accepts the pending
   submission; Closed cancels or abandons.
3. Undo applies only to ordinary moves (status among draft, assigned,
   in_progress; reorders; Gantt dates), 15 seconds plus 5 seconds of grace,
   refused if the task changed since.
4. Task locks are 60-second leases renewed every 20 seconds.
5. "Impact" for a Gantt move means a broken finish-to-start link either way, a
   task on the critical path, or a due date past the project target (there are
   no milestones); a link is broken only when the successor starts before the
   predecessor's due day. Downstream tasks are never moved.
6. Bulk status offers only Draft, Ready and In progress.
7. WIP limits count top-level open tasks; a card that enters Blocked because of
   a dependency is exempt.
8. An owner's board Undo passes the dependency override itself (12d I1).
9. The importer and templates bypass the WIP and dependency gates; both are
   owner-only (12d I2).
10. Approving an Owner request re-checks the dependency, WIP and date rules at
    decision time and asks the owner to confirm each override.
11. A manager's accept request on a waiting task is filed; the owner is asked at
    decision time.

### Lock #13 (ticket 3FQEKB notes)

1. Only a changed assignee meets the new rules in `update_task`, so a flagged
   task keeps its owner while other fields are edited.
2. Reviewers and approvers are not assignment: the Chairman and viewers stay in
   those lists (this is the open question Q1).
3. The on-hold responsible person is the assignee, so holding a flagged task
   needs a new responsible person.
4. Templates keep the "chairman" role name so old templates load; that role now
   creates the task unassigned; a viewer role fills subtasks only.
5. A bulk Undo that would restore the Chairman as owner is refused.
6. The Chairman selects tasks for bulk Assign in the List only, not on the
   Board.
7. A forbidden current owner stays selected and marked in the picker, so saving
   other fields never silently unassigns.

### Earlier

- Unrated criticality sorts below Low, with an amber badge (QY0WG2).
- "Today" is the server's date in `Asia/Karachi`, and each project's timezone is
  used for its tasks (lock #10).
- The Board maps 11 statuses into 7 columns (CR121Z).
- Sign-in history is kept 90 days and pruned at most hourly (3M2AYA).
- Blocked-attempt notices are capped at 5 per recipient and person in 10
  minutes, with owner-access attempts counted separately (KBWY86).
- Whether closed tasks may change by import, re-parenting, criticality or
  schedule edits was left to Claude's best-practice call (memory): they may not,
  until reopened (T8WHJR).
- An Owner may still leave on hold, changes requested or reopened through an
  ordinary edit with a reason, because no release action exists; managers
  cannot (open design question from the 2026-09-22 review, memory).
