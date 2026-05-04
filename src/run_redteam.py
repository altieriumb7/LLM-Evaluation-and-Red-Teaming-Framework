from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import load_config
from src.runner import run_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LLM evaluation and red-team prompts.")
    parser.add_argument("--config", default="evals/config.yaml", help="Path to YAML config.")
    parser.add_argument("--output-dir", help="Override report output directory.")
    parser.add_argument("--prompt-file", action="append", help="Override prompt file. Can be supplied multiple times.")
    parser.add_argument("--mock-profile", choices=["robust", "mixed", "vulnerable"], help="Override mock model behavior.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)

    if args.output_dir or args.prompt_file or args.mock_profile:
        from dataclasses import replace

        run = config.run
        provider = config.provider
        if args.output_dir:
            run = replace(run, output_dir=args.output_dir)
        if args.prompt_file:
            run = replace(run, prompt_files=args.prompt_file)
        if args.mock_profile:
            provider = replace(provider, mock_profile=args.mock_profile)
        config = replace(config, run=run, provider=provider)

    root = config_path.parent.parent if config_path.parent.name == "evals" else Path.cwd()
    result = run_evaluation(config, base_dir=root)
    summary = result["report"]["summary"]
    print(json.dumps({"summary": summary, "paths": result["paths"]}, indent=2))


if __name__ == "__main__":
    main()

