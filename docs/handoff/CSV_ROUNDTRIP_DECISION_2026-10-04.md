# CSV round-trip decision R2

Status: pending Aly's sample workplan; neither CSV option is approved or implemented.

Aly asked for a workflow suitable for people with basic Excel. XLSX is the
recommended primary download/edit/upload format because its existing template
includes instructions, dropdowns and date formatting. Review the sample workplan
against that workflow before choosing a CSV contract.

The current CSV download protects spreadsheet cells by adding an apostrophe.
That loses information on re-upload: a stored title `=1+1` is exported as
`'=1+1`, which the importer currently treats as a changed title. Removing every
leading apostrophe would corrupt titles that intentionally contain one. Matching
against the stored title would also hide a deliberate edit to the same text.

## Recommended option: reversible, versioned CSV templates

- Add one first line to new editable CSV templates:
  `Astra CSV Text Encoding,apostrophe-v1`.
- Keep the configured column header immediately below it. Apply the reversible
  encoding to headers and data cells.
- Prefix one apostrophe when a value starts with a formula character or an
  apostrophe. In a marked template, decode exactly that added apostrophe before
  validating values. Unprefixed ordinary values stay ordinary values.
- Examples: `=1+1` becomes `'=1+1`; a literal `'=1+1` becomes `''=1+1`;
  a literal `'hello` becomes `''hello`; `O'Brien` stays `O'Brien`.
- Ordinary unmarked CSV uploads keep their current literal-text interpretation.
  Do not infer the encoding from task titles or strip their apostrophes.
- Reject an unknown encoding version. If the marker is absent, explain in preview
  that the upload uses ordinary CSV rules; do not silently guess its origin.
- Keep report and portfolio CSV downloads under their existing safe-export rules.
  They are reports, not the editable import-template format.
- XLSX templates and uploads keep their existing behavior.

Verification required: safe exported cells; exact title/description/key and
literal-apostrophe round trips; edits and new rows; legacy CSV; aliases and
delimiters; unknown markers; HTTP preview and commit. Preservation of this format
by Aly's spreadsheet software is unverified until tested with that software.

## Alternative: preserve the current CSV format

Keep apostrophe protection and literal CSV imports. Use XLSX for editing and
re-uploading formula-prefixed or apostrophe-prefixed text without ambiguity.
Document that such CSV exports can propose a text change on re-upload. This
requires Aly to revise 3NT40T's exact CSV round-trip acceptance criterion.

Aly's decision is required because either option changes the promised CSV
contract. Other independently specified repairs can proceed while R2 is pending.
