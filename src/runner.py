from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import AppConfig, load_config
from src.models import EvaluationRecord
from src.prompts import load_prompt_files
from src.providers import build_provider
from src.reporting import records_to_dict, write_reports
from src.scoring import LLMJudgeScorer, RuleBasedScorer


def run_evaluation(config: AppConfig, base_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    cases = load_prompt_files(config.run.prompt_files, base_dir=root, max_cases=config.run.max_cases)
    provider = build_provider(config.provider)

    if not config.scoring.rule_based and config.scoring.llm_judge.enabled:
        scorer = LLMJudgeScorer(config.scoring.llm_judge)
    else:
        scorer = RuleBasedScorer()

    records: list[EvaluationRecord] = []
    for case in cases:
        response = provider.generate(case)
        score = scorer.score(case, response)
        records.append(EvaluationRecord(case=case, response=response, score=score))

    metadata = {
        "run_name": config.run.name,
        "provider": provider.name,
        "model": provider.model,
        "scoring_mode": scorer.scoring_mode,
        "prompt_files": config.run.prompt_files,
    }
    report = records_to_dict(records, metadata)
    output_dir = root / config.run.output_dir
    report_paths = write_reports(
        report,
        output_dir=output_dir,
        run_name=config.run.name,
        formats=config.reporting.formats,
        include_passed_examples=config.reporting.include_passed_examples,
    )
    return {"report": report, "paths": report_paths}


def run_evaluation_from_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    config = load_config(path)
    root = path.parent.parent if path.parent.name == "evals" else Path.cwd()
    return run_evaluation(config, base_dir=root)
