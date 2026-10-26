"""30-minute station-availability regression on genuine historical snapshots."""
import argparse
import csv
import hashlib
import html
import io
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE = "https://data.smartdublin.ie/dublinbikes-api/bikes/dublin_bikes/historical/stations.csv"
STATIONS = ["10", "100", "11", "12", "13"]
NUMERIC = ["lag_1", "lag_2", "lag_3", "past_mean", "change", "capacity_known", "hour_sin", "hour_cos", "weekday_sin", "weekday_cos"]


def capture(start, end, target, stations=STATIONS):
    start = date.fromisoformat(start); end = date.fromisoformat(end)
    if not 2 <= (end-start).days <= 7: raise ValueError("Request 2–7 days of history")
    if end > datetime.now(timezone.utc).date(): raise ValueError("Future history requested")
    url = BASE + "?" + urllib.parse.urlencode({"dt_start": start.isoformat(), "dt_end": end.isoformat()})
    request = urllib.request.Request(url, headers={"User-Agent": "PortfolioBikeForecast/1.0"})
    out = io.StringIO(); kept = 0; scanned = 0
    with urllib.request.urlopen(request, timeout=60) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8-sig", newline=""))
        required = {"station_id", "last_reported", "num_bikes_available", "capacity"}
        if not required.issubset(reader.fieldnames or []): raise ValueError("Unexpected CSV schema")
        writer = csv.DictWriter(out, fieldnames=reader.fieldnames); writer.writeheader()
        for row in reader:
            scanned += 1
            if scanned > 500_000: raise ValueError("Source exceeds bounded download")
            if row["station_id"] in stations and row["last_reported"][14:16] in ("00", "30"):
                writer.writerow(row); kept += 1
    if kept < 100: raise ValueError("Insufficient real data; no synthetic replacement")
    target = Path(target); target.parent.mkdir(parents=True, exist_ok=True)
    raw = out.getvalue().encode(); target.write_bytes(raw)
    provenance = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "source_url": url,
                  "source_mode": "Historical replay downloaded from regularly refreshed API, not a current forecast",
                  "source_rows_scanned": scanned, "rows_retained": kept, "sampling": "Selected station IDs; exact source records at minute 00 or 30, no interpolation",
                  "station_ids": stations, "sha256": hashlib.sha256(raw).hexdigest(),
                  "attribution": "Dublin City Council / Smart Dublin, Dublinbikes API DCC", "licence": "Creative Commons Attribution; catalogue cc-by does not specify a version"}
    target.with_name("provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return provenance


def clean(frame):
    required = {"station_id", "last_reported", "num_bikes_available", "num_docks_available", "capacity", "is_installed", "is_renting", "is_returning"}
    if not required.issubset(frame): raise ValueError("Missing required columns")
    f = frame.copy(); quality = {"input_rows": len(f)}
    f["station_id"] = f["station_id"].astype(str)
    f["time"] = pd.to_datetime(f["last_reported"], errors="coerce")
    # The source returns naive datetime labels without an explicit time zone.
    # Preserve that source clock, do not falsely label it UTC or convert DST.
    if f["time"].dt.tz is not None: raise ValueError("Expected naive provider clock; review timezone semantics")
    valid = f["time"].notna() & f["station_id"].str.fullmatch(r"\d+")
    for col in ("num_bikes_available", "num_docks_available", "capacity"):
        f[col] = pd.to_numeric(f[col], errors="coerce")
        valid &= np.isfinite(f[col]) & (f[col] == np.floor(f[col])) & (f[col] >= 0)
    valid &= (f["capacity"] > 0) & (f["num_bikes_available"] <= f["capacity"]) & (f["num_docks_available"] <= f["capacity"])
    valid &= f["num_bikes_available"] + f["num_docks_available"] <= f["capacity"]
    for col in ("is_installed", "is_renting", "is_returning"):
        valid &= f[col].astype(str).str.lower().isin(["true", "1"])
    valid &= f["time"].dt.minute.isin([0, 30]) & (f["time"].dt.second == 0)
    quality["invalid_or_unavailable_rows"] = int((~valid).sum()); f = f[valid].copy()
    keys = ["station_id", "time"]
    # Conflicting duplicates invalidate the key rather than hiding either value.
    conflict = f.groupby(keys)[["num_bikes_available", "capacity"]].nunique().max(axis=1) > 1
    bad_keys = set(conflict[conflict].index)
    quality["conflicting_keys"] = len(bad_keys)
    f = f[[tuple(v) not in bad_keys for v in f[keys].itertuples(index=False, name=None)]]
    quality["identical_duplicates"] = int(f.duplicated(keys).sum()); f = f.drop_duplicates(keys).sort_values(keys)
    quality["usable_rows"] = len(f); quality["stations"] = int(f["station_id"].nunique())
    if f.empty: raise ValueError("No valid observations")
    return f, quality


def features(frame):
    parts = []; quality = {"missing_grid_slots": 0, "rows_without_complete_lags": 0}
    for station, f in frame.groupby("station_id"):
        f = f.set_index("time").sort_index()
        grid = pd.date_range(f.index.min(), f.index.max(), freq="30min")
        quality["missing_grid_slots"] += len(grid)-len(f)
        f = f.reindex(grid); x = pd.DataFrame(index=grid)
        x["target"] = f["num_bikes_available"]
        for lag in (1, 2, 3): x[f"lag_{lag}"] = f["num_bikes_available"].shift(lag)
        x["past_mean"] = x[["lag_1", "lag_2", "lag_3"]].mean(axis=1, skipna=False)
        x["change"] = x["lag_1"]-x["lag_2"]
        x["capacity_known"] = f["capacity"].shift(1)
        # Eligibility uses past capacities only: a future capacity change must
        # not decide whether an origin was forecastable.
        stable = (f["capacity"].shift(1) == f["capacity"].shift(2)) & (f["capacity"].shift(2) == f["capacity"].shift(3))
        x["hour_sin"] = np.sin(2*np.pi*(grid.hour+grid.minute/60)/24)
        x["hour_cos"] = np.cos(2*np.pi*(grid.hour+grid.minute/60)/24)
        x["weekday_sin"] = np.sin(2*np.pi*grid.dayofweek/7); x["weekday_cos"] = np.cos(2*np.pi*grid.dayofweek/7)
        x["station_id"] = station; x["target_time"] = grid; x["origin_time"] = grid-pd.Timedelta(minutes=30)
        valid = x[NUMERIC+["target"]].notna().all(axis=1) & stable
        quality["rows_without_complete_lags"] += int((~valid).sum())
        parts.append(x[valid].reset_index(drop=True))
    result = pd.concat(parts, ignore_index=True).sort_values(["target_time", "station_id"]).reset_index(drop=True)
    return result, quality


def split(frame):
    times = sorted(frame["target_time"].unique())
    if len(times) < 48: raise ValueError("Need at least 48 distinct complete target times")
    first_test = pd.Timestamp(times[int(.8*len(times))])
    # First test forecast uses data through first_test-30min. All training labels
    # must already be observed then. No future station label can enter the fit.
    train = frame[frame["target_time"] <= first_test-pd.Timedelta(minutes=30)].copy()
    test = frame[frame["target_time"] >= first_test].copy()
    known = set(train["station_id"]); test = test[test["station_id"].isin(known)]
    if len(train) < 100 or len(test) < 30: raise ValueError("Insufficient train/test data")
    return train, test


def scores(y, prediction):
    return {"mae_bikes": float(np.mean(np.abs(y-prediction))), "rmse_bikes": float(np.sqrt(np.mean((y-prediction)**2)))}


def run(source, output):
    raw = pd.read_csv(source, dtype={"station_id": str}); f, quality = clean(raw); data, fq = features(f)
    train, test = split(data)
    encoder = ColumnTransformer([("numeric", StandardScaler(), NUMERIC), ("station", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["station_id"])])
    model = make_pipeline(encoder, Ridge(alpha=10.0))
    started = time.perf_counter(); model.fit(train[NUMERIC+["station_id"]], train["target"]); fit_seconds = time.perf_counter()-started
    predictions = np.clip(model.predict(test[NUMERIC+["station_id"]]), 0, test["capacity_known"].to_numpy())
    baseline = test["lag_1"].to_numpy(); y = test["target"].to_numpy()
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    backtest = test[["station_id", "origin_time", "target_time", "target"]].copy(); backtest["ridge"] = predictions; backtest["persistence"] = baseline
    backtest.to_csv(output/"backtest.csv", index=False, float_format="%.6f")
    per_station = [{"station_id": station, "test_rows": len(g), "ridge": scores(g["target"].to_numpy(), g["ridge"].to_numpy()), "persistence": scores(g["target"].to_numpy(), g["persistence"].to_numpy())} for station, g in backtest.groupby("station_id")]
    report = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "mode": "Historical replay; no current operational forecast", "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
              "clock": "Naive provider timestamps preserved; timezone unspecified, no UTC claim. DST transitions need source review.",
              "horizon_minutes": 30, "quality": {**quality, **fq}, "split": {"training_rows": len(train), "test_rows": len(test), "train_first_target": str(train["target_time"].min()), "train_last_target": str(train["target_time"].max()), "first_test_origin": str(test["origin_time"].min()), "first_test_target": str(test["target_time"].min()), "last_test_target": str(test["target_time"].max())},
              "method": "Fixed alpha=10 Ridge; scaler and station encoder fit only on earlier training rows; rolling one-step 30min holdout; no imputation or hyperparameter search", "fit_seconds": fit_seconds,
              "ridge": scores(y, predictions), "persistence": scores(y, baseline), "per_station": per_station,
              "training_numeric_means": dict(zip(NUMERIC, model.steps[0][1].named_transformers_["numeric"].mean_.tolist())),
              "limitations": "Five stations and a short historical window; provider outages are skipped, no new-station generalisation, no live launch or future accuracy guarantee. Source publication delays not simulated."}
    report["ridge_beats_persistence_mae"] = report["ridge"]["mae_bikes"] < report["persistence"]["mae_bikes"]
    (output/"metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    body = html.escape(json.dumps(report, indent=2))
    (output/"report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Bike availability replay</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px;background:#f3f7f3;color:#163d37}pre{white-space:pre-wrap;background:white;padding:24px;border-radius:12px}</style><h1>Bike availability: 30-minute historical forecast</h1><p>Actual Smart Dublin station snapshots. Historical replay, not current bike availability.</p><pre>'+body+'</pre><p>Data: Dublin City Council / Smart Dublin. Creative Commons Attribution (catalogue cc-by).</p></html>')
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--input", default="examples/source_snapshot.csv"); p.add_argument("--output", default="outputs")
    p.add_argument("--download", action="store_true"); p.add_argument("--start", default="2026-10-19"); p.add_argument("--end", default="2026-10-24")
    args = p.parse_args()
    if args.download: capture(args.start, args.end, args.input)
    print(json.dumps(run(args.input, args.output), indent=2))
