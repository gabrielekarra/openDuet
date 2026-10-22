# Third-party notices

Original OpenDuet source is MIT licensed; dependencies and model weights retain
their own licenses. They are not relicensed by this repository.

## Kev inference and optional weights

- **Kev inference source**, Jared Palmer and contributors, Apache-2.0, upstream
  commit `90512f1c517d977741f2104470a40635408236c9`. Unmodified inference source,
  complete license and provenance are in `openduet/kev/vendor/kev/`.
- **Kev 4B**, `jaredpalmer/kev-4b`, Apache-2.0. Official adapter, tokenizer and
  trained pointer head; pinned revision `6cfce5c2fa4b4bd64026336ab649c5ca78857d52`.
- **Qwen3.5 4B Base**, `Qwen/Qwen3.5-4B-Base`, Apache-2.0, pinned revision
  `1001bb4d826a52d1f399e183466143f4da7b741b`.
- **Kev merged MLX 8-bit conversion**, `RoderickQiu/kev-4b-mlx-8bit`, Apache-2.0,
  revision `6929ac37119fb11c2db74eb66b10a886c6d0dd3a`.

The complete file sizes, SHA-256 values and license links are recorded in
`openduet/kev/manifest.json`. Downloads require an explicit operator action.
Models chosen by users have their own terms and are not bundled here.

## Runtime dependencies

| Components | License family |
| --- | --- |
| Python | Python Software Foundation |
| FastAPI, Starlette, Uvicorn, HTTPX, jsonschema, NumPy, PyYAML | MIT / BSD |
| MCP Python SDK | MIT |
| cryptography | Apache-2.0 / BSD |
| Pillow, openpyxl, python-pptx, python-docx, pypdf, ReportLab | HPND / MIT / BSD |
| Playwright | Apache-2.0 |
| Chromium | BSD and component-specific licenses distributed with Chromium |
| LibreOffice | MPL-2.0 / LGPL-3.0-or-later; system package notices apply |
| Poppler | GPL-2.0-or-later; system package notices apply |
| PyTorch, Transformers, PEFT, tokenizers, safetensors, Hugging Face Hub | BSD / Apache-2.0 |
| MLX, mlx-lm | MIT |
| PyObjC | MIT |
| faster-whisper, CTranslate2 | MIT |

Consult installed distributions and system-package notices for complete
component-specific texts. The optional research package has its own dependency
lock. There is no bundled noVNC, native driver, Kokoro/TTS or licensing worker in
the current distribution; their historical materials remain under the native tag.
The glasses assets originate in this repository's native predecessor and were
preserved before its removal.
