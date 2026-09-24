---
id: 01M3A3XCTCPXATBPQGVRMXY7BG
title: "Hosted attachments: managed upload, streaming and storage"
status: backlog
ready: true
creator: Claude
assignee: Aly Jafferani
goal: "Hosted Astra lets the App Owner attach files to a task as either an HTTPS link or an Astra-managed upload, stored privately and downloaded only through task authorization, as decided in Owner decision Items 5-16 on 6G89SJ."
context: |-
  Astra attachments today are LOCAL FILE PATH links only (task_attachments.path; service.py add_task_attachment). No bytes are stored.
  A hosted Astra cannot use local paths: a remote user's browser and the server do not share a disk.
  Aly decided the hosted design on 2026-09-19/20 as Owner decision Items 5-16, recorded as notes on ticket 6G89SJ (Attachments on tasks). Read those notes first; this ticket is that work.
  6G89SJ itself was narrowed on 2026-09-24 (Slack thread ts 1790256175.671249, 'okay proceed' ts 1790263718.995539) to fixing three review findings on the current link model; Items 5-16 were moved here.
  Items in short:
  - Item 5: two attachment types, clearly labelled: HTTPS link, and managed upload served only after task authorization. No client-local, server-local, device or UNC paths in the hosted product.
  - Items 6-7: one storage interface, two backends (private OCI Object Storage, protected private-server folder); one active backend per installation, chosen by the App Owner; a backend change is a verified (size + SHA-256) migration with rollback.
  - Item 8: 25 MB default upload cap, App Owner may raise it to a hard 250 MB ceiling; stream uploads, enforce the cap while streaming, delete partial files on failure.
  - Item 9: dangerous-type denylist (extension, declared MIME, file signature), App Owner configurable, secure defaults; mismatches rejected.
  - Items 10-11: no malware scanning for now (accepted risk); no malware warning in the UI; never label a file safe or scanned.
  - Items 12-13: any syntactically valid HTTPS URL; reject other schemes, embedded credentials, file/device schemes; Astra never fetches, probes or previews a link; open in a new tab with rel=noopener noreferrer.
  - Items 14-16: downloads are streamed through Astra with task access rechecked per request and audited (success and denial); no storage URL is exposed by default. Only the App Owner may create a permanent direct link for one attachment, after a confirmation that it bypasses task authorization; creation and revocation are audited and notify the App Owner.
  - 2026-09-20: every file and final-result mutation is App Owner-only; hosted Astra never shows or reveals local Explorer paths.
  Open questions for Aly before building: whether today's path links are migrated, hidden or kept for a desktop-only install; which backend and download mode the first hosted deployment (Oracle Cloud VM) uses.
  Known today: the current 'Copy path' button (app.js buildAttachments) and the attachment_path column in the final-results CSV export (web.py) show local paths, which conflicts with the 2026-09-20 note once hosted.
definition-of-done: "Owner Items 5-16 on 6G89SJ are each met or explicitly deferred by Aly on this ticket: HTTPS-link and managed-upload types, one storage interface with OCI and private-folder backends, 25 MB default and 250 MB hard cap enforced while streaming, dangerous-type denylist, authorized streamed downloads audited on success and denial, Owner-only audited permanent direct links; no local path is shown in hosted mode; unit and HTTP tests cover authorization, CSRF and each rejection; existing tests green."
tags:
  - astra
  - asana
blocked-by: []
related:
  - 01M2JNPRGYD7TGGSHZV16G89SJ
commits: []
created-at: 2026-09-24T16:27:54Z
updated-at: 2026-09-24T16:29:17Z
updated-by: Claude
---

# Hosted attachments: managed upload, streaming and storage

## Definition of Done

- [ ] Owner Items 5-16 on 6G89SJ are each met or explicitly deferred by Aly on this ticket: HTTPS-link and managed-upload types, one storage interface with OCI and private-folder backends, 25 MB default and 250 MB hard cap enforced while streaming, dangerous-type denylist, authorized streamed downloads audited on success and denial, Owner-only audited permanent direct links; no local path is shown in hosted mode; unit and HTTP tests cover authorization, CSRF and each rejection; existing tests green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-24 16:29 · Claude** — Filed by Claude 2026-09-24 under Aly's exclusive write lock #4 while fixing 6G89SJ. Nothing here is started; it waits in backlog for Aly to answer the open questions in the context.
