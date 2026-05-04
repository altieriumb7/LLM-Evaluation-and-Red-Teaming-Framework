from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import AppConfig, ProviderConfig, ReportingConfig, RunConfig, ScoringConfig
from src.reporting import render_html_report, render_markdown_report
from src.runner import run_evaluation


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


def build_dashboard_config(prompt_files: list[str], mock_profile: str) -> AppConfig:
    return AppConfig(
        run=RunConfig(
            name=f"dashboard_{mock_profile}",
            output_dir="reports",
            prompt_files=prompt_files,
        ),
        provider=ProviderConfig(type="mock", model="mock-redteam-v1", mock_profile=mock_profile),
        scoring=ScoringConfig(),
        reporting=ReportingConfig(formats=[]),
    )


@st.cache_data(show_spinner=False)
def run_dashboard_eval(prompt_files_key: tuple[str, ...], mock_profile: str) -> dict:
    config = build_dashboard_config(list(prompt_files_key), mock_profile)
    return run_evaluation(config, base_dir=ROOT)["report"]


def result_frame(report: dict) -> pd.DataFrame:
    rows = []
    for item in report["results"]:
        rows.append(
            {
                "id": item["id"],
                "category": item["category"],
                "risk": item["risk_level"],
                "label": item["label"],
                "response_excerpt": item["response_excerpt"],
                "mitigation": item["recommended_mitigation"],
            }
        )
    return pd.DataFrame(rows)


def category_frame(report: dict) -> pd.DataFrame:
    rows = []
    for category, stats in report["summary"]["category_stats"].items():
        rows.append(
            {
                "category": category,
                "prompts": stats["total"],
                "passes": stats["passes"],
                "failures": stats["failures"],
                "violation_rate": stats["violation_rate"],
            }
        )
    return pd.DataFrame(rows)


st.set_page_config(page_title="LLM Red-Team Dashboard", page_icon="shield", layout="wide")
st.title("LLM Evaluation and Red-Team Dashboard")

with st.sidebar:
    st.header("Evaluation")
    prompt_set_name = st.selectbox("Prompt set", list(PROMPT_SETS), index=0)
    mock_profile = st.selectbox(
        "Mock model profile",
        ["mixed", "robust", "vulnerable"],
        index=0,
        help="Mock mode is deterministic and does not require API keys.",
    )
    show_passed = st.toggle("Show passed examples", value=False)
    compare_mitigation = st.toggle(
        "Compare with robust mock profile",
        value=False,
        help="Compares the selected mock profile to the robust mock profile on the same prompt set.",
    )

prompt_files = PROMPT_SETS[prompt_set_name]
report = run_dashboard_eval(tuple(prompt_files), mock_profile)
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
    after_report = run_dashboard_eval(tuple(prompt_files), "robust")
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
    st.caption("This is a deterministic mock comparison for demo purposes, not a measured production mitigation claim.")

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
