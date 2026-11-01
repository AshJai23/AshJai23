# Market research: what this can and cannot do

Release 0.4.0 adds a separate experimental price model. Scam screening remains the 0.3.0 deterministic engine: no trained fraud classifier or FCA lookup. Neither section decides whether an investment is safe or suitable.

## Try it

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
streamlit run app.py
# API alternative
uvicorn smartinvest.api:app --host 127.0.0.1 --port 8000
# Optional deliberate refresh; requires access to the fixed ECB public endpoint
python scripts/refresh_ecb.py
```

Open **Investment research & experimental forecasts**, then **Analyse ECB currency example**. In the private browser demo choose **Market research → Try ECB FX example**. Upload your own legally usable price CSV to research shares/ETFs: exact columns `date,symbol,price,currency`, daily-like observations, at least 240 shared dates per symbol, one quote currency, at most ten symbols and 20,000 total rows / 2 MiB. Duplicate dates, non-positive/nonfinite prices, future dates and mixed currencies are rejected. Historical rankings are descriptive; the app makes no automatic best-buy selection.

API: POST `/v1/market-research` with `{"csv_text":"date,symbol,price,currency\n...", "horizon":5}`. Input stays local; no user-supplied URL is fetched. Do not send credentials or personal financial details. Downloadable results include fitted parameters, split dates and individual held-out predictions.

## Real data and freshness

Source: [ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html), [fixed download](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip), [reuse terms](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html), [methodology](https://data.ecb.europa.eu/methodology/exchange-rates).

Captured 1 November 2026; latest observation 30 October 2026. Processed snapshot: 5,253 rows, three currency series, 1,751 common dates each from 2 January 2020. ECB reference rates are informational, not executable trading quotes; the ECB discourages transactional use. This is historical replay, not live polling. A bundled snapshot does not refresh itself. A visible age flag warns after seven calendar days. No stock/ETF quote subscription or always-on ingestion was provisioned.

Attribution: European Central Bank. SmartInvest AI filters dates and derives GBP per currency unit: EURGBP = GBP per EUR; USDGBP = GBP per EUR / USD per EUR; JPYGBP = GBP per EUR / JPY per EUR. These modifications and model calculations are ours, not ECB advice. Source and processed checksums, timestamps and byte counts are in `examples/market/source-manifest.json`. Do not interpret FX unit prices as shares, funds, total returns or a recommendation to trade currencies.

## Actual fitted model and evaluation

Pure-Python Ridge regression (alpha=1) estimates forward log-price change from four causal features: last log change, mean last five, mean last twenty and standard deviation of last twenty log changes. Feature scaling uses training data only. This is a real least-squares fit, not deep learning, LLM training or a fraud model.

Chronological 60/20/20 train/calibration/test allocation; target windows crossing boundaries are purged. No hyperparameter search or test tuning. The default five-observation benchmark has 1,025 training origins, 345 calibration origins and 346 held-out test origins per series. The frozen training-only model is also used for the final projection; it is deliberately not refitted on held-out data. Historical context at a test origin is available, but future target prices are not features. Origins overlap within each partition, so test errors are dependent and no significance claim is made.

| Series | Ridge held-out MAPE | Unchanged-price MAPE | Model beat baseline? |
| --- | ---: | ---: | --- |
| EURGBP | 0.377% | 0.351% | No |
| JPYGBP | 0.672% | 0.698% | Yes, this period only |
| USDGBP | 0.684% | 0.682% | No |

The model loses two of three comparisons. These price forecast errors do not demonstrate a profitable trading strategy. Bands use the 90th-percentile calibration absolute log residual; held-out empirical coverage is about 95–96% in this one snapshot. They have no guaranteed future coverage or probability-of-profit interpretation under drift. Forecast horizons count subsequent observations, not calendar dates or a verified trading calendar.

Actual coefficients, train/test boundaries, errors, individual predictions, runtime, Python/platform and traced peak memory: `validation/v0.4.0/ecb-held-out.json`. AI-authored tests/evaluation; no independent review, investment professional validation or prospective trading study.

## Descriptive comparisons and limitations

Only shared dates are used; excluded unmatched rows are counted. Annualised volatility scales the population standard deviation of log changes by observed frequency; max drawdown uses running historical peaks. The 252-observation price change is not guaranteed to equal one calendar year. No dividends, corporate-action adjustment, fees, taxes, transaction costs, liquidity, spreads, portfolio weights or exchange-rate conversion of arbitrary uploads are applied. Use appropriate adjusted input data and verify units (GBP differs from GBX). Uploaded source/licence/provenance is unverified.

The category guide covers cash/deposits, diversified funds/ETFs, bonds and individual shares in general terms, with [MoneyHelper](https://www.moneyhelper.org.uk/en/savings/how-to-save/should-i-save-or-invest). It does not identify today's best product or offer a personal allocation. There are no buy/sell orders or trade execution. Asset allocation, suitability, licensed current market feeds and professional review remain outside this prototype.
