from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import run_evaluation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phonphai QA evaluation with lexical metrics and LLM-as-a-judge."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to testcase file (.csv, .json, .jsonl, or .xlsx if openpyxl is installed).",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation/outputs",
        help="Directory for row-level and summary outputs.",
    )
    parser.add_argument(
        "--chat-endpoint",
        default=None,
        help="Override the chat endpoint. Default comes from EVAL_CHAT_ENDPOINT or .env.",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Override the judge model. Default comes from EVAL_JUDGE_MODEL or .env.",
    )
    parser.add_argument(
        "--judge-prompt-file",
        default=None,
        help="Optional text file containing the LLM judge instructions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only evaluate the first N testcases after loading the dataset.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_evaluation(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        chat_endpoint_override=args.chat_endpoint,
        judge_model_override=args.judge_model,
        judge_prompt_file=args.judge_prompt_file,
        limit=args.limit,
    )


if __name__ == "__main__":
    sys.exit(main())
