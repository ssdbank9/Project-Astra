# Open questions for Aly

Each question says what is undecided, why it matters, and a recommended
default. "Go with your defaults" is a valid answer to any of them. The first
five matter most, because they block phase A work or the server move.

---

## The five that matter most

### Q1. Should reviewers and approvers also exclude the Chairman and project viewers?

- **Today:** the Chairman and viewers can be picked as reviewers and approvers.
  Lock #13 treated reviewing as "not receiving work". A designated approver may
  file Owner requests, so the Chairman as an approver can, for example, ask for
  a task to be put on hold (review 13b I1).
- **Why it matters:** it is the one place where the Chairman can still start a
  change to someone's work.
- **Recommended default:** keep both as reviewers (reviewing is oversight). As
  approvers, allow the Chairman and viewers to request acceptance of a
  submission only, not holds, reopens or schedule decisions. If that feels too
  fine-grained, the simpler default is to leave everything as it is today.

### Q2. PR #4: what extra work, and how should it reach `main`?

- **Today:** PR #4 (Excel import, draft, head `5adec82`) has been held since
  2026-09-23 for "more work"; on 2026-09-25 you said to skip it for now. The
  extra work was never named. This branch already contains all of PR #4.
- **Recommended default:** treat ticket 3NT40T (Excel import hardening
  follow-ups, already in todo) as the extra work and do it on this branch.
  Then merge PR #4 as it is (or close it as superseded), and open one pull
  request from `codex/migration-safety-remediation` into `main`. You merge each
  pull request yourself.

### Q3. Who may reopen a closed project (Z72D79)?

- **Today:** a closed project cannot be reopened at all.
- **Recommended default:** any owner, primary or secondary, the same as closing,
  with a required reason, recorded in history and notified to the other owners.
  This matches your 2026-09-24 rule that secondary owners have the same project
  rights as the primary.

### Q7. Server basics: region, Ubuntu version and DuckDNS name

- **Needed for:** phase D. The 2026-09-20 handoff lists these as open setup
  values.
- **Recommended default:** your tenancy's home region; Ubuntu 24.04 LTS (Astra
  needs Python 3.11 or newer); a short DuckDNS name you are happy for users to
  see, for example `astra-<something>.duckdns.org`.

### Q8. Password change at first sign-in, and changing your own password

- **Today:** only owners set passwords; nobody is asked to change a temporary
  password; members cannot change their own. The 2026-09-20 sharing plan lists
  a forced first-login change as a gate before inviting users.
- **Recommended default:** build both before inviting anyone: a new account (or
  one an owner reset) must choose a new password at first sign-in; every user
  can change their own password by typing the current one; 8-character minimum;
  still no lockout.

---

## Development (phase A)

### Q4. Should settings changes notify the other owners, or only be recorded (Z72D79)?

- **Recommended default:** record only, in history. On 2026-09-24 you said
  reviewer-change notices were not needed; the same reasoning keeps the Inbox
  quiet here. Reopening a project is the exception: notify, like closing.

### Q5. Where should app-wide settings history appear (Z72D79)?

- **Covers:** the entity active flag and the import template settings.
- **Recommended default:** a "Settings history" list on the People and access
  screen, under the owner-access history; project settings (working days,
  holidays, budget, entities) appear in that project's Activity tab.

### Q6. Fix the JPEBCM gap now?

- **Today:** re-filing a project to entities that no longer include its primary
  entity leaves the old primary set, so the project rolls up to an entity it is
  not linked to (review, Medium).
- **Recommended default:** yes, a small ticket: clear the primary (the project
  shows as Unassigned, as your 2026-09-21 rule says) and add a test.

### Q13. Close backlog tickets that the build has overtaken?

- RWMRKM (My Work) and 4G3NY0 (month calendar) were built in FKVHH8; S1C6PN
  (workload) was dropped by you; X8FNA5 (shell) was built as Gate 2 slices 1-7;
  A48JEX (board by sections) was built as a status board instead.
- **Recommended default:** move them to done (or abandon S1C6PN) with a note
  pointing at the tickets that delivered them. Only you can do that for tickets
  assigned to you.

### Q14. Which Gate 2 leftovers go in before launch?

- Divide the board by entity; filter the project Activity tab; "since Monday"
  deltas on Home; live refresh of lock badges; a Manage entry in the left rail.
- **Recommended default:** before launch: the Activity filter, entity
  swimlanes, the Manage entry, and a light live refresh while the Board is open.
  After launch: "since Monday" deltas (the UX research lists them as later).

### Q15. Who runs the real-device and screen-reader check, and on what?

- **Recommended default:** you, with a 20-minute checklist from Codex, on your
  own phone, one tablet if available, and NVDA (free) on Windows.

### Q16. Should Unrated tasks keep sorting below Low?

- **Today:** yes, with an amber badge (QY0WG2).
- **Recommended default:** keep it.

### Q17. May an owner keep leaving "on hold", "changes requested" or "reopened" through an ordinary edit?

- **Today:** yes, with a reason, because no dedicated release action exists;
  managers cannot (open since the 2026-09-22 review).
- **Recommended default:** keep it; it is audited.

### Q18. Which branch after this one is merged?

- **Today:** your rule is "only `codex/migration-safety-remediation`".
- **Recommended default:** after the merge, `main` is the release branch and
  each phase gets one short-lived branch (for example
  `codex/phase-b-hardening`), merged by pull request that you approve.

### Q23. What to do with `claude/review-report-2026-09-22` and old branches?

- That branch holds tickets EBSJ4J, N4KQBB, T81ZV6, GDPJD1, VTEM1V, JE5W89, some
  of them overtaken (per the memory notes). `claude/hs3jry-complete` is merged.
- **Recommended default:** copy the still-relevant tickets (VTEM1V template
  download cap, JE5W89 regional CSV dates, GDPJD1 contrast if not fixed) onto
  the main board, then delete the merged branches. Nothing is deleted without
  your word.

### Q24. Gantt: may a successor start on the predecessor's due day?

- **Today:** yes; a link counts as broken only when the successor starts
  before the predecessor's due day (review 12b I1).
- **Recommended default:** keep it.

---

## Production and deployment (phases B to D)

### Q10. Backup: how does the server reach Object Storage, and which encryption tool?

- **Recommended default:** a write-only pre-authenticated request to a private
  bucket, with lifecycle rules for the 7/4/3 retention; encryption with `age`
  to a key only you hold (gpg is fine if you prefer it).

### Q11. Rate-limit sign-in at the proxy?

- **Today:** no limit, by your choice (no lockout). The README says a hosted
  deployment should rate-limit in front of Astra.
- **Recommended default:** yes, gently: fail2ban on Caddy's log bans one
  address for 15 minutes after 20 wrong passwords in 10 minutes. No account is
  ever locked.

### Q12. Version number for the first release?

- **Recommended default:** `0.2.0`, tagged `v0.2.0` on `main`, with a
  `CHANGELOG.md`.

### Q20. How big will the pilot be?

- **Needed for:** the performance test in phase B.
- **Recommended default:** test at 20 projects, 3,000 tasks, 30 users and a
  year of history, which is well above a small pilot.

### Q21. Data residency and the privacy note

- **Needed for:** the privacy note and the region choice.
- **Recommended default:** data stays in your Oracle home region; the note names
  you as the person responsible, lists what is stored and for how long, and says
  how to ask for removal.

### Q22. Keep Python's built-in web server for the pilot?

- **Today:** `astra serve` uses `ThreadingHTTPServer`, meant for local use.
- **Recommended default:** keep it behind Caddy for the pilot, bound to
  `127.0.0.1`, after adding request timeouts in phase B. Revisit if the pilot
  grows. This keeps Astra free of dependencies.

### Q25. Keep the repository public once the site is live?

- **Today:** public, by your 2026-09-21 decision.
- **Recommended default:** keep it public; no secret ever goes into git. Make it
  private if you would rather not show the code.

---

## Distribution (phases E and F)

### Q9. Support and feedback channel

- **Recommended default:** one channel you already use with the group (for
  example a group chat or one email address), linked from a "Help" item in the
  account menu.

### Q19. First users and timing

- **Recommended default:** a trial with synthetic data first, then three to five
  real users on one real project for two weeks, then the rest.
