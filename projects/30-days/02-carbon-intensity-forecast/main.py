"""One-step Great Britain carbon-intensity forecasting with a chronological backtest."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
from pathlib import Path
import time
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE_URL = "https://api.carbonintensity.org.uk/intensity"
PERIOD = pd.Timedelta(minutes=30)
FEATURES = ["lag_1", "lag_2", "lag_48", "past_3h_mean", "past_3h_std",
            "hour_sin", "hour_cos", "weekday_sin", "weekday_cos"]


def fetch_history(days: int):
    if not 7 <= days <= 30:
        raise ValueError("Choose 7 to 30 days of history")
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=days)
    stamp = lambda value: value.strftime("%Y-%m-%dT%H:%MZ")
    url = f"{BASE_URL}/{stamp(start)}/{stamp(end)}"
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "AshJai23-Portfolio/1.0", "Accept": "application/json"})
            with urlopen(request, timeout=25) as response:
                return json.load(response), url
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(0.5 * 2 ** attempt)
    raise RuntimeError("Unreachable")


def load_series(payload: dict):
    """Keep actual observations only; never substitute the supplier's forecast."""
    if not isinstance(payload.get("data"), list):
        raise ValueError("Expected carbon-intensity API data list")
    observations = {}
    audit = {"input_rows": len(payload["data"]), "missing_actual": 0,
             "invalid_rows": 0, "duplicate_timestamps": 0}
    for row in payload["data"]:
        try:
            timestamp = pd.Timestamp(row["from"])
            end = pd.Timestamp(row["to"])
            if timestamp.tzinfo is None or end.tzinfo is None:
                raise ValueError("Timestamp must include timezone")
            timestamp = timestamp.tz_convert("UTC")
            if end - timestamp != PERIOD or timestamp != timestamp.floor("30min"):
                raise ValueError("Expected half-hour settlement interval")
            actual = row["intensity"].get("actual")
            if actual is None:
                audit["missing_actual"] += 1
                continue
            if isinstance(actual, bool):
                raise ValueError("Boolean is not carbon intensity")
            actual = float(actual)
            if not math.isfinite(actual) or actual < 0:
                raise ValueError("Actual must be finite and non-negative")
            if timestamp in observations:
                audit["duplicate_timestamps"] += 1
            observations[timestamp] = actual
        except (KeyError, TypeError, ValueError, OverflowError):
            audit["invalid_rows"] += 1
    if not observations:
        raise ValueError("No actual carbon-intensity observations")
    series = pd.Series(observations, dtype=float).sort_index()
    timeline = pd.date_range(series.index.min(), series.index.max(), freq=PERIOD)
    series = series.reindex(timeline)
    series.name = "actual_gco2_per_kwh"
    audit["observed_intervals"] = int(series.notna().sum())
    audit["unobserved_intervals_inside_window"] = int(series.isna().sum())
    return series, audit


def feature_at(series: pd.Series, target_time: pd.Timestamp):
    past_times = pd.date_range(target_time - 48 * PERIOD, periods=48, freq=PERIOD)
    past = series.reindex(past_times).to_numpy(dtype=float)
    if not np.isfinite(past).all():
        return None
    hour = target_time.hour + target_time.minute / 60
    weekday = target_time.dayofweek
    return [past[-1], past[-2], past[0], float(past[-6:].mean()), float(past[-6:].std()),
            math.sin(2 * math.pi * hour / 24), math.cos(2 * math.pi * hour / 24),
            math.sin(2 * math.pi * weekday / 7), math.cos(2 * math.pi * weekday / 7)]


def build_examples(series: pd.Series):
    rows, targets, stamps = [], [], []
    for timestamp, actual in series.items():
        if pd.isna(actual):
            continue
        features = feature_at(series, timestamp)
        if features is not None:
            rows.append(features)
            targets.append(actual)
            stamps.append(timestamp)
    return pd.DataFrame(rows, columns=FEATURES, index=pd.DatetimeIndex(stamps)), np.array(targets)


def model():
    return make_pipeline(StandardScaler(), Ridge(alpha=10.0))


def evaluate(x: pd.DataFrame, y: np.ndarray):
    if len(x) < 240:
        raise ValueError("Need at least 240 complete examples after lag construction")
    cutoff = int(len(x) * 0.8)
    fitted = model().fit(x.iloc[:cutoff], y[:cutoff])
    prediction = np.maximum(0, fitted.predict(x.iloc[cutoff:]))
    persistence = x.iloc[cutoff:]["lag_1"].to_numpy()
    truth = y[cutoff:]
    score = lambda p: {"mae_gco2_per_kwh": float(mean_absolute_error(truth, p)),
                       "rmse_gco2_per_kwh": float(np.sqrt(mean_squared_error(truth, p)))}
    metrics = {"ridge": score(prediction), "persistence_baseline": score(persistence)}
    metrics["ridge_beats_persistence_on_mae"] = metrics["ridge"]["mae_gco2_per_kwh"] < metrics["persistence_baseline"]["mae_gco2_per_kwh"]
    split = {"training_examples": cutoff, "test_examples": len(x) - cutoff,
             "train_last_target_utc": x.index[cutoff - 1].isoformat(),
             "test_first_target_utc": x.index[cutoff].isoformat(),
             "test_last_target_utc": x.index[-1].isoformat()}
    backtest = pd.DataFrame({"target_from_utc": x.index[cutoff:].astype(str),
                             "actual": truth, "ridge": prediction, "persistence": persistence})
    return metrics, split, backtest, fitted


def next_forecast(series, x, y):
    timestamp = series.index[-1] + PERIOD
    issued_at = pd.Timestamp.now(tz="UTC")
    features = feature_at(series, timestamp)
    if features is None:
        return {"available": False, "reason": "Missing observations in the latest 24-hour feature window"}
    refitted = model().fit(x, y)
    next_x = pd.DataFrame([features], columns=FEATURES)
    return {"available": True, "interval_from_utc": timestamp.isoformat(),
            "interval_to_utc": (timestamp + PERIOD).isoformat(),
            "issued_at_utc": issued_at.isoformat(),
            "estimate_kind": ("future_forecast" if timestamp >= issued_at else
                              "current_interval_nowcast" if timestamp + PERIOD > issued_at else
                              "historical_gap_estimate_due_to_data_delay"),
            "ridge_gco2_per_kwh": float(max(0, refitted.predict(next_x)[0])),
            "persistence_gco2_per_kwh": float(features[0]),
            "last_observed_interval_from_utc": series.index[-1].isoformat(),
            "note": "One interval after the latest available actual; check its timestamp for staleness."}


def render_report(result):
    metrics = result["metrics"]
    rows = "".join(f"<tr><td>{escape(name)}</td><td>{values['mae_gco2_per_kwh']:.3f}</td><td>{values['rmse_gco2_per_kwh']:.3f}</td></tr>"
                   for name, values in metrics.items() if isinstance(values, dict))
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1"><title>Carbon intensity forecast</title>
    <style>body{{font:16px/1.6 system-ui;background:#101c2a;color:#e2edf0;max-width:920px;margin:40px auto;padding:24px}}
    h1,h2{{color:#63e3cb}}th,td{{padding:14px;text-align:left;border-bottom:1px solid #345}}pre{{white-space:pre-wrap;background:#142d3a;padding:24px}}</style>
    <h1>GB carbon-intensity forecasting</h1><p>Built {escape(result['built_at_utc'])} · unit: gCO₂/kWh</p>
    <h2>Chronological holdout</h2><table><tr><th>Model</th><th>MAE</th><th>RMSE</th></tr>{rows}</table>
    <p>Ridge beats persistence on MAE: <b>{metrics['ridge_beats_persistence_on_mae']}</b>.
    Negative results are retained; this prototype does not promise a forecasting improvement.</p>
    <h2>Next interval after the latest actual</h2><pre>{escape(json.dumps(result['next_forecast'], indent=2))}</pre>
    <p>Evaluation uses the actual previous intervals at every forecast origin. It is a rolling one-step backtest,
    not a blind forecast for the entire holdout. Scaling is fitted on training data only.</p></html>"""


def run(payload, output: Path, source: str):
    series, audit = load_series(payload)
    x, y = build_examples(series)
    metrics, split, backtest, _ = evaluate(x, y)
    result = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "source": source,
              "data_attribution": "NESO Carbon Intensity API, CC BY 4.0; https://carbonintensity.org.uk/",
              "quality": audit, "features": FEATURES, "evaluation": "Chronological 80/20 rolling one-step holdout; no shuffled split",
              "split": split, "metrics": metrics, "next_forecast": next_forecast(series, x, y)}
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    backtest.to_csv(output / "backtest.csv", index=False)
    (output / "report.html").write_text(render_report(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--input", type=Path, help="Replay a saved API response")
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    try:
        if args.live:
            payload, source = fetch_history(args.days)
        else:
            payload, source = json.loads(args.input.read_text()), str(args.input)
        result = run(payload, args.output, source)
        print(json.dumps(result["metrics"], indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Forecast failed: {error}\n")


if __name__ == "__main__":
    main()
