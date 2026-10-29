# UK Retail Demand ML and MLOps Service

Status: planned; no implementation, data processing or training claimed.
Build: 2026-11-13 through 2026-11-19.

Can a reproducible model forecast next-week product demand more accurately than simple baselines, and can its predictions be served and monitored?

## Tools

Python, DuckDB / Parquet, scikit-learn or gradient boosting, PyTorch small neural comparator, MLflow local tracking or equivalent, FastAPI, CI, Drift and data-quality monitoring.

## Data

- [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) — Historical UK transactions; distinct predictive objective from W01, not live inventory or sales. Reuse verified ingestion only after auditing W01 outputs; report aggregate series counts separately from raw rows.

## Deliverables

- As-of product-week demand target, causal lag features and rolling temporal backtests
- Actually fitted ML model and small CPU neural comparator, training-only preprocessing and simple last-week/seasonal baselines
- Saved predictions, per-product and aggregate MAE/WAPE with zero-demand handling and negative results
- Versioned local experiment/artifact tracking, batch inference and validated prediction API
- Data/feature drift replay, quality gates, CI, model card, monitoring/runbook and interview explanation

## Acceptance

- Fix target, forecast horizon, returns treatment and product eligibility before testing; no future-derived filtering or random row split
- Separate train/validation/test chronologically, group overlapping forecast windows appropriately and freeze test selection
- Report actual training rows/time/epochs/parameters, machine resources, package/model versions and baseline comparisons
- Fit a small neural model rather than a placeholder; do not claim neural methods win if simpler models do better
- Evaluate unavailable/new products explicitly; no claim of inventory optimisation, causal impact, current retail demand or profit
- Distinct code/service/evaluation from W01 copilot; shared source ingestion does not make it a second copy of that project

See [build guide](../BUILD_GUIDE.md) for publication, evaluation and daily reporting requirements.
