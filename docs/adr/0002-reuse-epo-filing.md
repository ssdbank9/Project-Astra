# Reuse EPO's entity/project filing instead of re-deriving it

The Email Project Organizer (EPO) already files every Gmail thread into an entity and a
project inside the `_machine` archive. Rather than have Astra's AI first-pass **re-derive**
that filing from the evidence, the Assessor **reuses EPO's existing filing** as the default
Proposal — mapping EPO's entity/project onto an Astra entity/project (creating Astra projects
to match where none exists), with the App Owner confirming the mapping once and free to
**refile** any individual Proposal.

## Status

accepted

## Considered options

- **Reuse EPO's filing (chosen)** — start from work that is already assessed.
- **Re-derive filing in Astra** — rejected: it discards EPO's already-assessed decisions and
  risks silently disagreeing with them, giving the App Owner two conflicting answers.

## Consequences

- Astra is **coupled to EPO's filing output**: a change to EPO's entity/project scheme means
  re-mapping on the Astra side. This is an accepted, deliberate coupling.
- The per-Proposal **refile/override** keeps a human correction path, so EPO is a strong
  default, not an unchallengeable authority.
- Astra only **reads** `_machine`; it never modifies EPO. (This is the light, read-only touch
  of EPO's *output* — distinct from the deferred Phase-0 reconciliation of EPO itself.)
