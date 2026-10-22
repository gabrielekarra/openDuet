"""Deterministic action and disclosure policy. Unknown effects always need approval."""

import json
import re


def check_payload(arguments):
    text = json.dumps(arguments)
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        raise ValueError("Government identification must not be passed to tools")
    if re.search(
        r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b|\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b", text, re.I
    ):
        raise ValueError("Government IDs and full bank account identifiers must not be shared")
    if re.search(r'"(?:password|passwd|secret|api_key|access_token)"\s*:\s*"[^"\s]+"', text, re.I):
        raise ValueError("Enter credentials through the private sign-in form")
    for match in re.finditer(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", text):
        digits = [int(d) for d in match.group() if d.isdigit()]
        if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
            continue
        total = sum(
            (d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 else d for i, d in enumerate(reversed(digits))
        )
        if total % 10 == 0:
            raise ValueError("Full payment card numbers must not be passed to tools")


FORBIDDEN = re.compile(
    r"(?:transfer[_ -]?(?:money|funds|between|account)|(?:buy|sell|trade)[_ -]?(?:stock|securit|equities|crypto)|other[_ -]?(?:person|user)[_ -]?account|impersonate[_ -]?account)",
    re.I,
)
CONSEQUENTIAL = re.compile(
    r"\b(send|pay|purchase|sign|delete|remove|publish|post|submit|execute|run_payroll|checkout|transfer)\b",
    re.I,
)


def classify(name, annotations=None, safe=False):
    words = name.replace("_", " ").replace("-", " ")
    if FORBIDDEN.search(name) or FORBIDDEN.search(words):
        return "forbidden"
    annotations = annotations or {}
    if annotations.get("destructiveHint") or CONSEQUENTIAL.search(words):
        return "consequential"
    if annotations.get("readOnlyHint") is True:
        return "read"
    # An operator safe-list cannot override explicit destructive metadata or hard limits.
    if safe:
        return "read"
    if re.search(r"(?:draft|preview|prepare|simulate)", words, re.I):
        return "prepare"
    return "consequential"


def check_outgoing(text, user_request="", *, owner_delivery=False):
    check_payload({"content": text})
    if owner_delivery:
        return text
    sensitive = re.search(
        r"\b(diagnos\w*|medical record|cartella clinic\w*|salary|stipendio|net worth|patrimonio)\b",
        text,
        re.I,
    )
    explicit = re.search(r"\b(share|send|forward|invia|condivid|inoltra)\w*\b", user_request, re.I)
    if sensitive and not explicit:
        raise ValueError("Sharing personal health or financial information needs an explicit user request")
    return text
