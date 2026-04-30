from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval_runner.dataset import infer_theme_from_input_path, load_rows, normalize_row, validate_rows
from eval_runner.metrics import write_csv
from eval_runner.models import QUESTION_FIELDS
from retrieval_tuning import (
    CURRENT_DIR,
    average_curves,
    compute_best_configs,
    evaluate_hybrid_task,
    evaluate_rerank_task,
    get_thread_theme_engine,
    is_cuda_device,
    recall_at,
    render_svg_line_chart,
    run_parallel_tasks,
    safe_slug,
    write_json,
)

DEFAULT_WORKERS = 1
DEFAULT_SEMANTIC_WEIGHT = 0.6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate rerank recall@k with one fixed hybrid alpha."
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
        default=str(CURRENT_DIR / "outputs" / "retrieval_rerank_tuning"),
        help="Directory for CSV/JSON/SVG outputs.",
    )
    parser.add_argument(
        "--max-k",
        type=int,
        default=100,
        help="Maximum retrieval k and recall@k.",
    )
    parser.add_argument(
        "--semantic-weight",
        type=float,
        default=DEFAULT_SEMANTIC_WEIGHT,
        help="Single semantic weight to use for hybrid retrieval before reranking.",
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
        "--rerank-device",
        default=None,
        help="Override RERANK_DEVICE, for example cpu or cuda.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of parallel worker threads for rerank evaluation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.qdrant_host:
        os.environ["QDRANT_HOST"] = args.qdrant_host
    if args.rerank_device:
        os.environ["RERANK_DEVICE"] = args.rerank_device

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if is_cuda_device(args.rerank_device) and args.workers > 1:
        print(
            "Warning: CUDA reranking is not safe with threaded workers on Windows. "
            "Falling back to --workers 1 to avoid PyTorch/CrossEncoder access violations.",
            file=sys.stderr,
        )
        args.workers = 1

    if args.workers > 1:
        os.environ["RETRIEVER_RERANKER_SCOPE"] = "thread"

    semantic_weight = round(min(max(args.semantic_weight, 0.0), 1.0), 4)

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

    hybrid_results = run_parallel_tasks(
        tasks=tasks,
        worker_count=args.workers,
        description="Preparing hybrid retrieval for rerank",
        evaluator=evaluate_hybrid_task,
    )

    rerank_inputs = [{**result, "max_k": args.max_k} for result in hybrid_results]
    rerank_results = run_parallel_tasks(
        tasks=rerank_inputs,
        worker_count=args.workers,
        description="Evaluating rerank",
        evaluator=evaluate_rerank_task,
    )

    per_query_rows: list[dict[str, Any]] = []
    curve_bucket: dict[tuple[str, str], list[list[float]]] = defaultdict(list)
    best_config_bucket: dict[tuple[str, str], list[dict[str, int | float]]] = defaultdict(list)
    config_grid_rows: list[dict[str, Any]] = []

    for result in rerank_results:
        theme = result["theme"]
        question_type = result["question_type"]
        bm25_weight = result["bm25_weight"]
        rerank_curve = result["rerank_curve"]
        best_global = result["best_global"]
        config_grid = result["config_grid"]
        testcase_id = result["testcase_id"]
        query_text = result["query"]
        evidence = result["evidence"]
        hybrid_docs = result["hybrid_docs"]
        reranked_docs = result["reranked_docs"]

        curve_bucket[(theme, question_type)].append(rerank_curve)
        curve_bucket[("overall", question_type)].append(rerank_curve)
        best_config_bucket[(theme, question_type)].append(
            {
                "retrieval_k": int(best_global["retrieval_k"]),
                "rerank_top_k": int(best_global["rerank_top_k"]),
                "recall": float(best_global["recall"]),
            }
        )

        for item in config_grid:
            config_grid_rows.append(
                {
                    "theme": theme,
                    "question_type": question_type,
                    "testcase_id": testcase_id,
                    "semantic_weight": semantic_weight,
                    "bm25_weight": bm25_weight,
                    "retrieval_k": item["retrieval_k"],
                    "rerank_top_k": item["rerank_top_k"],
                    "recall": round(float(item["recall"]), 6),
                }
            )

        per_query_rows.append(
            {
                "theme": theme,
                "question_type": question_type,
                "testcase_id": testcase_id,
                "semantic_weight": semantic_weight,
                "bm25_weight": bm25_weight,
                "query": query_text,
                "evidence": evidence,
                "rerank_recall_at_1": round(recall_at(rerank_curve, 1), 6),
                "rerank_recall_at_5": round(recall_at(rerank_curve, 5), 6),
                "rerank_recall_at_10": round(recall_at(rerank_curve, 10), 6),
                "rerank_recall_at_20": round(recall_at(rerank_curve, 20), 6),
                "rerank_recall_at_50": round(recall_at(rerank_curve, 50), 6),
                "rerank_recall_at_100": round(recall_at(rerank_curve, 100), 6),
                "best_retrieval_k": int(best_global["retrieval_k"]),
                "best_rerank_top_k": int(best_global["rerank_top_k"]),
                "best_rerank_recall": round(float(best_global["recall"]), 6),
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
                "rerank_top_100": json.dumps(
                    [
                        {
                            "content": item.get("content", ""),
                            "metadata": item.get("metadata", {}),
                            "score": round(float(item.get("score", 0.0)), 6),
                        }
                        for item in reranked_docs
                    ],
                    ensure_ascii=False,
                ),
            }
        )

    summary_rows: list[dict[str, Any]] = []
    plot_rows: list[dict[str, Any]] = []
    for (theme, question_type), curves in sorted(curve_bucket.items()):
        averaged_curve = average_curves(curves, args.max_k)
        summary_rows.append(
            {
                "theme": theme,
                "question_type": question_type,
                "semantic_weight": semantic_weight,
                "bm25_weight": round(1.0 - semantic_weight, 4),
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
                    "k": idx,
                    "recall": round(recall, 6),
                }
            )

    best_config_rows: list[dict[str, Any]] = []
    for (theme, question_type), rows in sorted(best_config_bucket.items()):
        if not rows:
            continue
        avg_retrieval_k = sum(int(item["retrieval_k"]) for item in rows) / len(rows)
        avg_rerank_top_k = sum(int(item["rerank_top_k"]) for item in rows) / len(rows)
        avg_recall = sum(float(item["recall"]) for item in rows) / len(rows)
        best_config_rows.append(
            {
                "theme": theme,
                "question_type": question_type,
                "semantic_weight": semantic_weight,
                "bm25_weight": round(1.0 - semantic_weight, 4),
                "avg_best_retrieval_k": round(avg_retrieval_k, 2),
                "avg_best_rerank_top_k": round(avg_rerank_top_k, 2),
                "avg_best_rerank_recall": round(avg_recall, 6),
                "testcase_count": len(rows),
            }
        )

    write_csv(output_dir / "per_query_results.csv", per_query_rows)
    write_json(output_dir / "per_query_results.json", per_query_rows)
    write_csv(output_dir / "recall_curve_summary.csv", summary_rows)
    write_json(output_dir / "recall_curve_summary.json", summary_rows)
    write_csv(output_dir / "recall_curve_points.csv", plot_rows)
    write_csv(output_dir / "best_config_summary.csv", best_config_rows)
    write_csv(output_dir / "rerank_config_grid.csv", config_grid_rows)

    for theme in sorted({row["theme"] for row in summary_rows}):
        for question_type in sorted(
            {row["question_type"] for row in summary_rows if row["theme"] == theme}
        ):
            values = [
                point["recall"]
                for point in plot_rows
                if point["theme"] == theme and point["question_type"] == question_type
            ]
            if values:
                render_svg_line_chart(
                    title=f"{theme.title()} {question_type} Rerank Recall@k",
                    subtitle=f"Fixed semantic weight {semantic_weight:.1f}",
                    x_label="k",
                    y_label="Recall",
                    series=[{"label": f"{semantic_weight:.1f}", "values": values}],
                    output_path=output_dir
                    / "plots"
                    / f"{safe_slug(theme)}_{safe_slug(question_type)}_rerank_recall.svg",
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
