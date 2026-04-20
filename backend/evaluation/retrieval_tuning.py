from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval_runner.dataset import infer_theme_from_input_path, load_rows, normalize_row, validate_rows
from eval_runner.metrics import compute_overlap_metrics, write_csv
from eval_runner.models import QUESTION_FIELDS

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
RETRIEVER_DIR = BACKEND_DIR / "services" / "retriever"

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(RETRIEVER_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVER_DIR))

MAX_PLOT_SERIES = 11


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep retrieval hyperparameters and plot recall@k curves."
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
        default=str(CURRENT_DIR / "outputs" / "retrieval_tuning"),
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
        "--rerank-device",
        default=None,
        help="Override RERANK_DEVICE, for example cpu or cuda.",
    )
    return parser.parse_args()


def make_theme(theme_name: str):
    if theme_name == "manual":
        from themes.manual import ManualTheme

        return ManualTheme()
    if theme_name == "disaster":
        from themes.disaster import DisasterTheme

        return DisasterTheme()
    raise ValueError(f"Unsupported theme: {theme_name}")


def safe_slug(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


def average_curves(curves: list[list[float]], max_k: int) -> list[float]:
    if not curves:
        return [0.0] * max_k
    totals = [0.0] * max_k
    for curve in curves:
        for idx in range(max_k):
            totals[idx] += curve[idx]
    return [total / len(curves) for total in totals]


def recall_at(values: list[float], target_k: int) -> float:
    if not values:
        return 0.0
    index = min(max(target_k, 1), len(values)) - 1
    return values[index]


def compute_recall_curve(docs: list[dict[str, Any]], evidence: str, max_k: int) -> list[float]:
    curve: list[float] = []
    context_parts: list[str] = []
    for rank in range(max_k):
        if rank < len(docs):
            content = str(docs[rank].get("content", "")).strip()
            if content:
                context_parts.append(content)
        joined_context = "\n".join(context_parts)
        _, recall, _ = compute_overlap_metrics(joined_context, evidence)
        curve.append(recall)
    return curve


def compute_best_configs(
    reranked_docs: list[dict[str, Any]],
    evidence: str,
    max_k: int,
) -> tuple[dict[str, int | float], list[dict[str, int | float]]]:
    best_by_rerank_k: dict[int, tuple[float, int]] = {}
    all_rows: list[dict[str, int | float]] = []

    for retrieval_k in range(1, max_k + 1):
        subset = reranked_docs[:retrieval_k]
        subset_sorted = sorted(
            subset, key=lambda item: item.get("score", float("-inf")), reverse=True
        )
        for rerank_top_k in range(1, retrieval_k + 1):
            context = "\n".join(
                str(item.get("content", "")).strip()
                for item in subset_sorted[:rerank_top_k]
                if item.get("content")
            )
            _, recall, _ = compute_overlap_metrics(context, evidence)
            row = {
                "retrieval_k": retrieval_k,
                "rerank_top_k": rerank_top_k,
                "recall": recall,
            }
            all_rows.append(row)
            current = best_by_rerank_k.get(rerank_top_k)
            if current is None or recall > current[0]:
                best_by_rerank_k[rerank_top_k] = (recall, retrieval_k)

    best_global = max(
        all_rows,
        key=lambda item: (item["recall"], -item["retrieval_k"], -item["rerank_top_k"]),
        default={"retrieval_k": 1, "rerank_top_k": 1, "recall": 0.0},
    )
    best_global = dict(best_global)
    best_global["best_retrieval_k_per_rerank_top_k"] = json.dumps(
        {
            str(k): {"recall": recall, "retrieval_k": retrieval_k}
            for k, (recall, retrieval_k) in sorted(best_by_rerank_k.items())
        },
        ensure_ascii=False,
    )
    return best_global, all_rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def render_svg_line_chart(
    title: str,
    subtitle: str,
    x_label: str,
    y_label: str,
    series: list[dict[str, Any]],
    output_path: Path,
) -> None:
    width = 1200
    height = 720
    margin_left = 90
    margin_right = 260
    margin_top = 90
    margin_bottom = 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    max_x = max((len(item["values"]) for item in series), default=1)
    max_x = max(max_x, 1)

    palette = [
        "#0f4c5c",
        "#e36414",
        "#6a994e",
        "#7b2cbf",
        "#bc4749",
        "#277da1",
        "#f4a261",
        "#4d908e",
        "#577590",
        "#c1121f",
        "#8d99ae",
    ]

    def x_pos(index: int) -> float:
        if max_x == 1:
            return margin_left
        return margin_left + (index / (max_x - 1)) * plot_width

    def y_pos(value: float) -> float:
        return margin_top + (1 - min(max(value, 0.0), 1.0)) * plot_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfbf7"/>',
        f'<text x="{margin_left}" y="42" font-size="28" font-family="Segoe UI, Arial, sans-serif" fill="#1f2933">{escape_xml(title)}</text>',
        f'<text x="{margin_left}" y="68" font-size="16" font-family="Segoe UI, Arial, sans-serif" fill="#52606d">{escape_xml(subtitle)}</text>',
    ]

    for tick in range(6):
        value = tick / 5
        y = y_pos(value)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_width}" y2="{y:.2f}" stroke="#d9e2ec" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 12}" y="{y + 5:.2f}" text-anchor="end" font-size="13" font-family="Segoe UI, Arial, sans-serif" fill="#52606d">{value:.1f}</text>'
        )

    x_ticks = [1, 5, 10, 20, 40, 60, 80, 100]
    x_ticks = [tick for tick in x_ticks if tick <= max_x]
    for tick in x_ticks:
        x = x_pos(tick - 1)
        parts.append(
            f'<line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{margin_top + plot_height}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{margin_top + plot_height + 28}" text-anchor="middle" font-size="13" font-family="Segoe UI, Arial, sans-serif" fill="#52606d">{tick}</text>'
        )

    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#1f2933" stroke-width="2"/>'
    )
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#1f2933" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{margin_left + plot_width / 2:.2f}" y="{height - 22}" text-anchor="middle" font-size="16" font-family="Segoe UI, Arial, sans-serif" fill="#1f2933">{escape_xml(x_label)}</text>'
    )
    parts.append(
        f'<text x="26" y="{margin_top + plot_height / 2:.2f}" transform="rotate(-90 26 {margin_top + plot_height / 2:.2f})" text-anchor="middle" font-size="16" font-family="Segoe UI, Arial, sans-serif" fill="#1f2933">{escape_xml(y_label)}</text>'
    )

    for idx, item in enumerate(series):
        color = palette[idx % len(palette)]
        points = " ".join(
            f"{x_pos(point_idx):.2f},{y_pos(value):.2f}"
            for point_idx, value in enumerate(item["values"])
        )
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="{points}"/>'
        )

    legend_x = margin_left + plot_width + 24
    legend_y = margin_top + 18
    parts.append(
        f'<text x="{legend_x}" y="{legend_y - 12}" font-size="16" font-family="Segoe UI, Arial, sans-serif" fill="#1f2933">Semantic Weight</text>'
    )
    for idx, item in enumerate(series):
        color = palette[idx % len(palette)]
        y = legend_y + idx * 26
        parts.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 26}" y2="{y}" stroke="{color}" stroke-width="4"/>'
        )
        parts.append(
            f'<text x="{legend_x + 36}" y="{y + 5}" font-size="14" font-family="Segoe UI, Arial, sans-serif" fill="#323f4b">{escape_xml(item["label"])}</text>'
        )

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def escape_xml(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def main() -> int:
    args = parse_args()
    if args.qdrant_host:
        os.environ["QDRANT_HOST"] = args.qdrant_host
    if args.rerank_device:
        os.environ["RERANK_DEVICE"] = args.rerank_device

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

    theme_engines = {theme: make_theme(theme) for theme in sorted(rows_by_theme)}
    per_query_rows: list[dict[str, Any]] = []
    curve_bucket: dict[tuple[str, str, str, float], list[list[float]]] = defaultdict(list)
    best_config_bucket: dict[tuple[str, str, float], list[dict[str, int | float]]] = defaultdict(
        list
    )
    config_grid_rows: list[dict[str, Any]] = []

    for theme, theme_rows in rows_by_theme.items():
        theme_engine = theme_engines[theme]
        for row in theme_rows:
            evidence = row["Evidence"]
            for question_type, field_name in QUESTION_FIELDS.items():
                query_text = row[field_name]
                if not query_text:
                    continue
                for semantic_weight in weights:
                    bm25_weight = round(1.0 - semantic_weight, 4)
                    rankings = theme_engine.rank_candidates(
                        query=query_text,
                        fetch_k=args.max_k,
                        semantic_weight=semantic_weight,
                        bm25_weight=bm25_weight,
                    )
                    hybrid_docs = rankings["hybrid_docs"]
                    reranked_docs = rankings["reranked_docs"]
                    hybrid_curve = compute_recall_curve(hybrid_docs, evidence, args.max_k)
                    rerank_curve = compute_recall_curve(reranked_docs, evidence, args.max_k)
                    best_global, config_grid = compute_best_configs(
                        reranked_docs, evidence, args.max_k
                    )

                    key_base = (theme, question_type, semantic_weight)
                    curve_bucket[(theme, question_type, "hybrid", semantic_weight)].append(
                        hybrid_curve
                    )
                    curve_bucket[(theme, question_type, "rerank", semantic_weight)].append(
                        rerank_curve
                    )
                    curve_bucket[("overall", question_type, "hybrid", semantic_weight)].append(
                        hybrid_curve
                    )
                    curve_bucket[("overall", question_type, "rerank", semantic_weight)].append(
                        rerank_curve
                    )

                    best_config_bucket[key_base].append(
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
                                "testcase_id": row["testcase_id"],
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
                            "testcase_id": row["testcase_id"],
                            "semantic_weight": semantic_weight,
                            "bm25_weight": bm25_weight,
                            "query": query_text,
                            "evidence": evidence,
                            "hybrid_recall_at_1": round(recall_at(hybrid_curve, 1), 6),
                            "hybrid_recall_at_5": round(recall_at(hybrid_curve, 5), 6),
                            "hybrid_recall_at_10": round(recall_at(hybrid_curve, 10), 6),
                            "hybrid_recall_at_20": round(recall_at(hybrid_curve, 20), 6),
                            "hybrid_recall_at_50": round(recall_at(hybrid_curve, 50), 6),
                            "hybrid_recall_at_100": round(recall_at(hybrid_curve, 100), 6),
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
    for (theme, question_type, mode, semantic_weight), curves in sorted(curve_bucket.items()):
        averaged_curve = average_curves(curves, args.max_k)
        bm25_weight = round(1.0 - semantic_weight, 4)
        summary_row = {
            "theme": theme,
            "question_type": question_type,
            "mode": mode,
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
        summary_rows.append(summary_row)
        for idx, recall in enumerate(averaged_curve, start=1):
            plot_rows.append(
                {
                    "theme": theme,
                    "question_type": question_type,
                    "mode": mode,
                    "semantic_weight": semantic_weight,
                    "bm25_weight": bm25_weight,
                    "k": idx,
                    "recall": round(recall, 6),
                }
            )

    best_config_rows: list[dict[str, Any]] = []
    for (theme, question_type, semantic_weight), rows in sorted(best_config_bucket.items()):
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
            for mode in ("hybrid", "rerank"):
                chart_series = []
                for semantic_weight in weights:
                    matched = next(
                        (
                            row
                            for row in summary_rows
                            if row["theme"] == theme
                            and row["question_type"] == question_type
                            and row["mode"] == mode
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
                        and point["mode"] == mode
                        and point["semantic_weight"] == semantic_weight
                    ]
                    chart_series.append(
                        {
                            "label": f"{semantic_weight:.1f}",
                            "values": values,
                        }
                    )
                if chart_series:
                    render_svg_line_chart(
                        title=f"{theme.title()} {question_type} {mode.title()} Recall@k",
                        subtitle=f"Evidence-overlap recall, averaged across {len(chart_series)} semantic-weight settings",
                        x_label="k",
                        y_label="Recall",
                        series=chart_series,
                        output_path=output_dir
                        / "plots"
                        / f"{safe_slug(theme)}_{safe_slug(question_type)}_{safe_slug(mode)}_recall.svg",
                    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
