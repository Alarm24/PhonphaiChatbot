# Evaluation Runner

This folder contains a standalone QA evaluation runner for Phonphai.

## Structure
- `run_eval.py`: thin entrypoint
- `eval_runner/cli.py`: CLI arguments
- `eval_runner/pipeline.py`: orchestration
- `eval_runner/dataset.py`: testcase loading and normalization
- `eval_runner/client.py`: chatbot calls and tool-route checks
- `eval_runner/judge.py`: OpenRouter judge client
- `eval_runner/metrics.py`: lexical metrics, aggregation, output writers
- `eval_runner/models.py`: shared models and constants
- `eval_runner/settings.py`: `.env` loading

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
- Checks whether the agent routed to the expected tool for the theme:
  - `manual` -> `search_user_manuals`
  - `disaster` -> `search_disaster_protocols`
  - `remedy` -> `search_remedy_tickets`
  - The check is inferred from `sources.theme` returned by the agent
- Aggregates scores by `theme` and `question_type`.

## Required testcase columns
- `Question`
- `Human_question`
- `Ground_truth`
- `Evidence`
- `Source`

`Question` or `Human_question` may be blank on a row, but not both.

The theme is inferred from the input filename and must include one of:
- `manual`
- `disaster`
- `remedy`

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
