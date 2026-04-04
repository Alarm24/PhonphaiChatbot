from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from langsmith import traceable

from .models import JudgeDecision
from .text_utils import normalize_text


def load_judge_prompt(prompt_path: str | None, default_prompt: str) -> str:
    if not prompt_path:
        return default_prompt
    return normalize_text(open(prompt_path, "r", encoding="utf-8").read())


def extract_json_object(text: str) -> str:
    text = normalize_text(text)
    if not text:
        raise ValueError("Judge returned an empty response.")

    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if match:
            return match.group(1)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Judge response does not contain JSON: {text}")
    return text[start : end + 1]


def call_openrouter_judge(
    judge_endpoint: str,
    api_key: str,
    judge_model: str,
    judge_temperature: float,
    prompt: str,
) -> JudgeDecision:
    payload = {
        "model": judge_model,
        "temperature": judge_temperature,
        "messages": [
            {
                "role": "system",
                "content": "You are an evaluation judge. Return only valid JSON that matches the schema.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "judge_decision",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "correctness": {"type": "boolean"},
                        "helpfulness": {"type": "boolean"},
                        "irrelevancy": {"type": "boolean"},
                        "extraneousness": {"type": "boolean"},
                        "conciseness": {"type": "boolean"},
                        "rationale": {"type": "string"},
                    },
                    "required": [
                        "correctness",
                        "helpfulness",
                        "irrelevancy",
                        "extraneousness",
                        "conciseness",
                        "rationale",
                    ],
                    "additionalProperties": False,
                },
            },
        },
    }
    request = urllib.request.Request(
        judge_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Judge request failed with HTTP {exc.code}: {error_body or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach judge endpoint '{judge_endpoint}'.") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected judge response shape: {body}") from exc

    return JudgeDecision.model_validate(json.loads(extract_json_object(content)))


@traceable(
    run_type="llm",
    metadata={"ls_provider": "openrouter", "ls_model_name": "google/gemini-2.5-flash"},
)
def judge_answer(
    judge_endpoint: str,
    api_key: str,
    judge_model: str,
    judge_temperature: float,
    judge_prompt: str,
    question: str,
    ground_truth: str,
    evidence: str,
    source: str,
    answer: str,
) -> JudgeDecision:
    prompt = f"""{judge_prompt}

Question:
{question}

Reference Answer:
{ground_truth}

Context Evidence:
{evidence}

Source Document:
{source}

Candidate Answer:
{answer}
"""
    return call_openrouter_judge(
        judge_endpoint=judge_endpoint,
        api_key=api_key,
        judge_model=judge_model,
        judge_temperature=judge_temperature,
        prompt=prompt,
    )
