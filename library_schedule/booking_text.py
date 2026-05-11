from __future__ import annotations

import re


USERNAME_SUFFIX_RE = re.compile(r"\s+([A-Za-z]{4,}\d{3,})$")


def clean_booking_for_display(value: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        return ""

    without_suffix = USERNAME_SUFFIX_RE.sub("", cleaned).strip()
    return without_suffix or cleaned
