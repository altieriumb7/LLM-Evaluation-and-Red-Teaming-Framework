from pathlib import Path

import requests

from src.config import AppConfig, ProviderConfig, ReportingConfig, RunConfig
from src.models import ModelResponse
from src.runner import run_evaluation


ROOT = Path(__file__).resolve().parents[1]


def test_run_mock_evaluation_and_write_reports() -> None:
    config = AppConfig(
        run=RunConfig(
            name="test_mock_run",
            output_dir="reports",
            prompt_files=["prompts/adversarial_prompts.yaml"],
            max_cases=6,
        ),
        provider=ProviderConfig(type="mock", mock_profile="vulnerable"),
        reporting=ReportingConfig(formats=["json", "markdown"]),
    )

    result = run_evaluation(config, base_dir=ROOT)

    assert result["report"]["summary"]["total_prompts"] == 6
    assert result["report"]["summary"]["failures"] == 6
    assert Path(result["paths"]["json"]).exists()
    assert Path(result["paths"]["markdown"]).exists()


def test_run_evaluation_records_runtime_error_and_continues(monkeypatch) -> None:
    class FailingProvider:
        name = "failing_provider"
        model = "test-model"

        def generate(self, case):
            if case.id.endswith("01"):
                raise requests.RequestException("simulated outage")
            return ModelResponse(
                case_id=case.id,
                provider=self.name,
                model=self.model,
                text="I cannot provide unsafe instructions.",
            )

    monkeypatch.setattr("src.runner.build_provider", lambda _: FailingProvider())

    config = AppConfig(
        run=RunConfig(
            name="test_runtime_error",
            output_dir="reports",
            prompt_files=["prompts/adversarial_prompts.yaml"],
            max_cases=2,
        ),
        provider=ProviderConfig(type="mock", mock_profile="mixed"),
        reporting=ReportingConfig(formats=[]),
    )

    result = run_evaluation(config, base_dir=ROOT)

    assert result["report"]["summary"]["total_prompts"] == 2
    assert any(
        finding["rule_id"] == "runtime.error"
        for item in result["report"]["results"]
        for finding in item["findings"]
    )
