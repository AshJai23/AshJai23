import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from main import normalise, render_report, run, write_database


def event(event_id="a", magnitude=2.5, updated=2000):
    return {"id": event_id, "properties": {"type": "earthquake", "time": 1000,
            "updated": updated, "mag": magnitude, "place": "<script>alert(1)</script>"},
            "geometry": {"type": "Point", "coordinates": [1, 2, 3]}}


def payload(*events):
    return {"type": "FeatureCollection", "features": list(events)}


class PipelineTests(unittest.TestCase):
    def test_latest_revision_wins_regardless_of_input_order(self):
        rows, audit = normalise(payload(event(magnitude=4, updated=5000), event(magnitude=2, updated=2000)))
        self.assertEqual(rows[0]["magnitude"], 4)
        self.assertEqual(audit["duplicate_ids"], 1)

    def test_null_magnitude_is_preserved(self):
        rows, audit = normalise(payload(event(magnitude=None)))
        self.assertIsNone(rows[0]["magnitude"])
        self.assertEqual(audit["missing_magnitude"], 1)

    def test_invalid_coordinate_and_nan_are_rejected(self):
        bad = event("bad")
        bad["geometry"]["coordinates"][1] = 95
        rows, audit = normalise(payload(event(), bad, event("nan", float("nan"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(audit["invalid_rows"], 2)

    def test_negative_magnitude_and_depth_are_not_discarded(self):
        row = event(magnitude=-0.3)
        row["geometry"]["coordinates"][2] = -1
        rows, _ = normalise(payload(row))
        self.assertEqual(rows[0]["magnitude"], -0.3)

    def test_database_reload_is_idempotent_and_html_is_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = run(payload(event()), output, "unit-test fixture")
            rows, _ = normalise(payload(event()))
            write_database(output / "earthquakes.sqlite", rows)
            with sqlite3.connect(output / "earthquakes.sqlite") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0], 1)
            self.assertIn("&lt;script&gt;", render_report(result))
            self.assertNotIn("<script>", render_report(result))

    def test_empty_input_does_not_replace_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            run(payload(event()), output, "fixture")
            previous = (output / "summary.json").read_text()
            with self.assertRaises(ValueError):
                run(payload(), output, "empty fixture")
            self.assertEqual(previous, (output / "summary.json").read_text())


if __name__ == "__main__":
    unittest.main()
