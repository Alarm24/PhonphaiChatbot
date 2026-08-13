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
- Uses an LLM judge with a CHIE+C rubric for:
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

## CHIE+C evaluation rubric
The judge prompt is based on CHIE, an LLM-based evaluation framework for generative machine reading comprehension introduced by Phatthiyaphaibun et al. (2024). CHIE evaluates answers with four binary aspects:
- **Correctness**: whether the response matches the reference answer.
- **Helpfulness**: whether the response adds relevant, useful information grounded in the context.
- **Irrelevancy**: whether the response adds unnecessary information from the context. Lower is better.
- **Extraneousness**: whether the response adds information not found in the context. Lower is better.

This runner uses **CHIE+C**, where the added **+C** is **Conciseness**. Conciseness checks whether the answer is direct, non-repetitive, and free from unnecessary filler while preserving the required information.

The LLM judge returns binary decisions for each aspect. `Agree` is stored as `1`, and `Disagree` is stored as `0`. For `correctness`, `helpfulness`, and `conciseness`, higher means better. For `irrelevancy` and `extraneousness`, lower means better.

Reference: Phatthiyaphaibun, W. et al. (2024). "CHIE: Generative MRC Evaluation for in-context QA with Correctness, Helpfulness, Irrelevancy, and Extraneousness Aspects." Proceedings of the 2nd GenBench Workshop on Generalisation (Benchmarking) in NLP, pages 154-164. https://aclanthology.org/2024.genbench-1.10/

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
uv sync --project evaluation
uv run --project evaluation python evaluation/run_eval.py --input path\to\testcases.csv
```

Optional flags:

```powershell
uv run --project evaluation python evaluation/run_eval.py `
  --input path\to\testcases.xlsx `
  --output-dir outputs/run_01 `
  --chat-endpoint http://localhost:8080/api/v1/chat/ `
  --judge-model google/gemini-2.5-flash `
  --limit 10
```

## Retrieval Tuning
Run retrieval tuning through the same `uv` project so retriever-side dependencies such as `langchain-huggingface` are available.

Hybrid-only tuning sweeps semantic weight (`alpha`) and retrieval `k`, without running the reranker:

```powershell
cd backend
uv sync --project evaluation
uv run --project evaluation python evaluation/run_retrieval_hybrid_tuning.py `
  --max-k 100 `
  --qdrant-host localhost `
  --workers 10
```

Rerank-only tuning uses one fixed semantic weight and sweeps rerank `k`:

```powershell
cd backend
uv sync --project evaluation
uv run --project evaluation python evaluation/run_retrieval_rerank_tuning.py `
  --max-k 100 `
  --qdrant-host localhost `
  --rerank-device cpu `
  --semantic-weight 0.6 `
  --workers 4
```

Notes:
- `run_retrieval_hybrid_tuning.py` is for hybrid alpha/k evaluation only.
- `run_retrieval_rerank_tuning.py` is for rerank k evaluation only and does not sweep alpha.
- With `--rerank-device cuda`, the rerank runner forces `--workers 1` on Windows to avoid native PyTorch/CUDA crashes.
- The older combined `run_retrieval_tuning.py` is still available if you need both stages together.

## Output files
- `eval_rows.csv`: one row per evaluated prompt
- `eval_rows.json`: same data in JSON
- `eval_summary.csv`: aggregated means by `theme x question_type`, plus `overall`
- `eval_summary.json`: same summary in JSON

## Notes
- The lexical metrics use normalized word overlap for space-delimited text.
- For Thai-heavy text, the runner falls back to character trigram overlap to avoid a hard dependency on a Thai tokenizer.
