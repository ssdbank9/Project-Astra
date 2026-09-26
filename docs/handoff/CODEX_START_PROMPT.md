# Codex start prompt — Project Astra (2026-09-26)

Aly: paste everything between the two lines below as your first message to
Codex. It assumes the handoff pack is committed under `docs/handoff/` on the
branch; if it lands somewhere else, change the paths in the first list.

---

You are taking over Project Astra from Claude. Astra is a private, owner-hosted
project tracker: Python standard library only, one SQLite database, a plain
HTML/CSS/JavaScript front end. I am Aly Jafferani, the App Owner and the only
person who makes decisions. Work only from GitHub, never from an old local copy.

- Repository: https://github.com/ssdbank9/Project-Astra.git (public)
- Branch: `codex/migration-safety-remediation`
- Expected head: `0b90ceb4a8677ef331f1b12f8cbc5ee4c39f9f33`, or a later commit
  that adds only the handoff pack and retires the write lock protocol
- Schema v20; the full suite was `Ran 676 tests`, `OK`
- My Windows checkout: `C:\Users\Aly Jafferani\Documents\ChatGPT\Project-Astra`.
  Never use `...\ChatGPT\New project`; it is an old, unrelated repository.

## 1. Read these first, in this order

1. `docs/handoff/README.md` (the index of the pack)
2. `docs/handoff/HANDOFF_2026-09-26.md` (state, setup, rules, architecture,
   permissions, board, gaps, risks)
3. `docs/handoff/NEXT_STEPS.md` (phases A to F)
4. `docs/handoff/OPEN_QUESTIONS.md` and `docs/handoff/DECISIONS_LOG.md`
5. `AGENTS.md`, `CLAUDE.md` and `pending-global-mistakes.md`. On my Windows
   machine also read `C:\Users\Aly Jafferani\.codex\mistakes.md` if it exists.
6. `README.md` (current behaviour, schema upgrade notes)
7. `docs/handoff/DEPLOYMENT_RUNBOOK.md` only when we reach phase D.

## 2. Rules you must follow

- Work only on `codex/migration-safety-remediation` unless I name another
  branch. Pull before you read or edit.
- Never force-push. Never rebase, amend or reset published history. Never
  reset, clean or discard someone else's work.
- The exclusive write lock protocol was retired by Aly on 2026-09-26
  (Slack ts 1790403410.978849). Lock #14 was the last.
- Right before a normal push, run
  `git ls-remote origin refs/heads/codex/migration-safety-remediation` and check
  that it still shows the head you pulled. If origin moved since you pulled,
  pull (merge), re-run the tests, then push normally.
- After each push, report the final SHA, the files changed, the tickets and
  their lanes, and the tests run with the exact result.
- jaira: never run `jaira init`, never use `--force`, never set `JAIRA_USER` to
  me, never edit `.jaira/tickets/` by hand. You may move a ticket into `human` or
  `signoff`, never out of `human`, `signoff` or `done`. The ticket file rides in
  the same commit as the code. Ask me before taking over any ticket assigned to
  me, every time. In a cloud container keep ticket ref sync off:
  `~/.jaira/settings.json` = `{"remote": "nosync"}` and
  `export JAIRA_NO_SNAPSHOT=1`.
- Get an independent adversarial review (a separate read-only reviewer, revert
  experiments, a browser check for UI work) before you call anything ready.
- Never commit secrets, `.env` files, keys, a live SQLite database, venvs or
  caches. The repository is public.
- Keep files LF. Before pushing, check the diff has no CR bytes
  (`git diff --check` and a search for `\r`).
- Keep the front end lean: no framework, no build step, no CDN, no inline
  `style=` attributes, colours as `:root` tokens.
- Do not deploy, provision anything, expose the server, create real users, send
  external notifications or turn on external AI unless I say so. I do every
  account and credential step myself.
- Never merge a pull request unless I tell you to for that pull request.
- Give me PowerShell steps one line at a time, and keep your messages short and
  plain.
- Every fact you report must come from the repository, git, the tests or me.
  Say "unverified" when you cannot check something.

## 3. Preflight (read-only; report the output)

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

Expect `Ran 676 tests` and `OK` (about 11 minutes). Node must be installed, or
the UI driver tests are skipped. Then list the board by lane with
`jaira next --per-lane --json`, or from the ticket files' `status:` lines. Expect 33 in
signoff, 4 in human, 1 in todo, 15 in backlog and 15 in done.

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
