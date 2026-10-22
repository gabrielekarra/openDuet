# Make deliverables

Work is ready for the user's review; the agent does not mark it completed.
Make retains original artifacts and parent-linked versions, source references,
diffs and revision requests. Telegram sends downloadable files and supports
“Revise / Modifica” followed by a reply. Revisions return to the original task's
channel/provider and delivery surface.

| Format | Structured content |
| --- | --- |
| XLSX | Sheets with literal assumptions, validated formulas, number formats, widths and charts |
| PPTX | Title/section/bullets, columns, quote, table, chart or uploaded-image layouts; notes and review flags |
| DOCX | Executive summary, heading levels, paragraphs, tables and sources |
| PDF | Downloadable text report with sources |
| Dashboard | Validated tiles, tables, charts and where-to-look items; no executable JavaScript |
| Webapp | Static HTML/CSS/JS prototype ZIP, served in the separate sandbox origin |

XLSX formulas reject external/executable/indirect functions and links. When
LibreOffice is installed, generated models are actually recalculated and error
cells are rejected. Otherwise the result clearly says recalculation is pending
in the user's spreadsheet app. `scripts/check_office.py` changes a twelve-month
forecast assumption, verifies recalculated totals change, and checks a real
PPTX-to-PNG preview. The workspace Compose image includes these converters.

PPTX previews use LibreOffice and Poppler when installed; structured slide
summaries remain the fallback. Notes and “needs review” flags are retained.
Task-scoped sources retrieved by tools are appended to structured exports.
Unknown citation IDs are flagged rather than rendered as verified source chips.

Dashboards also produce a PNG for Telegram. An optional local-time refresh
specification creates subsequent versions from newly retrieved data. The host
requires confirmation before a model can enable that schedule and claims each
local day once across restarts. Old dashboard versions remain downloadable.

Prototypes run as static files on the separate prototype origin in an opaque
sandbox with network access disabled. They cannot call the workspace API, read
its storage or access model/account credentials. They are experiments to review,
not automatically published production applications. Use a different HTTPS
hostname for prototypes in a remote deployment.
