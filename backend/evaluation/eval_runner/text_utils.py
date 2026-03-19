from __future__ import annotations

import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def normalize_theme(value: Any) -> str:
    return normalize_text(value).lower()


def contains_thai(text: str) -> bool:
    return any("\u0E00" <= char <= "\u0E7F" for char in text)
