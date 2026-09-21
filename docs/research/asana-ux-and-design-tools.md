# Asana UX patterns and design-tool options for Astra

**Research date:** 2026-09-19  
**Scope:** Navigation, work views, task detail, attachments, hierarchy, search and filters, notifications, permission cues, and collaborative design tooling.  
**Source rule:** First-party product documentation only.

## Executive recommendation

Use Asana as an **interaction-pattern reference**, not as a visual template. Astra should adopt the useful information architecture—a stable navigation shell, multiple views over one task model, contextual task detail, permission-aware controls, and an actionable inbox—while developing its own typography, spacing, color, iconography, and component language.

For the design workspace:

- Choose **Figma** for the fastest route to polished, collaborative prototypes and a strong developer handoff, especially if agent-assisted implementation matters.
- Choose **Penpot** instead if self-hosting, design-data control, open standards, and a web-native CSS mental model outweigh Figma's broader workflow ecosystem.
- Use **Storybook later as an implementation companion**, not as the design canvas, once Astra has a reusable coded component layer.

For this project's current stage, the practical default is **Figma**, with a tightly scoped prototype rather than a wholesale redesign. If the design files themselves must remain on infrastructure controlled by the owner, select **Penpot**.

## 1. Transferable Asana patterns

### 1.1 Navigation shell

Asana describes five persistent interface areas: a sidebar, contextual header, global top bar, main pane, and task-details pane. The sidebar exposes personal destinations and projects; the top bar carries global creation and search; the main pane changes with the chosen destination; and the task pane preserves the surrounding work context while showing details. ([Asana: Navigating Asana](https://help.asana.com/s/article/navigating-asana))

**Adapt for Astra:**

- Left navigation: Home/Portfolio, My work, Inbox, Projects, Final results, and Owner administration when authorized.
- Global top bar: universal search, one primary Create action, unread indicator, profile/session controls.
- Contextual project header: project identity, status/privacy/role cues, member access, and view tabs.
- Main work canvas: List, Board, or Timeline without changing the underlying task identity.
- Right task drawer: fast inspection and ordinary updates while the project stays visible beneath it.
- Full task page: deep governance work, long histories, submissions, final results, or attachment administration.

This is an information-architecture recommendation. Do not reproduce Asana's trade dress, illustrations, exact layout measurements, or proprietary assets.

### 1.2 List, Board, and Timeline are views—not separate workflows

Asana's Board view supports section/stage grouping, drag and drop, filters, sorting, grouping and subgroups, hidden empty groups, saved views, and configurable card detail. ([Asana: Board view](https://help.asana.com/s/article/board-view)) Its Timeline view keeps scheduled work on a time axis, exposes unscheduled work separately, shows dependencies, and can expand first-level subtasks. ([Asana: Timeline](https://help.asana.com/s/article/timeline))

**Adapt for Astra:**

| View | Primary job | Essential Astra behavior |
|---|---|---|
| List | Daily operational control | Dense rows; sortable fields; hierarchy expansion; inline low-risk edits; bulk selection later |
| Board | Workflow and bottleneck scan | Status columns; visible criticality/due cues; role-gated drag; confirmation and reason where governance requires it |
| Timeline | Schedule and dependency reasoning | Date bars; dependency lines; unscheduled tray; overdue/today markers; hierarchy expansion |

All three must operate on the same tasks and enforce the same lifecycle and authorization rules. A view change must never silently change task meaning. Filters should persist per user/view, with an obvious reset and an indication when results are filtered.

### 1.3 Task detail: drawer first, full page when depth demands it

Asana puts completion, title, assignee, dates, project membership, dependencies, custom fields, description, comments, collaborators, subtasks, and attachments in the task-details pane, while retaining a full-screen option. ([Asana: Task fields](https://help.asana.com/s/article/task-fields))

**Adapt for Astra:**

- Keep the task title, status, accountable owner, due state, criticality, and permission badge above the fold.
- Separate **accountability** (owner), **participation** (collaborators), and **governance** (reviewer/approver); do not collapse them into one people field.
- Present lifecycle actions as named actions—Submit, Accept, Reopen, Put on hold—not as an unrestricted status dropdown.
- Group the body into scannable sections: Overview, Schedule and dependencies, Subtasks, Attachments, Submission/approval, and History.
- Use a drawer for normal work; provide a stable full-page URL for long review sessions and shareable deep links.
- Preserve the user's position in the underlying list/board/timeline after closing the drawer.

### 1.4 Attachments: one area, two clearly different source types

Asana displays uploads in both a dedicated attachments area and the timestamped activity feed. It also links external storage providers without altering those providers' permissions. Asana's own uploads have a per-file size limit and larger files are directed to external providers. ([Asana: Task comments and attachments](https://help.asana.com/s/article/task-comments-and-attachments))

**Adapt for Astra's approved dual model:**

- Use one Attachments section with an explicit type badge on every record:
  - **External link** — HTTPS destination, opened in the browser; destination permissions remain outside Astra.
  - **Astra-managed file** — uploaded bytes stored in the installation's configured backend.
- Show display name, source type, uploader, time, optional note, size/hash for managed files, and current final-result designation.
- Keep the primary action type-specific: **Open external link** versus **Download file**.
- Show permanent-link state only to the App Owner, with unmistakable wording that it bypasses continuing task authorization.
- Put removal, final-result unmarking, permanent-link generation, and revocation behind deliberate confirmations and surface the resulting audit entries in History.
- Hide add/remove controls when the current role cannot use them; backend authorization remains authoritative.

Do not import Asana's specific 100 MB limit. Astra's owner-approved policy remains a 25 MB default with a configurable 250 MB hard ceiling.

### 1.5 Hierarchy should be visible and inheritance explicit

Asana treats subtasks as independent tasks embedded under a parent; parent project, tags, and assignee are not automatically inherited. ([Asana: Tasks and subtasks](https://help.asana.com/s/article/tasks-and-subtasks))

**Adapt for Astra:**

- Present a clear breadcrumb: Project → parent task → current task.
- Use expand/collapse in List and Timeline, with completed/total roll-up separate from the parent's declared progress.
- State any inheritance beside the field rather than relying on hidden propagation.
- Make re-parenting a deliberate operation with cycle/error feedback.
- Keep dependency relationships visually distinct from parent/child relationships.

### 1.6 Search and filters should explain the active result set

Asana's advanced search stacks filters, returns only objects the searcher is permitted to see, and can save a live search view whose results update as work changes. ([Asana: Search and search views](https://help.asana.com/s/article/search-and-search-views))

**Adapt for Astra:**

- Apply authorization before returning results, counts, autocomplete suggestions, or exports.
- Use filter chips for entity, project, status, criticality, owner, due band, and open-only state.
- Provide **Clear all**, a result count, and a human-readable summary such as “Critical open work due in 14 days.”
- Keep global search distinct from current-view filtering.
- Add named saved views only after the underlying filter behavior is stable.
- Use explicit empty states: no data, no matches, or no access are different conditions.

### 1.7 Inbox should support triage, not just display alerts

Asana's Inbox distinguishes unread activity, bookmarks, and archive; supports filters, sorting, density choices, and saved tabs; and keeps task detail available while triaging notifications. It generally omits notifications caused by the user's own actions. ([Asana: Inbox](https://help.asana.com/s/article/inbox))

**Adapt for Astra:**

- Make Inbox a first-class destination rather than a modal once notification volume grows.
- Support unread/read, archive, task/project filters, actor, event type, and newest/relevance sorting.
- Open the related task in a detail pane without losing inbox position.
- Keep unread status separate from approval or acknowledgement; marking read must never approve work.
- Deliberately diverge from Asana where Astra governance requires it: the App Owner must receive the approved attachment-attempt and attachment-action notifications even when an action would otherwise be considered self-generated.

### 1.8 Permission cues belong beside the action and object

Asana documents object-level access and distinct Admin, Editor, Commenter, and Viewer capabilities; it also exposes a member's permission in the task/project interface. ([Asana: Permissions overview](https://help.asana.com/s/article/permissions-overview), [Asana: Individual project permissions](https://help.asana.com/s/article/individual-project-permissions), [Asana: Task permissions](https://help.asana.com/s/article/task-permissions))

**Adapt for Astra:**

- Show a compact role/access badge in project and task headers: App Owner, Project Manager, Member, or Viewer.
- Hide impossible forms and destructive actions instead of inviting a predictable 403 response.
- For visible-but-restricted information, explain why it is read-only.
- Pair every sensitive control with server-side authorization and an audit event where required.
- Do not copy Asana's “highest permission wins” behavior across multiple containers unless Astra explicitly adopts and tests that rule.

## 2. Recommended Astra UX direction

### 2.1 Information architecture

```text
Astra
├─ Home / Portfolio
├─ My work
├─ Inbox
├─ Projects
│  └─ Project
│     ├─ List
│     ├─ Board
│     ├─ Timeline
│     └─ Project settings (authorized roles only)
├─ Final results
└─ Administration (App Owner only)
```

The navigation should remain shallow. Entity is a filtering and context dimension, not necessarily another mandatory navigation level.

### 2.2 First prototype flows

Prototype these flows before polishing every screen:

1. Navigate from Portfolio to a project, switch List → Board → Timeline, and retain filter context.
2. Open a task in the drawer, follow a dependency, return without losing place, then open the full task page.
3. Experience the same task as App Owner, Project Manager, and Viewer; unavailable actions should disappear or become clearly read-only.
4. Add an external HTTPS attachment and open it safely in a new tab.
5. Upload an Astra-managed file, see progress/errors, and download it through the normal authorized path.
6. Attempt to remove an attachment marked as a final result; see the block, unmark deliberately, then remove.
7. Generate and revoke an owner-only permanent direct link with the approved bypass warning.
8. Triage the resulting owner notifications from Inbox and open the relevant task in context.

### 2.3 Component starter set

Start with a small system rather than designing screens as isolated pictures:

- Shell: sidebar, top bar, contextual header, view tabs, page/drawer layout.
- Work display: task row, board card, timeline item, hierarchy disclosure, dependency indicator.
- Governance: role badge, privacy/access badge, lifecycle action bar, reason dialog, confirmation dialog, audit event.
- Attachments: external-link row, managed-file row, upload progress/error, final-result badge, permanent-link state.
- Triage: notification row, unread marker, filter chip, empty state, permission-denied/read-only explanation.
- Foundations: typography scale, spacing, color roles, focus state, disabled state, criticality/due-state tokens.

Use semantic design tokens such as `surface`, `text-muted`, `danger`, `criticality-high`, and `due-overdue`; do not encode meaning only through color.

## 3. Collaborative design-tool comparison

| Criterion | Figma | Penpot | Storybook |
|---|---|---|---|
| Primary role | Collaborative product design and prototyping | Collaborative product design and prototyping with self-host option | Coded component development, documentation, and review |
| Collaboration | Link/invite sharing with view/edit permissions and in-context comments | Shared files/prototypes, comments, team libraries | Review of running component examples; design embeds/integrations |
| Prototype depth | Strong interactive components, variables, conditions, modes | Board-to-board flows, overlays, animations, shareable flows | Interaction testing on real components rather than screen-flow authoring |
| Design system | Components, variants, variables, published libraries | Components, variants, shared libraries, DTCG-aligned tokens | Stories become executable component/state documentation |
| Developer handoff | Dev Mode, inspect/code details, ready-for-dev states, integrations | Inspect mode, measurements, CSS/HTML/SVG output; CSS-like Flex layouts | The implementation itself is inspectable and testable |
| Hosting/data | Figma-hosted service | Cloud or self-hosted via Docker/Kubernetes options | Hosted wherever Astra's development workflow chooses |
| Best fit for Astra | Fastest high-fidelity collaboration and agent-assisted handoff | Private/self-hosted design workspace and open token portability | Later, when reusable coded components exist |

### 3.1 Figma

Figma supports file/prototype sharing by invitation or link with view/edit controls, and comments are available to users with view access. ([Figma: Share files and prototypes](https://help.figma.com/hc/en-us/articles/360040531773-Share-files-and-prototypes), [Figma: Guide to comments](https://help.figma.com/hc/en-us/articles/360039825314-Guide-to-comments-in-Figma)) Components, styles, variables, and libraries support a reusable design system, while variables can represent design tokens and prototype state. ([Figma: Build your design system](https://help.figma.com/hc/en-us/articles/14548865734679-Lesson-3-Build-your-design-system), [Figma: Guide to variables](https://help.figma.com/hc/en-us/articles/15339657135383-Guide-to-variables-in-Figma))

Figma's Dev Mode exposes layout, spacing, properties, variables, prototype interactions, version comparison, and ready-for-development states, but it requires paid-plan seat types. ([Figma: Guide to Dev Mode](https://help.figma.com/hc/en-us/articles/15023124644247-Guide-to-Dev-Mode)) Figma also documents remote and desktop MCP servers that can pass design context to tools including Claude Code and Codex; the remote server is link-based and has the broadest feature set. ([Figma: Guide to the Figma MCP server](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server), [Figma: Compare remote and desktop MCP](https://help.figma.com/hc/en-us/articles/35281385065751-Figma-MCP-collection-Compare-Figma-s-remote-and-desktop-MCP-servers))

**Choose Figma when:** rapid collaboration, polished prototypes, mature design-system workflow, and AI/developer handoff are the leading priorities.

**Tradeoffs:** cloud-hosted design data; plan/seat constraints for some advanced capabilities; disciplined file permissions and library ownership are required.

### 3.2 Penpot

Penpot can run in its cloud service or on a controlled server; official self-hosting options include Docker Compose and Kubernetes-oriented deployments. ([Penpot: Cloud or self-host](https://help.penpot.app/user-guide/first-steps/cloud-selfhost/), [Penpot: Self-hosting guide](https://help.penpot.app/technical-guide/getting-started/)) It supports components, variants, shared libraries, design tokens, comments, prototypes, and inspect/code output. ([Penpot: Libraries](https://help.penpot.app/user-guide/design-systems/libraries/), [Penpot: Variants](https://help.penpot.app/user-guide/design-systems/variants/), [Penpot: Comments](https://help.penpot.app/user-guide/account-teams/comments/), [Penpot: Prototyping](https://help.penpot.app/user-guide/prototyping-testing/prototyping/))

Its design tokens follow the W3C Design Tokens Community Group format and can be exported, while its Flex Layout uses CSS Flexbox concepts and exposes generated specifications/code in Inspect mode. ([Penpot: Design Tokens](https://help.penpot.app/user-guide/design-systems/design-tokens/), [Penpot: Flexible Layouts](https://help.penpot.app/user-guide/designing/flexible-layouts/), [Penpot: Dev tools](https://help.penpot.app/user-guide/dev-tools/))

Penpot prototype links can be shared outside a team and may allow comments or code inspection depending on link permissions, so link governance must be deliberate. ([Penpot: Testing and View mode](https://help.penpot.app/user-guide/prototyping-testing/testing-view-mode/))

**Choose Penpot when:** the owner wants the design environment on controlled infrastructure, prefers open token portability, or wants design layouts to map closely to CSS concepts.

**Tradeoffs:** self-hosting adds patching, backup, availability, and access-management work; the collaboration/integration ecosystem is smaller than Figma's; public prototype links require careful permission handling.

### 3.3 Storybook as a later companion

Storybook can link or embed Figma designs alongside component stories, helping teams compare coded components with their design source and find inconsistencies earlier. ([Storybook: Design integrations](https://storybook.js.org/docs/8/sharing/design-integrations))

For Astra, this becomes useful only after the front end has a meaningful reusable component layer. It should not delay the first UX prototype and is not a substitute for Figma or Penpot.

## 4. Decision guide

- Pick **Figma** if the immediate goal is to co-design and validate Astra quickly, then hand precise screens and interactions to a coding agent/developer.
- Pick **Penpot** if the design artifacts themselves need private/self-hosted control or open-standard token portability.
- Do **not** adopt two primary design canvases; that creates duplicate components and uncertain authority.
- Whichever tool is chosen, designate one library/file as the source of truth, use named components and semantic tokens, and record approved flows in the repository alongside implementation requirements.

## 5. Proposed next deliverable

Create one desktop-first prototype at approximately 1440 px width, plus a narrow-laptop check around 1024 px. Cover the eight priority flows above with realistic Astra task data and three permission personas. Review information hierarchy and permissions first; visual polish comes after the workflows are accepted.

The prototype should end with an implementation brief containing:

- annotated screens and interaction states;
- the token list and component inventory;
- permission visibility rules;
- empty, loading, error, denied, and long-content states;
- keyboard/focus expectations;
- a mapping from each approved screen to existing or proposed Astra routes/components.

