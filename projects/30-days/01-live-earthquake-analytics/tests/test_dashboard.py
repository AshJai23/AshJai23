from datetime import date, datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np

from dashboard import Handler, api
from geography import catalogue, contains, country, filter_events, ring_contains, validate_location
from hazards import daily_rows, earthquake_data, forecast, year_range
from outlook import predict_year


def synthetic_history():
    """Explicitly synthetic daily weather for deterministic leakage tests only."""
    rows = []
    current = date(2017, 1, 1)
    while current < date(2026, 1, 1):
        seasonal = 6 * np.cos(2 * np.pi * current.month / 12)
        rows.append({"date": current.isoformat(), "wind_speed_10m_max": 18 + seasonal + .1 * (current.year - 2017),
                     "wind_gusts_10m_max": 38 + seasonal, "precipitation_sum": 1.0})
        current += timedelta(days=1)
    return rows


def event(lon, lat, identifier="x"):
    return {"id": identifier, "properties": {"type": "earthquake", "mag": 3,
            "time": 1735689600000, "updated": 1735689600000, "place": "test fixture"},
            "geometry": {"type": "Point", "coordinates": [lon, lat, 5]}}


class GeographyTests(unittest.TestCase):
    def test_land_boundary_filter_does_not_use_a_country_bounding_box(self):
        uk = country("GBR")
        self.assertTrue(contains(uk, -.1278, 51.5074))  # London
        self.assertFalse(contains(uk, 2.3522, 48.8566))  # Paris
        self.assertFalse(contains(uk, 0, 55))  # North Sea inside UK's bounding box

    def test_country_holes_and_multipolygons(self):
        feature = {"geometry": {"type": "MultiPolygon", "coordinates": [
            [[[0,0],[10,0],[10,10],[0,10],[0,0]], [[4,4],[6,4],[6,6],[4,6],[4,4]]],
            [[[20,0],[22,0],[22,2],[20,2],[20,0]]]]}}
        self.assertTrue(contains(feature, 2, 2))
        self.assertFalse(contains(feature, 5, 5))
        self.assertTrue(contains(feature, 21, 1))

    def test_country_validation_blocks_invalid_weather_point(self):
        with self.assertRaisesRegex(ValueError, "inside"):
            validate_location("GBR", 28.61, 77.20)
        with self.assertRaises(ValueError):
            validate_location("ALL", 51.5, -.1)

    def test_invalid_coordinates_do_not_match(self):
        self.assertFalse(contains(country("GBR"), float("nan"), 50))

    def test_every_default_weather_point_is_in_its_mapped_area(self):
        for item in catalogue():
            with self.subTest(country=item["name"]):
                validate_location(item["code"], item["latitude"], item["longitude"])


class WeatherTests(unittest.TestCase):
    def test_thunderstorm_is_provider_flag_and_high_gust_is_separate(self):
        payload = {"daily_units": {"wind_speed_10m_max": "km/h", "wind_gusts_10m_max": "km/h"},
                   "daily": {"time": ["2025-01-01", "2025-01-02", "2025-01-03"],
                    "wind_speed_10m_max": [10, 20, None], "wind_gusts_10m_max": [30, 70, None],
                    "precipitation_sum": [0, 2, None], "weather_code": [95, 3, None]}}
        result = daily_rows(payload)
        self.assertTrue(result[0]["provider_thunderstorm"])
        self.assertFalse(result[0]["high_gust_indicator"])
        self.assertFalse(result[1]["provider_thunderstorm"])
        self.assertTrue(result[1]["high_gust_indicator"])
        self.assertIsNone(result[2]["high_gust_indicator"])
        self.assertIsNone(result[2]["provider_thunderstorm"])

    def test_wrong_units_and_malformed_arrays_fail(self):
        with self.assertRaisesRegex(ValueError, "km/h"):
            daily_rows({"daily": {"time": []}, "daily_units": {}})

    def test_forecast_horizon_is_capped(self):
        with self.assertRaisesRegex(ValueError, "16"):
            forecast(51, 0, 365)

    def test_year_range_rejects_future_history_and_applies_archive_delay(self):
        with self.assertRaises(ValueError):
            year_range(2027, date(2026, 10, 25))
        start, end = year_range(2026, date(2026, 10, 25), archive=True)
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 10, 18))

    def test_zero_earthquakes_is_valid_for_a_country(self):
        result = earthquake_data("GBR", fetcher=lambda _: {"type": "FeatureCollection", "features": [event(139.6,35.6)]})
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["events"], [])

    def test_year_catalogue_is_paginated_before_polygon_filter(self):
        calls = []
        def fetch(url):
            calls.append(url)
            outside_year = event(-.1278, 51.5074, "next-year")
            outside_year["properties"]["time"] = 1767225600000  # 2026-01-01, outside the requested year
            return {"features": [event(-.1278, 51.5074), outside_year]}
        result = earthquake_data("GBR", 2025, fetcher=fetch)
        self.assertEqual(result["count"], 1)
        self.assertIn("starttime=2025-01-01", calls[0])
        self.assertIn("endtime=2026-01-01", calls[0])
        self.assertIn("minlatitude=", calls[0])
        self.assertFalse(result["truncated"])


class OutlookTests(unittest.TestCase):
    def test_year_outlook_has_12_months_and_chronological_holdout(self):
        result = predict_year(synthetic_history(), 2027, today=date(2026,10,25))
        self.assertEqual(len(result["months"]), 12)
        self.assertEqual(result["holdout_years"], [2024, 2025])
        self.assertEqual(result["training_years"], list(range(2017, 2026)))
        self.assertEqual(result["holdout_months"], 24)
        self.assertTrue(all(0 <= row["high_gust_day_fraction"] <= 1 for row in result["months"]))
        self.assertIn("not exact storm dates", result["interpretation"])

    def test_target_and_later_years_cannot_leak_into_hindcast(self):
        original = synthetic_history()
        changed = [{**r, "wind_speed_10m_max": 9999, "wind_gusts_10m_max": 9999}
                   if r["date"] >= "2024-01-01" else r.copy() for r in original]
        a = predict_year(original, 2024, today=date(2026,10,25))
        b = predict_year(changed, 2024, today=date(2026,10,25))
        self.assertEqual(a["months"], b["months"])
        self.assertEqual(a["training_end_year"], 2023)

    def test_insufficient_history_fails_instead_of_fabricating_months(self):
        short = [r for r in synthetic_history() if r["date"] >= "2023-01-01"]
        with self.assertRaisesRegex(ValueError, "six complete"):
            predict_year(short, 2027, today=date(2026,10,25))

    def test_future_year_limit_is_enforced(self):
        with self.assertRaises(ValueError):
            predict_year(synthetic_history(), 2050, today=date(2026,10,25))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_dashboard_and_country_configuration_are_served(self):
        with urlopen(self.base) as response:
            text = response.read().decode()
        self.assertIn("Predict selected year", text)
        with urlopen(self.base + "/api/config") as response:
            data = json.load(response)
        self.assertGreater(len(data["countries"]), 170)
        self.assertTrue(any(x["code"] == "IND" for x in data["countries"]))

    def test_invalid_point_returns_actionable_400(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/weather?country=GBR&latitude=28.6&longitude=77.2")
        self.assertEqual(caught.exception.code, 400)
        self.assertIn("inside", json.load(caught.exception)["error"])

    def test_static_path_traversal_is_not_exposed(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/../main.py")
        self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
