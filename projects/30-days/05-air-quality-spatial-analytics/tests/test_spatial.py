"""Synthetic test-only CSV values; production examples use actual LAQN responses."""
import copy
import json
import math
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from main import analyse, capture, haversine, write_outputs


def fixture():
    meta = [{"@SiteCode":code,"@SiteName":code,"@SiteType":"Urban Background","@Latitude":str(51.5+i*.01),"@Longitude":str(-.1+i*.01),"@DateClosed":""} for i,code in enumerate(["AA1","BB1"])]
    texts = {s["@SiteCode"]:"MeasurementDateGMT,Test: Nitrogen Dioxide (ug/m3),Test: PM10 Particulate (ug/m3)\n"+"".join(f"2026-10-25 {h:02d}:00:00,{h},10\n" for h in range(24)) for s in meta}
    return {"window_start_utc":"2026-10-25T00:00:00+00:00","window_end_utc":"2026-10-26T00:00:00+00:00","mode":"SYNTHETIC TEST FIXTURE ONLY","retrieved_at_utc":"2026-10-26T09:00:00+00:00","requested_sites":["AA1","BB1"],"sites":meta,"csv_by_site":texts}


class SpatialTests(unittest.TestCase):
    def test_full_coverage_zero_value_and_matched_hours(self):
        r = analyse(fixture()); s = r["stations"][0]
        self.assertEqual(s["valid_hours"],24); self.assertEqual(s["mean_available"],11.5)
        self.assertEqual(r["common_hour_coverage"]["NO2"]["common_hours"],24)
    def test_units_are_read_from_headers_and_wrong_units_are_rejected(self):
        x = fixture(); x["csv_by_site"]["AA1"] = x["csv_by_site"]["AA1"].replace("Nitrogen Dioxide (ug/m3)","Nitrogen Dioxide (mg/m3)")
        r = analyse(x); self.assertEqual(r["quality"]["unsupported_unit_columns"],1)
        self.assertEqual(r["stations"][0]["valid_hours"],0)
    def test_missing_values_are_not_zero(self):
        x = fixture(); x["csv_by_site"]["AA1"] = x["csv_by_site"]["AA1"].replace(",10\n",",\n")
        r = analyse(x); s = next(s for s in r["stations"] if s["site"]=="AA1" and s["pollutant"]=="PM10")
        self.assertIsNone(s["mean_available"]); self.assertEqual(s["coverage"],0)
    def test_nonfinite_and_negative_values_are_rejected(self):
        x = fixture(); x["csv_by_site"]["AA1"] = x["csv_by_site"]["AA1"].replace(",0,10",",NaN,10").replace(",1,10",",inf,10").replace(",2,10",",-1,10")
        self.assertEqual(analyse(x)["quality"]["invalid_values"],3)
    def test_comparison_uses_intersection_not_different_hours(self):
        x = fixture()
        for code, keep in [("AA1",range(18)),("BB1",range(6,24))]:
            lines = x["csv_by_site"][code].splitlines(); x["csv_by_site"][code] = lines[0]+"\n"+"\n".join(lines[h+1] for h in keep)
        r = analyse(x); self.assertEqual(r["common_hour_coverage"]["NO2"]["common_hours"],12)
        s = [s for s in r["stations"] if s["pollutant"]=="NO2"]
        self.assertNotEqual(s[0]["mean_available"],s[1]["mean_available"])
        self.assertEqual(s[0]["mean_common_hours"],s[1]["mean_common_hours"])
    def test_projected_or_swapped_coordinate_fields_are_not_accepted(self):
        x = fixture(); x["sites"][0]["@Latitude"] = "6700000"
        r = analyse(x); self.assertEqual(r["quality"]["invalid_metadata_sites"],1)
    def test_missing_metadata_is_reported(self):
        x = fixture(); x["sites"] = x["sites"][:1]
        self.assertEqual(analyse(x)["quality"]["missing_metadata_sites"],1)
    def test_closed_station_is_excluded(self):
        x = fixture(); x["sites"][0]["@DateClosed"] = "2026-10-01 00:00:00"
        self.assertEqual(analyse(x)["quality"]["metadata_sites_usable"],1)
    def test_identical_duplicate_counts_once(self):
        x = fixture(); x["csv_by_site"]["AA1"] += "2026-10-25 00:00:00,0,10\n"
        r = analyse(x); self.assertEqual(r["quality"]["identical_duplicates"],2); self.assertEqual(r["stations"][0]["valid_hours"],24)
    def test_conflicting_duplicate_key_is_removed(self):
        x = fixture(); x["csv_by_site"]["AA1"] += "2026-10-25 00:00:00,99,10\n"
        r = analyse(x); self.assertEqual(r["quality"]["conflicting_duplicate_keys"],1); self.assertEqual(r["stations"][0]["valid_hours"],23)
    def test_extra_inclusive_endpoint_midnight_is_excluded(self):
        x = fixture(); x["csv_by_site"]["AA1"] += "2026-10-26 00:00:00,99,99\n"
        self.assertEqual(analyse(x)["quality"]["outside_window_rows"],1)
    def test_gmt_day_remains_twenty_four_hours_at_dst_transition(self):
        r = analyse(fixture()); self.assertTrue(all(s["expected_hours"]==24 for s in r["stations"]))
    def test_unknown_clock_column_is_rejected(self):
        x = fixture(); x["csv_by_site"]["AA1"] = x["csv_by_site"]["AA1"].replace("MeasurementDateGMT","LocalTime")
        with self.assertRaises(ValueError): analyse(x)
    def test_aware_window_is_required(self):
        x = fixture(); x["window_start_utc"] = "2026-10-25T00:00:00"
        with self.assertRaises(ValueError): analyse(x)
    def test_haversine_distance_is_in_kilometres(self):
        self.assertAlmostEqual(haversine(51,0,52,0),111.195,places=2)
        self.assertEqual(haversine(51,0,51,0),0)
    def test_nearest_station_does_not_select_itself(self):
        for s in analyse(fixture())["stations"]:
            self.assertNotEqual(s["site"],s["nearest_eligible_site"]); self.assertGreater(s["nearest_distance_km"],0)
    def test_geojson_order_and_html_escaping(self):
        x = fixture(); x["sites"][0]["@SiteName"] = "<script>bad()</script>"
        with tempfile.TemporaryDirectory() as d:
            write_outputs(analyse(x),d); geo = json.loads((Path(d)/"observations.geojson").read_text())
            self.assertEqual(geo["features"][0]["geometry"]["coordinates"],[-.1,51.5])
            self.assertNotIn("<script>",(Path(d)/"report.html").read_text())
    def test_live_failure_is_not_replaced_with_test_data(self):
        with tempfile.TemporaryDirectory() as d, patch("main.get", side_effect=TimeoutError):
            p = Path(d)/"source.json"
            with self.assertRaises(TimeoutError): capture("2026-10-25",["AA1"],p)
            self.assertFalse(p.exists())
    def test_partial_source_failure_is_explicit_not_silent(self):
        x = fixture(); third = dict(x["sites"][0]); third["@SiteCode"] = "CC1"
        responses = [json.dumps({"Sites":{"Site":x["sites"]+[third]}}), x["csv_by_site"]["AA1"], urllib.error.HTTPError("https://provider.example",400,"bad",{},None), x["csv_by_site"]["AA1"]]
        with tempfile.TemporaryDirectory() as d, patch("main.get", side_effect=responses):
            snapshot = capture("2026-10-25",["AA1","BB1","CC1"],Path(d)/"source.json")
        self.assertEqual(snapshot["request_errors"]["BB1"]["http_status"],400)
        result = analyse(snapshot); self.assertEqual(result["quality"]["missing_csv_sites"],1)
        self.assertEqual(next(s for s in result["stations"] if s["site"]=="BB1")["coverage"],0)


if __name__ == "__main__": unittest.main()
