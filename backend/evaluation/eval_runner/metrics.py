from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import EvalRow
from .text_utils import contains_thai, normalize_text

SOURCE_PATTERN = re.compile(
    r"^(?P<filename>.+?)\s*-\s*(?:\u0e2b\u0e19\u0e49\u0e32|page|pages?)\s*(?P<start>\d+)(?:\s*[-\u2013]\s*(?P<end>\d+))?\s*$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedSourceReference:
    raw: str
    filename: str
    normalized_filename: str
    page_start: int | None
    page_end: int | None
    pages: frozenset[int]


def build_retrieved_context(retrieved_sources: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for item in retrieved_sources:
        content = normalize_text(item.get("content"))
        if content:
            parts.append(content)
    return "\n".join(parts)


def tokenize_for_overlap(text: str) -> list[str]:
    normalized = normalize_text(text).lower().replace(".", "")
    if not normalized:
        return []

    if contains_thai(normalized):
        compact = re.sub(r"\s+", "", normalized)
        if len(compact) < 3:
            return list(compact)
        return [compact[i : i + 3] for i in range(len(compact) - 2)]

    word_tokens = re.findall(r"[a-z0-9]+", normalized)
    if word_tokens:
        return word_tokens

    compact = re.sub(r"\s+", "", normalized)
    if len(compact) < 3:
        return list(compact)
    return [compact[i : i + 3] for i in range(len(compact) - 2)]


def compute_overlap_metrics(retrieved_context: str, evidence: str) -> tuple[float, float, float]:
    pred_tokens = tokenize_for_overlap(retrieved_context)
    ref_tokens = tokenize_for_overlap(evidence)

    if not pred_tokens and not ref_tokens:
        return 1.0, 1.0, 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0, 0.0, 0.0

    pred_counter = Counter(pred_tokens)
    ref_counter = Counter(ref_tokens)
    overlap = sum((pred_counter & ref_counter).values())

    precision = overlap / sum(pred_counter.values()) if pred_counter else 0.0
    recall = overlap / sum(ref_counter.values()) if ref_counter else 0.0
    f1_score = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1_score


def normalize_filename(value: str) -> str:
    normalized = normalize_text(value).lower()
    normalized = re.sub(r"\.[a-z0-9]{1,8}$", "", normalized)
    normalized = re.sub(r"^\d+\s*[\.)-]?\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def parse_source_reference(value: str) -> ParsedSourceReference:
    raw = normalize_text(value)
    if not raw:
        return ParsedSourceReference(
            raw="",
            filename="",
            normalized_filename="",
            page_start=None,
            page_end=None,
            pages=frozenset(),
        )

    match = SOURCE_PATTERN.match(raw)
    if not match:
        filename = raw
        return ParsedSourceReference(
            raw=raw,
            filename=filename,
            normalized_filename=normalize_filename(filename),
            page_start=None,
            page_end=None,
            pages=frozenset(),
        )

    filename = normalize_text(match.group("filename"))
    page_start = int(match.group("start"))
    page_end = int(match.group("end") or page_start)
    if page_end < page_start:
        page_start, page_end = page_end, page_start

    return ParsedSourceReference(
        raw=raw,
        filename=filename,
        normalized_filename=normalize_filename(filename),
        page_start=page_start,
        page_end=page_end,
        pages=frozenset(range(page_start, page_end + 1)),
    )


def compute_set_metrics(
    predicted: set[str] | set[int],
    reference: set[str] | set[int],
) -> tuple[float, float, float]:
    if not predicted and not reference:
        return 1.0, 1.0, 1.0
    if not predicted or not reference:
        return 0.0, 0.0, 0.0

    overlap = len(predicted & reference)
    precision = overlap / len(predicted)
    recall = overlap / len(reference)
    f1_score = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1_score


def compute_source_match_metrics(
    source: str,
    retrieved_sources: list[dict[str, str]],
) -> dict[str, Any]:
    reference = parse_source_reference(source)
    parsed_retrieved = [
        parse_source_reference(item.get("title", ""))
        for item in retrieved_sources
        if normalize_text(item.get("title"))
    ]

    retrieved_filenames = sorted(
        {parsed.filename for parsed in parsed_retrieved if parsed.filename}
    )
    retrieved_pages = sorted({page for parsed in parsed_retrieved for page in parsed.pages})

    file_precision, file_recall, file_f1_score = compute_set_metrics(
        {parsed.normalized_filename for parsed in parsed_retrieved if parsed.normalized_filename},
        {reference.normalized_filename} if reference.normalized_filename else set(),
    )
    page_precision, page_recall, page_f1_score = compute_set_metrics(
        set(retrieved_pages),
        set(reference.pages),
    )

    return {
        "source_filename": reference.filename,
        "source_page_start": reference.page_start,
        "source_page_end": reference.page_end,
        "retrieved_filenames": retrieved_filenames,
        "retrieved_pages": retrieved_pages,
        "file_precision": file_precision,
        "file_recall": file_recall,
        "file_f1_score": file_f1_score,
        "page_precision": page_precision,
        "page_recall": page_recall,
        "page_f1_score": page_f1_score,
    }


def mean_or_zero(values: list[float]) -> float:
    return 0.0 if not values else statistics.fmean(values)


def aggregate_results(results: list[EvalRow]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[EvalRow]] = defaultdict(list)
    for row in results:
        grouped[(row.theme, row.question_type, row.format_based)].append(row)

    summary = []
    for (theme, question_type, format_based), rows in sorted(grouped.items()):
        summary.append(build_summary_row(theme, question_type, format_based, rows))

    overall_by_question_type: dict[tuple[str, str], list[EvalRow]] = defaultdict(list)
    for row in results:
        overall_by_question_type[(row.question_type, row.format_based)].append(row)
    for (question_type, format_based), rows in sorted(overall_by_question_type.items()):
        summary.append(build_summary_row("overall", question_type, format_based, rows))

    return summary


def build_summary_row(
    theme: str,
    question_type: str,
    format_based: str,
    rows: list[EvalRow],
) -> dict[str, Any]:
    return {
        "theme": theme,
        "question_type": question_type,
        "format_based": format_based,
        "testcase_count": len(rows),
        "tool_called_correctly_mean": round(
            mean_or_zero([row.tool_called_correctly for row in rows]), 6
        ),
        "cost_mean": round(mean_or_zero([row.cost for row in rows]), 10),
        "precision_mean": round(mean_or_zero([row.precision for row in rows]), 6),
        "recall_mean": round(mean_or_zero([row.recall for row in rows]), 6),
        "f1_score_mean": round(mean_or_zero([row.f1_score for row in rows]), 6),
        "correctness_mean": round(mean_or_zero([row.correctness for row in rows]), 6),
        "helpfulness_mean": round(mean_or_zero([row.helpfulness for row in rows]), 6),
        "irrelevancy_mean": round(mean_or_zero([row.irrelevancy for row in rows]), 6),
        "extraneousness_mean": round(mean_or_zero([row.extraneousness for row in rows]), 6),
        "conciseness_mean": round(mean_or_zero([row.conciseness for row in rows]), 6),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
