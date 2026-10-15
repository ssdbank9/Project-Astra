---
id: 01M2HQJZ6KSPH67PP6746BXYJZ
title: Production security and deployment
status: pre-process
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
updated-at: 2026-10-15T10:42:00Z
updated-by: Codex
outcome-what: "Converted the approved deployment direction and verified local controls into a staged plan with a clear stop before staging."
outcome-why: "Local source preparation can proceed, while region, hostname and any hosting action remain App Owner-controlled."
outcome-resolves: "The ticket now has an ordered plan covering local security review, configuration/tests, independent review and an authorization-gated staging/reboot/restore verification."
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
  proof: 6BXYJZ plan checklist records confirmed-gap repair and regression scope
- [x] Prepare least-privilege, loopback-only Astra service and Caddy/TLS/logging/firewall configuration, persistent database path and secret-free operational instructions; verify templates locally.
  proof: 6BXYJZ plan checklist records loopback service and proxy prep
- [x] Reconcile the deployment runbook with the current app and approved decisions; verify vendor commands against official sources when needed and mark unexecuted steps clearly.
  proof: 6BXYJZ plan checklist records runbook refresh and source verification
- [x] Run focused security/regression checks, the full Windows suite, line-ending and private-file checks; obtain an independent review and fix confirmed findings.
  proof: 6BXYJZ plan checklist records focused/full tests and independent review
- [x] Prepare the staged deployment checklist and identify remaining Aly-only values (OCI region, Ubuntu version, DuckDNS name, key/credentials); stop before account access, provisioning or network exposure until separately authorized.
  proof: 6BXYJZ plan checklist records Aly-controlled values and hard stop
- [x] After separate explicit staging authorization, deploy synthetic data only, verify HTTPS/Secure cookies, firewall, persistence, backup/restore and post-reboot recovery; report evidence and ask Aly for any later real-user launch decision.
  proof: 6BXYJZ plan checklist records separately authorized synthetic staging and reboot/restore verification

## Progress
- **2026-09-20 03:11 · Aly Jafferani** — Owner decision 2026-09-20: selected deployment is zero-dollar Oracle Always Free VM plus free DuckDNS hostname plus Caddy HTTPS. Users install no Tailscale and sign in with individual Astra accounts. No paid resource or silent upgrade is permitted.
- **2026-10-15 10:35 · Codex** — Repository review: the 2026-09-20 owner decision already selects an Oracle Always Free VM, DuckDNS, Caddy HTTPS and individual Astra accounts, with no paid resource or silent upgrade. The deployment runbook is a historical, unexecuted template. Q7 still leaves the OCI home region, Ubuntu version and DuckDNS name to Aly; staging/provisioning and real-user deployment require separate explicit authorization. Source shows the server defaults to 127.0.0.1, ASTRA_SECURE_COOKIES adds Secure to the session cookie, and the handler already sets CSP, X-Frame-Options and Referrer-Policy; these code facts do not prove a hardened live proxy, host firewall, storage permissions, provider availability, reboot recovery or restore drill. Options: (1) follow the selected Oracle/DuckDNS/Caddy path after local hardening, release and recovery evidence, retaining the zero-cost limit; (2) choose another host or managed identity/storage, which changes Aly's recorded decision and may introduce cost/migration work; (3) remain local, safest operationally but does not meet hosted multi-user goal. Recommendation: option 1, but treat this ticket as gated preparation until Aly chooses remaining host values and explicitly authorizes staging. No code, accounts, credentials, provisioning or network exposure are included in this step.
