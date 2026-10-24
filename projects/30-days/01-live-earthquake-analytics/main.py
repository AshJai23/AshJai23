"""Validate a live USGS earthquake snapshot and publish SQL-backed analytics."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from html import escape
import json
import math
from pathlib import Path
import sqlite3
import time
from urllib.request import Request, urlopen

SOURCE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


def fetch_json(url: str) -> dict:
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "AshJai23-Portfolio/1.0", "Accept": "application/json"})
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(0.5 * 2 ** attempt)
    raise RuntimeError("Unreachable")


def number(value, *, optional=False):
    if value is None and optional:
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric observation")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Observation is not finite")
    return result


def iso_ms(value):
    return datetime.fromtimestamp(number(value) / 1000, timezone.utc).isoformat()


def normalise(payload: dict):
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise ValueError("Expected a USGS GeoJSON FeatureCollection")
    events = {}
    audit = {"input_rows": len(payload["features"]), "invalid_rows": 0,
             "duplicate_ids": 0, "non_earthquakes": 0, "missing_magnitude": 0}
    for feature in payload["features"]:
        try:
            props = feature["properties"]
            if props.get("type", "earthquake") != "earthquake":
                audit["non_earthquakes"] += 1
                continue
            event_id = feature["id"]
            if not isinstance(event_id, str) or not event_id:
                raise ValueError("Missing event ID")
            geometry = feature["geometry"]
            if geometry.get("type") != "Point":
                raise ValueError("Expected Point geometry")
            longitude, latitude, depth = map(number, geometry["coordinates"])
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                raise ValueError("Coordinates out of range")
            event = {
                "event_id": event_id, "time_utc": iso_ms(props["time"]),
                "updated_utc": iso_ms(props.get("updated", props["time"])),
                "magnitude": number(props.get("mag"), optional=True),
                "latitude": latitude, "longitude": longitude, "depth_km": depth,
                "place": str(props.get("place") or "Unknown"),
                "source_url": str(props.get("url") or ""),
            }
            if event_id in events:
                audit["duplicate_ids"] += 1
                if event["updated_utc"] < events[event_id]["updated_utc"]:
                    continue
            events[event_id] = event
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            audit["invalid_rows"] += 1
    rows = sorted(events.values(), key=lambda row: row["time_utc"])
    audit["accepted_rows"] = len(rows)
    audit["missing_magnitude"] = sum(row["magnitude"] is None for row in rows)
    return rows, audit


def write_database(path: Path, rows: list[dict]):
    """Replace the current snapshot atomically; repeated loads do not duplicate events."""
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, time_utc TEXT NOT NULL, updated_utc TEXT NOT NULL,
            magnitude REAL, latitude REAL NOT NULL, longitude REAL NOT NULL,
            depth_km REAL NOT NULL, place TEXT NOT NULL, source_url TEXT NOT NULL
        )""")
        db.execute("DELETE FROM events")
        db.executemany("""INSERT INTO events VALUES (
            :event_id, :time_utc, :updated_utc, :magnitude, :latitude,
            :longitude, :depth_km, :place, :source_url)""", rows)
        db.execute("""CREATE VIEW IF NOT EXISTS magnitude_distribution AS
            SELECT CASE WHEN magnitude IS NULL THEN 'Unknown'
                        WHEN magnitude < 2 THEN 'Below 2'
                        WHEN magnitude < 4 THEN '2 to below 4'
                        WHEN magnitude < 6 THEN '4 to below 6'
                        ELSE '6 and above' END AS magnitude_band,
                   COUNT(*) AS event_count FROM events GROUP BY magnitude_band""")


def summarise(path: Path, audit: dict, source: str, generated_ms=None):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        stats = dict(db.execute("""SELECT COUNT(*) AS event_count,
            ROUND(AVG(magnitude), 3) AS mean_magnitude, MAX(magnitude) AS largest_magnitude,
            MIN(time_utc) AS first_event_utc, MAX(time_utc) AS latest_event_utc FROM events""").fetchone())
        bins = [dict(row) for row in db.execute("SELECT * FROM magnitude_distribution ORDER BY magnitude_band")]
        largest = [dict(row) for row in db.execute("""SELECT event_id, time_utc, place,
            magnitude, depth_km FROM events WHERE magnitude IS NOT NULL
            ORDER BY magnitude DESC, time_utc DESC LIMIT 10""")]
    return {"built_at_utc": datetime.now(timezone.utc).isoformat(), "source": source,
            "feed_generated_utc": iso_ms(generated_ms) if generated_ms is not None else None,
            "scope": "Current USGS past-day snapshot, earthquake events only",
            "quality": audit, "statistics": stats, "magnitude_distribution": bins,
            "largest_events": largest}


def render_report(summary: dict) -> str:
    stats = summary["statistics"]
    bins = "".join(f"<tr><td>{escape(row['magnitude_band'])}</td><td>{row['event_count']}</td></tr>"
                   for row in summary["magnitude_distribution"])
    events = "".join("<tr>" + "".join(f"<td>{escape(str(row[key]))}</td>"
                    for key in ["time_utc", "place", "magnitude", "depth_km"]) + "</tr>"
                    for row in summary["largest_events"])
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Live earthquake analytics</title><style>
    body{{font:16px/1.6 system-ui;background:#101c2a;color:#e2edf0;max-width:1000px;margin:40px auto;padding:24px}}
    h1,h2{{color:#63e3cb}}table{{border-collapse:collapse;width:100%;margin:24px 0}}
    td,th{{border-bottom:1px solid #345;padding:10px;text-align:left}}code{{color:#f6c66a}}
    .cards{{display:flex;gap:28px;flex-wrap:wrap}}.card{{background:#142d3a;padding:24px;border-radius:16px}}
    </style><h1>Live earthquake analytics</h1>
    <p>USGS past-day feed · generated {escape(str(summary['feed_generated_utc']))}</p>
    <div class="cards"><div class="card">Events: <b>{stats['event_count']}</b></div>
    <div class="card">Largest magnitude: <b>{stats['largest_magnitude']}</b></div>
    <div class="card">Missing magnitude: <b>{summary['quality']['missing_magnitude']}</b></div></div>
    <h2>Magnitude distribution</h2><table><tr><th>Magnitude</th><th>Events</th></tr>{bins}</table>
    <h2>Largest reported events</h2><table><tr><th>UTC time</th><th>Place</th><th>Magnitude</th><th>Depth km</th></tr>{events}</table>
    <p>Snapshot analysis, not an earthquake prediction or public warning service.
    Incomplete observations stay visible in the quality report. Magnitude types can differ.</p></html>"""


def run(payload, output: Path, source: str):
    output.mkdir(parents=True, exist_ok=True)
    rows, audit = normalise(payload)
    if not rows:
        raise ValueError("No valid earthquake events; previous output has not been replaced")
    write_database(output / "earthquakes.sqlite", rows)
    summary = summarise(output / "earthquakes.sqlite", audit, source, payload.get("metadata", {}).get("generated"))
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    (output / "report.html").write_text(render_report(summary))
    with (output / "events.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--input", type=Path, help="Replay a saved USGS JSON snapshot")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    try:
        payload = fetch_json(SOURCE_URL) if args.live else json.loads(args.input.read_text())
        result = run(payload, args.output, SOURCE_URL if args.live else str(args.input))
        print(json.dumps(result["statistics"], indent=2))
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Data pipeline failed: {error}\n")


if __name__ == "__main__":
    main()
