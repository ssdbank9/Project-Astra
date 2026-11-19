# Astra privacy note

> **Draft for Aly's approval (2026-11-19). Not yet published.** Items marked
> **[ALY]** are Aly's to decide (`OPEN_QUESTIONS.md` Q21). Every statement below
> was checked against the code and `deploy/` at the time of writing, and
> fact-checked by a second agent; the backup and hosting parts describe the
> deployment runbook's plan, which is not yet in place. `NEXT_STEPS.md` E6 asks
> for this note to be linked from the sign-in page; that link is not built.

Astra is a private project tracker run by **[ALY: name]** for an invited group.
It is free, has no advertising and sells nothing. **[ALY]** is responsible for
the data in it.

## What Astra stores

- **About you:** your name, your email address, your role, whether your account
  is active, and when and by whom it was created. Your password is never stored:
  only a salted PBKDF2-SHA256 hash of it (600,000 rounds).
- **Your work:** the projects, tasks, notes, submissions and reviews you and
  others add, the files App Owners attach, and the history of every change (who
  did what, when and why). Refused attempts, such as trying to change something
  your role does not allow, are recorded on the task too.
- **Your account's history:** role changes, password resets and deactivation,
  with the reason given.
- **Sign-ins:** each sign-in attempt (the email typed, the time, whether it
  succeeded). Failed attempts are cleared when you next sign in, and every
  record is deleted after 90 days. A signed-in session is kept as a code that
  expires after 12 hours; Astra does not store your IP address or browser with
  it.
- **Files:** files attached to a task are kept on Astra's server
  **[ALY: or in a private storage bucket in the same Oracle account, if one is
  taken up]**.

Work, history and Inbox notices have no set deletion date: they stay for as long
as Astra runs.

Astra uses one cookie, to keep you signed in, and your browser keeps your view
preferences (such as a chosen filter) on your own device. Astra has no
analytics, no tracking and no adverts, and its pages load nothing from other
websites (even the font is served by Astra itself). Astra sends no email and
calls no outside service except the storage bucket, if one is used; no AI
service is turned on.

## Where it is kept

On a server in **[ALY]**'s Oracle Cloud account, in the **[ALY: region]**
region, reached only over HTTPS. The web server's logs keep the network address
each request came from: old access-log files are deleted after 30 days, but the
current file and the system journal can hold addresses for longer (the journal
is limited by size, not by age).

## Who can see what

- You see the projects you have been added to, their tasks and files, and part
  of each task's history, with names.
- Project managers see and edit their projects, with their full history.
- App Owners and the Chairman see every project and its full history, and the
  list of users (name, email, role, status). App Owners manage accounts and
  files, and are notified of every task change someone else makes.
- An App Owner can make a permanent direct link to an attached file; anyone
  with that link can download the file without signing in, until the link is
  revoked or the file is removed. Making and revoking a link, and each download
  through it, are recorded.

## Backups

**[ALY: confirm once the backups are running.]** The plan:

- Every night the database and the files kept on the server are backed up, on
  the server, encrypted with a key only **[ALY]** holds.
- The database backup (not the files) is also copied to a private storage
  bucket in the same Oracle account, where daily copies are kept for 7 days,
  weekly ones for 4 weeks and monthly ones for 3 months; and weekly to
  **[ALY]**'s own computer.
- Copies on the server and on **[ALY]**'s computer have no set deletion date
  yet. Files kept in a storage bucket, if one is used, are not in these backups.

Data that is corrected or removed in Astra stays in older backups until those
copies are deleted.

## Leaving, and your data

- Accounts are deactivated, not deleted: a deactivated account cannot sign in,
  and its tasks and history stay, because other people's work depends on them.
- To ask what Astra holds about you, or for an account to be deactivated or
  your details to be corrected, contact **[ALY: contact]**.
- Astra can export tasks as a spreadsheet file. There is no one-click export of
  everything about one person yet; ask **[ALY]** and it will be put together by
  hand.
