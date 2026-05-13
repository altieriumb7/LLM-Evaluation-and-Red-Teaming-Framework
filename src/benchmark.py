from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


VALID_STATUSES = {"PASS", "FAIL", "WARNING"}


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    category: str
    prompt: str
    expected_behavior: str
    observed_output: str
    qualitative_assessment: str
    status: str
    notes: str = ""


def _safe_status(value: str) -> str:
    normalized = str(value).upper().strip()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"Invalid benchmark status '{value}'. Expected one of {sorted(VALID_STATUSES)}.")
    return normalized


def load_benchmark_cases(path: str | Path) -> list[BenchmarkCase]:
    benchmark_path = Path(path)
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    raw = yaml.safe_load(benchmark_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Benchmark file root must be a mapping.")

    entries = raw.get("cases")
    if not isinstance(entries, list):
        raise ValueError("Benchmark file must contain a 'cases' list.")

    seen_ids: set[str] = set()
    cases: list[BenchmarkCase] = []
    for idx, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Benchmark case #{idx} must be a mapping.")
        required = {
            "id",
            "category",
            "prompt",
            "expected_behavior",
            "observed_output",
            "qualitative_assessment",
            "status",
        }
        missing = required - set(entry.keys())
        if missing:
            raise ValueError(f"Benchmark case #{idx} missing fields: {', '.join(sorted(missing))}")

        case_id = str(entry["id"])
        if case_id in seen_ids:
            raise ValueError(f"Duplicate benchmark case id: {case_id}")
        seen_ids.add(case_id)

        cases.append(
            BenchmarkCase(
                id=case_id,
                category=str(entry["category"]),
                prompt=str(entry["prompt"]),
                expected_behavior=str(entry["expected_behavior"]),
                observed_output=str(entry["observed_output"]),
                qualitative_assessment=str(entry["qualitative_assessment"]),
                status=_safe_status(str(entry["status"])),
                notes=str(entry.get("notes", "")),
            )
        )
    return cases


def summarize_benchmark_cases(cases: list[BenchmarkCase]) -> dict[str, Any]:
    total = len(cases)
    pass_count = sum(1 for case in cases if case.status == "PASS")
    fail_count = sum(1 for case in cases if case.status == "FAIL")
    warning_count = sum(1 for case in cases if case.status == "WARNING")
    categories = sorted({case.category for case in cases})
    pass_rate = round(pass_count / total, 4) if total else 0.0
    by_category: dict[str, dict[str, int]] = {}
    for case in cases:
        stats = by_category.setdefault(case.category, {"total": 0, "pass": 0, "fail": 0, "warning": 0})
        stats["total"] += 1
        stats[case.status.lower()] += 1

    return {
        "total_cases": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warning_count": warning_count,
        "pass_rate": pass_rate,
        "categories_covered": categories,
        "category_breakdown": by_category,
    }


def build_demo_benchmark_report(cases: list[BenchmarkCase], source_path: str) -> dict[str, Any]:
    summary = summarize_benchmark_cases(cases)
    return {
        "metadata": {
            "mode": "demo",
            "is_sample": True,
            "source_cases_path": source_path,
            "generated_at": "deterministic-demo",
            "description": "Curated sample benchmark for public demo. No external API calls are performed.",
        },
        "summary": summary,
        "results": [
            {
                "id": case.id,
                "category": case.category,
                "prompt": case.prompt,
                "expected_behavior": case.expected_behavior,
                "observed_output": case.observed_output,
                "qualitative_assessment": case.qualitative_assessment,
                "status": case.status,
                "notes": case.notes,
            }
            for case in cases
        ],
    }


def write_demo_benchmark_artifacts(
    report: dict[str, Any],
    output_dir: str | Path,
    json_name: str = "demo_results.json",
    csv_name: str = "demo_summary.csv",
    markdown_name: str = "qualitative_case_gallery.md",
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    json_path = output / json_name
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    csv_path = output / csv_name
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        summary = report["summary"]
        writer.writerow(["total_cases", summary["total_cases"]])
        writer.writerow(["pass_count", summary["pass_count"]])
        writer.writerow(["fail_count", summary["fail_count"]])
        writer.writerow(["warning_count", summary["warning_count"]])
        writer.writerow(["pass_rate", summary["pass_rate"]])
        writer.writerow(["categories_covered", ",".join(summary["categories_covered"])])

    markdown_path = output / markdown_name
    lines = [
        "# Demo Qualitative Case Gallery",
        "",
        "_This file is generated from deterministic demo artifacts._",
        "",
        "## Summary",
        "",
        f"- Total cases: {report['summary']['total_cases']}",
        f"- Pass: {report['summary']['pass_count']}",
        f"- Fail: {report['summary']['fail_count']}",
        f"- Warning: {report['summary']['warning_count']}",
        f"- Pass rate: {report['summary']['pass_rate']:.1%}",
        "",
    ]
    for item in report["results"]:
        lines.extend(
            [
                f"### {item['id']} [{item['status']}]",
                "",
                f"- Category: {item['category']}",
                f"- Prompt: {item['prompt']}",
                f"- Expected behavior: {item['expected_behavior']}",
                f"- Observed/demo output: {item['observed_output']}",
                f"- Assessment: {item['qualitative_assessment']}",
                f"- Notes: {item['notes']}",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(markdown_path)}


def load_benchmark_report(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(f"Benchmark report not found: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "summary" not in payload or "results" not in payload:
        raise ValueError("Invalid benchmark report format.")
    return payload
