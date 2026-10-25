# OpenDuet launch media — 25 October 2026

These files are direct captures of the OpenDuet web console, rendered in real Chromium.
The workspace and business content are samples. Model decisions and Telegram account/API
responses are scripted fixtures, not a live LLM or a real Telegram client.

The capture uses `tests/fixtures/openduet_preview.py` with a temporary, in-memory provider
override for readable sample requests and tool replies. The existing runtime performs the
actual `create_artifact`, `read_attachment` and approval-gated `remember` operations.
No product source, stored user data or external account was modified.

## Suggested public caption

EN: “OpenDuet product tour · sample data and simulated model/accounts.”

IT: “Tour di OpenDuet · dati di esempio, modello e account simulati.”

## Assets

| File | Dimensions / length | What it shows |
| --- | --- | --- |
| `chat-result.png` | 1440 × 1000 | A clean sample channel: assignment and completion reply. |
| `review-approval.png` | 1440 × 1000 | A real pending memory-update approval with its exact payload. |
| `make-file.png` | 1440 × 1000 | Real Markdown and DOCX artifacts produced by the runtime. |
| `sourced-report.png` | 1440 × 1000 | DOCX preview and original workbook/cell source link. |
| `connections.png` | 1440 × 1000 | The real connector directory and provider setup links; accounts are not connected. |
| `proactivity.png` | 1440 × 1000 | Real attention settings in brief-only mode; Kev weights were not loaded. |
| `demo.mp4` | 1280 × 800; 22.76 s; H.264; 287,577 bytes | Task → Make → approval → saved preference. |
| `demo.webm` | 1280 × 800; same recording | Original browser recording. |
| `demo.vtt` | English text track | Descriptions of the visible workflow, including sample-data disclosure. |

## Verification

- Captured with `/usr/bin/chromium` and the repository’s installed Playwright.
- The workflow created a brief, opened its preview, approved a memory write and
  verified the saved preference in Settings.
- Uploaded a real generated sample XLSX (`Revenue!A1 = 100`), read its cell through
  the runtime, generated a sourced DOCX, downloaded the actual DOCX and verified
  `100` in `word/document.xml`.
- Inspected the final six screenshots and video frames at 2, 11 and 18 seconds.
- No credentials are visible. No human onboarding time, real Telegram delivery,
  Stripe account, local model quality or owner-Mac screen control is demonstrated.
- An earlier capture fixture reused a tool-call identifier and failed. That capture
  was replaced by the successful run on a fresh sample database. No failed/debug
  screenshot is included.

## Capture commands

Temporary capture helpers ran outside the repository:

```sh
PYTHONPATH=/workspace/openduet .venv/bin/python /tmp/openduet-launch-preview.py
PLAYWRIGHT_BROWSERS_PATH=/tmp/openduet-launch-playwright PYTHONPATH=/workspace/openduet \
  .venv/bin/python /tmp/capture-openduet-launch.py
ffmpeg -y -i demo.webm -c:v libx264 -preset medium -crf 23 \
  -pix_fmt yuv420p -movflags +faststart -an demo.mp4
```

The provider override and browser driver were disposable capture helpers, not
runtime changes. The preview used loopback port 8778 and a fresh temporary data
directory; only sample credentials were used. The preview was stopped after capture.

## Checksums

```text
193cd61a29ade47ca3442253df731f4935ddb7a8c78427dd145bb28e50a88b94  chat-result.png
92fd6342e4e3fb58cffa6741c4d38ac2cf9e07bf265f744e0a18aee631ad3e84  connections.png
b2108ba913fc641b7266017ea65cac104cf8420b42912ae08069ef67f1b4bec2  demo.mp4
b5ddbcd627a47e7b87537f5d31212080defcf8a6608a783cbb56d990cf7132d2  demo.vtt
24e37fce8f195e814d4f534b2691c2664d91200493af9f34b1b063e8ff23abd1  demo.webm
c806fe15ee53ac2f83e7e3448fcf39c16381fe598ff8187d9a41f3c3fa8b12c4  make-file.png
75bfaada9ee08409961907b61880f11ec9b5fa71c488e49d591f3bffc8a7ef69  proactivity.png
570f6f61f782ff474b072c6b0bad034f8033a6cef023fd33f99fc20debdd0cdd  review-approval.png
026918530979ecfce139434f006afb3d66dfc9ba7d287ba791a4601ff2484115  sourced-report.png
```
