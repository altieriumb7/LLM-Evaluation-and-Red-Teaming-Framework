---
title: LLM Evaluation and Red-Teaming Framework
emoji: 🧪
colorFrom: red
colorTo: gray
sdk: docker
app_port: 8501
pinned: false
---

# LLM Evaluation and Red-Teaming Framework

Streamlit + CLI tooling for safe pre-deployment LLM red-teaming.  
The public Space runs in **demo mode** by default (no live API calls).

## Live Demo (Hugging Face Spaces)

Hosted demo is intended for CV/portfolio use:
- Demo benchmark artifacts are static/deterministic.
- Live provider/judge calls are disabled by default.
- No API key is required for public browsing.

## Safety Model for Public Demo

- `DEMO_MODE=true` disables live external model execution in the dashboard.
- `ALLOW_LIVE_RUNS=false` prevents accidental quota usage.
- API keys are never displayed.
- Session API key input (when enabled) is in-memory only and not persisted.

## Repository Structure

```text
app.py
src/
evals/
prompts/
benchmarks/
reports/
tests/
```

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

CLI evaluator:

```bash
python -m src.run_redteam --config evals/config.yaml
```

## Docker Setup

```bash
docker build -t llm-redteam .
docker run --rm -p 8501:8501 --env-file .env llm-redteam
```

Compose:

```bash
docker compose up --build
```

## Hugging Face Spaces Deployment (Docker SDK)

1. Create a Space.
2. Choose **SDK: Docker**.
3. Push this repository.
4. Set Space Variables:
   - `DEMO_MODE=true`
   - `ALLOW_LIVE_RUNS=false`
   - `DEFAULT_CONFIG_PATH=evals/config.yaml`
   - `REPORTS_DIR=reports`
   - `BENCHMARK_MODE=demo`
5. Optional Secret:
   - `OPENAI_API_KEY` (only needed for private live runs).

Notes:
- Free Space storage is ephemeral.
- Runtime-generated files under `reports/` are not guaranteed to persist.

## Benchmark Layer

Source cases:
- `benchmarks/qualitative_redteam_cases.yaml`

Generate deterministic demo artifacts:

```bash
python -m src.generate_demo_benchmark
```

Outputs:
- `reports/demo_benchmark/demo_results.json`
- `reports/demo_benchmark/demo_summary.csv`
- `reports/demo_benchmark/qualitative_case_gallery.md`

The dashboard tab **“Benchmark & Qualitative Evaluation”** loads these artifacts and shows:
- total/pass/fail/warning/pass-rate
- category breakdown
- qualitative case gallery
- failure/warning examples
- downloadable JSON/CSV/Markdown

## Full Live Evaluation (Local/Private)

1. Set `DEMO_MODE=false` and `ALLOW_LIVE_RUNS=true`.
2. Export `OPENAI_API_KEY` (or provider-specific `api_key_env`).
3. Run CLI or dashboard config-run button.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key_here"
```

## Security

- Never commit `.env` or real API keys.
- Public demo should keep `DEMO_MODE=true`.
- User-provided keys in dashboard are session-only.

## Limitations

- Demo benchmark results are illustrative artifacts, not scientific measurements.
- Live evaluation requires credentials and network access.
- Hugging Face free-tier storage is ephemeral.
- Optional integrations in config (DeepEval/LangSmith) are placeholders unless extended.

## CV / Portfolio Positioning

This project demonstrates:
- practical LLM safety evaluation workflow design,
- public-safe MLOps deployment patterns,
- deterministic qualitative benchmark reporting,
- transparent failure handling and reproducibility practices.
