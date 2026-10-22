"""Small deterministic checks in addition to approvals. These are not a trained DLP classifier."""

import json
import re


def check_payload(arguments):
    text = json.dumps(arguments)
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        raise ValueError("Government identification must not be passed to tools")
    for match in re.finditer(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", text):
        digits = [int(d) for d in match.group() if d.isdigit()]
        if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
            continue
        total = sum(
            (d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 else d for i, d in enumerate(reversed(digits))
        )
        if total % 10 == 0:
            raise ValueError("Full payment card numbers must not be passed to tools")
