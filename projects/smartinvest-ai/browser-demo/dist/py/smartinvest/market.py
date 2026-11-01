"""Descriptive price research and fitted, leakage-aware Ridge projections.

No buy/sell recommendation, fraud probability, suitability assessment or guarantee.
Pure Python keeps the same implementation usable in Streamlit and Pyodide.
"""
from __future__ import annotations
import csv
from datetime import date
import io
import math
import re
import statistics
import time

MAX_BYTES = 2 * 1024 * 1024
MIN_OBSERVATIONS = 240
FEATURES = ["last_log_change", "mean_5_log_changes", "mean_20_log_changes", "std_20_log_changes"]


def parse_prices(data: bytes, as_of: date | None = None) -> tuple[dict, str]:
    if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES:
        raise ValueError("Provide a non-empty price CSV up to 2 MiB")
    as_of = as_of or date.today()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Price CSV must be UTF-8") from exc
    if "\x00" in text:
        raise ValueError("NUL characters are not supported")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    assets, seen, currencies = {}, set(), set()
    try:
        if reader.fieldnames is None or len(reader.fieldnames) != 4 or set(reader.fieldnames) != {"date", "symbol", "price", "currency"}:
            raise ValueError("Price CSV needs exactly date,symbol,price,currency")
        for row_number, row in enumerate(reader, 1):
            if row_number > 20000:
                raise ValueError("Price CSV exceeds 20,000 rows")
            if None in row or any(x is None for x in row.values()):
                raise ValueError("A price row does not match the header")
            symbol = row["symbol"].strip().upper()
            currency = row["currency"].strip().upper()
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,24}", symbol) or not re.fullmatch(r"[A-Z]{3}", currency):
                raise ValueError("Use a short plain symbol and three-letter quote currency")
            try:
                when = date.fromisoformat(row["date"])
                price = float(row["price"])
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid ISO date or numeric price") from exc
            if when.isoformat() != row["date"] or when > as_of:
                raise ValueError("Dates must be YYYY-MM-DD and not in the future")
            if not math.isfinite(price) or not 1e-9 <= price <= 1e12:
                raise ValueError("Prices must be finite and between 1e-9 and 1e12")
            if (symbol, when) in seen:
                raise ValueError("Duplicate symbol/date rows are not allowed")
            seen.add((symbol, when)); currencies.add(currency)
            assets.setdefault(symbol, {})[when] = price
            if len(assets) > 10:
                raise ValueError("Compare at most 10 symbols")
    except csv.Error as exc:
        raise ValueError("Malformed price CSV") from exc
    if not assets or len(currencies) != 1:
        raise ValueError("Use non-empty data with one common quote currency; do not mix GBP, GBX or USD")
    return assets, next(iter(currencies))


def _features(prices, i):
    changes = [math.log(prices[j]) - math.log(prices[j-1]) for j in range(i-19, i+1)]
    return [changes[-1], statistics.mean(changes[-5:]), statistics.mean(changes), statistics.pstdev(changes)]


def _solve(matrix, rhs):
    n = len(rhs)
    a = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(a[i][col]))
        a[col], a[pivot] = a[pivot], a[col]
        if abs(a[col][col]) < 1e-12:
            raise ValueError("Numerically unstable model; use the baseline")
        scale = a[col][col]; a[col] = [x/scale for x in a[col]]
        for i in range(n):
            if i != col:
                factor = a[i][col]
                a[i] = [x-factor*y for x, y in zip(a[i], a[col])]
    return [a[i][-1] for i in range(n)]


def _fit(x, y):
    means = [statistics.mean(row[j] for row in x) for j in range(4)]
    scales = [statistics.pstdev(row[j] for row in x) or 1.0 for j in range(4)]
    z = [[(value-means[j])/scales[j] for j, value in enumerate(row)] for row in x]
    intercept = statistics.mean(y)
    matrix = [[sum(row[j]*row[k] for row in z)+(1.0 if j == k else 0.0) for k in range(4)] for j in range(4)]
    rhs = [sum(row[j]*(target-intercept) for row, target in zip(z, y)) for j in range(4)]
    return {"means": means, "scales": scales, "coefficients": _solve(matrix, rhs), "intercept": intercept}


def _predict(model, x):
    result = model["intercept"] + sum(b*(value-mean)/scale for b, value, mean, scale in zip(model["coefficients"], x, model["means"], model["scales"]))
    if not math.isfinite(result) or abs(result) > 3:
        raise ValueError("Projection is numerically extreme; no model forecast returned")
    return result


def forecast_series(dates, prices, horizon=5):
    if type(horizon) is not int or horizon not in (1, 5, 20):
        raise ValueError("Choose a horizon of 1, 5 or 20 subsequent observations")
    n = len(prices)
    if n < MIN_OBSERVATIONS:
        raise ValueError("Need at least 240 common daily observations per symbol")
    if statistics.median((b-a).days for a, b in zip(dates, dates[1:])) > 4:
        raise ValueError("This model expects daily-like observations, not weekly/monthly prices")
    cut1, cut2 = int(n*.6), int(n*.8)
    train = list(range(20, cut1-horizon))
    calibration = list(range(cut1, cut2-horizon))
    test = list(range(cut2, n-horizon))
    if min(map(len, (train, calibration, test))) < 20:
        raise ValueError("Not enough purged training/calibration/test observations")
    features = {i: _features(prices, i) for i in range(20, n)}
    target = lambda i: math.log(prices[i+horizon]) - math.log(prices[i])
    start = time.perf_counter()
    model = _fit([features[i] for i in train], [target(i) for i in train])
    fitted_seconds = time.perf_counter()-start
    calibration_errors = sorted(abs(target(i)-_predict(model, features[i])) for i in calibration)
    q = calibration_errors[min(len(calibration_errors)-1, math.ceil(.9*(len(calibration_errors)+1))-1)]
    predictions, errors, baseline_errors, covered = [], [], [], []
    for i in test:
        log_change = _predict(model, features[i]); predicted = prices[i]*math.exp(log_change)
        actual = prices[i+horizon]
        errors.append(abs(predicted-actual)); baseline_errors.append(abs(prices[i]-actual))
        covered.append(abs(target(i)-log_change) <= q)
        predictions.append({"origin_date": dates[i].isoformat(), "target_date": dates[i+horizon].isoformat(), "actual": actual, "ridge": predicted, "persistence": prices[i]})
    projected_log = _predict(model, features[n-1])
    projection = prices[-1]*math.exp(projected_log)
    return {
        "model": "Ridge regression, alpha=1, four causal return features plus intercept",
        "training_method": "closed-form regularised least squares; no neural model or LLM",
        "features": FEATURES, "parameters": model,
        "horizon_observations": horizon, "training_rows": len(train), "calibration_rows": len(calibration), "test_rows": len(test),
        "train_first_origin": dates[train[0]].isoformat(), "train_last_target": dates[train[-1]+horizon].isoformat(),
        "calibration_first_origin": dates[calibration[0]].isoformat(), "calibration_last_target": dates[calibration[-1]+horizon].isoformat(),
        "test_first_origin": dates[test[0]].isoformat(), "test_last_target": dates[test[-1]+horizon].isoformat(),
        "training_seconds": round(fitted_seconds, 6),
        "ridge_mae": statistics.mean(errors), "persistence_mae": statistics.mean(baseline_errors),
        "ridge_mape_pct": statistics.mean(100*e/p["actual"] for e, p in zip(errors, predictions)),
        "persistence_mape_pct": statistics.mean(100*e/p["actual"] for e, p in zip(baseline_errors, predictions)),
        "model_beat_baseline": statistics.mean(errors) < statistics.mean(baseline_errors),
        "calibration_band_test_coverage": statistics.mean(covered),
        "projection": projection, "persistence_projection": prices[-1],
        "projected_price_change_pct": 100*math.expm1(projected_log),
        "calibration_band_low": prices[-1]*math.exp(projected_log-q),
        "calibration_band_high": prices[-1]*math.exp(projected_log+q),
        "band_note": "90th-percentile calibration residual band in log-price change. No guaranteed coverage under market drift; not a probability of profit.",
        "forecast_fit_note": "Same training-only fitted model used for held-out test and final projection; no refit on calibration/test data.",
        "held_out_predictions": predictions,
    }


def analyse_prices(data: bytes, horizon=5, as_of: date | None = None):
    as_of = as_of or date.today(); assets, currency = parse_prices(data, as_of)
    common = sorted(set.intersection(*(set(x) for x in assets.values())))
    if len(common) < MIN_OBSERVATIONS:
        raise ValueError("Need at least 240 shared daily observations across the selected symbols")
    results = []
    for symbol, series in sorted(assets.items()):
        prices = [series[d] for d in common]
        changes = [math.log(b)-math.log(a) for a, b in zip(prices, prices[1:])]
        annual_count = 365.25*(len(common)-1)/(common[-1]-common[0]).days
        peak = prices[0]; drawdown = 0.0
        for price in prices:
            peak = max(peak, price); drawdown = min(drawdown, price/peak-1)
        results.append({"symbol": symbol, "quote_currency": currency, "observations": len(common),
                        "excluded_noncommon_rows": len(series)-len(common),
                        "last_price": prices[-1], "first_date": common[0].isoformat(), "last_date": common[-1].isoformat(),
                        "full_period_price_change_pct": 100*(prices[-1]/prices[0]-1),
                        "trailing_252_observation_change_pct": 100*(prices[-1]/prices[-253]-1) if len(prices) >= 253 else None,
                        "annualised_log_volatility_pct": 100*statistics.pstdev(changes)*math.sqrt(annual_count),
                        "max_drawdown_pct": 100*drawdown,
                        "forecast": forecast_series(common, prices, horizon)})
    return {"mode": "price_history_research_not_recommendations", "as_of_date": as_of.isoformat(),
            "latest_observation": common[-1].isoformat(), "observation_age_calendar_days": (as_of-common[-1]).days,
            "stale_after_7_calendar_days": (as_of-common[-1]).days > 7,
            "quote_currency": currency, "assets": results,
            "limitations": ["No best investment, suitability, buy/sell instruction or guaranteed return is identified.",
                            "Comparisons use only shared dates and one quote currency. Splits, dividends, fees, taxes and spreads are not modelled.",
                            "Price changes are not guaranteed total investment returns. Check source adjustments and units.",
                            "Horizon is subsequent observations, not exact calendar/trading dates. No live feed is implied.",
                            "Chronological splits purge overlapping target windows. Calibration bands can fail under market drift."]}
