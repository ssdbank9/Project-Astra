# Astra every-ticket board audit — 2026-10-13

**No, all tickets are not knocked off.** The existing board has 85 tickets:
**25 done, 39 signoff, 7 human, 14 backlog**. That is 60 not in Done.
TV43F1 adds one coordination ticket for this package, making 86 total.

Source: read-only `jaira list --json`, reconciled with 86 local tracked/working
ticket files. State is a dated snapshot; reviewers must recount the frozen
package, including any later owner transition. Ticked DoD is a declared claim,
not independent runtime verification. Done does not imply deployed readiness.

## Final package lane counts

| Lane | Count |
| --- | ---: |
| done | 25 |
| signoff | 39 |
| human | 8 |
| backlog | 14 |
| pre-process | 0 |
| in-progress | 0 |
| review | 0 |
| todo | 0 |
| blocked | 0 |
| **Total** | **86** |

## What the open tickets mean

- 39 signoff: 38 declare complete DoD; JM7CFP still has its criterion unticked.
- Seven existing human: four historical owner decision tickets, 3NT40T,
  accepted 2FREQ9 awaiting owner lane closure, and B1 ZQQCJM awaiting acceptance.
- 14 backlog: two launch/hosting gates (TRPV3J, 6BXYJZ), five
  superseded/dropped reconciliation candidates, seven historically deferred features.
- W6ZSGA, JM7CFP and 2FREQ9 have recorded chat acceptance; do not ask Aly again.
  Acceptance, proof completeness and board closure are different facts.
- All 25 Done tickets declare complete DoD. Their entire code/acceptance proof
  was not independently rerun ticket-by-ticket by this board inventory.
- A6 UI leftovers and B2/B4/B5/B6/B7/C release work are not each represented
  by a separate current ticket. Existing ticket count is not the full gate count.

## Existing safe changes included in this publication

Done changes already present locally and recorded as updated-by Aly: JPEBCM, 3M2AYA, 2RPSWM,
VZ1ENJ, ZFP6ET, SXAWHN, 827Q51 and AY5EZ0. W6ZSGA has a pre-existing
Codex progress note, not a lane change. These are committed as supplied;
this task creates no new acceptance for them. Existing README/log edits are
reconciled into the current package rather than silently discarded.

Private source XLSX/PDF, data, Temp logs/screenshots, environments and keys
are excluded. Some inaccessible temporary directories cannot be inventoried;
their contents are unverified and nothing from them is staged.

## Every ticket

| ID | Title | Lane | Assignee | Declared DoD | Disposition |
| --- | --- | --- | --- | --- | --- |
| 2Z8AH5 | Custom fields on tasks | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| 386TA6 | Project status updates | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| 4G3NY0 | Task calendar (month) view | backlog | Aly Jafferani | 0/1; complete=false | Calendar built in FKVHH8; Aly reconciles/ closes |
| 6BXYJZ | Production security and deployment | backlog | Aly Jafferani | 0/1; complete=false | Deployment gate; assigned Aly; no staging/deployment authorization |
| A48JEX | Board (Kanban) view: sections as columns | backlog | Aly Jafferani | 0/1; complete=false | Status Board delivered instead; scope reconciliation by Aly |
| C86ZMY | Sections: group tasks within a project | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| F9HBSJ | Daily summary and notification policy | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| KK400X | AI first-pass: propose the board from minutes, notes, and emails | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| MXY7BG | Hosted attachments: managed upload, streaming and storage | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| PRJAD8 | Goals with progress roll-up | backlog | Aly Jafferani | 0/1; complete=false | Historically deferred from first pilot; retain open unless Aly changes scope |
| RWMRKM | My Work: personal cross-project task view | backlog | Aly Jafferani | 0/1; complete=false | My Work built in FKVHH8; Aly reconciles/ closes |
| S1C6PN | Workload / capacity view | backlog | Aly Jafferani | 0/1; complete=false | Workload historically dropped; Aly records disposition |
| TRPV3J | Backups and restore | backlog | Aly Jafferani | 0/1; complete=false | Launch recovery work missing; assigned Aly; ask before takeover |
| X8FNA5 | Cohesive UX shell + feature interoperability | backlog | Aly Jafferani | 0/1; complete=false | Shell built across Gate 2; Aly reconciles/ closes |
| 03G8EH | Serialize task submissions and refuse submits against a changed task | done | Claude | 5/5; complete=true | Board Done; original proof still subject to independent release review |
| 0D9Q3X | Owner inbox: show the requested status and reason, and reload the task after a 409 | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| 1Z4PHZ | Make the xlsx test fixture deterministic (zip timestamps flake an import test) | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| 2RPSWM | Limit designated approvers to acceptance requests | done | Codex | 5/5; complete=true | Board Done; original proof still subject to independent release review |
| 39DNZT | Maintainability: replace the repeated migrate() version blocks with a step registry | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| 3M2AYA | Sign-in never locks anyone out; owners reset passwords in the app; 8-character minimum | done | Claude | 5/5; complete=true | Board Done; original proof still subject to independent release review |
| 5GK6SB | Polish closed/submitted task hints from ARZWV7 review | done | Claude | 5/5; complete=true | Board Done; original proof still subject to independent release review |
| 67T315 | Fault and retry tests for every legacy migration step v1-v12 | done | Claude | 4/4; complete=true | Board Done; original proof still subject to independent release review |
| 7E1K4B | Finish Phase A3 literal search and CSV whitespace guards | done | Aly Jafferani | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| 827Q51 | Expose linked scheduling in the phone schedule table | done | Codex | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| 9MK29X | Maintainability: split AstraService.update_task into policy, validation and persistence helpers | done | Claude | 2/2; complete=true | Board Done; original proof still subject to independent release review |
| A836XC | Make legacy SQLite migrations atomic and retry-safe | done | Claude | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| ARZWV7 | Hide or disable task edits the server refuses on closed and submitted tasks | done | Claude | 4/4; complete=true | Board Done; original proof still subject to independent release review |
| AY5EZ0 | Bound stalled HTTP requests before launch | done | Codex | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| DVS19Q | db.transaction() leaves the connection inside an open transaction when COMMIT fails | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| EXEZPM | Maintainability: pass the Owner decision context explicitly instead of _active_owner_request_id | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| G9G9PX | Approving one of two identical pending Owner requests leaves the other pending | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| JPEBCM | Per-entity portfolio roll-up with budgets | done | Aly Jafferani | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| SRFCZD | Harden task state integrity and idempotency | done | Claude | 6/6; complete=true | Board Done; original proof still subject to independent release review |
| SXAWHN | Linked task movement and automatic project schedule | done | Codex | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| T8WHJR | Keep completed, cancelled and abandoned tasks immutable outside reopen | done | Claude | 7/7; complete=true | Board Done; original proof still subject to independent release review |
| VZ1ENJ | Show person names in workplan change preview | done | Codex | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| WNXSDA | Maintainability: schema-level idempotency key and indexed lookup for pending Owner requests | done | Claude | 3/3; complete=true | Board Done; original proof still subject to independent release review |
| Z72D79 | Record settings changes and let owners reopen a closed project | done | Aly Jafferani | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| ZFP6ET | Preserve timeline row order and reliable later-row dragging | done | Codex | 1/1; complete=true | Board Done; original proof still subject to independent release review |
| 2FREQ9 | Notify App Owners and Chairman when deadlines move later | human | Codex | 1/1; complete=true | Chat accepted; declared DoD complete; Aly-only lane closure; no repeat acceptance |
| 3NT40T | Excel import hardening follow-ups | human | Codex | 0/8; complete=false | DoD 0/8; WYM776/B1 repairs and later XLSX choice need criterion reconciliation |
| AX572Q | Prototype governed Astra drag-and-drop | human | Aly Jafferani | 1/1; complete=true | Owner-led decision/acceptance reconciliation; inspect existing history before asking again |
| JQY55P | Explore Astra native-HTML UX shell | human | Aly Jafferani | 1/1; complete=true | Owner-led decision/acceptance reconciliation; inspect existing history before asking again |
| MTEDTM | Consolidate Astra decisions and sharing handoff | human | Aly Jafferani | 1/1; complete=true | Owner-led decision/acceptance reconciliation; inspect existing history before asking again |
| TV43F1 | Freeze pre-deployment review package and audit every board ticket | human | Codex | 1/1; complete=true | This review package; coordination, not a newly delivered app feature |
| Z9JCZ6 | Adopt Monday and Trello workflow UX lessons | human | Aly Jafferani | 1/1; complete=true | Owner-led decision/acceptance reconciliation; inspect existing history before asking again |
| ZQQCJM | B1 security review and verified HTTP hardening | human | Codex | 1/1; complete=true | B1 locally verified/pushed; awaiting Aly acceptance; hosted proof absent |
| 16JJ96 | Allow owners to rename an entity without breaking project links | signoff | Codex | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 1G7Q4C | Prevent mixed Manager saves from silently dropping edits | signoff | Codex | 4/4; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 3C1Z74 | Gate 2 slice 7: phone and accessibility pass, plus the Gate 2 leftovers | signoff | Claude | 4/4; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 3FQEKB | Assignment rules: Chairman assigns, never receives; viewers get subtasks only | signoff | Claude | 5/5; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 4T4DEA | Gate 2 slice 1: design foundation (tokens, self-hosted Inter, focus rings, no inline styles, no sideways scroll) | signoff | Claude | 6/6; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 5WZ4A8 | Project schedule dates with change history | signoff | Claude | 3/3; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 6G89SJ | Attachments on tasks | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 8B9NBH | Project & task templates | signoff | Claude | 3/3; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| 9R7A87 | Parent/subtask hierarchy and roll-up | signoff | Aly Jafferani | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| AYW0QC | Calendar Gantt + critical path | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| C9KPH6 | Import tasks and Gantt from Excel/CSV | signoff | Claude | 13/13; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| CR121Z | Gate 2 slice 5: project page with Overview, List, Board, Timeline and Activity tabs | signoff | Claude | 5/5; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| CS93C6 | Final results repository (deliverables database) | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| D73AQW | Gantt: visible colour-coded task steps with hover and click detail | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| DR3PKR | Gate 2 slice 3: docked task side panel with its own link | signoff | Claude | 5/5; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| FKVHH8 | Gate 2 slice 6: My Work groups and calendar month view, Inbox polish | signoff | Claude | 5/5; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| G1PPV7 | A viewer assigned a top-level task before 3FQEKB can still submit it | signoff | Claude | 7/7; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| GTEYTG | Secondary owners: primary owner can grant and remove full Owner access | signoff | Claude | 11/11; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| HS3JRY | Reconcile latest Owner-only authorization | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| JM7CFP | Simple project-bound Excel workplans and task-row timeline scheduling | signoff | Codex | 0/1; complete=false | Chat accepted; DoD unticked; reconcile later Excel/drag child evidence; Aly-only closure |
| JN1QYG | Board drag and drop with Move to and 15-second Undo | signoff | Claude | 4/4; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| JZACMP | Schedule-revision model: baseline / current / pending | signoff | Aly Jafferani | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| K62ZAP | Full history for Owner and Chairman; hide approval details from other non-managers' task history | signoff | Claude | 7/7; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| KBWY86 | Blocked-attempt notices: notify the acting owner for Item 2 events and cap repeats per person | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| PDDS2D | Server command to transfer the primary owner and reset a password | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| PZTYC9 | Gate 2 slice 2: shell frame (left rail, top bar, hash router, filters in the URL, toolbar into menus) | signoff | Claude | 6/6; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| QY0WG2 | Criticality: approved sorting and confirmation workflow | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| SFAZD7 | A0: restore the Windows test baseline | signoff | Codex | 5/5; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| VPYGY5 | Gate 2 slice 4: Command Center Home | signoff | Claude | 6/6; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| W6ZSGA | Project plan options and minimal bound workplan CSV | signoff | Codex | 1/1; complete=true | Chat accepted; declared DoD complete; Aly-only lane closure |
| WSA9FZ | Consolidate local Astra data under the main checkout | signoff | Codex | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| WYM776 | Repair independent importer defects before launch development | signoff | Codex | 6/6; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| X07XV4 | Task locks and Gantt date drag | signoff | Claude | 4/4; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| XDA2JR | Project calendar: workweeks and holidays | signoff | Aly Jafferani | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| XV92JJ | Bulk select and WIP limits | signoff | Claude | 4/4; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| XX9RFM | Notify owners when a project is closed or its dates change | signoff | Claude | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| Y3WC71 | Exports and search | signoff | Claude | 4/4; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| Z24KVH | Durable in-app notification inbox for the owner | signoff | Aly Jafferani | 1/1; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |
| ZSZ9T2 | Limit Project history event kinds for non-managers | signoff | Claude | 6/6; complete=true | Declared DoD complete; review/acceptance and Aly-only lane transition remain |

## Handoff document inventory for other LLMs

Read every entry below. Dated receipts describe their own tested scope;
historical facts are not automatically current facts. Read AGENTS.md and
accepted root handoffs/design references too, as the review prompt directs.

- [A0_2026-10-04.md](A0_2026-10-04.md)
- [AGENT_START_PROMPT.md](AGENT_START_PROMPT.md)
- [AUTOMATIC_TIMELINE_SCHEDULING_2026-10-12.md](AUTOMATIC_TIMELINE_SCHEDULING_2026-10-12.md)
- [B1_SECURITY_2026-10-13.md](B1_SECURITY_2026-10-13.md)
- [BOARD_AUDIT_2026-10-13.md](BOARD_AUDIT_2026-10-13.md)
- [CSV_ROUNDTRIP_DECISION_2026-10-04.md](CSV_ROUNDTRIP_DECISION_2026-10-04.md)
- [DEADLINE_NOTICES_2026-10-13.md](DEADLINE_NOTICES_2026-10-13.md)
- [DECISIONS_LOG.md](DECISIONS_LOG.md)
- [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md)
- [DESKTOP_VERIFICATION_2026-10-11.md](DESKTOP_VERIFICATION_2026-10-11.md)
- [ENTITY_RENAME_2026-10-07.md](ENTITY_RENAME_2026-10-07.md)
- [FREE_HOSTING_2026-10-13.md](FREE_HOSTING_2026-10-13.md)
- [HANDOFF_2026-09-26.md](HANDOFF_2026-09-26.md)
- [HTTP_TIMEOUT_2026-10-13.md](HTTP_TIMEOUT_2026-10-13.md)
- [IMPORTER_REPAIRS_2026-10-04.md](IMPORTER_REPAIRS_2026-10-04.md)
- [INDEPENDENT_LLM_REVIEW_PROMPT.md](INDEPENDENT_LLM_REVIEW_PROMPT.md)
- [JM7CFP_VERIFICATION_2026-10-09.md](JM7CFP_VERIFICATION_2026-10-09.md)
- [MIXED_SAVE_REPAIR_2026-10-04.md](MIXED_SAVE_REPAIR_2026-10-04.md)
- [NEXT_STEPS.md](NEXT_STEPS.md)
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
- [OWNER_EXCEL_WORKPLAN.md](OWNER_EXCEL_WORKPLAN.md)
- [PRE_DEPLOYMENT_REVIEW_2026-10-13.md](PRE_DEPLOYMENT_REVIEW_2026-10-13.md)
- [Q1_APPROVER_PERMISSIONS_2026-10-05.md](Q1_APPROVER_PERMISSIONS_2026-10-05.md)
- [README.md](README.md)
- [TABLE_SCHEDULING_2026-10-12.md](TABLE_SCHEDULING_2026-10-12.md)
- [TIMELINE_DRAG_REPAIR_2026-10-12.md](TIMELINE_DRAG_REPAIR_2026-10-12.md)
- [TIMELINE_DRAG_VERIFICATION_2026-10-11.md](TIMELINE_DRAG_VERIFICATION_2026-10-11.md)
- [WORKPLAN_CSV_2026-10-07.md](WORKPLAN_CSV_2026-10-07.md)

## Owner action and launch boundary

Only Aly may accept work or leave human/signoff/done lanes. This audit does
not claim, close, archive, delete or move an Aly-assigned ticket. Superseded
criteria should be explicitly retired with replacement evidence, not ticked
as work that happened. External-model reviews and hosted checks remain
unverified until their actual receipts exist.
