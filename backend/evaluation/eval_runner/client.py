from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid

from .models import EXPECTED_TOOL_BY_THEME
from .text_utils import normalize_text


def call_chat_endpoint(chat_endpoint: str, question: str, testcase_id: str) -> tuple[str, list[dict[str, str]]]:
    payload = {
        "session_id": f"eval-{testcase_id}-{uuid.uuid4().hex[:8]}",
        "message": question,
    }
    request = urllib.request.Request(
        chat_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Chat request failed with HTTP {exc.code}: {error_body or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Unable to reach chat endpoint '{chat_endpoint}'. Ensure the API gateway is running."
        ) from exc

    answer = normalize_text(body.get("response"))
    sources = body.get("sources") or []
    if not isinstance(sources, list):
        sources = []

    normalized_sources = []
    for item in sources:
        if isinstance(item, dict):
            normalized_sources.append(
                {
                    "title": normalize_text(item.get("title")),
                    "theme": normalize_text(item.get("theme")),
                    "content": normalize_text(item.get("content")),
                }
            )
    return answer, normalized_sources


def evaluate_tool_usage(theme: str, retrieved_sources: list[dict[str, str]]) -> tuple[str, str, int]:
    expected_tool = EXPECTED_TOOL_BY_THEME[theme]
    actual_tool = infer_actual_tool(retrieved_sources)
    tool_called_correctly = int(bool(actual_tool) and actual_tool == expected_tool)
    return expected_tool, actual_tool, tool_called_correctly


def infer_actual_tool(retrieved_sources: list[dict[str, str]]) -> str:
    if not retrieved_sources:
        return ""

    source_themes = {
        normalize_text(item.get("theme")).lower()
        for item in retrieved_sources
        if normalize_text(item.get("theme"))
    }
    if len(source_themes) != 1:
        return ""

    source_theme = next(iter(source_themes))
    return EXPECTED_TOOL_BY_THEME.get(source_theme, "")
