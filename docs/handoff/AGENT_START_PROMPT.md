# Agent start prompt — Project Astra (2026-09-26)

Aly: paste everything between the two lines below as your first message to
whichever agent takes over next. It works for any AI coding agent and for a
human developer. It assumes the handoff pack is committed under
`docs/handoff/` on the branch. For the file each tool reads by itself, see
"Using this with a specific tool" in `docs/handoff/README.md`.

---

You are taking over Project Astra. Astra is a private, owner-hosted project
tracker: Python standard library only, one SQLite database, a plain
HTML/CSS/JavaScript front end. I am Aly Jafferani, the App Owner and the only
person who makes decisions. Work only from GitHub, never from an old local copy.

- Repository: https://github.com/ssdbank9/Project-Astra.git (public)
- Branch: `codex/migration-safety-remediation` (the name is historical; it is
  the working branch for every agent)
- Head: the head you pull. The pack was written at `0b90ceb`; the commits
  made since are listed in `HANDOFF_2026-09-26.md` section 1, "Since the pack
  was written". Tell me the head you pulled in the preflight.
- Schema v20; the full suite is `Ran 680 tests`, `OK` (676 at `0b90ceb`)
- My Windows checkout: `C:\Users\Aly Jafferani\Documents\ChatGPT\Project-Astra`.
  Never use `...\ChatGPT\New project`; it is an old, unrelated repository.

## 1. Read these first, in this order

1. `AGENTS.md` in the repository root: the working rules. It is the single
   source of the rules for every agent and developer.
2. `docs/handoff/README.md` (the index of the pack)
3. `docs/handoff/HANDOFF_2026-09-26.md` (state, setup, rules, architecture,
   permissions, board, gaps, risks)
4. `docs/handoff/NEXT_STEPS.md` (phases A to F)
5. `docs/handoff/OPEN_QUESTIONS.md` and `docs/handoff/DECISIONS_LOG.md`
6. `pending-global-mistakes.md`. On my Windows machine also read
   `C:\Users\Aly Jafferani\.codex\mistakes.md` if it exists.
7. `README.md` (current behaviour, schema upgrade notes)
8. `docs/handoff/DEPLOYMENT_RUNBOOK.md` only when we reach phase D.

## 2. Rules you must follow

Follow every rule in `AGENTS.md`. In short:

- Work only on `codex/migration-safety-remediation` unless I name another
  branch. Pull before you start.
- Right before a push, check with `git ls-remote` that origin has not moved
  since you pulled. If it has, pull (merge), re-run the tests, then push
  normally. Never force-push, rebase or amend published history.
- After each push, tell me the final SHA, the files changed, the tickets and
  their lanes, and the tests run with the exact result.
- Use the jaira CLI for the board, never hand edits. Never run `jaira init`,
  never use `--force`, never set `JAIRA_USER` to me. Move tickets into `human`
  or `signoff`, never out of `human`, `signoff` or `done`. The ticket file
  rides in the same commit as its code.
- Get an independent review of every change by someone who did not write it
  before you call it ready.
- Never commit secrets, `.env` files, keys, a live database, venvs or caches.
  Keep files LF.
- Do not deploy, provision anything or create real users unless I say so.
  When a step needs a decision, an account, a password or an acceptance,
  ask me.
- Give me PowerShell steps one line at a time, and keep your messages short and
  plain.
- Every fact you report must come from the repository, git, the tests or me.
  Say "unverified" when you cannot check something.

## 3. Preflight (read-only; report the output)

If `jaira` is not installed:
`go install github.com/BeMuCa/jaira/cmd/jaira@v0.2.0` (it prints
`jaira version dev`, which is expected).

Linux or macOS:

```bash
git fetch origin
git switch codex/migration-safety-remediation
git pull --ff-only
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/heads/codex/migration-safety-remediation
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python tests/run.py
node --check src/astra/static/app.js
jaira validate --json
```

Windows PowerShell (one line at a time):

```powershell
git fetch origin
git switch codex/migration-safety-remediation
git pull --ff-only
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/heads/codex/migration-safety-remediation
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe tests\run.py
node --check src\astra\static\app.js
jaira validate --json
```

Expect `Ran 680 tests` and `OK` (about 6 to 11 minutes). Node must be
installed, or the UI driver tests are skipped. Then list the board by lane
with `jaira next --per-lane --json`, or from the ticket files' `status:`
lines. Expect 34 in signoff, 4 in human, 1 in todo, 15 in backlog and 15 in
done, unless I have accepted or sent back tickets since.

## 4. Your first task

Stay read-only for this task.

1. Run the preflight and report it.
2. Make a full (non-shallow) clone in a scratch folder and try merging
   `codex/migration-safety-remediation` into `origin/main` there. Report any
   conflicts and run the full suite on the merge result. Do not push anything.
   Note that `main` carries two ticket files this branch lacks (WT5TCK and
   0RSY5C); say whether WT5TCK is now covered by 3FQEKB and whether the bug in
   0RSY5C still exists.
3. Check ticket 3NT40T (Excel import hardening follow-ups) item by item against
   the code. Items 3 and 6 look already fixed by `c295bb7` and `d295d78`;
   confirm or refute each item with file and line references.
4. Write me a one-page summary: what is ready for my signoff, the merge result,
   what 3NT40T still needs, and the open questions I still have to answer
   (from `OPEN_QUESTIONS.md`), with your recommended default for each.

After that, the plan is `NEXT_STEPS.md` phase A: I sign off and answer the
questions; then you do the small review fixes (A3) and 3NT40T, then prepare
the pull request into `main` for me to merge.

---
