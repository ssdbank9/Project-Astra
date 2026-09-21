# Assessor reaches Gemini by API but Claude and Codex by subscription CLI

The AI first-pass uses a provider-swappable **Assessor** (Claude, Codex, or Gemini).
The App Owner holds a **Gemini API key** but only **monthly subscriptions** — not API
keys — for Claude and Codex. So the Assessor reaches **Gemini via its API** and reaches
**Claude and Codex via their local subscription CLIs** (`claude -p`, `codex exec`); one
Assessor interface hides which transport ran.

## Status

accepted

## Considered options

- **API for all three** — rejected: there are no Claude/Codex API keys to call.
- **CLI for all three** — rejected: Gemini's CLI isn't installed, and its API is the more
  turnkey, structured-output path (EPO already drives it).
- **Mixed transport (chosen)** — Gemini API + Claude/Codex CLI.

## Consequences

- The three adapters are deliberately **not uniform**: one is an HTTP/API adapter, two are
  subprocess adapters over a CLI. That asymmetry is expected, not a smell.
- The CLI adapters depend on `claude`/`codex` being installed and logged in on the host;
  a missing/expired login degrades that provider, not the whole Assessor.
- If the App Owner later obtains Claude/Codex API access, that is a **new adapter behind the
  same interface**, not a rewrite.
