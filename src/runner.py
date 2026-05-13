from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import requests

from src.config import AppConfig, load_config
from src.config import infer_config_base_dir
from src.models import EvaluationRecord, ModelResponse, RuleFinding, ScoreResult
from src.prompts import load_prompt_files
from src.providers import build_provider
from src.reporting import records_to_dict, write_reports
from src.scoring import LLMJudgeScorer, RuleBasedScorer

logger = logging.getLogger(__name__)


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
        response: ModelResponse | None = None
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = provider.generate(case)
                score = scorer.score(case, response)
                break
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                last_error = exc
                if attempt == 1:
                    logger.warning("Evaluation failed for case %s after retries: %s", case.id, exc)
                else:
                    logger.info("Retrying case %s after error: %s", case.id, exc)
        else:
            message = f"{type(last_error).__name__}: {last_error}" if last_error is not None else "Unknown evaluation error."
            response = ModelResponse(
                case_id=case.id,
                provider=provider.name,
                model=provider.model,
                text=f"[evaluation_error] {message}",
                metadata={"error": message},
            )
            score = ScoreResult(
                case_id=case.id,
                category=case.category,
                passed=False,
                label="FAIL",
                score=0.0,
                findings=[
                    RuleFinding(
                        rule_id="runtime.error",
                        message="Case failed during provider or scoring execution.",
                        evidence=message[:240],
                        severity="high",
                    )
                ],
                scoring_mode=getattr(scorer, "scoring_mode", "unknown"),
            )
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
    root = infer_config_base_dir(path, config.run.prompt_files)
    return run_evaluation(config, base_dir=root)
