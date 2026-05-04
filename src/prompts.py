from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.models import EvaluationCase, SUPPORTED_CATEGORIES


REQUIRED_PROMPT_FIELDS = {"id", "category", "prompt", "expected_behavior"}


def load_prompt_file(path: str | Path) -> list[EvaluationCase]:
    prompt_path = Path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    raw = yaml.safe_load(prompt_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Prompt file must be a mapping: {prompt_path}")

    entries = raw.get("prompts")
    if not isinstance(entries, list):
        raise ValueError(f"Prompt file must contain a 'prompts' list: {prompt_path}")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Prompt entry {index} in {prompt_path} must be a mapping.")
        missing = REQUIRED_PROMPT_FIELDS - set(entry)
        if missing:
            raise ValueError(f"Prompt entry {index} in {prompt_path} is missing: {', '.join(sorted(missing))}")

        case_id = str(entry["id"])
        if case_id in seen_ids:
            raise ValueError(f"Duplicate prompt id '{case_id}' in {prompt_path}")
        seen_ids.add(case_id)

        category = str(entry["category"])
        if category not in SUPPORTED_CATEGORIES:
            allowed = ", ".join(sorted(SUPPORTED_CATEGORIES))
            raise ValueError(f"Unsupported category '{category}' in {case_id}. Allowed: {allowed}")

        tags_raw = entry.get("tags", [])
        if not isinstance(tags_raw, list):
            raise ValueError(f"tags must be a list for prompt id '{case_id}'.")

        checks_raw = entry.get("checks", {})
        if not isinstance(checks_raw, dict):
            raise ValueError(f"checks must be a mapping for prompt id '{case_id}'.")

        cases.append(
            EvaluationCase(
                id=case_id,
                category=category,
                prompt=str(entry["prompt"]),
                expected_behavior=str(entry["expected_behavior"]),
                risk_level=str(entry.get("risk_level", "medium")),
                tags=[str(tag) for tag in tags_raw],
                checks=checks_raw,
                source_file=str(prompt_path),
            )
        )

    return cases


def load_prompt_files(paths: list[str | Path], base_dir: str | Path | None = None, max_cases: int | None = None) -> list[EvaluationCase]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for path in paths:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = root / resolved
        for case in load_prompt_file(resolved):
            if case.id in seen_ids:
                raise ValueError(f"Duplicate prompt id across prompt files: {case.id}")
            seen_ids.add(case.id)
            cases.append(case)

    if max_cases is not None:
        return cases[: int(max_cases)]
    return cases

