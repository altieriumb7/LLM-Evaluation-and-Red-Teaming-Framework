from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st

from src.benchmark import (
    build_demo_benchmark_report,
    load_benchmark_cases,
    load_benchmark_report,
    summarize_benchmark_cases,
    write_demo_benchmark_artifacts,
)
from src.config import AppConfig, ProviderConfig, ReportingConfig, RunConfig, infer_config_base_dir, load_config
from src.reporting import render_html_report, render_markdown_report
from src.runner import run_evaluation
from src.runtime_settings import RuntimeSettings, live_execution_allowed, load_runtime_settings


ROOT = Path(__file__).parent
PROMPT_SETS = {
    "General red-team": ["prompts/adversarial_prompts.yaml"],
    "Healthcare safety": ["prompts/healthcare_prompts.yaml"],
    "Finance safety": ["prompts/finance_prompts.yaml"],
    "All prompt sets": [
        "prompts/adversarial_prompts.yaml",
        "prompts/healthcare_prompts.yaml",
        "prompts/finance_prompts.yaml",
    ],
}
BENCHMARK_CASES_PATH = ROOT / "benchmarks" / "qualitative_redteam_cases.yaml"


def resolve_from_root(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT / path


def build_dashboard_config(prompt_files: list[str], mock_profile: str, reports_dir: str) -> AppConfig:
    return AppConfig(
        run=RunConfig(
            name=f"dashboard_{mock_profile}",
            output_dir=reports_dir,
            prompt_files=prompt_files,
        ),
        provider=ProviderConfig(type="mock", model="mock-redteam-v1", mock_profile=mock_profile),
        scoring=replace(load_config(ROOT / "evals" / "config.yaml").scoring),
        reporting=ReportingConfig(formats=[]),
    )


@st.cache_data(show_spinner=False)
def run_dashboard_eval(prompt_files_key: tuple[str, ...], mock_profile: str, reports_dir: str) -> dict:
    config = build_dashboard_config(list(prompt_files_key), mock_profile, reports_dir)
    return run_evaluation(config, base_dir=ROOT)["report"]


def result_frame(report: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": item["id"],
                "category": item["category"],
                "risk": item["risk_level"],
                "label": item["label"],
                "response_excerpt": item["response_excerpt"],
                "mitigation": item["recommended_mitigation"],
            }
            for item in report["results"]
        ]
    )


def category_frame(report: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "category": category,
                "prompts": stats["total"],
                "passes": stats["passes"],
                "failures": stats["failures"],
                "violation_rate": stats["violation_rate"],
            }
            for category, stats in report["summary"]["category_stats"].items()
        ]
    )


def config_requires_external_api(config: AppConfig) -> bool:
    uses_provider_api = config.provider.type == "openai_compatible"
    uses_judge_api = (not config.scoring.rule_based) and config.scoring.llm_judge.enabled
    return uses_provider_api or uses_judge_api


def run_selected_config(
    selected_config_path: Path,
    settings: RuntimeSettings,
    session_api_key: str | None,
) -> dict | None:
    config = load_config(selected_config_path)
    config = replace(config, run=replace(config.run, output_dir=settings.reports_dir))
    external_required = config_requires_external_api(config)

    if not live_execution_allowed(settings, external_required):
        if settings.demo_mode:
            st.warning("Public demo mode is enabled. Live provider/judge calls are disabled.")
        else:
            st.warning("ALLOW_LIVE_RUNS=false. Live evaluation is disabled.")
        return None

    provider_key_name = config.provider.api_key_env
    judge_key_name = config.scoring.llm_judge.api_key_env
    env_has_provider_key = bool(os.getenv(provider_key_name))
    env_has_judge_key = bool(os.getenv(judge_key_name))
    session_key = (session_api_key or "").strip()

    if external_required and not (env_has_provider_key or env_has_judge_key or session_key):
        st.info(
            "No API key available. Set OPENAI_API_KEY (or provider-specific api_key_env) in environment, "
            "or provide a temporary session key below."
        )
        return None

    original_provider_key = os.getenv(provider_key_name)
    original_judge_key = os.getenv(judge_key_name)
    if session_key and not env_has_provider_key:
        os.environ[provider_key_name] = session_key
    if session_key and not env_has_judge_key:
        os.environ[judge_key_name] = session_key

    try:
        base_dir = infer_config_base_dir(selected_config_path, config.run.prompt_files)
        return run_evaluation(config, base_dir=base_dir)
    finally:
        if session_key and original_provider_key is None:
            os.environ.pop(provider_key_name, None)
        if session_key and original_provider_key is not None:
            os.environ[provider_key_name] = original_provider_key
        if session_key and original_judge_key is None:
            os.environ.pop(judge_key_name, None)
        if session_key and original_judge_key is not None:
            os.environ[judge_key_name] = original_judge_key


def ensure_demo_benchmark_artifacts(reports_dir: Path) -> Path:
    output_dir = reports_dir / "demo_benchmark"
    output_json = output_dir / "demo_results.json"
    if output_json.exists():
        return output_json
    cases = load_benchmark_cases(BENCHMARK_CASES_PATH)
    report = build_demo_benchmark_report(cases, source_path=BENCHMARK_CASES_PATH.relative_to(ROOT).as_posix())
    write_demo_benchmark_artifacts(report, output_dir)
    return output_json


def available_config_files() -> list[Path]:
    evals_dir = ROOT / "evals"
    return sorted(evals_dir.glob("*.yaml")) + sorted(evals_dir.glob("*.yml"))


def available_benchmark_reports(reports_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for folder in [reports_dir / "demo_benchmark", reports_dir / "live_benchmark"]:
        if folder.exists():
            candidates.extend(sorted(folder.glob("*.json")))
    return candidates


def benchmark_to_frames(benchmark_report: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    results = pd.DataFrame(benchmark_report["results"])
    category_rows = []
    for category, stats in benchmark_report["summary"]["category_breakdown"].items():
        category_rows.append(
            {
                "category": category,
                "total": stats["total"],
                "pass": stats["pass"],
                "fail": stats["fail"],
                "warning": stats["warning"],
            }
        )
    return results, pd.DataFrame(category_rows)


def benchmark_summary_csv(benchmark_report: dict) -> str:
    summary = benchmark_report["summary"]
    lines = [
        "metric,value",
        f"total_cases,{summary['total_cases']}",
        f"pass_count,{summary['pass_count']}",
        f"fail_count,{summary['fail_count']}",
        f"warning_count,{summary['warning_count']}",
        f"pass_rate,{summary['pass_rate']}",
        f"categories_covered,\"{','.join(summary['categories_covered'])}\"",
    ]
    return "\n".join(lines)


def benchmark_markdown_gallery(benchmark_report: dict) -> str:
    lines = ["# Qualitative Benchmark Gallery", ""]
    for item in benchmark_report["results"]:
        lines.extend(
            [
                f"## {item['id']} [{item['status']}]",
                f"- Category: {item['category']}",
                f"- Prompt: {item['prompt']}",
                f"- Expected behavior: {item['expected_behavior']}",
                f"- Observed/demo output: {item['observed_output']}",
                f"- Assessment: {item['qualitative_assessment']}",
                f"- Notes: {item['notes']}",
                "",
            ]
        )
    return "\n".join(lines)


st.set_page_config(page_title="LLM Red-Team Dashboard", page_icon="🧪", layout="wide")
st.title("LLM Evaluation and Red-Team Dashboard")

settings = load_runtime_settings()
reports_dir_path = resolve_from_root(settings.reports_dir)
reports_dir_path.mkdir(parents=True, exist_ok=True)
demo_report_path = ensure_demo_benchmark_artifacts(reports_dir_path)
config_files = available_config_files()
benchmark_reports = available_benchmark_reports(reports_dir_path)
if demo_report_path not in benchmark_reports:
    benchmark_reports = [demo_report_path] + benchmark_reports

with st.sidebar:
    st.header("Runtime Settings")
    mode = "demo" if settings.demo_mode else "live"
    st.caption(f"Current mode: **{mode}**")
    st.write(f"`DEMO_MODE`: `{settings.demo_mode}`")
    st.write(f"`ALLOW_LIVE_RUNS`: `{settings.allow_live_runs}`")
    st.write(f"`OPENAI_API_KEY present`: `{settings.openai_api_key_present}`")
    st.write(f"`DEFAULT_CONFIG_PATH`: `{settings.default_config_path}`")
    st.write(f"`REPORTS_DIR`: `{settings.reports_dir}`")

    st.divider()
    st.header("Selections")
    config_options = [path.relative_to(ROOT).as_posix() for path in config_files] or [settings.default_config_path]
    default_config = settings.default_config_path if settings.default_config_path in config_options else config_options[0]
    selected_config = st.selectbox("Config file", config_options, index=config_options.index(default_config))

    benchmark_options = [path.relative_to(ROOT).as_posix() for path in benchmark_reports]
    selected_benchmark_report = st.selectbox(
        "Benchmark report",
        benchmark_options,
        index=benchmark_options.index(demo_report_path.relative_to(ROOT).as_posix()) if benchmark_options else 0,
    )

    prompt_set_name = st.selectbox("Prompt set (mock evaluation view)", list(PROMPT_SETS), index=0)
    mock_profile = st.selectbox("Mock model profile", ["mixed", "robust", "vulnerable"], index=0)
    show_passed = st.toggle("Show passed examples", value=False)
    compare_mitigation = st.toggle("Compare with robust mock profile", value=False)

    session_api_key = ""
    if (not settings.demo_mode) and settings.allow_live_runs:
        session_api_key = st.text_input(
            "Session API key (not persisted)",
            type="password",
            help="Used only for this session if environment key is missing.",
        )
    st.caption(f"Selected config: `{selected_config}`")
    st.caption(f"Selected benchmark: `{selected_benchmark_report}`")

if settings.demo_mode:
    st.info(
        "Public demo mode: live model calls are disabled. This demo uses sample benchmark reports. "
        "Clone the repo and set OPENAI_API_KEY to run full evaluations."
    )

st.warning(
    "Live testing setup: to run real OpenAI-compatible evaluations, set DEMO_MODE=false, "
    "ALLOW_LIVE_RUNS=true, and provide OPENAI_API_KEY as a private Hugging Face Secret or as a "
    "temporary session key. Never put API keys in the public repository."
)

tab_eval, tab_benchmark = st.tabs(["Evaluation Dashboard", "Benchmark & Qualitative Evaluation"])

with tab_eval:
    prompt_files = PROMPT_SETS[prompt_set_name]
    report = run_dashboard_eval(tuple(prompt_files), mock_profile, settings.reports_dir)
    summary = report["summary"]
    categories = category_frame(report)
    results = result_frame(report)
    failures = results[results["label"] == "FAIL"]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Prompts Tested", summary["total_prompts"])
    metric_cols[1].metric("Pass Rate", f"{(summary['passes'] / summary['total_prompts'] if summary['total_prompts'] else 0):.1%}")
    metric_cols[2].metric("Fail Rate", f"{(summary['failures'] / summary['total_prompts'] if summary['total_prompts'] else 0):.1%}")
    metric_cols[3].metric("Violation Rate", f"{summary['total_violation_rate']:.1%}")

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Violation Rate By Category")
        st.bar_chart(categories.set_index("category")["violation_rate"], height=320)
    with right:
        st.subheader("Evaluation Categories")
        st.dataframe(
            categories,
            hide_index=True,
            use_container_width=True,
            column_config={"violation_rate": st.column_config.ProgressColumn("violation_rate", format="%.1f", min_value=0, max_value=1)},
        )

    st.subheader("Failed Prompts")
    if failures.empty and not show_passed:
        st.success("No failing examples were detected by the active rule-based scorer.")
    else:
        if failures.empty:
            st.success("No failing examples were detected by the active rule-based scorer. Showing passed examples.")
        for item in report["results"]:
            if item["passed"] and not show_passed:
                continue
            status = "PASS" if item["passed"] else "FAIL"
            with st.expander(f"{status} - {item['id']} - {item['category']}", expanded=not item["passed"]):
                st.write("Prompt")
                st.code(item["prompt"], language="text")
                st.write("Model response excerpt")
                st.write(item["response_excerpt"])
                st.write("Recommended mitigation")
                st.info(item["recommended_mitigation"])
                if item["findings"]:
                    st.write("Rule findings")
                    st.dataframe(pd.DataFrame(item["findings"]), hide_index=True, use_container_width=True)

    if compare_mitigation:
        st.subheader("Before And After Mock Comparison")
        after_report = run_dashboard_eval(tuple(prompt_files), "robust", settings.reports_dir)
        comparison = pd.DataFrame(
            [
                {
                    "run": f"selected profile: {mock_profile}",
                    "total_prompts": summary["total_prompts"],
                    "failures": summary["failures"],
                    "violation_rate": summary["total_violation_rate"],
                },
                {
                    "run": "robust mock profile",
                    "total_prompts": after_report["summary"]["total_prompts"],
                    "failures": after_report["summary"]["failures"],
                    "violation_rate": after_report["summary"]["total_violation_rate"],
                },
            ]
        )
        st.dataframe(
            comparison,
            hide_index=True,
            use_container_width=True,
            column_config={"violation_rate": st.column_config.ProgressColumn("violation_rate", format="%.1f", min_value=0, max_value=1)},
        )
        st.caption("Deterministic mock comparison only. Not a production mitigation claim.")

    st.subheader("Run Selected Config")
    st.caption("May consume API credits if provider/judge uses external model endpoints.")
    if st.button("Run Selected Config (may consume API credits)", use_container_width=True):
        try:
            selected_config_path = resolve_from_root(selected_config)
            run_result = run_selected_config(selected_config_path, settings, session_api_key)
            if run_result:
                st.success("Evaluation completed.")
                st.json({"summary": run_result["report"]["summary"], "paths": run_result["paths"]})
        except Exception as exc:  # surfaced intentionally to avoid silent failures
            st.error("Config run failed.")
            st.exception(exc)

    st.subheader("Export Report")
    markdown_report = render_markdown_report(report, include_passed_examples=show_passed)
    html_report = render_html_report(report, include_passed_examples=show_passed)
    download_cols = st.columns(2)
    download_cols[0].download_button(
        "Download Markdown",
        data=markdown_report,
        file_name=f"{report['metadata']['run_name']}.md",
        mime="text/markdown",
    )
    download_cols[1].download_button(
        "Download HTML",
        data=html_report,
        file_name=f"{report['metadata']['run_name']}.html",
        mime="text/html",
    )
    with st.expander("Raw Result Data"):
        st.dataframe(results, hide_index=True, use_container_width=True)

with tab_benchmark:
    selected_report_path = resolve_from_root(selected_benchmark_report)
    benchmark_report = load_benchmark_report(selected_report_path)
    benchmark_results, benchmark_categories = benchmark_to_frames(benchmark_report)
    benchmark_summary = benchmark_report["summary"]

    if benchmark_report.get("metadata", {}).get("is_sample", False):
        st.info("This benchmark report is a deterministic demo/sample artifact. It does not perform live API calls.")
    else:
        st.warning("This benchmark report is not marked as demo/sample.")

    metrics = st.columns(6)
    metrics[0].metric("Total Cases", benchmark_summary["total_cases"])
    metrics[1].metric("Pass", benchmark_summary["pass_count"])
    metrics[2].metric("Fail", benchmark_summary["fail_count"])
    metrics[3].metric("Warning", benchmark_summary["warning_count"])
    metrics[4].metric("Pass Rate", f"{benchmark_summary['pass_rate']:.1%}")
    metrics[5].metric("Categories", len(benchmark_summary["categories_covered"]))

    st.subheader("Benchmark Summary")
    st.dataframe(
        benchmark_categories,
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Qualitative Case Gallery")
    for item in benchmark_report["results"]:
        with st.expander(f"{item['status']} - {item['id']} - {item['category']}", expanded=item["status"] != "PASS"):
            st.write("Input prompt")
            st.code(item["prompt"], language="text")
            st.write("Expected behavior")
            st.write(item["expected_behavior"])
            st.write("Observed/demo output")
            st.write(item["observed_output"])
            st.write("Qualitative assessment")
            st.write(item["qualitative_assessment"])
            st.caption(f"Notes: {item['notes']}")

    st.subheader("Failure / Warning Examples")
    flagged = benchmark_results[benchmark_results["status"].isin(["FAIL", "WARNING"])]
    if flagged.empty:
        st.success("No failure or warning examples in selected benchmark report.")
    else:
        st.dataframe(flagged[["id", "category", "status", "qualitative_assessment", "notes"]], hide_index=True, use_container_width=True)

    st.subheader("Download Benchmark Artifacts")
    download_cols = st.columns(3)
    download_cols[0].download_button(
        "Download JSON report",
        data=json.dumps(benchmark_report, indent=2),
        file_name=selected_report_path.name,
        mime="application/json",
    )
    download_cols[1].download_button(
        "Download CSV summary",
        data=benchmark_summary_csv(benchmark_report),
        file_name="benchmark_summary.csv",
        mime="text/csv",
    )
    download_cols[2].download_button(
        "Download Markdown gallery",
        data=benchmark_markdown_gallery(benchmark_report),
        file_name="qualitative_case_gallery.md",
        mime="text/markdown",
    )

    st.caption("Hosted public demo defaults to static demo benchmark artifacts. Live runs require explicit configuration.")
