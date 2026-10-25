# OpenDuet launch site

Portable, buildless English/Italian marketing site for https://github.com/gabrielekarra/openDuet.
Target origin: https://openduet.gabrielekarra.chatgpt.site

```sh
python build.py
python -m http.server 8779 --bind 127.0.0.1 --directory dist
```

The generator uses only Python's standard library; the deployed site is plain HTML/CSS/JS.
Keep `.openai/hosting.json` project identity when updating the existing Site.
The Sites deployment repository tracks `dist/` for exact source publication;
this public GitHub mirror regenerates it with `python build.py`.
No backend, analytics tracker, cookies, signup form or user-data collection is included.
Workflow-sharing links carry campaign parameters; this does not itself measure visits.

## Asset provenance

UI pictures and the 22.76-second video are direct captures of OpenDuet's real
web console with sample data, accounts and a fixture model. File creation,
source reading, DOCX download and approval-gated memory updates execute in the
runtime. The media do not demonstrate live Telegram, a live issuer or control
of the owner's Mac. Capture details/checksums are in the main repository's
`docs/launch/media/media-notes.md`. Captions and page copy label the sample context.

The glasses mark is the project's existing brand. Instrument Sans is bundled
under its SIL Open Font License; retain `assets/fonts/OFL.txt`. The social
preview is a browser rendering of `social.html`, using that same mark and font.

## Design and verification

The existing warm ground, olive accent and glasses identity carry the launch.
The subject's own request → review → file flow becomes the interactive hero.
One font, large two-line headings, flat fields and real interface captures
replace stock feature cards. The live controls switch real screenshots, copy
sample requests and share the selected workflow through a normal URL.

The design skill's draw/inspector files were unavailable through the package
and filesystem. No seed, automated taste score or inspector pass is claimed.
Manual browser review fixed missing arrow glyphs, enlarged the hero crop and
verified complete lazy-loaded pictures. All EN/IT pages were inspected at
1440, 768 and 390 px. Measured overflow was zero; all headings fit within two
lines; all four product pictures loaded. Tabs, keyboard navigation, real
clipboard copies, share-link fallback, image dialog, reduced motion and actual
video playback passed in Chromium. No console exceptions were observed.

The public source Site workflow helper was also unavailable in the executor.
Source is pushed with the Site's scoped Git credential, through hidden stdin
and process-memory HTTP headers; the deployment archive contains only the
tracked hosting manifest and `dist/` from the exact verified pushed commit.
Never store source credentials in this checkout or pass them in shell arguments.

The page describes a release candidate and retains links to actual validation
and the post-closure acceptance checklist. There are no customer endorsements,
invented usage figures, provider certifications or claims of viral growth.
