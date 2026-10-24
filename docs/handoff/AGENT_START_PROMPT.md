# Agent start prompt — Project Astra (2026-10-24)

This is the current pick-up prompt. It is the same text as section 11 of
[HANDOFF_2026-10-24.md](HANDOFF_2026-10-24.md), which explains the state it
refers to. The September prompt this file used to hold is in git history
(`git log -p -- docs/handoff/AGENT_START_PROMPT.md`).

Aly: paste everything between the two lines as the first message to the next
agent (Claude on the new account, Codex or another model).

---

You are taking over Project Astra, a private, owner-hosted project tracker: Python (standard library plus Waitress), one SQLite database, plain HTML/CSS/JavaScript, no framework or build step. I am Aly Jafferani, the App Owner and the only person who makes decisions.

- Repository: https://github.com/ssdbank9/Project-Astra.git (public). Branch: `codex/migration-safety-remediation`.
- My Windows checkout: `C:\Users\Aly Jafferani\Documents\ChatGPT\Project-Astra`. Never use `...\ChatGPT\New project`.
- The current handover is `docs/handoff/HANDOFF_2026-10-24.md`. It was written at commit `a8be8d2` plus the handover commit. If the head you pull is newer, other agents have worked since: read `git log a8be8d2..HEAD` and the ticket notes, and trust them over the handover.

Before anything else:

1. Read `AGENTS.md`, then `docs/handoff/HANDOFF_2026-10-24.md`, then `docs/handoff/DECISIONS_LOG.md`, then `pending-global-mistakes.md` (and `C:\Users\Aly Jafferani\.codex\mistakes.md` if it exists).
2. Run read-only checks and report the output: `git fetch origin`, `git pull --ff-only`, `git status --short --branch`, `git rev-parse HEAD`, `git ls-remote origin refs/heads/codex/migration-safety-remediation`, `.venv\Scripts\python.exe tests\run.py` (expect at least 1112 tests and OK), and the board by lane (`jaira list --json`; the tickets are under the `tickets` key).
3. Tell me, in a few short lines:
   - the head you pulled;
   - the test result;
   - the board counts by lane;
   - anything that changed since `a8be8d2`;
   - the first item from section 8 of the handover that is still open.

Rules, in short (AGENTS.md wins if this differs):
- Pull before work. Before every push, check `git ls-remote` that origin has not moved. Never force-push, rebase or amend published history.
- Stage only your own files; never `git add .` or `-A`. LF line endings only.
- Run the full suite before every push and report the exact result and the final SHA.
- Get an independent review of every change from someone who did not write it. For guards, prove a test fails when the guard is removed. For UI work, check it in a browser.
- jaira:
  - Set `JAIRA_USER` to your own agent name, never to me.
  - Never run `jaira init` or any `--force`.
  - Move tickets into `human` or `signoff` only, never out of them.
  - The ticket file rides in the same commit as its code.
- Do not deploy, provision, create accounts, use credentials or turn on external AI unless I say so. Ask me for any decision, account, password or acceptance.
- Keep messages short and plain. Give me PowerShell commands one line at a time, and remind me to type `powershell` first if my window is Command Prompt.
- Every fact must come from the repository, git, the tests or me. Say "unverified" otherwise.

Do not start any implementation until I answer your report.

---
