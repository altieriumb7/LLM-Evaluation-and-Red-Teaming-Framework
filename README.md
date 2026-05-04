# LLM Evaluation and Red-Teaming Framework

Portfolio-quality tooling for pre-deployment evaluation of LLM applications. The framework runs adversarial prompt sets against either a local mock model or an OpenAI-compatible API, scores responses, and generates reports for safety review.

The project is mock-first: it runs locally without private API keys.

## What It Tests

- Hallucination and unsupported claims
- Prompt injection and instruction hierarchy failures
- Unsafe instruction following
- Bias and stereotyping
- Privacy leakage and credential exposure
- Jailbreak attempts and refusal failures

## Project Structure

```text
evals/                 YAML run configurations
prompts/               Red-team prompt datasets
src/                   Framework package
reports/               Generated reports
tests/                 Unit tests
app.py                 Streamlit dashboard
requirements.txt       Python dependencies
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux, activate with:

```bash
source .venv/bin/activate
```

## Run In Mock Mode

```bash
python -m src.run_redteam --config evals/config.yaml
```

This writes Markdown, JSON, and HTML reports to `reports/`.

You can also override prompt sets or mock behavior:

```bash
python -m src.run_redteam --config evals/config.yaml --prompt-file prompts/finance_prompts.yaml --mock-profile vulnerable
```

Mock profiles:

- `robust`: simulated safe responses
- `mixed`: deterministic mix of passes and failures
- `vulnerable`: simulated failures for every prompt

## Streamlit Dashboard

```bash
streamlit run app.py
```

The dashboard includes three preloaded prompt sets:

- General red-team
- Healthcare safety
- Finance safety

It displays total prompts, pass/fail rate, violation rate by category, failed prompt examples, model response excerpts, recommended mitigations, and exportable Markdown/HTML reports. It can also compare the selected mock profile with the robust mock profile as a demo-only before/after view.

## OpenAI-Compatible Provider

Set the provider in `evals/config.yaml`:

```yaml
provider:
  type: openai_compatible
  model: gpt-4.1-mini
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
```

Then set the key in your environment:

```bash
set OPENAI_API_KEY=your_key_here
```

On macOS/Linux:

```bash
export OPENAI_API_KEY=your_key_here
```

Credentials are never hardcoded. The framework reads only the environment variable named by `api_key_env`.

## Scoring

Rule-based scoring is enabled by default and is fully local. It checks category-specific failure patterns, case-level prohibited phrases or regexes, and required safe-completion signals.

LLM-as-judge scoring is intentionally separate from rule-based scoring. It is disabled by default so local execution does not require a model key or external service. To run judge-only scoring, set `scoring.rule_based: false` and `scoring.llm_judge.enabled: true`, then configure the judge model and `api_key_env`.

Before using judge scoring as a deployment gate, calibrate the judge prompt against labeled examples, review false positives and false negatives, and track judge drift over time.

## Optional Integrations

The config includes optional flags for DeepEval and LangSmith:

```yaml
optional_integrations:
  deepeval: false
  langsmith: false
```

They are not required for local execution and are not imported by default.

## Tests

```bash
pytest tests
```

The test suite covers prompt loading, mock evaluation, scoring, report generation, and config validation.

## Ethical Use

Use this framework only on systems you own or have explicit permission to test. The adversarial prompts are stored for evaluation purposes and are written to avoid actionable harmful details. Do not use this project to extract secrets, bypass controls on third-party systems, or generate operational harm.

## Limitations

- Rule-based checks are transparent and fast, but they can miss nuanced failures or flag benign text.
- The mock provider is deterministic and useful for demos/tests, but it is not evidence of real model behavior.
- Reported before/after comparisons are only shown when both runs are executed on the same prompt set. The dashboard demo comparison does not claim production mitigation impact.
- Domain-specific prompt sets should be expanded with expert review before deployment gates.
