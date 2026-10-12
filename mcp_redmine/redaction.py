"""Redact API credentials at the text output boundary, never in file bytes."""
import html
import json
import logging
import re
import traceback
from urllib.parse import quote, quote_plus

REDACTED = "[REDACTED]"

# The bundled API contract exposes user.api_key. Do not match generic `token`:
# upload.token is required to attach uploaded files to an issue.
def is_api_key(name):
    return isinstance(name, str) and re.sub(r"[-_\s]", "", name).lower() in {
        "apikey", "xredmineapikey",
    }


def response_api_keys(obj):
    """Recognize returned keys so sibling text echoes are sanitized as well."""
    if isinstance(obj, dict):
        for name, value in obj.items():
            if is_api_key(name) and isinstance(value, str):
                yield value
            yield from response_api_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from response_api_keys(value)


# Best-effort labelled credentials in plain text/HTML errors (not a general parser).
_LABELLED_KEY = re.compile(
    r"(?i)(\b(?:x[-_]redmine[-_])?api[-_ ]?key\b[\"']?\s*[:=]\s*)"
    r"(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;&<>}\]]+)"
)


def redact_text(text, secrets, *, labelled=True):
    for secret in sorted(set(secrets), key=len, reverse=True):
        if not secret:
            continue
        # Literal, JSON-escaped, HTML-escaped and URL-encoded echoes only.
        variants = {secret, json.dumps(secret, ensure_ascii=True)[1:-1],
                    html.escape(secret), html.escape(secret, quote=False),
                    quote(secret, safe=""), quote_plus(secret, safe="")}
        for variant in sorted(variants, key=len, reverse=True):
            text = text.replace(variant, REDACTED)
        # Also cover percent-encoding every UTF-8 byte (hex digits are case-insensitive).
        encoded = "".join(f"%{byte:02x}" for byte in secret.encode())
        text = re.sub(re.escape(encoded), lambda _: REDACTED, text, flags=re.I)

    def replace_label(match):
        value = match[0][len(match[1]):]
        delimiter = value[0] if value[0] in "\"'" else ""
        return match[1] + delimiter + REDACTED + delimiter

    return _LABELLED_KEY.sub(replace_label, text) if labelled else text


def redact(obj, secrets):
    """Copy JSON-like results, preserving keys and non-secret values."""
    if isinstance(obj, dict):
        return {redact_text(key, secrets) if isinstance(key, str) else key:
                REDACTED if is_api_key(key) else redact(value, secrets)
                for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(value, secrets) for value in obj]
    if isinstance(obj, str):
        return redact_text(obj, secrets)
    if isinstance(obj, bytes):
        # Text tool responses may contain non-JSON bytes. Preserve byte type for
        # YAML !!binary compatibility; raw download/image paths bypass this function.
        return redact_text(obj.decode("utf-8", errors="surrogateescape"), secrets).encode(
            "utf-8", errors="surrogateescape")
    return obj


class CredentialFilter(logging.Filter):
    """Protect server and HTTP diagnostic logs, including exception tracebacks."""
    def __init__(self, secrets):
        super().__init__()
        self.secrets = secrets

    def filter(self, record):
        secrets = self.secrets()
        record.msg = redact_text(record.getMessage(), secrets)
        record.args = ()
        if record.exc_info:
            record.exc_text = redact_text("".join(traceback.format_exception(*record.exc_info)), secrets)
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = redact_text(record.exc_text, secrets)
        return True
