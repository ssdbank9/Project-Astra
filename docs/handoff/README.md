# Astra handoff pack — 2026-09-26

This folder hands Project Astra from Claude to Codex. It was written at branch
`codex/migration-safety-remediation`, head `0b90ceb` (schema v20, 676 tests OK,
nothing deployed). It is meant to live at `docs/handoff/` in the repository.

## What is in the pack

| File | What it is for |
| --- | --- |
| `README.md` | This index and the reading order |
| `HANDOFF_2026-09-26.md` | The master handoff: status, setup on Windows and Linux, tests, working rules, architecture, feature history, permissions, board, gaps, risks, where the docs live |
| `NEXT_STEPS.md` | The plan from now to distribution: A close out development, B hardening, C release engineering, D deployment, E distribution, F operate |
| `DEPLOYMENT_RUNBOOK.md` | Command-level steps for the Oracle Cloud Always Free + DuckDNS + Caddy pilot, with Aly's steps marked, a check after every stage, update and rollback |
| `DECISIONS_LOG.md` | Every decision Aly has made that we found, with date and source, plus Claude's default calls that Aly has not overruled |
| `OPEN_QUESTIONS.md` | What Aly still has to decide, each with a recommended default |
| `CODEX_START_PROMPT.md` | The first message Aly pastes to Codex |

## Reading order for Codex

1. `CODEX_START_PROMPT.md`: the rules and the first task, in short.
2. `HANDOFF_2026-09-26.md`: sections 1 (status), 4 (rules) and 6 (permissions)
   first, then the rest.
3. `NEXT_STEPS.md`, phase A in full; skim the later phases.
4. `OPEN_QUESTIONS.md` and `DECISIONS_LOG.md`, before you propose any change of
   behaviour.
5. `AGENTS.md`, `CLAUDE.md`, `pending-global-mistakes.md` and `README.md` in the
   repository root.
6. `DEPLOYMENT_RUNBOOK.md` when the work reaches phase D.

## For Aly

- To test locally, follow section 2.1 of `HANDOFF_2026-09-26.md`.
- Your part of phase A is in `NEXT_STEPS.md` A1 (signoffs), A2 (questions),
  A7 (phone and screen-reader check) and A8 (the `tmp*` folders).
- The five questions that block the most work are at the top of
  `OPEN_QUESTIONS.md`.

## How this pack was checked

- Every SHA cited was checked with `git cat-file -t` in the repository, except
  three that the shallow container clone does not hold: `051db35` and
  `331f988` are remote branch heads confirmed with `git ls-remote`, and
  `c5ac1c0` is the first parent of `main`'s head `c841526`
  (`git cat-file -p c841526`).
- Every repository path cited exists at `0b90ceb`, apart from the files this
  pack proposes to create (`CHANGELOG.md`, `.github/workflows/tests.yml`) and
  the pack itself.
- Every `astra` command matches `src/astra/__main__.py`; every environment
  variable matches the code (`ASTRA_HOME`, `ASTRA_SECURE_COOKIES`,
  `ASTRA_ATTACHMENT_ROOTS`).
- Operating-system, Caddy, DuckDNS, OCI and encryption commands in the runbook
  were not run for this handoff; they are marked "verify".
- Facts taken from memory notes that could not be re-checked against the
  repository or Slack are marked "memory" or "unverified".
