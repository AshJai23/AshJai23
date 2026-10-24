import unittest

import numpy as np
import pandas as pd

from main import PERIOD, build_examples, evaluate, feature_at, load_series, next_forecast


def series():
    timestamps = pd.date_range("2026-01-01", periods=480, freq="30min", tz="UTC")
    values = 100 + 30 * np.sin(np.arange(480) * 2 * np.pi / 48)
    return pd.Series(values, index=timestamps)


class ForecastTests(unittest.TestCase):
    def test_features_do_not_depend_on_target_or_future(self):
        original = series()
        target = original.index[100]
        modified = original.copy()
        modified.loc[target:] = 99999
        np.testing.assert_allclose(feature_at(original, target), feature_at(modified, target))

    def test_gap_is_not_backfilled_with_future_observations(self):
        data = series()
        target = data.index[100]
        data.iloc[99] = np.nan
        self.assertIsNone(feature_at(data, target))
        x, _ = build_examples(data)
        self.assertNotIn(target, x.index)

    def test_supplier_forecast_is_never_used_as_actual(self):
        payload = {"data": [
            {"from": "2026-01-01T00:00Z", "to": "2026-01-01T00:30Z", "intensity": {"actual": 100, "forecast": 999}},
            {"from": "2026-01-01T00:30Z", "to": "2026-01-01T01:00Z", "intensity": {"actual": None, "forecast": 999}},
            {"from": "2026-01-01T01:00Z", "to": "2026-01-01T01:30Z", "intensity": {"actual": 101, "forecast": 999}},
        ]}
        data, audit = load_series(payload)
        self.assertTrue(pd.isna(data.iloc[1]))
        self.assertEqual(audit["missing_actual"], 1)
        self.assertEqual(data.iloc[0], 100)

    def test_training_and_scaling_are_chronological(self):
        x, y = build_examples(series())
        _, split, backtest, fitted = evaluate(x, y)
        cutoff = split["training_examples"]
        self.assertLess(pd.Timestamp(split["train_last_target_utc"]), pd.Timestamp(split["test_first_target_utc"]))
        np.testing.assert_allclose(fitted.named_steps["standardscaler"].mean_, x.iloc[:cutoff].mean().values)
        np.testing.assert_allclose(backtest["persistence"], x.iloc[cutoff:]["lag_1"])

    def test_next_forecast_is_one_half_hour_after_latest_actual(self):
        data = series()
        x, y = build_examples(data)
        forecast = next_forecast(data, x, y)
        self.assertEqual(pd.Timestamp(forecast["interval_from_utc"]), data.index[-1] + PERIOD)
        self.assertEqual(forecast["estimate_kind"], "historical_gap_estimate_due_to_data_delay")

    def test_short_dataset_fails_instead_of_reporting_fake_metrics(self):
        x, y = build_examples(series().iloc[:100])
        with self.assertRaisesRegex(ValueError, "at least 240"):
            evaluate(x, y)


if __name__ == "__main__":
    unittest.main()
