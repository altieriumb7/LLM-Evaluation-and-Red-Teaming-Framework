from pathlib import Path

from src.benchmark import (
    build_demo_benchmark_report,
    load_benchmark_cases,
    load_benchmark_report,
    summarize_benchmark_cases,
    write_demo_benchmark_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def test_load_benchmark_cases() -> None:
    cases = load_benchmark_cases(ROOT / "benchmarks" / "qualitative_redteam_cases.yaml")
    assert len(cases) == 8
    assert len({case.id for case in cases}) == len(cases)


def test_benchmark_summary_metrics() -> None:
    cases = load_benchmark_cases(ROOT / "benchmarks" / "qualitative_redteam_cases.yaml")
    summary = summarize_benchmark_cases(cases)
    assert summary["total_cases"] == 8
    assert summary["pass_count"] == 6
    assert summary["fail_count"] == 0
    assert summary["warning_count"] == 2
    assert summary["pass_rate"] == 0.75


def test_demo_benchmark_generation_is_deterministic() -> None:
    cases = load_benchmark_cases(ROOT / "benchmarks" / "qualitative_redteam_cases.yaml")
    report_a = build_demo_benchmark_report(cases, source_path="benchmarks/qualitative_redteam_cases.yaml")
    report_b = build_demo_benchmark_report(cases, source_path="benchmarks/qualitative_redteam_cases.yaml")
    assert report_a == report_b


def test_benchmark_reports_written_to_output_dir(tmp_path) -> None:
    cases = load_benchmark_cases(ROOT / "benchmarks" / "qualitative_redteam_cases.yaml")
    report = build_demo_benchmark_report(cases, source_path="benchmarks/qualitative_redteam_cases.yaml")
    output_dir = tmp_path / "custom_reports_dir"
    paths = write_demo_benchmark_artifacts(report, output_dir)

    assert Path(paths["json"]).exists()
    assert Path(paths["csv"]).exists()
    assert Path(paths["markdown"]).exists()

    loaded = load_benchmark_report(paths["json"])
    assert loaded["summary"]["total_cases"] == 8
