"""Synthetic fixtures test temporal/quality invariants, never reported as real data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from main import NUMERIC, capture, clean, features, run, split


def fixture(n=110):
    rows = []
    for station in ("10", "11"):
        for i, t in enumerate(pd.date_range("2026-10-01", periods=n, freq="30min")):
            bikes = i%20
            rows.append(dict(station_id=station, last_reported=str(t), num_bikes_available=bikes, num_docks_available=30-bikes,
                             capacity=30, is_installed=True, is_renting=True, is_returning=True))
    return pd.DataFrame(rows)


class ForecastTests(unittest.TestCase):
    def data(self): return clean(fixture())[0]
    def test_target_and_future_values_do_not_change_features(self):
        raw = fixture(); f, _ = clean(raw); x, _ = features(f)
        t = pd.Timestamp("2026-10-02 12:00")
        raw.loc[pd.to_datetime(raw.last_reported)>=t, "num_bikes_available"] = 25
        raw.loc[pd.to_datetime(raw.last_reported)>=t, "num_docks_available"] = 5
        y, _ = features(clean(raw)[0])
        np.testing.assert_array_equal(x[x.target_time==t][NUMERIC].to_numpy(), y[y.target_time==t][NUMERIC].to_numpy())
    def test_missing_observation_is_not_filled_across_a_gap(self):
        raw = fixture(); stamp = "2026-10-02 00:00:00"
        raw = raw[~((raw.station_id=="10") & (raw.last_reported==stamp))]
        x, q = features(clean(raw)[0]); bad = pd.date_range(stamp, periods=4, freq="30min")
        self.assertFalse(x[(x.station_id=="10") & x.target_time.isin(bad)].shape[0]); self.assertEqual(q["missing_grid_slots"], 1)
    def test_global_time_split_labels_available_at_first_test_origin(self):
        train, test = split(features(self.data())[0])
        self.assertLessEqual(train.target_time.max(), test.origin_time.min())
        self.assertEqual(set(train.station_id), set(test.station_id))
    def test_origin_is_exactly_thirty_minutes_before_target(self):
        x, _ = features(self.data())
        self.assertTrue(((x.target_time-x.origin_time)==pd.Timedelta(minutes=30)).all())
    def test_bad_counts_and_unknown_operational_flags_are_rejected(self):
        raw = fixture(); raw["num_bikes_available"] = raw["num_bikes_available"].astype(float); raw["is_renting"] = raw["is_renting"].astype(object)
        raw.loc[0,"num_bikes_available"] = 31; raw.loc[1,"num_bikes_available"] = -1
        raw.loc[2,"num_bikes_available"] = .5; raw.loc[3,"num_bikes_available"] = np.nan; raw.loc[4,"is_renting"] = "unknown"
        _, q = clean(raw); self.assertEqual(q["invalid_or_unavailable_rows"], 5)
    def test_conflicting_duplicate_key_is_quarantined(self):
        raw = fixture(); duplicate = raw.iloc[[10]].copy(); duplicate["num_bikes_available"] += 1; duplicate["num_docks_available"] -= 1
        f, q = clean(pd.concat([raw, duplicate], ignore_index=True))
        self.assertEqual(q["conflicting_keys"], 1); self.assertEqual(len(f), len(raw)-1)
    def test_identical_duplicate_is_counted(self):
        raw = fixture(); f, q = clean(pd.concat([raw, raw.iloc[[0]]], ignore_index=True))
        self.assertEqual(q["identical_duplicates"], 1); self.assertEqual(len(f),len(raw))
    def test_capacity_changes_do_not_create_leaking_features(self):
        raw = fixture(); raw.loc[40,"capacity"] = 31
        x, _ = features(clean(raw)[0]); t = pd.Timestamp(raw.loc[40,"last_reported"])
        # The changed target capacity is unknown at its origin; that forecast
        # must still exist, using the previous known capacity.
        self.assertEqual(x[(x.station_id=="10") & (x.target_time==t)].capacity_known.iloc[0],30)
        self.assertFalse(((x.station_id=="10") & x.target_time.isin(pd.date_range(t+pd.Timedelta(minutes=30),periods=3,freq="30min"))).any())
    def test_short_dataset_does_not_publish_metrics(self):
        with self.assertRaises(ValueError): split(features(clean(fixture(10))[0])[0])
    def test_training_scaler_uses_training_only_and_predictions_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"test_only_synthetic.csv"; raw = fixture(); raw.to_csv(p,index=False)
            report = run(p, Path(d)/"outputs"); train, _ = split(features(clean(raw)[0])[0])
            for name in NUMERIC: self.assertAlmostEqual(report["training_numeric_means"][name], train[name].mean())
            predictions = pd.read_csv(Path(d)/"outputs/backtest.csv")
            self.assertTrue(predictions.ridge.between(0,30).all())
    def test_no_live_failure_fallback_or_partial_file(self):
        with tempfile.TemporaryDirectory() as d, patch("urllib.request.urlopen", side_effect=TimeoutError):
            p = Path(d)/"source.csv"
            with self.assertRaises(TimeoutError): capture("2026-10-19", "2026-10-24", p)
            self.assertFalse(p.exists())
    def test_dates_outside_bounded_history_are_rejected(self):
        with self.assertRaises(ValueError): capture("2026-10-01", "2026-10-20", "unused.csv")


if __name__ == "__main__": unittest.main()
