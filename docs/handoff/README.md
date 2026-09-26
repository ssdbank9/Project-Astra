# Astra handoff pack — 2026-09-26

This folder hands Project Astra to whoever works on it next: an AI coding
agent in any tool, or a human developer. The pack calls that reader "the
agent". It was written at branch `codex/migration-safety-remediation`, head
`0b90ceb` (schema v20, 676 tests OK, nothing deployed); the commits made since
are listed in `HANDOFF_2026-09-26.md` section 1.

## What is in the pack

| File | What it is for |
| --- | --- |
| `README.md` | This index, the reading order, and how to use the pack with a specific tool |
| `HANDOFF_2026-09-26.md` | The master handoff: status, setup on Windows and Linux, tests, working rules, architecture, feature history, permissions, board, gaps, risks, where the docs live |
| `NEXT_STEPS.md` | The plan from now to distribution: A close out development, B hardening, C release engineering, D deployment, E distribution, F operate |
| `DEPLOYMENT_RUNBOOK.md` | Command-level steps for the Oracle Cloud Always Free + DuckDNS + Caddy pilot, with Aly's steps marked, a check after every stage, update and rollback |
| `DECISIONS_LOG.md` | Every decision Aly has made that we found, with date and source, plus Claude's default calls that Aly has not overruled |
| `OPEN_QUESTIONS.md` | What Aly still has to decide, each with a recommended default |
| `AGENT_START_PROMPT.md` | The first message Aly pastes to the next agent |

The working rules themselves live in `AGENTS.md` in the repository root. That
file is the single source; `CLAUDE.md` repeats the same rules.

## Reading order for the agent

1. `AGENTS.md` in the repository root: the rules.
2. `AGENT_START_PROMPT.md`: the rules in short and the first task.
3. `HANDOFF_2026-09-26.md`: sections 1 (status), 4 (rules) and 6 (permissions)
   first, then the rest.
4. `NEXT_STEPS.md`, phase A in full; skim the later phases.
5. `OPEN_QUESTIONS.md` and `DECISIONS_LOG.md`, before you propose any change of
   behaviour.
6. `pending-global-mistakes.md` and `README.md` in the repository root.
7. `DEPLOYMENT_RUNBOOK.md` when the work reaches phase D.

## Using this with a specific tool

Nothing in the pack depends on one tool. Only the file a tool reads by itself
differs:

- **Codex** reads `AGENTS.md` automatically.
- **Claude Code** reads `CLAUDE.md` automatically. Its top part repeats the
  rules in `AGENTS.md`.
- **Any other tool** (Gemini, Cursor, another assistant) **or a human
  developer:** paste `AGENT_START_PROMPT.md` as the first message, or read it
  yourself, and follow `AGENTS.md`.

Wherever a step needs a decision, an account, a password or an acceptance, the
pack says "ask Aly".

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
- An independent fact-check of the pack was applied before it was committed
  (`146a5b3`).
