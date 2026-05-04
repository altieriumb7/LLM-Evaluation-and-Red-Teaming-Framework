from pathlib import Path

from src.models import SUPPORTED_CATEGORIES
from src.prompts import load_prompt_file, load_prompt_files


ROOT = Path(__file__).resolve().parents[1]


def test_load_prompt_file_has_required_categories() -> None:
    cases = load_prompt_file(ROOT / "prompts" / "adversarial_prompts.yaml")

    assert len(cases) >= 6
    assert {case.category for case in cases} == SUPPORTED_CATEGORIES
    assert all(case.id for case in cases)
    assert all(case.expected_behavior for case in cases)


def test_load_multiple_prompt_files() -> None:
    cases = load_prompt_files(
        ["prompts/healthcare_prompts.yaml", "prompts/finance_prompts.yaml"],
        base_dir=ROOT,
    )

    assert len(cases) == 8
    assert len({case.id for case in cases}) == len(cases)

