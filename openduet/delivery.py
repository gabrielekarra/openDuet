"""Verify explicit file assignments against host-created artifacts, never model claims."""

from __future__ import annotations

import re

PREFIX = "HOST DELIVERY CHECK: "
FORMATS = {
    "markdown": "md",
    "md": "md",
    "pdf": "pdf",
    "excel": "xlsx",
    "xlsx": "xlsx",
    "spreadsheet": "xlsx",
    "workbook": "xlsx",
    "foglio di calcolo": "xlsx",
    "powerpoint": "pptx",
    "pptx": "pptx",
    "slide deck": "pptx",
    "word": "docx",
    "docx": "docx",
    "csv": "csv",
}


def required_format(request):
    text = request.split("UNTRUSTED", 1)[0].strip().lower()
    if not re.match(
        r"^(?:(?:please|per favore|puoi|can you|could you)\s+)?(?:create|make|generate|write|build|produce|crea|genera|scrivi|realizza|prepara|prepare)\b",
        text,
    ):
        return ""
    found = re.search(r"\b(" + "|".join(re.escape(x) for x in FORMATS) + r")\b", text[:180])
    if not found:
        return ""
    # "Write an email about PDF exports" is not a request for a PDF file.
    if re.search(r"\b(email|mail|message|messaggio|reply|risposta)\b", text[: found.start()]):
        return ""
    return FORMATS[found[0]]


def missing_artifact(runtime, task):
    kind = required_format(task["request"])
    if not kind:
        return ""
    root = (runtime.config.data_dir / "artifacts").resolve()
    for item in runtime.store.rows("SELECT filename,format FROM artifacts WHERE task=?", (task["id"],)):
        path = (root / item["filename"]).resolve()
        if item["format"] == kind and path.is_relative_to(root) and path.is_file() and path.stat().st_size:
            return ""
    return kind
