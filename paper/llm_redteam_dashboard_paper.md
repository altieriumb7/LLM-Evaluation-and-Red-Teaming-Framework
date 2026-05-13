# An Open and Deployable Dashboard for LLM Red-Teaming and Qualitative Evaluation

## 1. Abstract
This repository provides a deployable Streamlit dashboard and CLI workflow for LLM red-teaming with a safe public-demo mode. The system combines deterministic mock evaluation, report generation, and a curated qualitative benchmark layer suitable for public portfolio deployment on Hugging Face Spaces. Results in this report are limited to repository artifacts generated locally (tests, demo benchmark outputs) and do not claim live model performance.

## 2. Introduction
Public demos of LLM safety tooling often face a tradeoff: either expose paid API paths or show no meaningful behavior. This project addresses that tradeoff by shipping:
1. a deterministic demo mode (`DEMO_MODE=true`) with no required API key, and
2. optional live evaluation pathways for private/local use.

## 3. System Overview
- UI entrypoint: `app.py`
- CLI entrypoint: `python -m src.run_redteam --config evals/config.yaml`
- Demo benchmark generator: `python -m src.generate_demo_benchmark`
- Core modules: `src/config.py`, `src/runner.py`, `src/scoring.py`, `src/reporting.py`, `src/benchmark.py`

## 4. Architecture
- Frontend: Streamlit dashboard (evaluation + benchmark tabs).
- Evaluation engine: loads prompt YAML, runs provider, scores, writes reports.
- Provider modes:
  - `mock` (local deterministic)
  - `openai_compatible` (requires key and explicit live enablement)
- Resilience: per-case retries and `runtime.error` recording in runner to continue execution after provider/scorer failures.

## 5. Deployment Model
- Hugging Face Spaces mode: Docker SDK (`README` frontmatter configured).
- Container runtime: Python 3.12 slim, Streamlit on port 8501.
- Public-safe defaults via env:
  - `DEMO_MODE=true`
  - `ALLOW_LIVE_RUNS=false`
- Live mode requires explicit opt-in and credentials.

## 6. Benchmark Design
Benchmark source: `benchmarks/qualitative_redteam_cases.yaml` (8 curated, safe, abstract cases).  
Generated artifacts:
- `reports/demo_benchmark/demo_results.json`
- `reports/demo_benchmark/demo_summary.csv`
- `reports/demo_benchmark/qualitative_case_gallery.md`

Case categories include:
- prompt injection resistance
- unsafe instruction refusal
- hallucination-risk handling
- policy compliance
- ambiguous-request robustness
- runtime error continuation
- config/path handling
- evaluator/judge failure handling

## 7. Qualitative Evaluation
From `reports/demo_benchmark/demo_results.json`:

| Metric | Value |
|---|---|
| Total cases | 8 |
| Pass | 6 |
| Fail | 0 |
| Warning | 2 |
| Pass rate | 0.75 |
| Categories covered | 8 |

Interpretation:
- The benchmark demonstrates behavior classes and failure-surface visibility.
- Results are deterministic demo annotations, not live external-model measurements.

## 8. Error Handling and Reproducibility
- Runner catches provider/scorer runtime failures per case and records `runtime.error`.
- Config base-dir inference reduces path fragility for config-driven runs.
- Reproducibility command set is documented in `REPRODUCIBILITY.md`.
- Test status: `20 passed` (`python -m pytest tests -q`).

## 9. Public Demo Mode and Safety Considerations
- Dashboard exposes mode and safety flags in sidebar.
- In demo mode, live external execution paths are blocked.
- API-key presence is shown as boolean only; key values are never rendered.
- Session key input is transient and not persisted.

## 10. Limitations
- Demo benchmark is illustrative and curated; it is not a peer-reviewed benchmark.
- Hugging Face free-tier filesystem is ephemeral.
- Full provider/judge validation requires external credentials/network.
- Docker runtime verification depends on local daemon availability.

## 11. Conclusion
The repository now supports a portfolio-grade public deployment pattern: safe by default, demonstrably useful without external keys, and extensible to private live evaluation workflows. The design prioritizes transparency (explicit demo labeling), resilience (per-case continuation), and reproducibility.

## 12. Reproducibility Checklist
- Install: `pip install -r requirements.txt`
- Tests: `python -m pytest tests -q`
- Demo benchmark generation: `python -m src.generate_demo_benchmark`
- Local app: `streamlit run app.py --server.headless true --server.port 8501`
- Docker build/run commands: see `REPRODUCIBILITY.md`
- Hugging Face variable settings: see `README.md` and `REPRODUCIBILITY.md`
