from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProviderConfig:
    type: str = "mock"
    model: str = "mock-redteam-v1"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    timeout_seconds: int = 60
    temperature: float = 0.0
    max_tokens: int = 700
    mock_profile: str = "mixed"


@dataclass(frozen=True)
class JudgeConfig:
    enabled: bool = False
    provider: str = "openai_compatible"
    model: str = "gpt-4.1-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"


@dataclass(frozen=True)
class ScoringConfig:
    rule_based: bool = True
    llm_judge: JudgeConfig = field(default_factory=JudgeConfig)


@dataclass(frozen=True)
class ReportingConfig:
    formats: list[str] = field(default_factory=lambda: ["markdown", "json"])
    include_passed_examples: bool = False


@dataclass(frozen=True)
class RunConfig:
    name: str = "mock_redteam"
    output_dir: str = "reports"
    prompt_files: list[str] = field(default_factory=lambda: ["prompts/adversarial_prompts.yaml"])
    max_cases: int | None = None


@dataclass(frozen=True)
class OptionalIntegrationsConfig:
    deepeval: bool = False
    langsmith: bool = False


@dataclass(frozen=True)
class AppConfig:
    run: RunConfig = field(default_factory=RunConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    optional_integrations: OptionalIntegrationsConfig = field(default_factory=OptionalIntegrationsConfig)


def _ensure_mapping(value: Any, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{section}' must be a mapping.")
    return value


def _ensure_list(value: Any, section: str) -> list[Any]:
    if isinstance(value, list):
        return value
    raise ValueError(f"Config field '{section}' must be a list.")


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping.")

    run_raw = _ensure_mapping(raw.get("run"), "run")
    provider_raw = _ensure_mapping(raw.get("provider"), "provider")
    scoring_raw = _ensure_mapping(raw.get("scoring"), "scoring")
    reporting_raw = _ensure_mapping(raw.get("reporting"), "reporting")
    integrations_raw = _ensure_mapping(raw.get("optional_integrations"), "optional_integrations")

    llm_judge_raw = _ensure_mapping(scoring_raw.get("llm_judge"), "scoring.llm_judge")

    run_config = RunConfig(
        name=str(run_raw.get("name", "mock_redteam")),
        output_dir=str(run_raw.get("output_dir", "reports")),
        prompt_files=[str(item) for item in _ensure_list(run_raw.get("prompt_files", ["prompts/adversarial_prompts.yaml"]), "run.prompt_files")],
        max_cases=run_raw.get("max_cases"),
    )

    provider_config = ProviderConfig(
        type=str(provider_raw.get("type", "mock")),
        model=str(provider_raw.get("model", "mock-redteam-v1")),
        base_url=str(provider_raw.get("base_url", "https://api.openai.com/v1")),
        api_key_env=str(provider_raw.get("api_key_env", "OPENAI_API_KEY")),
        timeout_seconds=int(provider_raw.get("timeout_seconds", 60)),
        temperature=float(provider_raw.get("temperature", 0.0)),
        max_tokens=int(provider_raw.get("max_tokens", 700)),
        mock_profile=str(provider_raw.get("mock_profile", "mixed")),
    )

    judge_config = JudgeConfig(
        enabled=bool(llm_judge_raw.get("enabled", False)),
        provider=str(llm_judge_raw.get("provider", "openai_compatible")),
        model=str(llm_judge_raw.get("model", "gpt-4.1-mini")),
        api_key_env=str(llm_judge_raw.get("api_key_env", "OPENAI_API_KEY")),
        base_url=str(llm_judge_raw.get("base_url", "https://api.openai.com/v1")),
    )

    scoring_config = ScoringConfig(
        rule_based=bool(scoring_raw.get("rule_based", True)),
        llm_judge=judge_config,
    )

    reporting_config = ReportingConfig(
        formats=[str(item) for item in _ensure_list(reporting_raw.get("formats", ["markdown", "json"]), "reporting.formats")],
        include_passed_examples=bool(reporting_raw.get("include_passed_examples", False)),
    )

    integrations_config = OptionalIntegrationsConfig(
        deepeval=bool(integrations_raw.get("deepeval", False)),
        langsmith=bool(integrations_raw.get("langsmith", False)),
    )

    config = AppConfig(
        run=run_config,
        provider=provider_config,
        scoring=scoring_config,
        reporting=reporting_config,
        optional_integrations=integrations_config,
    )
    validate_config(config, base_dir=config_path.parent.parent if config_path.parent.name == "evals" else Path.cwd())
    return config


def validate_config(config: AppConfig, base_dir: str | Path | None = None) -> None:
    if config.provider.type not in {"mock", "openai_compatible"}:
        raise ValueError("provider.type must be 'mock' or 'openai_compatible'.")
    if config.provider.mock_profile not in {"robust", "mixed", "vulnerable"}:
        raise ValueError("provider.mock_profile must be 'robust', 'mixed', or 'vulnerable'.")
    if config.run.max_cases is not None and int(config.run.max_cases) <= 0:
        raise ValueError("run.max_cases must be a positive integer when provided.")
    if not config.run.prompt_files:
        raise ValueError("At least one prompt file is required.")
    if not config.scoring.rule_based and not config.scoring.llm_judge.enabled:
        raise ValueError("At least one scoring mode must be enabled.")
    for fmt in config.reporting.formats:
        if fmt not in {"markdown", "json", "html"}:
            raise ValueError("reporting.formats may only include markdown, json, or html.")

    if base_dir is not None:
        root = Path(base_dir)
        missing = [path for path in config.run.prompt_files if not (root / path).exists()]
        if missing:
            raise FileNotFoundError(f"Prompt file(s) not found: {', '.join(missing)}")

