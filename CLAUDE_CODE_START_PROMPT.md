# Claude Code start prompt — Astra

Paste the block below into Claude Code.

```text
You are taking over the Astra project tracker from the private GitHub repository `ssdbank9/Project-Astra`. Work from the repository root on your current platform. The historical Windows source path was `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`, but that path is not required in a cloud container.

Read CLAUDE_CODE_HANDOFF_2026-09-21.md completely and follow it as the current execution handoff. Then read the active AGENTS.md instructions and every document listed under the handoff's authoritative-source section.

Before editing, report the live results of:
- jaira next --per-lane --json
- jaira resume --json
- jaira show HS3JRY --for-lane in-progress --json
- git status --short from this standalone repository
- the exact diff for the HS3JRY files
- the platform-appropriate project-venv test command (`.venv/bin/python tests/run.py` on Linux/macOS or `.venv\Scripts\python.exe tests\run.py` on Windows)
- node --check src\astra\static\app.js

Preserve all existing and unrelated changes. Start from branch `hs3jry-handoff`, where the in-progress HS3JRY implementation and its Jaira state are committed for transfer. Reconcile the stale README.md and CONTEXT.md authorization wording, verify the full Owner/Chairman/Manager/Viewer matrix, rerun all checks, record Jaira proof, and move/commit only as permitted by the lane rules. Do not move anything out of human or signoff.

The design decisions are closed. Use the approved defaults and ordered roadmap in the handoff. Ask Aly Jafferani only for a genuinely new choice, credential, external action or risk acceptance. Do not deploy, expose a server, create real users, ingest private sources, send external notifications, publish real files or configure external AI without explicit authorization.
```
