from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RuntimeSettings:
    demo_mode: bool
    allow_live_runs: bool
    default_config_path: str
    reports_dir: str
    benchmark_mode: str
    openai_api_key_present: bool

    @property
    def reports_path(self) -> Path:
        return Path(self.reports_dir)


def load_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings(
        demo_mode=_env_flag("DEMO_MODE", True),
        allow_live_runs=_env_flag("ALLOW_LIVE_RUNS", False),
        default_config_path=os.getenv("DEFAULT_CONFIG_PATH", "evals/config.yaml"),
        reports_dir=os.getenv("REPORTS_DIR", "reports"),
        benchmark_mode=os.getenv("BENCHMARK_MODE", "demo"),
        openai_api_key_present=bool(os.getenv("OPENAI_API_KEY")),
    )


def live_execution_allowed(settings: RuntimeSettings, requires_external_api: bool) -> bool:
    if not requires_external_api:
        return True
    return (not settings.demo_mode) and settings.allow_live_runs
