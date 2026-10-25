"""Pull or replay METAR observations and audit their data quality, not flying conditions."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from html import escape
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_STATIONS = ["EGLL", "EGCC", "EGPH", "VIDP", "VABB"]
FIELDS = {"temp": (-90, 60), "dewp": (-100, 60), "wspd": (0, 250),
          "wgst": (0, 300), "altim": (800, 1100), "lat": (-90, 90), "lon": (-180, 180)}
CORE = ["temp", "wspd", "altim"]


def parse_stations(value):
    stations = list(dict.fromkeys(x.strip().upper() for x in value.split(",")))
    if not 1 <= len(stations) <= 20 or any(not re.fullmatch(r"[A-Z0-9]{4}", s) for s in stations):
        raise ValueError("Supply 1–20 four-character ICAO station identifiers")
    return stations


def parse_time(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a timestamp")
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("Timestamp is not finite")
        return datetime.fromtimestamp(value, timezone.utc)
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must have a timezone")
    return result.astimezone(timezone.utc)


def fetch_observations(stations):
    url = "https://aviationweather.gov/api/data/metar?" + urlencode(
        {"ids": ",".join(stations), "format": "json", "hours": 3})
    request = Request(url, headers={"User-Agent": "AshJai23-WeatherQualityPortfolio/1.0", "Accept": "application/json"})
    # One scoped request, no tight retry loop. A 204 is valid empty data.
    with urlopen(request, timeout=30) as response:
        data = [] if response.status == 204 else json.load(response)
    return data, url


def audit(payload, stations, as_of, stale_minutes=90):
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON array of METAR records; an error object is not empty weather")
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not math.isfinite(stale_minutes) or stale_minutes <= 0:
        raise ValueError("Freshness threshold must be positive and finite")
    as_of = as_of.astimezone(timezone.utc)
    rows, rejected, unexpected, seen = [], [], 0, {}
    duplicates, conflicts = 0, set()
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            rejected.append({"index": index, "station": None, "reason": "Record is not an object"})
            continue
        station = raw.get("icaoId")
        if station not in stations:
            unexpected += 1
            continue
        try:
            observed = parse_time(raw.get("obsTime"))
        except (ValueError, TypeError, OverflowError, OSError):
            rejected.append({"index": index, "station": station, "reason": "Unusable observation timestamp"})
            continue
        issues, values = [], {}
        for field, (lower, upper) in FIELDS.items():
            value = raw.get(field)
            if value is None:
                values[field] = None
                continue
            try:
                if isinstance(value, bool):
                    raise ValueError()
                value = float(value)
                if not math.isfinite(value) or not lower <= value <= upper:
                    raise ValueError()
                values[field] = value
            except (ValueError, TypeError):
                values[field] = None
                issues.append("invalid_" + field)
        direction = raw.get("wdir")
        if direction not in [None, "VRB"]:
            try:
                if isinstance(direction, bool) or not 0 <= float(direction) <= 360:
                    raise ValueError()
                direction = float(direction)
            except (ValueError, TypeError):
                direction = None
                issues.append("invalid_wdir")
        if values["temp"] is not None and values["dewp"] is not None and values["dewp"] > values["temp"] + 1:
            issues.append("dewpoint_exceeds_temperature")
        if values["wgst"] is not None and values["wspd"] is not None and values["wgst"] < values["wspd"]:
            issues.append("gust_below_sustained_wind")
        age = (as_of - observed).total_seconds() / 60
        if age < -5:
            issues.append("future_observation")
        row = {"station": station, "observed_at_utc": observed.isoformat(), "age_minutes": round(age, 2),
               **values, "wdir": direction, "issues": issues, "provider_qc_field": raw.get("qcField")}
        key = (station, row["observed_at_utc"])
        if key in seen:
            duplicates += 1
            if {k: v for k, v in row.items() if k != "age_minutes"} != seen[key]:
                conflicts.add(station)
            # Keep the first report and flag conflicting copies; do not silently merge revisions.
            continue
        seen[key] = {k: v for k, v in row.items() if k != "age_minutes"}
        rows.append(row)
    summaries = []
    for station in stations:
        candidates = [r for r in rows if r["station"] == station]
        bad_times = sum(r["station"] == station for r in rejected)
        if not candidates:
            summaries.append({"station": station, "status": "FAIL", "observed_at_utc": None,
                              "age_minutes": None, "issues": ["unusable_station_records" if bad_times else "missing_station"],
                              "temp": None, "wspd": None, "altim": None, "wgst": None})
            continue
        latest = max(candidates, key=lambda r: r["observed_at_utc"])
        issues = list(latest["issues"])
        if latest["age_minutes"] > stale_minutes:
            issues.append("stale_observation")
        for field in CORE:
            if latest[field] is None and "invalid_" + field not in issues:
                issues.append("missing_" + field)
        if bad_times:
            issues.append("other_records_have_invalid_timestamps")
        if station in conflicts:
            issues.append("conflicting_duplicate")
        failing = any(i.startswith("invalid_") or i in ["future_observation", "dewpoint_exceeds_temperature", "gust_below_sustained_wind"] for i in latest["issues"])
        summaries.append({**latest, "status": "FAIL" if failing else "WARN" if issues else "PASS", "issues": issues})
    counts = {status: sum(r["status"] == status for r in summaries) for status in ["PASS", "WARN", "FAIL"]}
    return {"evaluated_at_utc": as_of.isoformat(), "stale_after_minutes": stale_minutes,
            "units": {"temp": "Celsius", "dewp": "Celsius", "wspd": "knots", "wgst": "knots", "altim": "hPa"},
            "quality": {"input_records": len(payload), "unique_usable_timestamp_records": len(rows),
                        "rejected_timestamp_or_structure_records": len(rejected), "unexpected_station_records": unexpected,
                        "duplicate_records": duplicates, "conflicting_duplicate_stations": sorted(conflicts)},
            "station_status_counts": counts, "stations": summaries,
            "missing_or_invalid_core_fields": {f: sum(s.get(f) is None for s in summaries) for f in CORE},
            "rejected_records": rejected, "observations": rows,
            "meaning": "PASS means these data-quality rules passed, not good weather or certified observation accuracy."}


def render(result):
    body = "".join("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in
             [r["station"], r["status"], r["observed_at_utc"], r["age_minutes"], r.get("temp"), r.get("wspd"), r.get("altim"), ", ".join(r["issues"]) or "None"]) + "</tr>" for r in result["stations"])
    counts = result["station_status_counts"]
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Weather data quality monitor</title><style>body{{font:16px/1.6 system-ui;background:#101c2a;color:#e2edf0;max-width:1200px;margin:32px auto;padding:24px}}h1,h2{{color:#63e3cb}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #345}}a{{color:#63e3cb}}</style>
    <h1>Weather data quality monitor</h1><p>Evaluated at {escape(result['evaluated_at_utc'])} · mode: {escape(result['mode'])}</p>
    <p>PASS: {counts['PASS']} · WARN: {counts['WARN']} · FAIL: {counts['FAIL']}</p>
    <p>Temperature °C · wind knots · pressure hPa. Missing gust does not mean zero gust.</p>
    <div class="scroll"><table><thead><tr><th>Station</th><th>Data status</th><th>Observation UTC</th><th>Age minutes</th><th>Temperature</th><th>Wind</th><th>Pressure</th><th>Issues</th></tr></thead><tbody>{body}</tbody></table></div>
    <h2>Interpretation</h2><p>{escape(result['meaning'])} Freshness limit: {result['stale_after_minutes']} minutes.</p>
    <p>One pulled snapshot, not continuous monitoring. No model training or weather prediction. No aviation decision support.</p>
    <p>Data: NOAA/NWS Aviation Weather Center, <a href="https://aviationweather.gov/data/api/">API documentation</a>. No endorsement implied.</p></html>"""


def write_outputs(result, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "quality.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "report.html").write_text(render(result))
    fields = ["station", "status", "observed_at_utc", "age_minutes", "temp", "wspd", "wgst", "altim", "issues"]
    with (output / "stations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({**r, "issues": ";".join(r["issues"])} for r in result["stations"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--input", type=Path)
    parser.add_argument("--stations", default=",".join(DEFAULT_STATIONS))
    parser.add_argument("--as-of", help="Timezone-aware evaluation clock for reproducible replay only")
    parser.add_argument("--stale-minutes", type=float, default=90)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    try:
        stations = parse_stations(args.stations)
        if args.live and args.as_of:
            raise ValueError("--as-of is for replay; live mode always uses the current clock")
        payload, source = fetch_observations(stations) if args.live else (json.loads(args.input.read_text()), str(args.input))
        as_of = parse_time(args.as_of) if args.as_of else datetime.now(timezone.utc)
        result = audit(payload, stations, as_of, args.stale_minutes)
        result.update(source=source, mode="live_pull" if args.live else "saved_snapshot_replay")
        write_outputs(result, args.output)
        if args.live:
            (args.output / "source_snapshot.json").write_text(json.dumps(payload, indent=2) + "\n")
        print(json.dumps({"quality": result["quality"], "statuses": result["station_status_counts"]}, indent=2))
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Weather quality check failed: {error}\n")


if __name__ == "__main__":
    main()
