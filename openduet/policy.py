"""Deterministic action and disclosure policy. Unknown effects always need approval."""

import json
import re


def check_payload(arguments):
    for field in ("action", "operation"):
        if isinstance(arguments.get(field), str) and FORBIDDEN.search(arguments[field]):
            raise ValueError("This operation is forbidden even with approval")
    text = json.dumps(arguments)
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        raise ValueError("Government identification must not be passed to tools")
    if re.search(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", text, re.I):
        raise ValueError("Government IDs must not be shared")
    lengths = {
        "IT": 27,
        "GB": 22,
        "DE": 22,
        "FR": 27,
        "ES": 24,
        "NL": 18,
        "BE": 16,
        "CH": 21,
        "AT": 20,
        "IE": 22,
        "PT": 25,
        "PL": 28,
        "GR": 27,
        "LU": 20,
        "DK": 18,
        "FI": 18,
        "NO": 15,
        "SE": 24,
    }
    for match in re.finditer(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b", text, re.I):
        value = match[0].replace(" ", "").upper()
        if len(value) != lengths.get(value[:2]):
            continue
        rearranged = value[4:] + value[:4]
        number = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
        if int(number) % 97 == 1:
            raise ValueError("Full bank account identifiers must not be shared")
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


def redact_identifiers(text):
    """Remove validated identifiers before retrieval results reach prompts or source caches."""
    patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b",
        r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b",
        r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)",
    ]

    def replace(match):
        try:
            check_payload({"content": match[0]})
        except ValueError:
            return "[sensitive identifier withheld]"
        return match[0]

    for pattern in patterns:
        text = re.sub(pattern, replace, text, flags=re.I)
    return text


def redact_data(value, private=lambda text: text, depth=0):
    if depth > 40:
        return "[deeply nested content withheld]"
    if isinstance(value, dict):
        return {key: redact_data(item, private, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_data(item, private, depth + 1) for item in value]
    if isinstance(value, str):
        return redact_identifiers(private(value))
    if type(value) in {int, float}:
        masked = redact_identifiers(private(str(value)))
        return value if masked == str(value) else masked
    return value
