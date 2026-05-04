from pathlib import Path
from dataclasses import replace

import pytest

from src.config import load_config, validate_config


ROOT = Path(__file__).resolve().parents[1]


def test_load_default_config() -> None:
    config = load_config(ROOT / "evals" / "config.yaml")

    assert config.provider.type == "mock"
    assert config.run.prompt_files == ["prompts/adversarial_prompts.yaml"]
    assert config.scoring.rule_based


def test_config_validation_rejects_bad_provider() -> None:
    config = load_config(ROOT / "evals" / "config.yaml")
    bad_config = replace(config, provider=replace(config.provider, type="unknown"))

    with pytest.raises(ValueError, match="provider.type"):
        validate_config(bad_config, base_dir=ROOT)

    validate_config(config, base_dir=ROOT)
