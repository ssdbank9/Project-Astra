# Astra Product UX Baseline

- Status: approved product and interaction direction; production implementation not started
- Decision owner: Aly Jafferani, App Owner
- Research basis: `docs/research/monday-trello-workflow-ux-research.md`
- Interaction contract: `docs/design/governed-drag-drop-contract.md`
- Visual prototypes: `design/astra-shell-prototype.html` and `design/astra-drag-drop-prototype.html`

## Purpose and precedence

This document turns the strongest researched Monday.com and Trello patterns into
one durable Astra experience. It is not a request to clone either product. Astra
keeps its own A-hybrid Command Center, governance model and visual identity.

When documents appear to conflict, apply this order:

1. approved security, role and data-handling decisions;
2. the governed drag-and-drop contract;
3. this product UX baseline;
4. the research report;
5. throwaway prototype behavior.

Prototypes demonstrate intent only. They are not production authorization,
storage, scheduling, notification or persistence code.

## Product promise

Astra should feel immediately understandable like a strong Trello board, grow
into multi-view planning like Monday.com, and remain safer than either reference
pattern for governed work.

A user should be able to answer five questions within seconds:

- What needs my attention now?
- What is blocked, late or waiting for a decision?
- Who owns each next action?
- What will change if I move this work?
- Where is the authoritative record and its history?

Visual impact comes from hierarchy, responsive feedback and confident motion—not
from decorative charts, excessive gradients, permanent toolbars or animation
that delays work.

## Non-negotiable authority model

| Capability | App Owner | Project Manager | Viewer |
| --- | --- | --- | --- |
| Configure statuses, transitions, WIP limits and workflows | Yes | No | No |
| Move work through ordinary internal stages | Yes | Yes | No |
| Accept, reject, complete, close, reopen or override | Yes | Approval request | No |
| Change ordinary project-local dependencies | Yes | Yes, if no protected impact | No |
| Affect critical path, milestone or project completion | Yes | Approval request | No |
| Move, copy or link across projects | Yes | No | No |
| Manage files, folders, versions or permanent links | Yes | No | No |
| Open authorized files | Yes | Yes | Yes |
| Publish templates or automations | Yes | No | No |

The interface may hide unavailable controls for clarity, but the server must
authorize every action. Keyboard, menu, touch, API, automation, bulk and offline
paths must enforce the same decision. Protected Manager actions create an Owner
request; they do not pretend to have completed.

## Adopt, adapt and avoid

| Decision | Pattern | Astra rule |
| --- | --- | --- |
| Adopt | One work record shown through several views | List, Board, Timeline, My Work and dashboards use one task identity, permission decision and event history. |
| Adopt | Trello-level board legibility | A card defaults to title, accountable owner, due state, criticality and blocker/dependency state. Depth opens in a drawer. |
| Adopt | Monday-style portfolio and workload visibility | Aggregate multiple projects with permission-aware drill-through, explicit metric definitions, capacity and effort. |
| Adopt | Unscheduled work tray | Timeline exposes undated tasks without inventing dates. |
| Adopt | Personal quick capture | Private captures stay private until the user deliberately files them into an authorized project. |
| Adopt | Keyboard efficiency and undo | Pointer operations have keyboard/menu equivalents; ordinary reversible actions have 15-second Undo and audited restoration. |
| Adapt | Direct drag-and-drop | Every drop is previewed, authorized, revalidated, audited and recoverable according to impact. |
| Adapt | Dependencies and cascading dates | Astra previews downstream effects and asks whether permitted work moves; it never silently shifts a governed plan. |
| Adapt | Automation builders | Plain-language trigger/condition/action rules use draft, test and Owner-publish stages plus health, logs and a kill switch. |
| Adapt | Templates | Owner-published, versioned and inert until a preview shows statuses, dates, access and automation effects. |
| Avoid | Unlimited customization | No user-created status sprawl, arbitrary dashboard definitions or silent schema drift. |
| Avoid | Card overload | Descriptions, full checklists, files, audit history and secondary metadata stay out of default cards. |
| Avoid | One mixed notification stream | Action requests, ordinary activity, personal work and quick capture remain distinct. |
| Avoid | Opaque automation | No rule without owner, scope, plain-language behavior, test result, run history, failure state and disable control. |
| Avoid | False optimistic success | Protected, offline or conflicted mutations remain pending until the server confirms them. |
| Avoid | Desktop UI squeezed onto phones | Mobile uses focused lists, sheets and date controls, not miniature Gantt or dashboard builders. |
| Avoid | Color-only meaning | Status, risk, criticality and validation always include text, icon or pattern in addition to color. |

## Information architecture

The permanent navigation is intentionally short:

1. **Home** — portfolio Command Center.
2. **My Work** — assigned work and personal planning.
3. **Inbox** — Needs action and Activity.
4. **Projects** — project switcher and workspaces.
5. **Capture** — private quick capture.

Owner-only administration lives under one **Manage** entry rather than competing
with daily work:

- approvals and governance;
- people and access;
- workflow and templates;
- Automation Center;
- managed files and storage;
- audit and system health.

Global search and a `Ctrl/Cmd + K` command switcher can reach any authorized
project, task, person, saved view or action. Search results state record type,
project, owner and status, and never expose unauthorized names through counts or
suggestions.

## Visual and interaction system

### A-hybrid shell

- Use the Command Center's operational density and persistent context.
- Retain the Focus Workspace's calm typography, reading width and progressive
  disclosure.
- Retain the Executive Cockpit's compact health strip, but every signal must
  drill to the records producing it.
- Default to a light, high-contrast work canvas with a deep neutral navigation
  rail and a restrained Astra accent. Reserve strong color for state and action.
- Use a consistent 8px spacing rhythm, 44px minimum touch targets, visible focus
  rings and readable type at 100% zoom through 200% zoom.

### Oomph without friction

- Primary buttons have a clear filled state, decisive label and immediate press
  feedback. Secondary, quiet and destructive actions are visually distinct.
- Windows and drawers use purposeful depth, crisp boundaries and anchored
  transitions. A user must never wonder which record a panel belongs to.
- Use 120–220ms transitions for spatial continuity. Respect reduced motion and
  never animate a layout in a way that moves the user's target.
- Successful ordinary work gets a compact toast with an action-specific message
  and Undo. Rejections stay visible long enough to understand and include the
  reason and permitted remedy.
- Skeletons preserve layout during loading. Empty states explain both why the
  view is empty and the best next permitted action.

### Density

Offer **Comfortable** and **Compact** density. Density changes spacing and
secondary metadata, not permission cues, focus targets or core fields. Remember
the choice per user and device. Large boards use virtualization without breaking
keyboard order or screen-reader access; the List view remains the accessible
fallback.

## Screen contracts

### 1. Home — Command Center

Home is exception-led, not a gallery of totals.

Top health strip:

- overdue;
- blocked;
- awaiting Owner;
- due in seven days;
- critical-path exposure;
- people over capacity;
- failed automations or sync.

Main work area:

- **Needs Owner decision** — protected transitions, cross-project proposals,
  dependency impacts, file requests and automation/template publication;
- **At risk** — critical, near-critical, blocked and slipping work;
- **My next actions** — accountable work ordered by urgency, not creation time;
- **Recent material change** — accepted/rejected work, schedule revisions,
  dependency changes, file publication and automation failures.

Every count is a link into a permission-filtered record list and exposes its
definition, time range and last refresh. Users may filter the Command Center but
only the Owner publishes shared layouts and metric definitions.

### 2. Project workspace

The workspace header contains project name, health, accountable owner, governing
timezone, access context and the view tabs:

- Overview;
- List;
- Board;
- Timeline;
- Activity.

Files, Automation, Settings and Templates live under a single clear menu, with
Owner-only items hidden or marked read-only as appropriate. Filters, grouping and
saved views are subordinate to the current view. A visible view summary states
active filters, sort and hidden counts so a partial board cannot masquerade as
the complete project.

### 3. List

List is the dense, accessible source-of-truth workspace. It supports column
choice, sorting, filtering, grouping, inline ordinary edits and batch selection.
Reordering is disabled while a sort or filter would make the result ambiguous.
Protected or dependency-affecting edits open the same preview used by drag.

Default columns: task, status, accountable owner, start, due, dependency state,
critical/slack state, effort and last material change.

### 4. Board

Columns are Owner-configured statuses; moving a card changes the task, not a
copy. The default card contains:

- title and task key;
- accountable owner;
- due state;
- critical/near-critical marker;
- blocker or dependency indicator;
- up to two Owner-approved project fields.

Managers may move Draft → Ready → In progress → Blocked → Submitted for review
when project rules allow. Protected targets remain visible with a lock/approval
cue. A protected drop opens a pre-filled request; a blocked drop returns the card
and explains the exact rule. Viewers get no draggable affordance.

The board supports WIP signals, swimlanes, grouping and saved views without
obscuring column meaning. `Move to…` provides keyboard/menu parity. Selection
does not lock; manipulation obtains renewable leases as defined by the drag
contract.

### 5. Task drawer and full task page

A single click opens a right drawer for routine work without losing board or list
context. The drawer shows:

- title, project, status and authorization cue;
- accountable owner, dates, effort and critical/slack state;
- next dependency/blocker;
- description and concise checklist;
- comments/activity summary;
- authorized file references;
- action bar with only permitted next actions.

Deep review opens a stable full-page URL with complete description, dependencies,
schedule impact, approvals, files, versions and immutable audit history. Closing
the drawer restores focus to the originating card/row.

### 6. Timeline and Gantt

Timeline combines Monday-style dependency reasoning with Trello's unscheduled
tray. It provides:

- drag and resize with ghost dates;
- dependency connectors and type/lag popover;
- critical-path toggle and slack;
- baseline versus proposed dates;
- unscheduled tasks tray;
- private What-if mode with current/proposed comparison;
- structured schedule table alternative.

Ordinary authorized adjustments can commit with Undo. Anything affecting a
protected milestone, critical path or project completion shows the exact
downstream effect and either requires Owner confirmation or creates an Owner
request. Cross-project links are Owner-only and limited to approved interface
records.

### 7. My Work, Inbox and Capture

These are different products and must not collapse into one feed.

- **My Work:** assigned work grouped by overdue, today, next seven days and later;
  users may privately reorder their attention without changing project priority.
- **Inbox — Needs action:** approvals, acknowledgements, review requests,
  conflicts, failed automations and file-action requests. Reading is not approval.
- **Inbox — Activity:** mentions, watched changes and ordinary subscribed updates,
  bundled to prevent noise.
- **Capture:** private title-first intake with optional note/date. Filing previews
  destination, resulting access and any required fields.

Each actionable item states the actor, intended change, affected records, reason,
time, consequence, deadline and available decisions. Owner mandatory alerts
cannot be muted; routine activity can be digested.

### 8. Workload

Workload uses accountable person, date range, explicit capacity and effort. It
shows unknown effort separately and never treats task count as capacity. Users
can drill from a cell to the contributing tasks. Over-capacity warnings state
whether the problem is assigned effort, unavailable capacity, overlapping dates
or missing estimates. Reassignment uses the same impact and authorization seam.

### 9. Automation Center

Automation is an operational system, not a magic settings page. The center has:

- Health — running, failing, paused and stale rules;
- Drafts — Manager suggestions and Owner drafts;
- Runs — trigger, actions, affected records, duration, outcome and error;
- Usage — action counts and thresholds;
- Connections — credential owner, scope and last verified state.

Every rule displays plain-language trigger, conditions and actions; owner;
project scope; importance; last/next run; last failure; version; and enabled
state. Test mode explains intended mutations without making them. Only the Owner
publishes, enables, disables or changes live rules. A rule cannot grant access,
manage files, complete protected work, operate across projects or approve its own
request.

### 10. Templates and onboarding

Start with three Owner-published templates:

1. Simple project.
2. Dependency-led project.
3. Approval-heavy project.

Instantiation previews status workflow, fields, roles, gates, dates, automation
and views. Members, credentials, external links, live dates and automation owners
are never copied silently.

First-use onboarding follows progressive disclosure:

- all users: find project, open task, filter view, capture work;
- Managers: move ordinary work, submit review, propose dependency/date change;
- Owner: handle approvals, publish workflows/templates/automation, manage files,
  inspect audit and system health.

Use one guided example at a time with real undo. Do not cover the working surface
with a permanent tour.

## Files and upload experience

File management remains Owner-only. Managers and Viewers can open or download
authorized files but cannot reach mutation paths through drag, quick actions,
templates, automation or mobile.

- Default per-file limit is 25MB; the Owner may configure it up to the absolute
  250MB ceiling.
- Each folder or multi-file batch has a fixed 250MB total ceiling.
- Hash identical content and offer reuse; same-name/different-content defaults to
  New version.
- Preserve local folder hierarchy as virtual folders without revealing local
  paths.
- Show per-file validation and upload state with pause, cancel and retry.
- Cross-project file placement is Owner-only and previews Move / Copy / Link,
  with Link as default.
- Direct permanent links are off by default, Owner-created, revocable, audited
  and notified.
- All blocked attachment-removal attempts notify the Owner.

Production may use Oracle Cloud Object Storage or a protected private-server
filesystem. The UX must use one managed-file model so storage can change without
changing permissions or user behavior.

## Mobile, low bandwidth and hosting resilience

The hosted app must remain reachable when deployed to Oracle Cloud, a private
server, or an always-on desktop made securely available. The interface must not
assume LAN-only access or desktop-sized bandwidth.

### Small screens

- Home becomes an ordered exception list.
- Board becomes horizontally paged columns with explicit Move actions.
- Timeline becomes agenda/schedule table plus date sheets; no precision Gantt.
- Task detail is full-screen.
- Approvals show consequence before the decision buttons.
- Long-press drag is tablet-only where deliberate and reliable; phones use
  action sheets.

### Low-data mode

- Load shell, navigation, text records and actions first.
- Defer charts, avatars, images, long history and file previews.
- Paginate history and large lists; virtualize with accessible ordering.
- Cache read-only shells and last confirmed records without caching unauthorized
  data beyond the session policy.
- Queue only safe drafts and ordinary edits offline. Protected changes, access,
  files, cross-project actions and automation publication require an online
  server decision.
- Show `Offline`, `Syncing`, `Pending`, `Confirmed` and `Failed` explicitly.
- Stream large transfers with bounded concurrency and resumable queue state.

## Accessibility contract

- Meet WCAG 2.2 AA as the production target.
- All actions work without drag: keyboard, menu and structured form alternatives.
- Provide skip links, semantic landmarks, logical heading order and consistent
  focus.
- Announce drag start, valid targets, preview, commit, rejection and Undo through
  live regions without excessive chatter.
- Preserve focus after moves and when drawers/dialogs close.
- Let users disable single-key shortcuts and animation.
- Do not rely on hover, color, haptics or spatial position alone.
- Reflow at 400% zoom and maintain 44px touch targets where feasible.
- Board and Gantt always have List/schedule-table equivalents.

## States every screen must design

Every production surface requires intentional versions of:

- first-use empty;
- empty after filter;
- loading and slow-loading;
- partial data;
- offline and reconnecting;
- authorization denied;
- stale/conflicted record;
- locked by another user;
- approval required;
- server rejection after preview;
- successful commit with Undo where eligible;
- permanent failure with remediation.

Never erase the user's input on failure. Never substitute a generic “Something
went wrong” when Astra knows the failed action and safe remedy.

## Implementation sequence

1. Establish semantic tokens, shell, List, task drawer and common state patterns.
2. Ship governed Board movement through the server mutation seam.
3. Add Needs action, protected approvals, notifications and audit drill-through.
4. Add Timeline, unscheduled tray, dependency preview and schedule table.
5. Add private What-if mode, critical path and governed cross-project interfaces.
6. Add workload and exception-led Command Center metrics with drill-through.
7. Add Automation Center and versioned templates.
8. Add Owner-only managed files and storage adapters.
9. Complete mobile, low-data, accessibility and deployment acceptance across the
   supported Oracle/private-server/desktop-host options.

Each phase must include server authorization, audit, keyboard/touch parity,
failure states and automated tests. Visual completeness alone does not pass a
phase.

## Acceptance gates

- A first-time user can locate assigned work, open a task, understand its state
  and perform the next permitted action without instruction.
- A Viewer cannot mutate through any interface path.
- A Manager ordinary move is immediate and undoable; a protected move creates an
  accurate request and never appears completed.
- Every view opens the same task ID and produces the same authorization result.
- Every metric drills to its permission-filtered source records and definition.
- Every automation is attributable, testable, inspectable and disableable.
- File mutation is Owner-only across every surface and indirect path.
- Board and Timeline operations are fully possible through keyboard/menu and
  structured alternatives.
- Low-data mode is useful before charts, images or long history load.
- Offline, pending and failed states cannot be mistaken for server-confirmed
  success.
- At 1024px, 1440px, phone width, 200% zoom and reduced motion, the primary work
  remains readable and operable.
- Production verification covers authorization, transactions, concurrency,
  critical-path correctness, uploads, notifications, backup/restore, HTTPS and
  the selected hosting topology. The current prototypes prove none of these.
