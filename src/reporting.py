from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.models import EvaluationRecord


MITIGATIONS = {
    "hallucination": "Add retrieval grounding, calibrated uncertainty language, source checks, and abstention criteria.",
    "prompt_injection": "Enforce instruction hierarchy, isolate retrieved content, and add input/output filtering for injected commands.",
    "unsafe_instruction_following": "Strengthen safety policies, refuse operational harm, and route high-risk requests to safe alternatives.",
    "bias_stereotyping": "Use fairness test suites, protected-class language checks, and counterfactual evaluation before release.",
    "privacy_leakage": "Redact sensitive data, disable secret exposure, minimize logs, and add PII/credential detectors.",
    "jailbreak": "Harden system prompts, add policy-aware refusal checks, and test known jailbreak patterns continuously.",
}


def summarize_records(records: list[EvaluationRecord]) -> dict[str, Any]:
    total = len(records)
    failures = [record for record in records if not record.score.passed]
    category_stats: dict[str, dict[str, Any]] = {}

    for record in records:
        stats = category_stats.setdefault(
            record.case.category,
            {"total": 0, "failures": 0, "passes": 0, "violation_rate": 0.0},
        )
        stats["total"] += 1
        if record.score.passed:
            stats["passes"] += 1
        else:
            stats["failures"] += 1

    for stats in category_stats.values():
        stats["violation_rate"] = round(stats["failures"] / stats["total"], 4) if stats["total"] else 0.0

    return {
        "total_prompts": total,
        "passes": total - len(failures),
        "failures": len(failures),
        "total_violation_rate": round(len(failures) / total, 4) if total else 0.0,
        "category_stats": dict(sorted(category_stats.items())),
    }


def records_to_dict(records: list[EvaluationRecord], run_metadata: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_records(records)
    return {
        "metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            **run_metadata,
        },
        "summary": summary,
        "results": [
            {
                "id": record.case.id,
                "category": record.case.category,
                "risk_level": record.case.risk_level,
                "tags": record.case.tags,
                "prompt": record.case.prompt,
                "expected_behavior": record.case.expected_behavior,
                "provider": record.response.provider,
                "model": record.response.model,
                "response": record.response.text,
                "response_excerpt": excerpt(record.response.text),
                "label": record.score.label,
                "passed": record.score.passed,
                "score": record.score.score,
                "scoring_mode": record.score.scoring_mode,
                "findings": [
                    {
                        "rule_id": finding.rule_id,
                        "message": finding.message,
                        "evidence": finding.evidence,
                        "severity": finding.severity,
                    }
                    for finding in record.score.findings
                ],
                "recommended_mitigation": MITIGATIONS.get(record.case.category, "Review application policy and add targeted regression tests."),
            }
            for record in records
        ],
    }


def excerpt(text: str, limit: int = 260) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def render_markdown_report(report: dict[str, Any], include_passed_examples: bool = False) -> str:
    summary = report["summary"]
    lines = [
        f"# LLM Red-Team Evaluation Report: {report['metadata'].get('run_name', 'evaluation')}",
        "",
        "## Summary",
        "",
        f"- Total prompts tested: {summary['total_prompts']}",
        f"- Passed: {summary['passes']}",
        f"- Failed: {summary['failures']}",
        f"- Total violation rate: {summary['total_violation_rate']:.1%}",
        f"- Scoring mode: {report['metadata'].get('scoring_mode', 'rule_based')}",
        "",
        "## Failures By Category",
        "",
        "| Category | Prompts | Failures | Violation Rate | Recommended Mitigation |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    for category, stats in summary["category_stats"].items():
        lines.append(
            f"| {category} | {stats['total']} | {stats['failures']} | {stats['violation_rate']:.1%} | {MITIGATIONS.get(category, '')} |"
        )

    examples = [item for item in report["results"] if not item["passed"] or include_passed_examples]
    lines.extend(["", "## Examples", ""])
    if not examples:
        lines.append("No failing examples were detected by the active scorer.")
    for item in examples[:12]:
        lines.extend(
            [
                f"### {item['id']} ({item['category']}) - {item['label']}",
                "",
                f"**Prompt:** {item['prompt']}",
                "",
                f"**Response excerpt:** {item['response_excerpt']}",
                "",
                f"**Expected behavior:** {item['expected_behavior']}",
                "",
                f"**Recommended mitigation:** {item['recommended_mitigation']}",
                "",
            ]
        )
        if item["findings"]:
            lines.append("**Findings:**")
            for finding in item["findings"]:
                lines.append(f"- {finding['rule_id']}: {finding['message']} Evidence: `{finding['evidence']}`")
            lines.append("")

    lines.extend(
        [
            "## Ethical Use",
            "",
            "These prompts are intended for authorized evaluation of systems you own or have permission to test. "
            "Do not use this framework to extract secrets, bypass controls on third-party systems, or generate harmful instructions.",
            "",
        ]
    )
    return "\n".join(lines)


def render_html_report(report: dict[str, Any], include_passed_examples: bool = False) -> str:
    markdown = render_markdown_report(report, include_passed_examples)
    escaped = html.escape(markdown)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>LLM Red-Team Evaluation Report</title>"
        "<style>body{font-family:Arial,sans-serif;max-width:980px;margin:40px auto;line-height:1.5;}"
        "pre{white-space:pre-wrap;background:#f6f8fa;padding:16px;border-radius:8px;}</style>"
        "</head><body><pre>"
        f"{escaped}"
        "</pre></body></html>"
    )


def write_reports(
    report: dict[str, Any],
    output_dir: str | Path,
    run_name: str,
    formats: list[str],
    include_passed_examples: bool = False,
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    if "json" in formats:
        json_path = output / f"{run_name}.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        paths["json"] = str(json_path)

    if "markdown" in formats:
        md_path = output / f"{run_name}.md"
        md_path.write_text(render_markdown_report(report, include_passed_examples), encoding="utf-8")
        paths["markdown"] = str(md_path)

    if "html" in formats:
        html_path = output / f"{run_name}.html"
        html_path.write_text(render_html_report(report, include_passed_examples), encoding="utf-8")
        paths["html"] = str(html_path)

    return paths

