Dated review reports (adversarial, security, design) written against specific commits or pull requests.
One Markdown file per review, named `YYYY-MM-DD-<kind>.md`; no probe scripts, binaries or user data.

## Status after fixes (2026-09-22)

The high and medium findings of `2026-09-22-adversarial-review.md` that were
assigned to the two feature branches are fixed: on `claude/gantt-steps` in
7fcf863 and dc7aa0f (GF-1, GF-2, GF-3, GF-6, GF-7, GF-8, GF-10, GF-16, DTJ-06;
126 tests green) and on `claude/excel-import` in 95d20fd and b0149d0 (AS-1,
AS-2, AS-7, DI-2 to DI-6, XI3-01, XI3-02, XI3-03, XI3-05, XI3-07, XI3-09, MS-1
to MS-7, DTJ-03, DTJ-08, DTJ-10, DTJ-17; 188 tests green, 18 regression tests).
The remaining medium findings are Jaira tickets in todo: EBSJ4J (AS-3), N4KQBB
(AS-4), T81ZV6 (DI-1), GDPJD1 (GF-14 with MS-9), VTEM1V (XI3-04), JE5W89
(XI3-06); DTJ-04 is covered by WT5TCK on PR #3. Intended merge order: PR #3,
PR #2, PR #4. The report itself is left as written; `ASTRA_HANDOFF_2026-09-22.md`
at the repository root carries the current state.
An independent regression pass (report
https://claude.ai/artifact/XVS7iGTN3VNgychQJNt7cD) followed on 2026-09-23; see
"Status as of 2026-09-23" at the top of `ASTRA_HANDOFF_2026-09-22.md`.
