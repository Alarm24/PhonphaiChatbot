from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval_runner.dataset import infer_theme_from_input_path, load_rows, normalize_row, validate_rows
from eval_runner.metrics import write_csv
from eval_runner.models import QUESTION_FIELDS
from retrieval_tuning import (
    CURRENT_DIR,
    MAX_PLOT_SERIES,
    average_curves,
    evaluate_hybrid_task,
    recall_at,
    render_svg_line_chart,
    run_parallel_tasks,
    safe_slug,
    write_json,
)

DEFAULT_WORKERS = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep hybrid retrieval alpha and k, without reranking."
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=[
            str(CURRENT_DIR / "testcase" / "disaster_csv.csv"),
            str(CURRENT_DIR / "testcase" / "manual_csv.csv"),
        ],
        help="Input testcase files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(CURRENT_DIR / "outputs" / "retrieval_hybrid_tuning"),
        help="Directory for CSV/JSON/SVG outputs.",
    )
    parser.add_argument(
        "--max-k",
        type=int,
        default=100,
        help="Maximum k for retrieval and recall@k.",
    )
    parser.add_argument(
        "--weights",
        nargs="+",
        type=float,
        default=[round(step / 10, 1) for step in range(11)],
        help="Semantic weights to evaluate. BM25 weight becomes 1 - semantic_weight.",
    )
    parser.add_argument(
        "--themes",
        nargs="*",
        choices=["manual", "disaster"],
        default=None,
        help="Optional theme filter.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional testcase cap per input file for quick debugging.",
    )
    parser.add_argument(
        "--qdrant-host",
        default=None,
        help="Override QDRANT_HOST when running outside Docker.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of parallel worker threads for hybrid retrieval evaluation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.qdrant_host:
        os.environ["QDRANT_HOST"] = args.qdrant_host

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_weights = []
    for weight in args.weights[:MAX_PLOT_SERIES]:
        clamped = min(max(weight, 0.0), 1.0)
        normalized_weights.append(round(clamped, 4))
    weights = list(dict.fromkeys(normalized_weights))

    rows_by_theme: dict[str, list[dict[str, str]]] = defaultdict(list)
    for input_value in args.inputs:
        input_path = Path(input_value)
        theme = infer_theme_from_input_path(input_path)
        if args.themes and theme not in args.themes:
            continue
        raw_rows = load_rows(input_path)
        validate_rows(raw_rows)
        for index, row in enumerate(raw_rows):
            if args.limit is not None and len(rows_by_theme[theme]) >= args.limit:
                break
            rows_by_theme[theme].append(normalize_row(row, index=index, forced_theme=theme))

    tasks: list[dict[str, Any]] = []
    for theme, theme_rows in rows_by_theme.items():
        for row in theme_rows:
            for question_type, field_name in QUESTION_FIELDS.items():
                query_text = row[field_name]
                if not query_text:
                    continue
                for semantic_weight in weights:
                    tasks.append(
                        {
                            "theme": theme,
                            "row": row,
                            "question_type": question_type,
                            "query_text": query_text,
                            "semantic_weight": semantic_weight,
                            "max_k": args.max_k,
                        }
                    )

    results = run_parallel_tasks(
        tasks=tasks,
        worker_count=args.workers,
        description="Evaluating hybrid retrieval",
        evaluator=evaluate_hybrid_task,
    )

    per_query_rows: list[dict[str, Any]] = []
    curve_bucket: dict[tuple[str, str, float], list[list[float]]] = defaultdict(list)
    for result in results:
        theme = result["theme"]
        question_type = result["question_type"]
        semantic_weight = result["semantic_weight"]
        bm25_weight = result["bm25_weight"]
        hybrid_curve = result["hybrid_curve"]
        hybrid_docs = result["hybrid_docs"]

        curve_bucket[(theme, question_type, semantic_weight)].append(hybrid_curve)
        curve_bucket[("overall", question_type, semantic_weight)].append(hybrid_curve)
        per_query_rows.append(
            {
                "theme": theme,
                "question_type": question_type,
                "testcase_id": result["testcase_id"],
                "semantic_weight": semantic_weight,
                "bm25_weight": bm25_weight,
                "query": result["query"],
                "evidence": result["evidence"],
                "hybrid_recall_at_1": round(recall_at(hybrid_curve, 1), 6),
                "hybrid_recall_at_5": round(recall_at(hybrid_curve, 5), 6),
                "hybrid_recall_at_10": round(recall_at(hybrid_curve, 10), 6),
                "hybrid_recall_at_20": round(recall_at(hybrid_curve, 20), 6),
                "hybrid_recall_at_50": round(recall_at(hybrid_curve, 50), 6),
                "hybrid_recall_at_100": round(recall_at(hybrid_curve, 100), 6),
                "hybrid_top_100": json.dumps(
                    [
                        {
                            "content": item.get("content", ""),
                            "metadata": item.get("metadata", {}),
                        }
                        for item in hybrid_docs
                    ],
                    ensure_ascii=False,
                ),
            }
        )

    summary_rows: list[dict[str, Any]] = []
    plot_rows: list[dict[str, Any]] = []
    for (theme, question_type, semantic_weight), curves in sorted(curve_bucket.items()):
        averaged_curve = average_curves(curves, args.max_k)
        bm25_weight = round(1.0 - semantic_weight, 4)
        summary_rows.append(
            {
                "theme": theme,
                "question_type": question_type,
                "semantic_weight": semantic_weight,
                "bm25_weight": bm25_weight,
                "testcase_count": len(curves),
                "recall_at_1": round(recall_at(averaged_curve, 1), 6),
                "recall_at_5": round(recall_at(averaged_curve, 5), 6),
                "recall_at_10": round(recall_at(averaged_curve, 10), 6),
                "recall_at_20": round(recall_at(averaged_curve, 20), 6),
                "recall_at_50": round(recall_at(averaged_curve, 50), 6),
                "recall_at_100": round(recall_at(averaged_curve, 100), 6),
            }
        )
        for idx, recall in enumerate(averaged_curve, start=1):
            plot_rows.append(
                {
                    "theme": theme,
                    "question_type": question_type,
                    "semantic_weight": semantic_weight,
                    "bm25_weight": bm25_weight,
                    "k": idx,
                    "recall": round(recall, 6),
                }
            )

    write_csv(output_dir / "per_query_results.csv", per_query_rows)
    write_json(output_dir / "per_query_results.json", per_query_rows)
    write_csv(output_dir / "recall_curve_summary.csv", summary_rows)
    write_json(output_dir / "recall_curve_summary.json", summary_rows)
    write_csv(output_dir / "recall_curve_points.csv", plot_rows)

    for theme in sorted({row["theme"] for row in summary_rows}):
        for question_type in sorted(
            {row["question_type"] for row in summary_rows if row["theme"] == theme}
        ):
            chart_series = []
            for semantic_weight in weights:
                matched = next(
                    (
                        row
                        for row in summary_rows
                        if row["theme"] == theme
                        and row["question_type"] == question_type
                        and row["semantic_weight"] == semantic_weight
                    ),
                    None,
                )
                if not matched:
                    continue
                values = [
                    point["recall"]
                    for point in plot_rows
                    if point["theme"] == theme
                    and point["question_type"] == question_type
                    and point["semantic_weight"] == semantic_weight
                ]
                chart_series.append({"label": f"{semantic_weight:.1f}", "values": values})
            if chart_series:
                render_svg_line_chart(
                    title=f"{theme.title()} {question_type} Hybrid Recall@k",
                    subtitle=f"Evidence-overlap recall across {len(chart_series)} semantic-weight settings",
                    x_label="k",
                    y_label="Recall",
                    series=chart_series,
                    output_path=output_dir
                    / "plots"
                    / f"{safe_slug(theme)}_{safe_slug(question_type)}_hybrid_recall.svg",
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
