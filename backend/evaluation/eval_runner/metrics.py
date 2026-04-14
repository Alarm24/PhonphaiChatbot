from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .models import EvalRow
from .text_utils import contains_thai, normalize_text


def build_retrieved_context(retrieved_sources: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for item in retrieved_sources:
        content = normalize_text(item.get("content"))
        if content:
            parts.append(content)
    return "\n".join(parts)


def tokenize_for_overlap(text: str) -> list[str]:
    normalized = normalize_text(text).lower()
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
