# Reproducibility Checklist

## Runtime
- Python: 3.12

## Install
```bash
pip install -r requirements.txt
```

## Test
```bash
python -m pytest tests -q
```

## Streamlit
```bash
streamlit run app.py --server.headless true --server.port 8501
```

## Docker
```bash
docker build -t llm-redteam-hf .
docker run --rm -p 8501:8501 -e DEMO_MODE=true -e ALLOW_LIVE_RUNS=false llm-redteam-hf
```

## Hugging Face Spaces (Docker SDK)
- `DEMO_MODE=true`
- `ALLOW_LIVE_RUNS=false`
- `DEFAULT_CONFIG_PATH=evals/config.yaml`
- `REPORTS_DIR=reports`
- `BENCHMARK_MODE=demo`
- Optional secret: `OPENAI_API_KEY`

## Benchmark Generation
```bash
python -m src.generate_demo_benchmark
```

## Expected Generated Files
- `reports/demo_benchmark/demo_results.json`
- `reports/demo_benchmark/demo_summary.csv`
- `reports/demo_benchmark/qualitative_case_gallery.md`

## Environment Variables
- `DEMO_MODE`
- `ALLOW_LIVE_RUNS`
- `OPENAI_API_KEY`
- `DEFAULT_CONFIG_PATH`
- `REPORTS_DIR`
- `BENCHMARK_MODE`

## Known Limitations
- Hugging Face free storage is ephemeral.
- Demo benchmark is curated/static and does not represent live API measurements.
- Full external-provider validation requires API credentials and network access.
- Docker runtime verification requires a running local Docker daemon.
