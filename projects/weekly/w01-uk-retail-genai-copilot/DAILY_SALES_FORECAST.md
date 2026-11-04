# Retail weak-day forecast and decision support

User direction, 4 November 2026: help a retailer look forward, identify weak days and test actions. W01 now includes an aggregate daily-sales forecast panel. W03 remains a distinct planned product-week ML/PyTorch/MLOps service; this feature is not counted as another completed project.

## Use your own recent sales

Start the updated local application with `python serve.py --baseline`. The forecast panel works independently of the optional UCI SQL warehouse and does not require an LLM or model download. It fits a small numerical model from the uploaded aggregate daily data.

CSV columns must be exactly:

```csv
date,sales
```

Provide at least **196 consecutive completed calendar days** (about seven months), up to 5,000 rows / 2 MiB. Choose GBP, EUR or USD to declare the amounts' currency. Use a consistent non-negative sales definition and complete days before today. Do not include customer records. Known closed/zero-sales days need explicit zero rows; unknown days must not be silently invented as zero. Duplicate, missing, future/incomplete dates and invalid values are rejected.

The seven forecast dates follow the latest uploaded day. A current forecast requires data complete through yesterday. Older uploads show a replay warning; old public data cannot describe today's store. No current store data was provided in this development session.

## What the page shows

- Seven dated forecasts and empirical residual ranges.
- The lowest point-forecast day; overlapping ranges can make the ranking unreliable.
- Actual week-to-date sales versus the same completed weekdays in the prior week.
- Mean sales by weekday over the last eight weeks, for context.
- Backtest errors for the fitted model and repeating the same weekday from last week.
- Investigations and experiments: check stock/opening hours/footfall; consider a margin-checked small promotion; review staffing with uncertainty. No cause, sales lift, profit or ROI is estimated.

## Model and validation

Ridge regression is actually fitted using NumPy regularised least squares, alpha=10, on log(1+sales). Features: seven weekday indicators, prior-day-available log lags 7/14 and rolling log means 7/28. Standardisation uses training rows only. Seven-day projections update rolling features recursively with predictions; future actuals never enter a forecast window.

The first N−84 days form training history (28-day lookback removed). The next **28 days** calibrate model selection and error bands. The final **56 days** are eight weekly held-out forecast windows. Select Ridge versus same-weekday-last-week by calibration MAE only; test data does not select the winner. Backtests may use observed history before each new weekly origin, while fitted weights remain training-only.

After evaluation, a selected Ridge method is refitted on all known history. The held-out score measures the earlier procedure, not a prospective guarantee for these refitted weights. Saved coefficients, split dates, per-day predictions and all scores make the process auditable. The seasonal baseline needs no fitted weights.

Ranges use the 90th-percentile absolute calibration error, with measured held-out coverage. They do not guarantee future coverage or profitability. Calibration has only 28 daily errors, market drift/seasonal events can break it, and a final refit can change the error distribution.

## Actual real-source replay

Derived source: Chen, D. (2012), UCI Online Retail II, DOI 10.24432/C5CG6D, CC BY 4.0. [Official source](https://archive.ics.uci.edu/dataset/502/online+retail+ii). Fresh archive retrieved 4 November 2026. The CSV in `examples/historical-daily-sales-proxy.csv` contains **737 historical daily positive non-cancel invoice-line values**, summed across customer countries after deduplication. These can include charge/adjustment codes and are a sales proxy, not audited merchandise revenue.

The first/last archive dates are excluded because they can be partial. Calendar days without eligible archive lines are represented as zero recorded proxy value. This does not establish that a store was closed or had no demand. The last history date is **8 December 2011**; the resulting 9–15 December 2011 projections are explicitly historical simulation.

The fitted Ridge used **625 training examples**, 28 calibration days and 56 held-out test days. Actual held-out MAE: **Ridge £26,846.17; last-week baseline £11,250.17**. WAPE: **58.01% versus 24.31%**. Calibration selected the simpler last-week method; the model did not beat it. Full analysis took about 0.025 seconds in the recorded Python environment. These results are not current retail forecasts.

Actual model parameters/results: `evidence/2026-11-04/daily-forecast-real-source.json`. Real temporary Uvicorn POST smoke: `daily-forecast-http.json`. The UI can accept a recent shop CSV for a new fit and forecast; there is no fabricated current-data fallback.

## Run and API

```bash
python serve.py --baseline
python -m unittest discover -s tests -v
```

POST `/v1/retail-forecast` accepts JSON `{ "csv_text": "date,sales\n...", "currency": "GBP" }`. Server-side CSV parsing, training, backtest and forecast happen locally. Body limit is 2 MiB. No arbitrary URL fetching, paid service or model API is added.

60 Python tests passed, including causal future-value mutation, chronological splits, seasonal/zero-data baselines, missing/duplicate/future dates and forecast operation when the optional old warehouse is absent. Node simulated-DOM checks cover page flows and rendering of the real-source replay. Full native Windows graphical browser QA has not been performed.

The project remains in progress. Reliable free-form LLM explanations, independently reviewed forecasting/relevance evaluation, n8n execution and release review remain separate unfinished requirements.
