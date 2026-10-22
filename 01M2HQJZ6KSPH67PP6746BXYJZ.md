---
id: 01M2HQJZ6KSPH67PP6746BXYJZ
title: Production security and deployment
status: in-progress
ready: true
creator: Aly Jafferani
assignee: Codex
goal: "Harden and deploy the tracker for real multi-user use behind proper authentication, transport security, and hosting."
context: |-
  Astra tracker, section 11 gaps "Production security: Missing" and "Deployment/persistence: Unverified and unauthorized". Today it is a loopback dev server; login throttling, secure-cookie flag, and static security headers already exist.
  GATED on section 15 decisions: hosting, authentication provider, HTTPS termination, data residency, protected storage, deployment secrets. Do NOT expose to any network (incl. Tailscale) or deploy without explicit owner authorization.
definition-of-done: HTTPS termination + Secure cookie enabled (ASTRA_SECURE_COOKIES already supported); a production-grade server/hosting choice; hardened headers on all responses (already partly done); a security review of the deployment; post-reboot verification; nothing exposed to a network until approved.
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:43Z
updated-at: 2026-10-22T15:19:37Z
updated-by: Claude
outcome-what: "Finished the evidence-based scope and eight-step plan; local implementation work is authorized, while staging and exposure remain separately gated."
outcome-why: "The existing code already has several protections, so the work must target verified gaps and prove local readiness before any cloud action."
outcome-resolves: "Moves 6BXYJZ into implementation with local security, operator-preparation, regression and independent-review steps; no deployment authorization is inferred."
claimed-by: X1CarbonPC-29580
claimed-at: 2026-10-22T15:19:37Z
---

# Production security and deployment

## Definition of Done

- [ ] HTTPS termination + Secure cookie enabled (ASTRA_SECURE_COOKIES already supported); a production-grade server/hosting choice; hardened headers on all responses (already partly done); a security review of the deployment; post-reboot verification; nothing exposed to a network until approved.

## Options

- [x] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reconcile the selected Oracle Always Free, DuckDNS and Caddy design with all existing hardening, backup, release and open-decision evidence; separate proven local controls from unverified hosted controls.
  proof: 6BXYJZ plan checklist records evidence reconciliation and authorization boundaries
- [x] Inspect startup, HTTP security, reverse-proxy trust, cookie flags, logging, storage paths and operator files; record concrete deployment risks and affected tests.
  proof: 6BXYJZ plan checklist records source/config audit scope
- [x] Repair any confirmed local security or deploy-configuration gap without exposing the service; add targeted tests for each changed boundary and role.
  proof: src/astra/__main__.py: CLI rejects non-IPv4-loopback before _run; tests/test_core.py: test_serve_refuses_non_loopback_hosts_before_starting and test_serve_allows_the_documented_loopback_host
- [ ] Prepare least-privilege, loopback-only Astra service and Caddy/TLS/logging/firewall configuration, persistent database path and secret-free operational instructions; verify templates locally.
  proof: 6BXYJZ plan checklist records loopback service and proxy prep
- [x] Reconcile the deployment runbook with the current app and approved decisions; verify vendor commands against official sources when needed and mark unexecuted steps clearly.
  proof: docs/handoff/DEPLOYMENT_RUNBOOK.md: DuckDNS secret handling, Caddy version/validation, HSTS sequence and Q22 gate; official vendor links; docs/handoff/OPEN_QUESTIONS.md: Q22
- [x] Run focused security/regression checks, the full Windows suite, line-ending and private-file checks; obtain an independent review and fix confirmed findings.
  proof: tests/run.py: Ran 917 tests in 1005.884s, OK (skipped=1); independent read-only reviewer found no remaining confirmed defect
- [x] Prepare the staged deployment checklist and identify remaining Aly-only values (OCI region, Ubuntu version, DuckDNS name, key/credentials); stop before account access, provisioning or network exposure until separately authorized.
  proof: docs/handoff/DEPLOYMENT_RUNBOOK.md: Stage 0 owner choices and stop-before-provisioning rule; docs/handoff/NEXT_STEPS.md: deployment stages and launch gates
- [ ] After separate explicit staging authorization, deploy synthetic data only, verify HTTPS/Secure cookies, firewall, persistence, backup/restore and post-reboot recovery; report evidence and ask Aly for any later real-user launch decision.
  proof: 6BXYJZ plan checklist records separately authorized synthetic staging and reboot/restore verification

## Progress
- **2026-09-20 03:11 · Aly Jafferani** — Owner decision 2026-09-20: selected deployment is zero-dollar Oracle Always Free VM plus free DuckDNS hostname plus Caddy HTTPS. Users install no Tailscale and sign in with individual Astra accounts. No paid resource or silent upgrade is permitted.
- **2026-10-15 10:35 · Codex** — Repository review: the 2026-09-20 owner decision already selects an Oracle Always Free VM, DuckDNS, Caddy HTTPS and individual Astra accounts, with no paid resource or silent upgrade. The deployment runbook is a historical, unexecuted template. Q7 still leaves the OCI home region, Ubuntu version and DuckDNS name to Aly; staging/provisioning and real-user deployment require separate explicit authorization. Source shows the server defaults to 127.0.0.1, ASTRA_SECURE_COOKIES adds Secure to the session cookie, and the handler already sets CSP, X-Frame-Options and Referrer-Policy; these code facts do not prove a hardened live proxy, host firewall, storage permissions, provider availability, reboot recovery or restore drill. Options: (1) follow the selected Oracle/DuckDNS/Caddy path after local hardening, release and recovery evidence, retaining the zero-cost limit; (2) choose another host or managed identity/storage, which changes Aly's recorded decision and may introduce cost/migration work; (3) remain local, safest operationally but does not meet hosted multi-user goal. Recommendation: option 1, but treat this ticket as gated preparation until Aly chooses remaining host values and explicitly authorizes staging. No code, accounts, credentials, provisioning or network exposure are included in this step.
- **2026-10-15 10:54 · Codex** — New launch gate from official primary-source review: Python's current http.server documentation explicitly says this server is not recommended for production and only implements basic security checks (https://docs.python.org/3/library/http.server.html). OPEN_QUESTIONS.md Q22 currently proposes retaining it behind Caddy, but labels that as a recommendation rather than Aly's decision. Waitress's official documentation describes it as a production-quality, pure-Python WSGI server for Unix and Windows (https://docs.pylonsproject.org/projects/waitress/en/stable/); Astra currently uses BaseHTTPRequestHandler and would need a substantial WSGI adaptation plus a runtime dependency. Recommendation: retain the built-in server for local development, adapt the hosted entry point to WSGI/Waitress, and keep it loopback-only behind Caddy. Aly must choose this architecture or explicitly accept the documented built-in-server risk before hosted launch. Current local source/runbook changes add a CLI loopback guard, document the gate, remove the DuckDNS token from curl process arguments using a root-only curl config, and state the Caddy 2.10+ experimental request_body requirement. No account, staging or network action is authorized.
- **2026-10-15 10:58 · Codex** — 2026-10-15 · Independent read-only review of the current loopback guard, tests and runbook found no concrete defect; reviewer confirmed hosted-server Q22 blocks ready status. Test suite rerunning now. The guard is deliberately at the public astra serve --host CLI boundary and rejects non-IPv4-loopback binds before server startup. No hosting or network action was taken.
- **2026-10-15 12:42 · Codex** — Aly selected Waitress on 2026-10-15. The hosted WSGI adapter now initializes/migrates SQLite before Waitress listens, rejects non-loopback binds at the CLI, ignores forwarded client-address headers, limits request sizes and channel inactivity, and filters WSGI-forbidden hop-by-hop response headers. Stage 5 now installs declared dependencies. Independent read-only review found no remaining source defect; Caddy is unavailable locally, so its binary validation is unverified. Fresh full suite: 917 tests in 1005.884s, OK (skipped=1). No cloud, credentials, staging, HTTPS, reboot or hosted recovery checks were performed. Before staging, complete Caddy validation if available, obtain other LLM reviews, collect Aly-only host values, and request separate staging authorization.
