# Great Britain carbon-intensity forecasting

## Niche, data freshness and how to open

**Niche:** GB energy and council carbon reporting.

**Data truth:** Actual GB half-hour carbon observations; live command pulls source data, which can be delayed. Saved model scores are historical backtests.

**Website status:** runnable locally; no public project website has been deployed.
The GitHub address displays source code. An HTML file in GitHub's file viewer is
not a hosted dashboard.

From this project folder, install its documented dependencies, then run:

```bash
python main.py --live --days 28 --output outputs
```

Open the generated **`outputs/report.html`** from your local output folder.
It is a saved report; it refreshes only when you run the command again.

**Separate repository:** requested; creation is pending. The current folder and
its previous validation evidence remain available. Extraction is not a new
project and does not increase the completed count.

A reproducible ML project using the public NESO Carbon Intensity API. It compares
a regularised linear model against a persistence baseline for the next half-hour
interval, using only earlier actual observations as input.

**Business question:** does a small autoregressive model improve on simply
repeating the latest available carbon-intensity value?

## Run

Python 3.10+. From this project directory:

```bash
python -m venv .venv
# Activate the environment for your operating system, then:
python -m pip install -r requirements.txt
python main.py --live --days 28 --output outputs
python -m unittest discover -s tests -v
```

Open `outputs/report.html`; inspect `outputs/metrics.json` and
`outputs/backtest.csv`. No API key is needed. Refresh is pull-based when the
command is run; the source publishes half-hour intervals and actuals can be
delayed. It is not a continuously deployed forecast service.

Replay the real saved source response offline:

```bash
python main.py --input examples/source_snapshot.json --output outputs
```

## Method

- Target: **actual** national carbon intensity in **gCO2/kWh**. The API's own
  forecast is never used to fill missing actuals or presented as our model output.
- Features: lags 1, 2 and 48; past three-hour mean and standard deviation;
  cyclical hour-of-day and weekday. The features exclude the target interval.
- Missing observations: leave gaps unfilled and skip affected examples, rather
  than backfilling from future values. Require a complete previous 24 hours.
- Split: first 80% of complete examples for training; last 20% for testing.
- Model: `StandardScaler` + `Ridge(alpha=10)`, fitted only on the training period.
- Baseline: the last available actual observation.
- Metrics: MAE and RMSE in the target's original units. Poorer model performance
  is reported honestly; no accuracy percentage or production-readiness claim.
- After evaluation, refit on all observed examples to estimate one interval after
  the latest available actual. The output records the issue time and labels a
  future forecast, current-interval nowcast or historical gap estimate according
  to the target timestamp. A delayed source must not be mistaken for a future
  prediction.

This is a **rolling one-step backtest**: for each test interval, previous actuals
are assumed to be available at that forecast origin. It is not a blind forecast
of the entire test horizon and does not simulate historical publication delays.

## Evidence and limitations

The checked-in `examples/` contains a real 28-day API response, its measured
holdout results, per-interval predictions, report and six-test validation log.
Test-only deterministic sine-wave observations are explicitly synthetic.

The evaluation covers one period and one national series. The model can lose to
persistence in other periods. There is no hyperparameter search, uncertainty
calibration, regional modelling, financial-cost optimisation or production SLA.
No model files are loaded from untrusted sources or published as pickle files.

Validated with NumPy 2.3.5, pandas 2.2.3 and scikit-learn 1.8.0. Dependency ranges
in `requirements.txt` let users install compatible releases.

## Source and licence

- [NESO Carbon Intensity API](https://carbonintensity.org.uk/)
- [Official endpoint documentation](https://carbon-intensity.github.io/api-definitions/)
- [Time-series lag and evaluation guidance](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html)

Data attribution: National Energy System Operator (NESO), Carbon Intensity API.
The included source response is a saved copy; forecasts and derived results were
created by this project. API data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
No NESO endorsement is implied.
