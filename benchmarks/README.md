# Benchmarks

This folder contains curated qualitative benchmark cases used by the public demo.

- Source cases: `qualitative_redteam_cases.yaml`
- Generator: `python -m src.generate_demo_benchmark`
- Output folder: `reports/demo_benchmark`

Notes:
- These cases are deterministic and safe.
- They are for qualitative portfolio demonstration, not a scientific leaderboard.
- No external API calls are made when generating demo benchmark artifacts.
