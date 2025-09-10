# NQMP — Negation & Quantifier Minimal Pairs Bench

NQMP is a tiny, deterministic llm benchmark focused on **logical sensitivity** to small prompt flips
(e.g., `all ↔ any`, `at least ↔ at most`, insert/remove `not`, `and ↔ or`). It generates micro-contexts,
poses **minimal pairs** of questions, queries an LLM, and grades for **pairwise consistency**.

## Table of Contents
- [NQMP — Negation \& Quantifier Minimal Pairs Bench](#nqmp--negation--quantifier-minimal-pairs-bench)
  - [Table of Contents](#table-of-contents)
  - [Why NQMP?](#why-nqmp)
  - [Leaderboard](#leaderboard)
  - [Requirements](#requirements)
  - [Install](#install)
  - [Configure](#configure)
  - [Quickstart](#quickstart)
  - [Outputs](#outputs)
  - [CLI](#cli)
  - [Resuming Runs](#resuming-runs)
  - [Retry Behavior](#retry-behavior)
  - [Development](#development)
    - [Project Layout](#project-layout)
  - [License](#license)

## Why NQMP?
- Targets a common failure mode: models read the words but miss the **operator change**.
- Minimal setup: small synthetic contexts; exact-match grading; transparent artifacts.
- Reproducible: seedable generation, strict prompts, and self-contained evaluation.

## Leaderboard
The leaderboard below updates automatically when you generate reports.
It sorts by **pair joint accuracy** (both items in a pair must be correct), then item accuracy.

<!-- LEADERBOARD:START -->

|       timestamp | client     | model                        |   pairs |   seed |   item_accuracy |   pair_joint_accuracy | report                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | run_dir                                                                  |
|-----------------|------------|------------------------------|---------|--------|-----------------|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| 20250910_091655 | openrouter | google/gemini-2.5-pro        |     100 |     42 |           0.990 |                 0.980 | [md](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-google-gemini-2.5-pro-pairs100-20250910_085034/report_openrouter-google-gemini-2.5-pro-pairs100-20250910_091655.md) · [html](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sashsinha/nqmp-bench/main/results/openrouter-google-gemini-2.5-pro-pairs100-20250910_085034/report_openrouter-google-gemini-2.5-pro-pairs100-20250910_091655.html) · [chart](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-google-gemini-2.5-pro-pairs100-20250910_085034/operator_accuracy_openrouter-google-gemini-2.5-pro-pairs100-20250910_091655.png) · [dir](https://github.com/sashsinha/nqmp-bench/tree/main/results/openrouter-google-gemini-2.5-pro-pairs100-20250910_085034)                                                  | results/openrouter-google-gemini-2.5-pro-pairs100-20250910_085034        |
| 20250910_084619 | openrouter | google/gemini-2.5-flash      |     100 |     42 |           0.870 |                 0.770 | [md](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-google-gemini-2.5-flash-pairs100-20250910_084409/report_openrouter-google-gemini-2.5-flash-pairs100-20250910_084619.md) · [html](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sashsinha/nqmp-bench/main/results/openrouter-google-gemini-2.5-flash-pairs100-20250910_084409/report_openrouter-google-gemini-2.5-flash-pairs100-20250910_084619.html) · [chart](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-google-gemini-2.5-flash-pairs100-20250910_084409/operator_accuracy_openrouter-google-gemini-2.5-flash-pairs100-20250910_084619.png) · [dir](https://github.com/sashsinha/nqmp-bench/tree/main/results/openrouter-google-gemini-2.5-flash-pairs100-20250910_084409)                                    | results/openrouter-google-gemini-2.5-flash-pairs100-20250910_084409      |
| 20250910_083514 | openrouter | openai/gpt-4o-mini           |     100 |     42 |           0.775 |                 0.640 | [md](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-openai-gpt-4o-mini-pairs100-20250910_083236/report_openrouter-openai-gpt-4o-mini-pairs100-20250910_083514.md) · [html](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sashsinha/nqmp-bench/main/results/openrouter-openai-gpt-4o-mini-pairs100-20250910_083236/report_openrouter-openai-gpt-4o-mini-pairs100-20250910_083514.html) · [chart](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-openai-gpt-4o-mini-pairs100-20250910_083236/operator_accuracy_openrouter-openai-gpt-4o-mini-pairs100-20250910_083514.png) · [dir](https://github.com/sashsinha/nqmp-bench/tree/main/results/openrouter-openai-gpt-4o-mini-pairs100-20250910_083236)                                                                       | results/openrouter-openai-gpt-4o-mini-pairs100-20250910_083236           |
| 20250910_084052 | openrouter | google/gemini-2.5-flash-lite |     100 |     42 |           0.760 |                 0.620 | [md](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_083901/report_openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_084052.md) · [html](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sashsinha/nqmp-bench/main/results/openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_083901/report_openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_084052.html) · [chart](https://github.com/sashsinha/nqmp-bench/blob/main/results/openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_083901/operator_accuracy_openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_084052.png) · [dir](https://github.com/sashsinha/nqmp-bench/tree/main/results/openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_083901) | results/openrouter-google-gemini-2.5-flash-lite-pairs100-20250910_083901 |
| 20250910_082714 | echo       | echo                         |     100 |     42 |           0.360 |                 0.160 | [md](https://github.com/sashsinha/nqmp-bench/blob/main/results/echo-unknown-pairs100-20250910_082714/report_echo-unknown-pairs100-20250910_082714.md) · [html](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sashsinha/nqmp-bench/main/results/echo-unknown-pairs100-20250910_082714/report_echo-unknown-pairs100-20250910_082714.html) · [chart](https://github.com/sashsinha/nqmp-bench/blob/main/results/echo-unknown-pairs100-20250910_082714/operator_accuracy_echo-unknown-pairs100-20250910_082714.png) · [dir](https://github.com/sashsinha/nqmp-bench/tree/main/results/echo-unknown-pairs100-20250910_082714)                                                                                                                                                                                              | results/echo-unknown-pairs100-20250910_082714                            |

<!-- LEADERBOARD:END -->

## Requirements
- Python 3.10+

## Install
uv (recommended):
```bash
# from repo root
$ uv venv
$ uv pip install -e .
```

pip (alternative):
```bash
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -e .
```

## Configure
Create a `.env` if you plan to use OpenRouter:
```bash
$ cp .env.example .env
# Then set:
# OPENROUTER_API_KEY=...
#
# Optionally set:
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1/chat/completions
# MODEL_NAME=openai/gpt-4o-mini
```

## Quickstart
Offline demo (no API calls):
```bash
uv run nqmp all --pairs 100 --client echo
```

OpenRouter run:
```bash
uv run nqmp all --pairs 100 --client openrouter --model openai/gpt-4o-mini
```

## Outputs
When `--out` is omitted, runs go to:
```
results/{client}-{model}-pairs{N}-{YYYYMMDD_HHMMSS}/
```
Artifacts include:
- `dataset.jsonl`
- `predictions.jsonl`
- `run.log` (JSON lines, one per LLM call)
- `run_info.json`
- `metrics_{basename}.json`
- `operator_accuracy_{basename}.png`
- `report_{basename}.md`
- `report_{basename}.html`
- `correct_predictions_{basename}.jsonl`
- `incorrect_predictions_{basename}.jsonl`

## CLI
```bash
# Generate only
uv run nqmp generate --pairs 50 --seed 7

# Run over a dataset
uv run nqmp run --in results/<dataset-dir>/dataset.jsonl --client echo
# or
uv run nqmp run --in results/<dataset-dir>/dataset.jsonl --client openrouter --model <provider/model>

# Report or re-report
uv run nqmp report --in results/<run-dir>
```

## Resuming Runs
If a run times out or fails mid-way (e.g., transient 408/409/425/429/5xx), you can **resume** without losing progress. Give the run a stable `--out` directory so you can resume it later:
```bash
# First attempt
uv run nqmp all --pairs 100 --client openrouter --model openai/gpt-5-nano --out results/openrouter-openai-gpt-5-nano-pairs100

# If it fails/interrupted, resume safely (skips already-completed items)
uv run nqmp all --pairs 100 --client openrouter --model openai/gpt-5-nano --out results/openrouter-openai-gpt-5-nano-pairs100 --resume
```

## Retry Behavior
The OpenRouter client retries on transient statuses 408/409/425/429/5xx with exponential backoff (base 0.8, cap 8s, up to 4 retries). If an item still fails, the harness logs an `llm_error` and continues to the next item.

## Development
- Dependencies: `requests`, `python-dotenv`, `pandas`, `matplotlib`, `tabulate`, `ruff`.
- Lint: `ruff check` and `ruff format --check`
- Tests: `pytest -q`

### Project Layout
- `src/nqmp_bench/generator.py`: dataset generators (boolean and id-list operators)
- `src/nqmp_bench/harness.py`: run loop, logging, and resume
- `src/nqmp_bench/client.py`: OpenRouter client + echo stub
- `src/nqmp_bench/grader.py`: normalization and grading logic
- `src/nqmp_bench/report.py`: metrics, plots, and reports
- `src/nqmp_bench/cli.py`: CLI entry points

## License
MIT
