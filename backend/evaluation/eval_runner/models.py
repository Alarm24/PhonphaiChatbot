from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

EXPECTED_THEMES = {"manual", "disaster", "remedy"}
QUESTION_FIELDS = {
    "llm_question": "Question",
    "human_question": "Human_question",
}
REQUIRED_COLUMNS = {"Ground_truth", "Evidence", "Source"}
EXPECTED_TOOL_BY_THEME = {
    "manual": "search_user_manuals",
    "disaster": "search_disaster_protocols",
    "remedy": "search_remedy_tickets",
}
DEFAULT_JUDGE_PROMPT = """Please evaluate these answers based on their accuracy and relevance to the provided passage that based on the Criteria:
1. The Answer is Correct concerning the Reference Answer. Do you agree or disagree? Determine if the given answer accurately matches the reference answer provided. The correctness here means the answer must directly correspond to the reference answer, ensuring factual accuracy.
2. The Answer Includes Relevant, Additional Information from the Context. Do you agree or disagree? Assess whether the answer provides extra details that are not only correct but also relevant and enhance the understanding of the topic as per the information given in the context.
3. The Answer Includes Additional, Irrelevant Information from the Context. Do you agree or disagree? Check if the answer contains extra details that, while related to the context, do not directly pertain to the question asked. This information is not necessary for answering the question and is considered a digression.
4. The Answer Includes Information Not Found in the Context. Do you agree or disagree? Evaluate if the answer includes any information that is not included in the context. This information, even if correct, is extraneous as it goes beyond the provided text and may indicate conjecture or assumption.
5. The Answer is Concise and Free of Redundancy. Do you agree or disagree? Evaluate the efficiency of the language used. Check if the response is direct and avoids repetitive explanations or unnecessary conversational filler. A concise answer should maximize the information-to-word ratio."""


@dataclass
class EvalSettings:
    openrouter_api_key: str
    chat_endpoint: str = "http://localhost:8080/api/v1/chat/"
    judge_endpoint: str = "https://openrouter.ai/api/v1/chat/completions"
    judge_model: str = "google/gemini-2.5-flash"
    judge_temperature: float = 0.0


class JudgeDecision(BaseModel):
    correctness: bool = Field(description="True if the answer is correct with respect to the reference.")
    helpfulness: bool = Field(
        description="True if the answer adds relevant details grounded in the context."
    )
    irrelevancy: bool = Field(
        description="True if the answer adds irrelevant details from the context."
    )
    extraneousness: bool = Field(
        description="True if the answer contains information not found in the context."
    )
    conciseness: bool = Field(
        description="True if the answer is concise and avoids redundancy."
    )
    rationale: str = Field(description="A brief explanation for the judgments.")


@dataclass
class EvalRow:
    theme: str
    question_type: str
    testcase_id: str
    question: str
    human_question: str
    evaluated_prompt: str
    ground_truth: str
    evidence: str
    source: str
    model_response: str
    retrieved_sources: list[dict[str, str]]
    expected_tool: str
    actual_tool: str
    tool_called_correctly: int
    precision: float
    recall: float
    f1_score: float
    correctness: int
    helpfulness: int
    irrelevancy: int
    extraneousness: int
    conciseness: int
    judge_rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "question_type": self.question_type,
            "testcase_id": self.testcase_id,
            "Question": self.question,
            "Human_question": self.human_question,
            "evaluated_prompt": self.evaluated_prompt,
            "Ground_truth": self.ground_truth,
            "Evidence": self.evidence,
            "Source": self.source,
            "model_response": self.model_response,
            "expected_tool": self.expected_tool,
            "actual_tool": self.actual_tool,
            "tool_called_correctly": self.tool_called_correctly,
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "f1_score": round(self.f1_score, 6),
            "correctness": self.correctness,
            "helpfulness": self.helpfulness,
            "irrelevancy": self.irrelevancy,
            "extraneousness": self.extraneousness,
            "conciseness": self.conciseness,
            "judge_rationale": self.judge_rationale,
            "retrieved_sources": json.dumps(self.retrieved_sources, ensure_ascii=False),
        }
