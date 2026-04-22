import re

_MAX_LOG_SUMMARY_CHARS = 2000

_AUTH_PAIR_PATTERN = re.compile(
    r"(?i)(authorization)\s*[:=]\s*(Bearer\s+[A-Za-z0-9\-._~+/]+=*|[^,\n;]+)"
)
_SECRET_PAIR_PATTERN = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*([^,\s;\n]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/]+=*)")


def sanitize_for_log(value: str, *, max_chars: int = _MAX_LOG_SUMMARY_CHARS) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    text = _AUTH_PAIR_PATTERN.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    text = _SECRET_PAIR_PATTERN.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    text = _BEARER_PATTERN.sub("Bearer <redacted>", text)

    if len(text) > max_chars:
        text = f"{text[:max_chars]}...(truncated)"

    return text
