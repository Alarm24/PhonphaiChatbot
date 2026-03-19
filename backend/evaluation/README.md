# Evaluation Runner

This folder contains a standalone QA evaluation runner for Phonphai.

## What it does
- Calls the running chatbot through the API gateway.
- Evaluates both `Question` and `Human_question` separately.
- Computes lexical `precision`, `recall`, and `f1_score` against `Ground_truth`.
- Uses an LLM judge for:
  - `correctness` (`1` = agree, higher is better)
  - `helpfulness` (`1` = agree, higher is better)
  - `irrelevancy` (`1` = agree, lower is better)
  - `extraneousness` (`1` = agree, lower is better)
  - `conciseness` (`1` = agree, higher is better)
- Aggregates scores by `theme` and `question_type`.

## Required testcase columns
- `theme`
- `Question`
- `Human_question`
- `Ground_truth`
- `Evidence`
- `Source`

`Question` or `Human_question` may be blank on a row, but not both.

## Supported input formats
- `.csv`
- `.json`
- `.jsonl`
- `.xlsx` if `openpyxl` is installed

## Run
Start the backend stack first so the API gateway is reachable.

```powershell
cd backend
python evaluation/run_eval.py --input path\to\testcases.csv
```

Optional flags:

```powershell
python evaluation/run_eval.py `
  --input path\to\testcases.xlsx `
  --output-dir evaluation/outputs/run_01 `
  --chat-endpoint http://localhost:8080/api/v1/chat/ `
  --judge-model google/gemini-2.5-flash `
  --limit 10
```

## Output files
- `eval_rows.csv`: one row per evaluated prompt
- `eval_rows.json`: same data in JSON
- `eval_summary.csv`: aggregated means by `theme x question_type`, plus `overall`
- `eval_summary.json`: same summary in JSON

## Notes
- The lexical metrics use normalized word overlap for space-delimited text.
- For Thai-heavy text, the runner falls back to character trigram overlap to avoid a hard dependency on a Thai tokenizer.
