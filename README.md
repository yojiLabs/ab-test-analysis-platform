# A/B Test Analysis Platform

A self-serve toolkit for designing, analyzing, and reporting on product experiments (A/B tests) — built to mirror how a Product/Data Analyst would evaluate a real feature rollout, including sample size planning, statistical testing, and guardrail metric checks.

**Status:** In progress

## Problem

Product teams often run experiments without properly planning sample size, and then misread "statistically significant" results as automatic "ship it" decisions — ignoring guardrail metrics or practical significance. This project builds a reusable pipeline that does experiment analysis the way a rigorous analytics team would.

## What this project does

- Simulates a realistic product experiment (treatment vs. control) with a known underlying effect
- Calculates required sample size / minimum detectable effect (MDE) before analyzing results
- Runs the appropriate statistical test and reports lift, confidence intervals, and p-value
- Checks guardrail metrics to catch trade-offs a pure "primary metric" view would miss
- Surfaces results in a self-serve Streamlit app with a plain-English ship/no-ship recommendation

## Tech stack

- Python (pandas, scipy, statsmodels)
- SQLite for the underlying experiment data
- Streamlit for the interactive read-out app
- Matplotlib / Plotly for visualizations

## Project structure

```
ab-test-analysis-platform/
├── data/          # raw and processed experiment data
├── sql/           # queries to build analysis-ready tables
├── notebooks/     # exploratory analysis and validation
├── app/           # Streamlit app
├── reports/        # case study write-up and exported charts
├── requirements.txt
└── README.md
```

## How to run

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
streamlit run app/app.py
```

## Case study

See [`reports/case_study.md`](reports/case_study.md) for the full write-up: hypothesis, experiment design, results, and recommendation. *(coming soon)*

## Roadmap

- [x] Project setup
- [x] Define hypothesis and metrics
- [x] Generate/source experiment data
- [x] Sample size / power analysis
- [ ] Core analysis script
- [ ] Streamlit app
- [ ] Case study write-up