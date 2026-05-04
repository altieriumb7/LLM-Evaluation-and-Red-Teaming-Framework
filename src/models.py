from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_CATEGORIES = {
    "hallucination",
    "prompt_injection",
    "unsafe_instruction_following",
    "bias_stereotyping",
    "privacy_leakage",
    "jailbreak",
}


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    category: str
    prompt: str
    expected_behavior: str
    risk_level: str = "medium"
    tags: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    source_file: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    case_id: str
    provider: str
    model: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    message: str
    evidence: str
    severity: str = "medium"


@dataclass(frozen=True)
class ScoreResult:
    case_id: str
    category: str
    passed: bool
    label: str
    score: float
    findings: list[RuleFinding]
    scoring_mode: str = "rule_based"
    judge_feedback: str | None = None


@dataclass(frozen=True)
class EvaluationRecord:
    case: EvaluationCase
    response: ModelResponse
    score: ScoreResult

