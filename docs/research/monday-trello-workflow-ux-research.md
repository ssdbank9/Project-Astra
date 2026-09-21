# Monday.com and Trello workflow and UX research for Astra

**Initial research / source access:** 2026-09-19

**Independent verification refresh:** 2026-09-20

**Purpose:** Identify transferable workflow and interaction patterns for Astra from current first-party Monday.com and Trello documentation, informed—but not defined—by recent Reddit user feedback.

**Evidence rule:** Product capabilities are stated only from official first-party documentation. Reddit is treated as anecdotal experience evidence, not authoritative product documentation or proof of reliability, prevalence, or defects.

## Executive recommendation

Astra should remain an **A-hybrid command center**:

- Take Monday.com's strongest planning patterns: multiple views over one work model, portfolio dashboards, dependency-aware Gantt, workload visibility, and reusable templates.
- Take Trello's strongest interaction patterns: an immediately legible board, fast card manipulation, contextual card detail, lightweight personal capture, keyboard efficiency, and progressive disclosure.
- Do not reproduce either product's visual trade dress, terminology, unrestricted customization, or permission model.

The recommended experience has two deliberately different layers:

1. **Command Center** — a portfolio-level Home for exceptions, approvals, blocked work, deadlines, workload risk, and cross-project coordination.
2. **Focused project workspace** — List, Board, Timeline/Gantt, and Activity views operating on the same tasks, with a right-side task drawer for routine work and a full task page for deep review.

The authority model is not negotiable and must shape every interaction:

- **App Owner:** Aly Jafferani.
- **Owner only:** workflow and status configuration, cross-project actions and dependencies, all file management, template publishing, automation publishing, permission administration, and protected lifecycle actions.
- **Managers:** ordinary internal task operations and project-local dependency operations within granted scope.
- **Protected actions:** a Manager's attempt becomes a visible approval request; it never silently performs the protected change.
- **Audit:** every accepted, rejected, requested, blocked, automated, and overridden action is attributable and durable.

### Highest-value recommendations

1. **Keep the board simple by default.** Cards should show only title, accountable owner, due state, criticality, blocker/dependency state, and one or two optional project fields. Open the drawer for depth.
2. **Make drag-and-drop governed.** Managers may drag through ordinary working stages. Protected columns remain visible but visibly locked; dropping there opens an approval request with the intended transition and reason pre-filled. Viewers cannot drag.
3. **Treat Board, List, Timeline/Gantt, and Dashboard as views of the same record.** A task has one identity, one permission decision, and one event history across every view.
4. **Make automation inspectable.** Only the Owner may publish or enable an automation. Provide a draft/test/publish lifecycle, a plain-language rule summary, owner, scope, last run, next run, failures, action count, and one-click disable.
5. **Split the Inbox into “Needs action” and “Activity.”** Approval requests, review requests, assignments, dependency conflicts, and failed automations belong in Needs action. Ordinary updates belong in Activity. Read/dismiss is never approval.
6. **Make the Command Center exception-led.** Lead with overdue, blocked, awaiting Owner, workload risk, and recently changed—not decorative charts or total-card counts.
7. **Design mobile as a focused operational surface.** Prioritize triage, task read/update, comments, photos/files, approvals, and quick capture. Do not squeeze a desktop Gantt or dashboard onto a phone.
8. **Build low-bandwidth behavior explicitly.** Load a compact shell and text data first; lazy-load charts and history; make file upload resumable; show sync state; never present an optimistic protected change as completed before the server confirms it.

## Research method and evidence boundaries

### Official capability research

Official product support pages were reviewed for board/Kanban behavior, views, dependencies, automation, notifications/inbox, dashboards, workload, templates, mobile, permissions, keyboard/accessibility, and documented capacity or platform limits. Plan-gated capabilities are noted because Astra should borrow the interaction principle, not infer that every reference-product user receives the feature.

On 2026-09-20, the primary agent independently reopened a representative set of material official pages covering Kanban, Gantt/dependencies, dashboards, workload, automation health, Inbox/capture, permissions, mobile limitations, accessibility, keyboard operation, and documented scale. The refresh confirmed the comparison below and added Monday.com's current cross-account Autopilot hub. Time-sensitive reference-product details should be rechecked before implementation; Astra's recommendations do not depend on matching either product's plan packaging.

### Reddit feedback research

Reddit review was a purposive scan of recent discussions in `r/mondaydotcom`, `r/trello`, and `r/projectmanagement`, primarily from 2025-2026. Threads were selected because they discussed actual use, recent UI changes, automation, scale, notifications, mobile work, or performance. Self-promotion, speculation, and support anecdotes were not treated as verified product facts.

Signal labels used below:

- **Recurring theme:** substantially similar feedback appeared across at least three distinct threads or discussions.
- **Repeated theme:** appeared in two distinct discussions.
- **Minority / single-thread opinion:** useful design input, but not evidence of prevalence.
- **Inference for Astra:** a design conclusion drawn from official capabilities plus the user-feedback signal; it is not a claim about either product.

This is not a representative survey. Reddit contributors self-select, dissatisfied users may be overrepresented, votes are not a reliable population measure, and some replies come from vendors, partners, or people with undisclosed interests.

Representative Reddit threads were reopened on 2026-09-20 where the site allowed access. Several pages were intermittently unavailable to the browsing tool, so no inaccessible thread is the sole support for a recurring theme. The themes below are design hypotheses to test with Astra users, not prevalence estimates.

## Official feature comparison

| Area | Monday.com: documented capability | Trello: documented capability | Transferable lesson for Astra |
| --- | --- | --- | --- |
| Board / Kanban | Kanban is a board view driven by a status column. Users can create and edit cards in the view, drag cards within or across columns, and configure per-column WIP limits. ([Kanban View](https://support.monday.com/hc/en-us/articles/360000661379-The-Kanban-View)) | Boards contain lists and cards; lists can be rearranged and cards moved between lists. ([Create a board](https://support.atlassian.com/trello/docs/creating-a-new-board/)) | Use Trello-level immediate legibility with Monday-style field-backed status and optional WIP signals. Columns represent configured states, not separate records. |
| List / table | The main table is the underlying work surface; board views provide alternative visualizations. Monday documents many view types. ([Board views](https://support.monday.com/hc/en-us/articles/360001267945-The-board-views)) | Premium/Enterprise Table view supports list-style display, inline changes to selected fields, filtering, and drag reorder when no filter/sort is applied. ([Table view](https://support.atlassian.com/trello/docs/single-board-table-view/)) | Provide a dense List for operational work and a Board for flow. Disable ambiguous reordering while sorted/filtered, or make the effect explicit. |
| Timeline / Gantt | Gantt shows dated items and dependency arrows; moving a task can shift dependents. Gantt is Standard+, while milestones/critical path are Pro/Enterprise. ([Gantt View](https://support.monday.com/hc/en-us/articles/360015643840-The-Gantt-Chart-View-and-Widget)) | Timeline maps dated cards, supports grouping and an unscheduled-card area; current documentation says it is Premium/Enterprise and not available on mobile. ([Timeline view](https://support.atlassian.com/trello/docs/timeline-view)) | Use Monday's dependency reasoning and Trello's unscheduled tray. Provide a non-graphical schedule table as the accessible/mobile fallback. |
| Dependencies | Pro/Enterprise dependency columns support flexible, strict, or no-action date behavior. Monday also documents dependency types and Enterprise cross-project dependencies. ([Dependencies](https://support.monday.com/hc/en-us/articles/360007402599-Dependencies-on-monday-com), [Cross-project dependencies](https://support.monday.com/hc/en-us/articles/24601183683474-Cross-Project-Dependencies)) | Atlassian states that Trello has no built-in task-dependency management and documents linked cards, checklists, and Automation as workarounds. ([Task dependencies](https://support.atlassian.com/trello/docs/creating-and-managing-task-dependencies/)) | Retain Astra's operational project-local dependencies for Managers. Keep cross-project dependencies Owner-only. Default date propagation to proposal/preview rather than silent rescheduling. |
| Drag-and-drop | Board and Gantt interactions directly update the underlying board. ([Kanban View](https://support.monday.com/hc/en-us/articles/360000661379-The-Kanban-View), [Gantt View](https://support.monday.com/hc/en-us/articles/360015643840-The-Gantt-Chart-View-and-Widget)) | Drag is a core board interaction; Table view also supports drag under defined conditions. Trello documents a browser setting that can break drag-and-drop. ([Table view](https://support.atlassian.com/trello/docs/single-board-table-view/), [Supported platforms](https://support.atlassian.com/trello/docs/what-browsers-and-mobile-platforms-does-trello-support/)) | Drag must have a Move menu, keyboard action, and touch alternative. Always show the destination and resulting status before committing a protected or dependency-affecting change. |
| Automation | Trigger-condition-action recipes can update items, notify people, change statuses, and move items across boards. Monday documents plan-based quotas and rate/complexity limits. Its Autopilot hub provides cross-account health, usage, workflows and connections, including owner, last failure, board, root-cause classification and drill-through. ([Monday automations](https://support.monday.com/hc/en-us/articles/360001222900-Get-started-with-monday-automations), [Autopilot hub](https://support.monday.com/hc/en-us/articles/28738092924562-The-Autopilot-hub), [Pricing and quotas](https://support.monday.com/hc/en-us/articles/360002826680-Automations-and-integrations-pricing), [Rate limits](https://support.monday.com/hc/en-us/articles/9060097050258-Automation-and-integration-rate-limits)) | Automation supports rules, card buttons, board buttons, schedules, and due-date triggers; monthly runs and operation limits vary by plan. Trello also documents per-run logs, warnings, errors and change history. ([Trello automation](https://support.atlassian.com/trello/docs/automation-overview/), [Trello logs](https://support.atlassian.com/trello/docs/opening-the-command-log/), [Trello quotas](https://support.atlassian.com/trello/docs/butler-quotas-and-limits/)) | Adopt plain-language trigger/condition/action rules, action buttons, centralized health and useful run diagnostics. Add Astra-specific governance: Owner-only publish/enable, draft/test lifecycle, protected-action approval, explicit scope, and a kill switch. |
| Inbox / notifications | Monday separates broadly subscribed Update Feed content from specifically relevant bell notifications; My Work consolidates assigned tasks. ([Update Feed](https://support.monday.com/hc/en-us/articles/115005309885-The-Update-Feed-Inbox), [Notifications](https://support.monday.com/hc/en-us/articles/360001292545-Notifications-explained), [My Work](https://support.monday.com/hc/en-us/articles/360019300579-My-Work)) | Trello has a notification drawer and watch behavior. Its newer personal Inbox is a private capture area from which cards can be dragged to a board; Planner places calendar and board work side-by-side. ([Notifications](https://support.atlassian.com/trello/docs/receiving-trello-notifications/), [Trello Inbox](https://support.atlassian.com/trello/docs/trello-inbox/), [Planner](https://support.atlassian.com/trello/docs/trello-planner/)) | Combine three concepts without conflating them: assigned My Work, actionable governance Inbox, and private quick capture. Do not use one stream for all three. |
| Dashboards / command center | Dashboards aggregate multiple boards through widgets, with permission-aware source data and documented board/item/widget limits. ([Dashboards](https://support.monday.com/hc/en-us/articles/360002187819-The-Dashboards)) | Dashboard view charts single-board counts by list, due date, member, or label; the documented view has limited drill-through and no export. Workspace Table/Calendar views combine cards from multiple boards on Premium/Enterprise. ([Dashboard view](https://support.atlassian.com/trello/docs/dashboard-view), [Workspace views](https://support.atlassian.com/trello/docs/workspace-views/)) | Use Monday's cross-project aggregation but keep the visual vocabulary small. Every metric must drill to the exact permission-filtered tasks that produce it. |
| Workload | Workload uses assignee, dates, work schedules, and optional effort; dashboard placement can aggregate multiple boards. ([Workload Widget](https://support.monday.com/hc/en-us/articles/360010699760-The-Workload-Widget)) | Dashboard provides cards-per-member, but the reviewed official sources do not describe a comparable capacity-versus-effort model. ([Dashboard view](https://support.atlassian.com/trello/docs/dashboard-view)) | Implement explicit capacity and effort, not card count alone. Label missing effort as unknown and never imply precision the data does not support. |
| Templates / onboarding | The Template Center can create boards or multi-component workflows with views and automations; copied integrations may be disabled and plan limits apply. ([Monday templates](https://support.monday.com/hc/en-us/articles/360001362625-monday-com-templates)) | Board templates reproduce a workflow structure; card templates support repeated card content, with some mobile creation/editing limitations. ([Board templates](https://support.atlassian.com/trello/docs/creating-template-boards/), [Card templates](https://support.atlassian.com/trello/docs/creating-template-cards/)) | Provide Owner-published, versioned project and task templates with a preview. Never copy members, credentials, external links, automation owners, or live dates without explicit review. |
| First-use onboarding | Monday's existing-account guide introduces workspaces, boards, notifications, My Work, dashboards, templates, and automations as a progressive learning path. ([Existing-account onboarding](https://support.monday.com/hc/en-us/articles/360000613179-Get-started-in-an-existing-account)) | Trello's quick start begins with three simple lists—Today, This Week, Later—and has users add and move cards before introducing more depth. ([Trello quick start](https://support.atlassian.com/trello/docs/getting-started-with-trello-video-demo/)) | Copy Trello's first-five-minutes simplicity, then reveal Monday-style planning depth by role and need. |
| Mobile / touch | Mobile supports selected views including table, calendar, timeline, form, and Kanban; Gantt, Workload, and Chart are documented as unavailable, and dashboard views are read-only. ([Mobile board views](https://support.monday.com/hc/en-us/articles/360015740220-Mobile-app-board-views)) | Inbox is available across devices, while current Timeline documentation says Timeline is no longer available on mobile. Template creation/editing is partly web-only. ([Trello Inbox](https://support.atlassian.com/trello/docs/trello-inbox/), [Timeline view](https://support.atlassian.com/trello/docs/timeline-view), [Templates](https://support.atlassian.com/trello/docs/creating-template-boards/)) | Define a mobile task subset instead of promising desktop parity. Keep advanced configuration, Gantt editing, and dashboard construction desktop-first. |
| Permissions | Board types gate reach; board, column, workspace, and account permissions add controls, some Enterprise-only. Owners bypass board restrictions. ([Monday permissions](https://support.monday.com/hc/en-us/articles/360019222479-Permissions-on-monday-com)) | Board admins, normal members, observers, guests, and Workspace roles have different capabilities; normal board members generally edit without restriction, while observers are Premium. ([Board permissions](https://support.atlassian.com/trello/docs/changing-permissions-on-a-board/), [Workspace admin](https://support.atlassian.com/trello/docs/workspace-admin-capabilities/)) | Do not copy broad “normal member” editing or product-plan role semantics. Astra needs action-level server authorization matching its approved Owner/Manager/Viewer model. |
| Keyboard / accessibility | Monday documents shortcuts and ongoing WCAG 2.1 AA work; its screen-reader guide acknowledges partial keyboard parity and large-board virtualization limitations. ([Shortcuts](https://support.monday.com/hc/en-us/articles/115005339905-monday-com-Shortcuts), [Accessibility](https://support.monday.com/hc/en-us/articles/360000571925-Accessibility-on-monday-com), [Screen readers](https://support.monday.com/hc/en-us/articles/33660661840530-Using-monday-com-boards-with-screen-readers)) | Trello documents navigation/action shortcuts, undo/redo, and an option to disable shortcuts for accessibility. Atlassian targets WCAG 2.1 AA in its internal standards. ([Keyboard shortcuts](https://support.atlassian.com/trello/docs/keyboard-shortcuts-in-trello/), [Atlassian accessibility](https://www.atlassian.com/trust/compliance/resources/wcag)) | Make every pointer action available by keyboard; let users disable single-key shortcuts; preserve focus after moves; offer list/table alternatives to spatial views. |
| Documented scale / complexity | Monday documents board item limits, dashboard limits, linkage limits, and automation complexity/rate controls. ([Item limits](https://support.monday.com/hc/en-us/articles/4404058746642-Item-and-subitem-limits-per-board), [Dashboards](https://support.monday.com/hc/en-us/articles/360002187819-The-Dashboards), [Rate limits](https://support.monday.com/hc/en-us/articles/9060097050258-Automation-and-integration-rate-limits)) | Trello recommends keeping open cards below 1,000 per board—or below 500 when cards are attachment/checklist-heavy—and documents a 5,000-card hard maximum. ([Slow boards](https://support.atlassian.com/trello/docs/troubleshooting-a-slow-board/), [Adding cards](https://support.atlassian.com/trello/docs/adding-cards/)) | Show size/complexity health before degradation, encourage archive/split actions, and keep portfolio aggregation separate from loading every record into one board. |

## Reddit user-feedback themes

### Recurring themes

#### 1. Simplicity and visible work remain Trello's main attraction

Recent users continued to describe Trello as simple, flexible, and useful across personal and work contexts, even while criticizing its redesign. A 2026 satisfaction thread contains both long-term loyalty and UI complaints; another discussion describes Trello as beautiful and simple; project-management discussions commonly position it as easy to understand for smaller teams. ([Trello satisfaction thread](https://www.reddit.com/r/trello/comments/1udabns/how_satisfied_are_you_with_trello_in_2026_and_why/), [Shareable alternatives thread](https://www.reddit.com/r/trello/comments/1p98cg1/free_shareable_alternatives_to_trello/), [Kanban tools discussion](https://www.reddit.com/r/projectmanagement/comments/1cqv0dy/best_kanban_tools_for_switching_from_scrum/))

**Inference for Astra:** The Board should explain itself in seconds. Advanced planning must not cover the basic “what is where?” workflow with controls, badges, or charts.

#### 2. Feature and configuration growth can produce clutter and governance drift

Monday.com discussions repeatedly mention boards becoming harder to control as teams, automations, and access relationships grow. Users described uncertain automation behavior, access ambiguity, notification noise, inconsistent status vocabularies, and dashboards losing meaning when boards drift. ([Workspace scale thread](https://www.reddit.com/r/mondaydotcom/comments/1qade56/anyone_else_feeling_like_mondaycom_gets_messy/), [Automation health thread](https://www.reddit.com/r/mondaydotcom/comments/1ugzcyj/anyone_else_flying_blind_on_automation_health/), [Workspace audit themes](https://www.reddit.com/r/mondaydotcom/comments/1sjlic7/ive_audited_a_lot_of_mondaycom_workspaces_the/))

**Inference for Astra:** Owner-only workflow configuration is a product advantage, not a constraint to hide. Use a controlled status vocabulary, template versions, automation registry, and schema validation before data reaches dashboards.

#### 3. Recent UI changes and promoted features can displace core work

Across both product communities, some users objected to new controls, persistent bars, AI promotion, or changed layout consuming space or disrupting established workflows. The consistent issue was not opposition to every new feature; it was loss of control over the primary workspace. ([Trello UI thread](https://www.reddit.com/r/trello/comments/1mtl2sf/do_trellos_developers_even_use_it/), [Trello 2026 UI thread](https://www.reddit.com/r/trello/comments/1w910sk/trello_broke_their_ui_because_they_want_to_push/), [Monday mobile/AI thread](https://www.reddit.com/r/mondaydotcom/comments/1rjuyf7/why_does_monday_focus_on_ai_junk_instead_of/), [Monday AI-emphasis thread](https://www.reddit.com/r/mondaydotcom/comments/1v4i38c/mondaycom_has_changed_with_too_much_aiemphasis/))

**Inference for Astra:** New capabilities should be opt-in or contextual. Do not place AI, setup prompts, or secondary tools permanently in the card's scarce above-the-fold area.

#### 4. Mobile is often used for a narrower task set than desktop

Monday users described quick status checks, dashboards, updates, and field work as key mobile jobs, while asking for mobile-specific layouts and reliable file upload in weak connectivity. Trello users asked for faster priority access, cross-board views, search, calendar/workspace views, and better use of limited vertical space. ([Monday mobile feedback](https://www.reddit.com/r/mondaydotcom/comments/1rx2ugw/mondays_mobile_app_is_getting_better_and_we_want/), [Monday field-upload complaint](https://www.reddit.com/r/mondaydotcom/comments/1rjuyf7/why_does_monday_focus_on_ai_junk_instead_of/), [Trello mobile feedback](https://www.reddit.com/r/trello/comments/1hsocdg/trello_mobile_users_what_frustrates_you_most_about/))

**Inference for Astra:** Mobile should expose only the information and actions needed on the move. Background/resumable upload and an explicit pending-sync state matter more than mobile dashboard construction.

### Repeated themes

#### 5. Automation power is undermined when rules are opaque, brittle, or hard to trace

Monday threads cite missing context in notification actions, regressions in linked messages, field-type limitations, and uncertainty about whether distributed rules are working. A Trello thread reports delayed automation execution during an acknowledged incident; another 2026 satisfaction thread calls the automation UI weak. These are anecdotes, not verified present-tense capability limits. ([Monday multi-level automation](https://www.reddit.com/r/mondaydotcom/comments/1tjlj7i/automations_on_multilevel_board_are_broken/), [Monday automation UI change](https://www.reddit.com/r/mondaydotcom/comments/1rs12re/new_automation_system_way_worse/), [Monday column restrictions](https://www.reddit.com/r/mondaydotcom/comments/1vb0y1f/is_anyone_else_struggling_with_mondays_automation/), [Trello automation delay](https://www.reddit.com/r/trello/comments/1j3znb1/automation_completely_not_working/))

**Inference for Astra:** A rule builder alone is insufficient. Every run must say what fired, what it examined, what it changed or skipped, and why. Protected actions must stop at an approval request.

#### 6. Large or busy workspaces can feel slow or clunky

Users in both communities reported slow-loading boards, sluggish interactions, or temporary availability problems. Individual outage reports do not establish normal product performance, and some commenters reported no issue. ([Monday review thread](https://www.reddit.com/r/mondaydotcom/comments/1h6vg1a/what_do_you_think_of_mondaycom_would_love_to_hear/), [Trello large-list thread](https://www.reddit.com/r/trello/comments/1vvvnz4/is_anyone_else_having_trouble_with_trello/), [Trello performance thread](https://www.reddit.com/r/trello/comments/1r90vuc/trello_down/))

**Inference for Astra:** Set performance budgets, paginate or virtualize deliberately, keep the initial payload small, provide a low-data mode, and show service/sync health inside the product rather than leaving users to guess.

### Minority or single-thread opinions worth testing

- A new Trello user wanted card layout customization because static metadata consumed attention before attachments, links, checklists, and comments. ([New-user feedback](https://www.reddit.com/r/trello/comments/1i7rmn2/new_trello_user_feedback_questions/))
- One Trello discussion argued that planning and completion controls should be hideable because they diluted a pure visual-board workflow; another reply argued that Automation and Power-Ups are what make Trello flexible. ([“First do no harm” discussion](https://www.reddit.com/r/trello/comments/1ixwvry/new_trello_features_first_do_no_harm/))
- A Monday discussion described the platform as approachable and visual across disciplines, though some replies were openly biased or promotional. ([Monday Dev discussion](https://www.reddit.com/r/mondaydotcom/comments/1mjwcer/monday_dev_vs_jira_which_would_you_bet_on_for_2025/))

**Inference for Astra:** Offer compact and comfortable density, allow users to collapse secondary card metadata, and test task-drawer ordering with real owner/manager/viewer workflows. Do not infer broad user preference from these isolated comments.

## Patterns to adopt, adapt, and avoid

### Adopt

- **One record, many views:** List, Board, Timeline/Gantt, My Work, and Dashboard all read the same task and event model.
- **Visual board clarity:** A small number of stable columns, compact cards, obvious drag affordance, and card detail on demand.
- **Unscheduled work tray:** Timeline/Gantt should keep undated work visible rather than dropping it silently.
- **Dependency visualization:** Show links, conflicts, blockers, and the downstream effect of proposed date changes.
- **Private capture:** A personal Inbox for rough tasks that are not yet project records, with an explicit move/convert step.
- **Keyboard efficiency:** Quick switcher, board filter, create, move, undo where safe, and a visible shortcut reference.
- **Curated templates:** Owner-published templates for recurring project and task structures.
- **Cross-project exception dashboard:** Aggregate by governance-relevant risk, not by decorative volume.

### Adapt to Astra's governance

- **Drag-and-drop:** Ordinary Manager moves execute; protected drops create requests; Viewer drag is disabled. Every result is server-authoritative and audited.
- **Dependencies:** Managers manage project-local links. The Owner alone creates, changes, or removes cross-project links. A date cascade is previewed and approved before changing committed schedules.
- **Automation:** Managers may suggest or draft an automation, but only Aly Jafferani publishes/enables it. Automation can never grant permissions, manage files, perform a protected lifecycle transition, or mutate another project directly. Where policy permits, it may stop and create an Owner request; it cannot approve or execute that request itself.
- **Dashboards:** Users see only source records they may access. The Owner controls metric definitions and published layouts. Every chart supports drill-through to its contributing records.
- **Templates:** Templates encode approved structures but are inert until instantiated. Creation shows a diff-like preview of statuses, fields, automations, dates, and access effects.
- **Inbox:** Governance actions are durable. “Read,” “dismiss,” “archive,” “acknowledge,” “approve,” and “reject” are separate actions.
- **Files:** All add/remove/replace/publish/permanent-link actions remain Owner-only even inside otherwise Manager-editable tasks. A Manager sees a request-file-action path, not an enabled file mutation disguised as ordinary editing.

### Avoid

- Unlimited user-created statuses, fields, views, widgets, and automations.
- A universal status dropdown that bypasses named lifecycle actions and approval rules.
- Card fronts overloaded with every available field.
- Silent date cascades or dependency changes after a drag.
- Notification streams where routine activity obscures approval requests or failures.
- Automations without owner, scope, last-run state, version history, failure visibility, and disable control.
- Dashboards built from inconsistent status labels or incomparable fields.
- “AI” controls permanently occupying primary work space; suggestions must remain optional, reviewable, and never self-authorizing.
- Desktop layouts merely shrunk for mobile.
- Hidden optimistic changes that appear saved while offline, unauthorized, rejected, or awaiting approval.
- Relying on color alone for status, criticality, due state, permissions, or dependency conflict.

## Concrete Astra UI and workflow changes

### 1. Command Center home

Use a fixed, Owner-curated layout rather than a freeform widget canvas initially.

**Top strip:**

- Awaiting my action
- Overdue
- Blocked by dependency
- Critical and due soon
- Automation/file/sync failures

**Primary panels:**

- **Needs Owner decision:** protected transition requests, cross-project dependency requests, file requests, template/automation publication requests.
- **At-risk work:** overdue, blocked, no owner, no approved due date, missing evidence, or conflicting schedule.
- **Portfolio timeline:** milestone and project-level bars; expand on demand rather than rendering every task initially.
- **Workload:** people against explicit available capacity and declared effort, with “effort unknown” visible.
- **Recent material change:** accepted/rejected work, schedule revisions, dependency changes, file publication, and automation failures.

Every count or chart segment opens a filtered task list. The active filter is displayed in plain language and can be cleared in one action.

### 2. Project workspace

Use persistent tabs: **List · Board · Timeline · Activity**. Preserve filters and scroll position when switching views.

The project header shows:

- project name and health;
- current user's role and access scope;
- next milestone and schedule state;
- active filters;
- a single primary Create task action when permitted;
- Owner-only Configure and Files actions.

Avoid placing template, automation, AI, export, and settings as equal-weight permanent buttons. Put secondary tools behind one clearly labelled menu.

### 3. Governed Board and drag-and-drop

Board card default content:

- title;
- accountable owner;
- due/overdue label;
- criticality;
- blocked/predecessor badge;
- approval-request badge when relevant.

Interaction rules:

1. On pointer down or keyboard Move, identify legal destinations from the server-returned transition policy.
2. Highlight ordinary destinations normally, protected destinations with a lock/approval badge, and invalid destinations as unavailable.
3. For an ordinary Manager move, show the status name and require a reason only where policy requires it.
4. For a protected destination, open **Request Owner approval** with from/to, reason, dependency/file implications, and optional evidence.
5. Keep the card in its original column with a visible pending-request badge until approved. Do not “temporarily” place it in the protected column.
6. Announce success/failure to screen readers, restore focus to the moved card, and provide Undo only when reversal is itself authorized and auditable.

Column headers should show item count, WIP signal where configured, and collapse control. Only the Owner can reorder, add, rename, map, or delete status columns.

### 4. Task drawer and full task page

The drawer handles routine work without losing board context. Put these above the fold:

- title and stable ID;
- current status and permitted next actions;
- owner, due state, criticality, and blocker state;
- permission badge and pending approvals.

Use sections for Overview, Schedule & dependencies, Checklist/subtasks, Discussion, Evidence, Files, Approval, and History. Files are visible according to access but all file-management controls remain Owner-only. The full page is the deep-link target for audit review and long histories.

### 5. Timeline/Gantt and dependency workflow

- Render project-local finish-to-start links already supported by Astra.
- Add an unscheduled tray for missing dates.
- Distinguish baseline, approved current schedule, and pending proposed change.
- When moving a task with successors, show a preview: affected tasks, old/new dates, conflicts, and approval requirement.
- Provide **Propose dates** and **Apply approved change** as separate actions.
- Give every chart a synchronized table/list alternative.
- Cross-project dependency creation, removal, or date propagation is Owner-only and recorded in both affected project histories.

### 6. Automation Center

Automation should be a governed subsystem, not a collection of hidden board recipes.

Each automation record needs:

- name and plain-language summary;
- Owner, scope, trigger, conditions, actions, and protected-action behavior;
- status: draft, test, awaiting Owner, active, paused, failed, retired;
- version and change history;
- last/next run, recent success/failure counts, and action volume;
- run log with matched record, skipped condition, resulting change/request, and error;
- test against sample/current data without committing changes;
- Owner-only publish, enable, pause, retire, and ownership transfer.

An automation that reaches a protected action creates an Owner approval request. It must never approve its own request.

### 7. Inbox, My Work, and quick capture

Keep three distinct destinations:

- **My Work:** assigned tasks across accessible projects, grouped by overdue/today/next/unscheduled or by project.
- **Inbox — Needs action:** approval requests, assignments requiring acknowledgement, review requests, dependency conflicts, failed automations, and file-action requests.
- **Inbox — Activity:** mentions, comments, schedule/status changes, and audit events the user follows.

Optional **Private capture** creates a personal draft, not a project task. Conversion requires selecting a project and applying project policy. Managers cannot use capture-to-board to bypass task-creation rules; cross-project placement still requires Owner authority where applicable.

### 8. Workload

The first version should be a capacity table/heatmap, not an elaborate resource optimizer:

- person/team;
- available capacity for the period;
- committed effort;
- unestimated task count;
- overdue/blocked load;
- expandable contributing tasks.

Do not calculate capacity from card count alone. Do not automatically reassign work. A Manager can propose project-local reassignment within scope; the Owner controls cross-project balancing and any permission implications.

### 9. Templates and onboarding

Provide three Owner-published starter templates: simple project, dependency-led project, and approval-heavy project. Each template preview states statuses, fields, required roles, approval gates, automations, and default views.

Role-based onboarding should be brief and contextual:

- **Owner:** configure roles/statuses, review governance queue, publish template/automation, manage files, inspect audit.
- **Manager:** create/update project-local tasks, move ordinary stages, manage project-local dependencies, request protected actions.
- **Viewer/member:** find assigned work, comment or update only permitted fields, and understand locked controls.

Use sample data and a reversible guided tour. Do not present every feature on first login.

## Low-bandwidth, mobile, and accessibility requirements

### Low bandwidth and resilience

- Ship the navigation shell, counts, and text list before charts, avatars, thumbnails, histories, or dependency lines.
- Lazy-load inactive views and task sections; paginate event history and comments.
- Offer a **Low data mode** that defaults to List, suppresses decorative images, defers charts, and uses manual thumbnail loading.
- Use compact JSON responses, conditional requests/ETags, cached reference data, and incremental refresh rather than full-board reloads.
- Show `Saved`, `Saving`, `Queued`, `Awaiting approval`, `Failed`, and `Offline` as distinct states.
- Queue only safe drafts/ordinary edits offline. Protected transitions, permission changes, file management, cross-project actions, and automation publication require an online server decision.
- Make file upload resumable/chunked where feasible; preserve the entered note and metadata if upload fails; provide explicit retry/cancel. Do not require an unlocked foreground screen for the whole upload.
- Load aggregate Command Center counts first, then drill-down data. Provide “last updated” and refresh state.
- Establish performance budgets and test with large boards, long histories, constrained CPU, high latency, intermittent connectivity, and packet loss.

Trello officially states that its desktop apps require an active connection and do not provide offline sync. Astra should therefore treat offline support as its own explicit design decision and never imply that adopting a Trello-like interaction supplies offline reliability. ([Trello desktop apps](https://support.atlassian.com/trello/docs/trello-desktop-apps/))

### Mobile and touch

- Use a bottom or compact navigation path for Home, My Work, Inbox, Projects, and Search.
- Default project view to a compact task list or one-column-at-a-time board; provide a list picker rather than requiring long horizontal swipes.
- Use minimum 44-by-44 CSS-pixel touch targets, generous drag handles, and a tap-based Move action.
- Put approve/reject behind an explicit review screen with reason and impact; never place protected approval on a swipe gesture.
- Allow camera/file capture with background/resumable upload and visible pending state.
- Keep Gantt read-only or summary-first on small screens; route complex schedule edits to a task/date form with dependency impact preview.

### Accessibility

- Target WCAG 2.2 AA for Astra even though the reviewed products describe WCAG 2.1 AA programs.
- Use semantic headings, lists/tables, buttons, dialogs, and status text; do not recreate the board as unlabeled draggable `div` elements.
- Provide keyboard create/open/move/filter/search actions and allow users to disable single-key shortcuts.
- Support Move through a menu/dialog with the same destinations and permission explanations as drag-and-drop.
- Maintain a logical focus order; after move, return focus to the card in its new position or to the original card when a request is pending.
- Announce saved, rejected, invalid, and approval-request outcomes through an ARIA live region without stealing focus.
- Pair every color with icon/text; meet contrast; support zoom/reflow, reduced motion, dark/high-contrast modes, and comfortable/compact density.
- Provide a structured schedule table for every Gantt and exact contributing-record lists for every chart.
- Test with keyboard only, NVDA on Windows, VoiceOver on iOS/macOS where applicable, touch, 200%-400% zoom, and high-contrast settings.

## Recommended implementation sequence

1. **Governed Board foundation:** shared task model, compact card, drawer, legal destination policy, protected-drop request behavior, keyboard/touch Move, audit events.
2. **Needs-action Inbox:** approval queue plus Activity separation; unread/dismiss distinct from approve/reject.
3. **Timeline/Gantt hardening:** unscheduled tray, dependency rendering, schedule proposal preview, table alternative, Owner-only cross-project actions.
4. **Command Center:** exception cards and drill-through lists first; workload and portfolio timeline after metric definitions are stable.
5. **Automation Center:** registry and run log before a broad rule builder; then draft/test/publish.
6. **Templates and role onboarding:** only after the underlying policies and view behaviors are stable enough to encode safely.
7. **Mobile/low-data refinement:** implement alongside every stage, with constrained-network and assistive-technology acceptance tests—not as a final responsive-CSS pass.

## Acceptance checks for the research-derived direction

- A first-time Manager can identify current stage, owner, due risk, blocker, and permitted next move from a board card without training.
- A Manager's drop into a protected stage creates exactly one approval request, leaves the task's accepted status unchanged, and records the attempt.
- Aly Jafferani can approve/reject from Needs action and see actor, reason, before/after, and related evidence.
- A Viewer cannot mutate a card through drag, menu, keyboard, touch, API, automation, or offline replay.
- Every Board/List/Timeline/Dashboard representation opens the same task ID and applies the same authorization decision.
- Every dashboard metric drills into its permission-filtered contributing records and exposes its definition.
- An automation can be tested without mutation; a published run is attributable, explainable, disableable, and unable to self-approve protected work.
- Low-data mode makes the core task list usable without loading charts, images, or full history.
- Every drag operation has a keyboard and touch alternative; every Gantt has a structured table alternative.
- File controls remain Owner-only in every view and cannot be reached indirectly through template, automation, bulk action, or mobile UI.

## Sources

Sources were initially accessed 2026-09-19; a representative material set was independently refreshed 2026-09-20. Official sources establish product capabilities; Reddit sources supply anecdotal UX signals only.

### Official Monday.com sources

- [The Kanban View](https://support.monday.com/hc/en-us/articles/360000661379-The-Kanban-View)
- [The board views](https://support.monday.com/hc/en-us/articles/360001267945-The-board-views)
- [The Gantt Chart View and Widget](https://support.monday.com/hc/en-us/articles/360015643840-The-Gantt-Chart-View-and-Widget)
- [Dependencies on monday.com](https://support.monday.com/hc/en-us/articles/360007402599-Dependencies-on-monday-com)
- [Cross-Project Dependencies](https://support.monday.com/hc/en-us/articles/24601183683474-Cross-Project-Dependencies)
- [Get started with monday automations](https://support.monday.com/hc/en-us/articles/360001222900-Get-started-with-monday-automations)
- [The Autopilot hub](https://support.monday.com/hc/en-us/articles/28738092924562-The-Autopilot-hub)
- [The Update Feed (Inbox)](https://support.monday.com/hc/en-us/articles/115005309885-The-Update-Feed-Inbox)
- [Notifications explained](https://support.monday.com/hc/en-us/articles/360001292545-Notifications-explained)
- [My Work](https://support.monday.com/hc/en-us/articles/360019300579-My-Work)
- [The Dashboards](https://support.monday.com/hc/en-us/articles/360002187819-The-Dashboards)
- [The Workload Widget](https://support.monday.com/hc/en-us/articles/360010699760-The-Workload-Widget)
- [monday.com templates](https://support.monday.com/hc/en-us/articles/360001362625-monday-com-templates)
- [Mobile app - board views](https://support.monday.com/hc/en-us/articles/360015740220-Mobile-app-board-views)
- [Permissions on monday.com](https://support.monday.com/hc/en-us/articles/360019222479-Permissions-on-monday-com)
- [monday.com Shortcuts](https://support.monday.com/hc/en-us/articles/115005339905-monday-com-Shortcuts)
- [Accessibility on monday.com](https://support.monday.com/hc/en-us/articles/360000571925-Accessibility-on-monday-com)
- [Using monday.com boards with screen readers](https://support.monday.com/hc/en-us/articles/33660661840530-Using-monday-com-boards-with-screen-readers)

### Official Trello / Atlassian sources

- [Create a board](https://support.atlassian.com/trello/docs/creating-a-new-board/)
- [Table view](https://support.atlassian.com/trello/docs/single-board-table-view/)
- [Timeline view](https://support.atlassian.com/trello/docs/timeline-view)
- [Automation overview](https://support.atlassian.com/trello/docs/automation-overview/)
- [View automation logs](https://support.atlassian.com/trello/docs/opening-the-command-log/)
- [Receive Trello notifications](https://support.atlassian.com/trello/docs/receiving-trello-notifications/)
- [Trello Inbox](https://support.atlassian.com/trello/docs/trello-inbox/)
- [Trello Planner](https://support.atlassian.com/trello/docs/trello-planner/)
- [Dashboard view](https://support.atlassian.com/trello/docs/dashboard-view)
- [Workspace views](https://support.atlassian.com/trello/docs/workspace-views/)
- [Turn your board into a template](https://support.atlassian.com/trello/docs/creating-template-boards/)
- [Create a template card](https://support.atlassian.com/trello/docs/creating-template-cards/)
- [Change permissions on a board](https://support.atlassian.com/trello/docs/changing-permissions-on-a-board/)
- [Workspace admin features](https://support.atlassian.com/trello/docs/workspace-admin-capabilities/)
- [Keyboard shortcuts in Trello](https://support.atlassian.com/trello/docs/keyboard-shortcuts-in-trello/)
- [Supported browsers and platforms](https://support.atlassian.com/trello/docs/what-browsers-and-mobile-platforms-does-trello-support/)
- [Trello desktop apps](https://support.atlassian.com/trello/docs/trello-desktop-apps/)
- [Atlassian WCAG program](https://www.atlassian.com/trust/compliance/resources/wcag)

### Reddit discussions used as UX signals

- [Monday.com: workspace complexity as teams grow](https://www.reddit.com/r/mondaydotcom/comments/1qade56/anyone_else_feeling_like_mondaycom_gets_messy/)
- [Monday.com: automation health visibility](https://www.reddit.com/r/mondaydotcom/comments/1ugzcyj/anyone_else_flying_blind_on_automation_health/)
- [Monday.com: recurring workspace audit themes](https://www.reddit.com/r/mondaydotcom/comments/1sjlic7/ive_audited_a_lot_of_mondaycom_workspaces_the/)
- [Monday.com: mobile and AI-priority complaint](https://www.reddit.com/r/mondaydotcom/comments/1rjuyf7/why_does_monday_focus_on_ai_junk_instead_of/)
- [Monday.com: mobile feedback thread](https://www.reddit.com/r/mondaydotcom/comments/1rx2ugw/mondays_mobile_app_is_getting_better_and_we_want/)
- [Monday.com: multi-level automation complaint](https://www.reddit.com/r/mondaydotcom/comments/1tjlj7i/automations_on_multilevel_board_are_broken/)
- [Monday.com: automation interface regression complaint](https://www.reddit.com/r/mondaydotcom/comments/1rs12re/new_automation_system_way_worse/)
- [Monday.com: automation/column restriction complaint](https://www.reddit.com/r/mondaydotcom/comments/1vb0y1f/is_anyone_else_struggling_with_mondays_automation/)
- [Monday.com: broad review thread](https://www.reddit.com/r/mondaydotcom/comments/1h6vg1a/what_do_you_think_of_mondaycom_would_love_to_hear/)
- [Monday.com: visual/cross-discipline discussion](https://www.reddit.com/r/mondaydotcom/comments/1mjwcer/monday_dev_vs_jira_which_would_you_bet_on_for_2025/)
- [Trello: 2026 satisfaction and simplicity](https://www.reddit.com/r/trello/comments/1udabns/how_satisfied_are_you_with_trello_in_2026_and_why/)
- [Trello: recent UI criticism](https://www.reddit.com/r/trello/comments/1w910sk/trello_broke_their_ui_because_they_want_to_push/)
- [Trello: 2025 redesign criticism and business use](https://www.reddit.com/r/trello/comments/1mtl2sf/do_trellos_developers_even_use_it/)
- [Trello: mobile board feedback](https://www.reddit.com/r/trello/comments/1hsocdg/trello_mobile_users_what_frustrates_you_most_about/)
- [Trello: new-user card-layout feedback](https://www.reddit.com/r/trello/comments/1i7rmn2/new_trello_user_feedback_questions/)
- [Trello: product-scope discussion](https://www.reddit.com/r/trello/comments/1ixwvry/new_trello_features_first_do_no_harm/)
- [Trello: large-list/performance anecdote](https://www.reddit.com/r/trello/comments/1vvvnz4/is_anyone_else_having_trouble_with_trello/)
- [Trello: automation delay anecdote](https://www.reddit.com/r/trello/comments/1j3znb1/automation_completely_not_working/)
- [Project Management: Kanban tool comparison](https://www.reddit.com/r/projectmanagement/comments/1cqv0dy/best_kanban_tools_for_switching_from_scrum/)
