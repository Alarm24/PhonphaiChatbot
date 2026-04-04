# ruff: noqa: T201
from __future__ import annotations

from pathlib import Path

from .client import call_chat_endpoint, evaluate_tool_usage
from .dataset import infer_theme_from_input_path, load_rows, normalize_row, validate_rows
from .judge import judge_answer, load_judge_prompt
from .metrics import (
    aggregate_results,
    build_retrieved_context,
    compute_overlap_metrics,
    write_csv,
    write_json,
)
from .models import DEFAULT_JUDGE_PROMPT, QUESTION_FIELDS, EvalRow
from .settings import get_eval_settings


def run_evaluation(
    input_path: Path,
    output_dir: Path,
    chat_endpoint_override: str | None = None,
    judge_model_override: str | None = None,
    judge_prompt_file: str | None = None,
    limit: int | None = None,
) -> int:
    settings = get_eval_settings()
    chat_endpoint = chat_endpoint_override or settings.chat_endpoint
    judge_model = judge_model_override or settings.judge_model
    judge_prompt = load_judge_prompt(judge_prompt_file, DEFAULT_JUDGE_PROMPT)

    output_dir.mkdir(parents=True, exist_ok=True)

    loaded_rows = load_rows(input_path)
    if limit is not None:
        loaded_rows = loaded_rows[:limit]
    validate_rows(loaded_rows)

    forced_theme = infer_theme_from_input_path(input_path)
    if not forced_theme:
        raise ValueError(
            "Unable to infer theme from input filename. Include one of: manual, disaster, remedy."
        )

    normalized_rows = [
        normalize_row(row, index, forced_theme=forced_theme)
        for index, row in enumerate(loaded_rows)
    ]
    results: list[EvalRow] = []

    for index, row in enumerate(normalized_rows, start=1):
        print(
            f"[{index}/{len(normalized_rows)}] Evaluating testcase {row['testcase_id']} ({row['theme']})",
            flush=True,
        )
        for question_type, column_name in QUESTION_FIELDS.items():
            prompt = row[column_name]
            if not prompt:
                continue

            (
                answer,
                retrieved_sources,
                raw_retrieved_chunks,
                selected_tools,
                cost,
            ) = call_chat_endpoint(
                chat_endpoint=chat_endpoint,
                question=prompt,
                testcase_id=str(row["testcase_id"]),
            )
            expected_tool, actual_tool, tool_called_correctly = evaluate_tool_usage(
                theme=row["theme"],
                retrieved_sources=retrieved_sources,
                selected_tools=selected_tools,
            )
            retrieved_context = build_retrieved_context(raw_retrieved_chunks)
            precision, recall, f1_score = compute_overlap_metrics(
                retrieved_context,
                row["Evidence"],
            )
            judgment = judge_answer(
                judge_endpoint=settings.judge_endpoint,
                api_key=settings.openrouter_api_key,
                judge_model=judge_model,
                judge_temperature=settings.judge_temperature,
                judge_prompt=judge_prompt,
                question=prompt,
                ground_truth=row["Ground_truth"],
                evidence=row["Evidence"],
                source=row["Source"],
                answer=answer,
            )

            results.append(
                EvalRow(
                    theme=row["theme"],
                    question_type=question_type,
                    testcase_id=str(row["testcase_id"]),
                    question=row["Question"],
                    human_question=row["Human_question"],
                    evaluated_prompt=prompt,
                    ground_truth=row["Ground_truth"],
                    evidence=row["Evidence"],
                    source=row["Source"],
                    model_response=answer,
                    retrieved_sources=retrieved_sources,
                    retrieved_context=retrieved_context,
                    expected_tool=expected_tool,
                    actual_tool=actual_tool,
                    tool_called_correctly=tool_called_correctly,
                    cost=cost,
                    precision=precision,
                    recall=recall,
                    f1_score=f1_score,
                    correctness=int(judgment.correctness),
                    helpfulness=int(judgment.helpfulness),
                    irrelevancy=int(judgment.irrelevancy),
                    extraneousness=int(judgment.extraneousness),
                    conciseness=int(judgment.conciseness),
                    judge_rationale=judgment.rationale,
                )
            )

    row_output = [row.to_dict() for row in results]
    summary_output = aggregate_results(results)

    write_csv(output_dir / "eval_rows.csv", row_output)
    write_json(output_dir / "eval_rows.json", row_output)
    write_csv(output_dir / "eval_summary.csv", summary_output)
    write_json(output_dir / "eval_summary.json", summary_output)

    print(f"Saved row-level results to {output_dir / 'eval_rows.csv'}")
    print(f"Saved summary results to {output_dir / 'eval_summary.csv'}")
    return 0
