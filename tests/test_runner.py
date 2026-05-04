from pathlib import Path

from src.config import AppConfig, ProviderConfig, ReportingConfig, RunConfig
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
