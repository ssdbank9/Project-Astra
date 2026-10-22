---
id: 01M2HQJZ6KSPH67PP6746BXYJZ
title: Production security and deployment
status: human
ready: true
creator: Aly Jafferani
assignee: Claude
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
updated-at: 2026-10-22T15:48:31Z
updated-by: Claude
outcome-what: "Plan step 4 done locally: deploy/ now holds the real systemd unit, Caddyfile, journald and sshd files and a read-only verify-host.sh; the runbook installs them instead of inline copies; tests/test_deploy_config.py pins loopback-only, least privilege, Secure cookies, header and body-limit parity with Astra, no secrets and LF."
outcome-why: "Copy-pasted config in a document drifts and is never tested; the files now ship with the release and fail the suite if a safety rule is broken."
outcome-resolves: "Step 4 of the 6BXYJZ plan. Full suite 1112 OK (skipped=1); 20 mutants caught; systemd-analyze verify clean and exposure 1.5 OK in WSL Ubuntu 26.04; independent review found no blockers and its findings are fixed except the Caddy admin-socket hardening, left for staging. caddy validate not run (Caddy not installed). Nothing deployed."
claimed-by: X1CarbonPC-29580
claimed-at: 2026-10-22T15:19:37Z
question: "Step 8 (synthetic staging on the Oracle Always Free VM) needs your explicit go-ahead and your Stage 0 choices (OCI region, Ubuntu version, DuckDNS name). Separately: may I install Caddy inside local WSL from Caddy's official apt repository, only to run caddy validate on deploy/caddy/Caddyfile?"
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
- [x] Prepare least-privilege, loopback-only Astra service and Caddy/TLS/logging/firewall configuration, persistent database path and secret-free operational instructions; verify templates locally.
  proof: deploy/ files + tests/test_deploy_config.py (10 tests, 20 mutants caught); WSL Ubuntu 26.04: systemd-analyze verify clean (ExecStart stubbed), exposure 1.5 OK; dash -n ok; caddy v2.11.7 validate: Valid configuration (as caddy user)
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
- **2026-10-22 15:24 · Claude** — Step 4 (local only, Aly 2026-10-22: 'do the local loopback service and Caddy config step only, no deployment or accounts'). Added deploy/ (systemd unit, Caddyfile, journald, sshd, read-only verify-host.sh, README) and tests/test_deploy_config.py; runbook stages 3/5/7/9 now install these files instead of inline copies, and the clone moved to stage 3 so stage 3 can install the ssh/journald files. Evidence: 9 tests; 20 mutants in a temp copy all caught (first run missed a secret hidden as Environment=DUCKDNS_TOKEN=..., scan fixed); WSL Ubuntu 26.04 systemd 259: systemd-analyze verify clean with ExecStart stubbed (as shipped only the missing venv path), systemd-analyze security exposure 1.5 OK; dash -n verify-host.sh ok. Not verified: caddy validate (Caddy not installed locally; installing it needs Aly's OK to download). Nothing deployed, no account, no network exposure.
- **2026-10-22 15:31 · Claude** — Independent review (read-only subagent) of step 4: no blockers. Fixed: M1 .gitattributes keeps deploy/** LF under core.autocrlf=true; M2 validate as the caddy user (runbook and verify-host) so a root-owned access log is never created; L1 runbook header sentence corrected, -Via added; L3 stage 5 rollback; L4 stages 14/15 reinstall changed deploy/ files; L5 placeholder check covers YOUR-DUCKDNS-NAME; nits: pre-release caddy refused, Waitress start-up line, header literals read from web.py, key/duckdns patterns scanned in comments too, 'up to 30 days'. Left open (README follow-up): bind Caddy admin API to a unix socket so the Astra sandbox cannot reach localhost:2019; untestable without Caddy, so it waits for the first staging host.
- **2026-10-22 15:42 · Claude** — Reassigned from Codex to Claude with Aly's instruction in chat on 2026-10-22: 'resume 6BXYJZ: do the local loopback service and Caddy config step only, no deployment or accounts'.
- **2026-10-22 15:48 · Claude** — caddy validate now run (Aly approved installing Caddy in local WSL from Caddy's official apt repo, 2026-10-22). Caddy v2.11.7 in WSL Ubuntu 26.04; its service stopped and disabled right after install. deploy/caddy/Caddyfile with <name> filled in: 'Valid configuration' as the caddy user; caddy fmt finds nothing to change; adapted JSON listens :443, upstream 127.0.0.1:8765, max_size 6000000, deferred headers deleting Server and Via, log file roll 10 MB x10 for 30 days. Unedited <name> placeholder is refused ('subject does not qualify for certificate'). Validation created /var/log/caddy/astra-access.log owned by caddy, confirming review finding M2; the empty test log was removed.
