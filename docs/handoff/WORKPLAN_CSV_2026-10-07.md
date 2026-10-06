# One-project workplan CSV — W6ZSGA

Aly approved the owner workflow: download one CSV from an existing Astra
project, fill task rows in Excel, upload it, review the preview, then confirm.
The same project may contain Shared work and named alternative plans.
This feature is implemented and verified locally; owner acceptance and hosting are separate.

## Owner workflow

1. Open the project and choose **Import workplan**.
2. Choose **Download project workplan (.csv)**. Existing tasks are filled in;
   fifty spare rows have Astra-generated Task IDs. Keep the first five rows
   and existing Task IDs unchanged.
3. Fill Task, Assigned To, Start and Finish. Dates use `yyyy-mm-dd`.
   Assigned To accepts an existing eligible user's email; the uploader's
   login does not automatically assign every task to that person.
4. Optional: use another Task ID in Part of to group a step under a task.
   Use Task IDs in Predecessors for finish-to-start links; separate multiple
   IDs with semicolons. Grouping does not create a dependency or merge tasks.
   Type accepts Task, Milestone or Action item. Plan defaults to Shared;
   use names such as Private or Charter for alternatives.
5. Save as CSV and upload to the same project. Check the preview, then confirm.
6. Download the updated workplan for later edits. Existing IDs identify tasks
   to update. Missing rows are retained; imports never delete tasks.

There are nine task columns: Task ID, Task, Part of, Assigned To, Start,
Finish, Predecessors, Type and Plan. Project ownership is configured once in
Astra. The CSV binds to the exact project ID and its current linked entity IDs;
entities follow the existing project-level model. Task-level entity selection
is outside this change. Multiple entities do not require multiple files.

## Safety and scheduling

- Spare `WP-` keys are reserved in project history at download under a write
  transaction, so independent downloads do not reuse new task keys.
- Existing unkeyed tasks receive persistent import keys through the existing
  filled-template workflow. Filled rows with blank keys receive keys at preview;
  after committing such a file, re-uploading its identical bytes is refused.
  Use the updated download to avoid duplicate creation.
- Wrong-project/entity uploads, altered identity/header/version and incompatible
  plan links are refused. Entity binding and preview fingerprints are checked
  again at commit. Partial imports recheck the graph after invalid rows are skipped.
- Shared prerequisites and parents may feed any alternative; a branch may
  link only to Shared or its own branch. Both CSV and native task links enforce it.
- Timeline and schedule table offer a Plan selector. Selecting an alternative
  includes Shared work and uses that alternative's calculated critical path.
  All plans shows the union of the separately calculated critical paths.
- The existing CPM rules remain: finish-to-start, inclusive calendar-day durations,
  cancelled/abandoned tasks excluded, isolated tasks excluded. This feature
  does not automatically move dates, level resources, or add lag/dependency types.
- Marked CSV text uses reversible apostrophe escaping for spreadsheet formula
  protection. Existing generic CSV/XLSX formats remain available.

## Verification record

Focused service/parser tests and HTTP role coverage pass. Local Chrome verified
download, fill, upload, preview, commit, plan selection and desktop/phone layout
using an isolated synthetic database. Guard-removal experiments are run on
disposable source copies, never on the working checkout.

Independent read-only review passed after correcting partial-import graph,
unkeyed-task graph and quoted/CR CSV regressions. All sixteen focused tests
and the HTTP role-matrix test passed independently. Eleven guard-removal
experiments each made the relevant regression fail as required.

Final Windows suite: `Ran 739 tests in 812.249s; OK (skipped=1)`. The one skip is the existing Windows
symlink limitation. See the commit containing ticket W6ZSGA for the source SHA. Real Rupani project population, actual user's database,
Microsoft Excel desktop save behavior and hosted deployment remain unverified.
