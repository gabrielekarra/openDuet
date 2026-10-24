# Retrieved sources and file locators

Only host-recorded source IDs from the current task are valid citations.
Connector results receive a collection ID and bounded individual record IDs;
each record retains its own URL, excerpt and locator. Briefs preserve each
event's source link. Unknown/foreign IDs are flagged in prose and refused before
artifact publication. A matching ID proves retrieval, not that a model's claim
or calculation follows from that excerpt.

## Input files

The web message API accepts `attachments: [uploaded_id]` alongside the user's
message. Extracted text is not copied into the message field, so long files do
not exceed its 32,000-character limit. Legacy Telegram/import references remain
supported. Inputs are immutable SHA-256 snapshots: a changed on-disk file must
be uploaded again. Normalized extraction and task access survive restarts and
are removed with the channel's stored context.

`read_attachment` accepts an input attachment ID, optional exact `locator`,
`offset` and `limit` (1–20). It returns inert records and `next_offset`; the host
also bounds each page's text. It cannot read another task's inputs or generated
attachments by guessing their IDs. A user-requested artifact revision inherits
only its recorded source snapshots and the corresponding input-file access.
`read_source` retrieves a recorded excerpt already available to this task.

| Format | Locator examples | Meaning |
| --- | --- | --- |
| XLSX | `'Revenue'!A1` | Exact sheet and cell; quoted sheet names escape apostrophes |
| CSV | `CSV!B2` | Logical CSV row/column, including quoted multiline fields |
| DOCX | `paragraph 3`, `table 1!R2C1` | Paragraph or table cell; no guessed pagination |
| PDF | `page 2` | Physical page in the uploaded PDF |
| PPTX | `slide 2, shape 3` | Text shape; table cells include row/column |
| TXT/MD | `line 12` | Original text line |
| Local voice transcript | `audio transcript` | Actual configured local Whisper output |

Formula records distinguish the formula from its saved cached value, which may
be absent. Uploaded formulas, external workbook links and macros are never
executed. Images and scanned pages do not acquire invented OCR text.

Limits are explicit: 20 MB uploads, 40 MB expanded Office archives, 2,000
extracted records and a bounded text budget. XLSX/CSV extraction visits at most
1,000 rows and 30 columns; PDF at most 40 pages and PPTX at most 50 slides.
Per-record text is clipped at 4,000 characters. `truncated` reports any detected
clipping; pagination covers the extracted snapshot, not omitted source content.

## Deliverables

Cite prose using `[^source_id]`. Structured cells, document sections and slide
figures use `source_ids: [id]`; DOCX table cells may be `{value, source_ids}`.
The host validates these references and builds the source appendix from recorded
excerpts. When references are supplied, unrelated retrieved records are omitted.

- XLSX cells carry source comments and hyperlinks. A local source links to its
  generated Sources sheet, with a collision-safe name.
- DOCX numeric cells/sections and PPTX figures link to the original URL or an
  internal appendix containing the retrieved file locator and excerpt.
- PDF citations link to the same URL or named appendix anchor; Markdown carries
  footnote definitions. CSV and HTML exports retain source appendices.
- Make previews expose the same verified references and local excerpts, including
  dashboard metric/table/chart references. There are no invented source URLs.

User-supplied reference strings without recorded IDs remain explicitly unverified.
No automatic semantic or arithmetic correctness claim is made for a model's
generated figures. Editable formulas and source excerpts remain available for
review.

Tests use actual generated Office/PDF inputs and output structures, task and
revision boundaries, digest changes, pagination, and a real Chromium upload →
read tool → cited DOCX → source excerpt → download flow. CI additionally checks
native LibreOffice recalculation and source-linked PPTX rendering.
