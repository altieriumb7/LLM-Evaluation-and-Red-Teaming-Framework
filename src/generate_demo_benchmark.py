from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.benchmark import build_demo_benchmark_report, load_benchmark_cases, write_demo_benchmark_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deterministic demo benchmark artifacts.")
    parser.add_argument("--cases", default="benchmarks/qualitative_redteam_cases.yaml", help="Path to benchmark cases YAML.")
    parser.add_argument("--output-dir", default="reports/demo_benchmark", help="Output folder for benchmark artifacts.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cases_path = Path(args.cases)
    cases = load_benchmark_cases(cases_path)
    report = build_demo_benchmark_report(cases, source_path=cases_path.as_posix())
    paths = write_demo_benchmark_artifacts(report, args.output_dir)
    print(json.dumps({"summary": report["summary"], "paths": paths}, indent=2))


if __name__ == "__main__":
    main()
