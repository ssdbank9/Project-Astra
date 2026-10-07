# Entity names and Rupani filing

Aly selected `Rupani group of Colleges` as the separate entity for
`Rupani IB School in Texas, USA` on 2026-10-07. The entity was created and
the existing project filed under it through the authenticated local browser.
No task import, account creation, timezone or budget change accompanied filing.
Aly chose to leave the project timezone unchanged for the global team.

Ticket 16JJ96 adds People & access → Rename an entity. Primary and secondary
owners may rename an entity, following the existing owner-only entity settings
policy. Chairman, project managers, members and viewers cannot rename entities.
The service changes only the name. Entity IDs, project links, primary filing
and active state remain unchanged. Settings history records actor and old/new
names. Duplicate names, including case variants, empty/non-string names and
control characters are refused. A no-op does not add a history event; an audit
failure rolls the name change back.

The six focused service/HTTP tests passed in both the parent and independent
reviewer runs. Three guard-removal probes each failed the corresponding
regression on disposable source copies. Synthetic browser rename and retained
filing were verified. The full Windows suite ran 745 tests in 746.073s:
OK (skipped=1), with the existing Windows symlink limitation. Final browser
verification exercised success followed by duplicate-name refusal and confirmed
appropriate status and error feedback. Local activation is recorded in ticket 16JJ96.
