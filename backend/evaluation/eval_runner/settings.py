from __future__ import annotations

import os
from pathlib import Path

from .models import EvalSettings
from .text_utils import normalize_text


def find_dotenv(start_dir: Path) -> Path | None:
    for directory in (start_dir, *start_dir.parents):
        candidate = directory / ".env"
        if candidate.exists():
            return candidate
    return None


def load_dotenv_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_eval_settings() -> EvalSettings:
    dotenv_path = find_dotenv(Path(__file__).resolve().parent)
    if dotenv_path is not None:
        load_dotenv_file(dotenv_path)

    api_key = normalize_text(os.getenv("OPENROUTER_API_KEY"))
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required in environment or .env")

    raw_temp = normalize_text(os.getenv("EVAL_JUDGE_TEMPERATURE"))
    judge_temperature = float(raw_temp) if raw_temp else 0.0

    return EvalSettings(
        openrouter_api_key=api_key,
        chat_endpoint=normalize_text(os.getenv("EVAL_CHAT_ENDPOINT"))
        or "http://localhost:8080/api/v1/chat/",
        judge_endpoint=normalize_text(os.getenv("EVAL_JUDGE_ENDPOINT"))
        or "https://openrouter.ai/api/v1/chat/completions",
        judge_model=normalize_text(os.getenv("EVAL_JUDGE_MODEL"))
        or "google/gemini-3-flash-preview",
        judge_temperature=judge_temperature,
    )
