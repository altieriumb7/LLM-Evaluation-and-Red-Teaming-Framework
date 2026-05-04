from src.config import JudgeConfig
from src.scoring import LLMJudgeScorer


def test_llm_judge_parser_accepts_json_fence() -> None:
    scorer = LLMJudgeScorer(JudgeConfig())

    parsed = scorer._parse_judge_json(
        '```json\n{"passed": false, "reason": "unsafe", "evidence": "detail", "severity": "high"}\n```'
    )

    assert parsed["passed"] is False
    assert parsed["severity"] == "high"

