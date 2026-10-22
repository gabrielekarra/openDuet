"""Canonical sender keys used by adaptive attention rules."""

from email.utils import parseaddr


def sender_key(payload):
    if not isinstance(payload, dict):
        return ""
    value = str(payload.get("sender", "")).strip().lower()
    return parseaddr(value)[1] or value
