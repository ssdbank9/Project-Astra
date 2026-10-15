---
id: 01M2HQJZ6KSPH67PP6746BXYJZ
title: Production security and deployment
status: backlog
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
updated-at: 2026-10-15T10:34:49Z
updated-by: Codex
outcome-what: Aly approved Codex takeover of production security and deployment planning.
outcome-why: "Prepare the deployment plan and close local security gates while keeping network exposure and deployment gated on Aly's explicit authorization."
outcome-resolves: Codex may define and verify the local pre-deployment work; hosting and any public exposure remain unverified and unauthorized.
---

# Production security and deployment

## Definition of Done

- [ ] HTTPS termination + Secure cookie enabled (ASTRA_SECURE_COOKIES already supported); a production-grade server/hosting choice; hardened headers on all responses (already partly done); a security review of the deployment; post-reboot verification; nothing exposed to a network until approved.

## Options

- [x] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-20 03:11 · Aly Jafferani** — Owner decision 2026-09-20: selected deployment is zero-dollar Oracle Always Free VM plus free DuckDNS hostname plus Caddy HTTPS. Users install no Tailscale and sign in with individual Astra accounts. No paid resource or silent upgrade is permitted.
