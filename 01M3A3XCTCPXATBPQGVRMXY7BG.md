---
id: 01M3A3XCTCPXATBPQGVRMXY7BG
title: "Hosted attachments: managed upload, streaming and storage"
status: in-progress
ready: true
creator: Claude
assignee: Claude
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
blocked-by: []
related:
  - 01M2JNPRGYD7TGGSHZV16G89SJ
commits: []
created-at: 2026-09-24T16:27:54Z
updated-at: 2026-11-09T14:25:36Z
updated-by: Claude
claimed-by: X1CarbonPC-26956
claimed-at: 2026-11-08T18:40:53Z
outcome-what: "Slice 1 (HTTPS links, private-folder uploads with cap and denylist, audited streamed downloads, paths hidden when hosted) pushed as 18c4e54; slices 2-4 not started"
outcome-why: "Aly chose delivery in slices on 2026-11-08; the ticket stays in progress until slices 2-4 land or Aly defers them"
outcome-resolves: nothing yet; DoD item 1 stays open
---

# Hosted attachments: managed upload, streaming and storage

## Definition of Done

- [ ] Owner Items 5-16 on 6G89SJ are each met or explicitly deferred by Aly on this ticket: HTTPS-link and managed-upload types, one storage interface with OCI and private-folder backends, 25 MB default and 250 MB hard cap enforced while streaming, dangerous-type denylist, authorized streamed downloads audited on success and denial, Owner-only audited permanent direct links; no local path is shown in hosted mode; unit and HTTP tests cover authorization, CSRF and each rejection; existing tests green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [ ] Slice 1: HTTPS links, private-folder uploads (25 MB, denylist), audited streamed downloads, path links hidden when hosted
- [~] Slice 2: App Owner-configurable cap (to 250 MB) and denylist
- [ ] Slice 3: Owner-only audited permanent direct links (Items 15-16)
- [ ] Slice 4: OCI Object Storage backend and verified backend migration with rollback (Items 6-7)

## Progress
- **2026-09-24 16:29 · Claude** — Filed by Claude 2026-09-24 under Aly's exclusive write lock #4 while fixing 6G89SJ. Nothing here is started; it waits in backlog for Aly to answer the open questions in the context.
- **2026-11-08 18:39 · Claude** — 2026-11-08 Aly's answers (chat with Claude), quoted from his picks: path links 'Hide when hosted' (desktop install keeps them, nothing deleted); storage 'Private folder on the VM' first, OCI later behind the same interface; downloads 'Through Astra only' (direct links Items 15-16 in a later slice); delivery 'In slices'. Slice 1 = HTTPS links + private-folder uploads (25 MB default cap, denylist) + audited streamed downloads + no local paths when hosted. Note: Waitress and Caddy currently cap request bodies at 6 MB (HANDOFF_2026-10-24 2.2), so the upload route needs its own limit.
- **2026-11-09 05:52 · Claude** — Slice 1 review (independent subagent, 2026-11-09): no blocker. Fixed from it: final-results view/CSV name a file result and link a link result (CASE by kind); import template export carries path links only and none without roots (service _template_prefill, importer existing_attachments); restore runbook now restores the uploads tar; denylist gains .xll .sct .wsc .ws .ps1xml .psc1 .msh* .vb .desktop .library-ms .search-ms .diagcab; .zip accepts PK\x07\x08; open_task_file closes the handle if the audit insert fails; a storage OSError after a committed removal is logged (astra.attachments), not raised. Left as nits: Caddy 25MiB equals Astra's limit so a body one byte over gets Caddy's 413 (JS pre-check normally prevents it); no sweeper for incoming/*.part after a process kill; validate_https_url accepts odd hosts like https://-/ by design (syntax only).
- **2026-11-09 05:52 · Claude** — Mutation check 2026-11-09: 30 slice-1 guards + 7 review-fix guards each removed in a throwaway copy, every one fails a test. Two tests were tightened to get there: the overlong-chunk test asserts the message, and the non-file download test patches storage out so the service must refuse by kind. Removing the EOF check in checked_chunks makes the read loop infinite, so the mutation script treats a timeout as caught.
- **2026-11-09 14:25 · Claude** — Slice 2 design (2026-11-09): one-row table attachment_settings (schema v24) holds the App Owner's upload limit in bytes (SQL CHECK 1..262144000 = 250 MB) and two JSON lists of ADDITIONS to the denylist (extensions, declared media types). The built-in denylist and the signature checks always apply; the owner can add, never remove (Item 9 'secure defaults'; if Aly wants a built-in type allowed, that is a new decision). attachment_storage.UploadPolicy carries limit + extras into check_upload/checked_chunks; service.upload_policy() reads it per upload so a change applies to the next upload without a restart. Owner-only get/update (/api/attachment-settings GET and PUT), audited as attachment_settings_changed via _app_setting_event like the import template config. Waitress and Caddy admit the 250 MB ceiling on the upload route; Astra refuses over the configured limit before reading a byte (friendly 413), which also closes the slice-1 nit about Caddy's 413 at exactly 25 MiB. task_detail carries upload_limit_bytes so the upload form shows the real limit. Admin dialog gets an Attachments section for owners.
