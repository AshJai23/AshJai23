"""Observed London pollution, matched-hour spatial summaries and coverage audit."""
import argparse
import csv
import hashlib
import html
import io
import json
import math
import re
import statistics
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

API = "https://api.erg.ic.ac.uk/AirQuality"
DEFAULT_SITES = ["MY1", "BL0", "CD1", "KC1", "GR4", "GN0", "HG1", "TH4"]
POLLUTANTS = {"Nitrogen Dioxide": "NO2", "PM10 Particulate": "PM10"}
ATTRIBUTION = "Information obtained from the Environmental Research Group, Imperial College London, using London Air Quality Network data, licensed under the Open Government Licence v2.0."


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "PortfolioAirSpatial/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response: data = response.read(2_000_001)
    if len(data) > 2_000_000: raise ValueError("Response too large")
    return data.decode("utf-8-sig")


def capture(day, site_codes, destination):
    day = date.fromisoformat(day)
    if day >= datetime.now(timezone.utc).date(): raise ValueError("Choose a completed GMT day")
    if not 1 <= len(site_codes) <= 10 or len(set(site_codes)) != len(site_codes) or any(not re.fullmatch(r"[A-Z0-9]{2,5}", c) for c in site_codes):
        raise ValueError("Choose 1–10 distinct station codes")
    end = day+timedelta(days=1); urls = {"metadata": API+"/Information/MonitoringSites/GroupName=London/Json"}
    payload = json.loads(get(urls["metadata"]))
    sites = payload["Sites"]["Site"]
    if isinstance(sites, dict): sites = [sites]
    by_code = {s["@SiteCode"]: s for s in sites}
    if any(c not in by_code for c in site_codes): raise ValueError("Unknown station code")
    snapshot = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "window_start_utc": day.isoformat()+"T00:00:00+00:00", "window_end_utc": end.isoformat()+"T00:00:00+00:00", "mode": "Live API download of delayed hourly observations for a completed day; no forecasts", "requested_sites": site_codes,
                "sites": [by_code[c] for c in site_codes], "csv_by_site": {}, "request_errors": {}, "urls": urls, "licence": "Open Government Licence v2.0", "attribution": ATTRIBUTION}
    # Low-rate serial server-side calls. No background polling, no retries, no
    # fabricated fallback when the provider is unavailable.
    for code in site_codes:
        url = API+f"/Data/Site/Wide/SiteCode={code}/StartDate={day}/EndDate={end}/csv"
        snapshot["urls"][code] = url
        try: snapshot["csv_by_site"][code] = get(url)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            snapshot["request_errors"][code] = {"type": type(exc).__name__, "http_status": getattr(exc, "code", None)}
    if len(snapshot["csv_by_site"]) < 2: raise ValueError("Need at least two real station responses; no fallback fabricated")
    snapshot["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+"\n")
    return snapshot


def aware(value):
    t = datetime.fromisoformat(value)
    if t.tzinfo is None: raise ValueError("Window endpoints must include a time zone")
    return t.astimezone(timezone.utc)


def haversine(lat1, lon1, lat2, lon2):
    for lat, lon in ((lat1, lon1), (lat2, lon2)):
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError("Invalid coordinates")
    a1, a2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((a2-a1)/2)**2 + math.cos(a1)*math.cos(a2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1, max(0, h))))


def analyse(snapshot, coverage_threshold=.75):
    if not 0 < coverage_threshold <= 1: raise ValueError("Coverage threshold must be (0,1]")
    start, end = aware(snapshot["window_start_utc"]), aware(snapshot["window_end_utc"])
    if end-start != timedelta(hours=24): raise ValueError("Expected exactly 24 GMT hours")
    expected = {start+timedelta(hours=i) for i in range(24)}
    quality = Counter({k:0 for k in ("input_csv_rows", "missing_values", "outside_window_rows", "invalid_timestamp_rows", "invalid_values", "unsupported_unit_columns", "invalid_metadata_sites", "missing_metadata_sites", "missing_csv_sites", "identical_duplicates", "conflicting_duplicate_keys")})
    issues = []; metadata = {}
    requested = snapshot["requested_sites"]
    for s in snapshot["sites"]:
        code = s["@SiteCode"]
        if code not in requested: continue
        if code in metadata: raise ValueError("Duplicate station metadata")
        try:
            # These decimal-degree fields are used deliberately. The differently
            # labelled LatitudeWGS84/LongitudeWGS84 fields contain projected values.
            lat, lon = float(s["@Latitude"]), float(s["@Longitude"])
            haversine(lat, lon, lat, lon)
            if not (50 <= lat <= 53 and -1 <= lon <= 1): raise ValueError("Outside London study bounds")
            if s.get("@DateClosed") and datetime.fromisoformat(s["@DateClosed"]).replace(tzinfo=timezone.utc) <= start: raise ValueError("Closed station")
            metadata[code] = {"site": code, "name": s["@SiteName"], "site_type": s.get("@SiteType", "Unknown"), "lat": lat, "lon": lon}
        except (ValueError, KeyError): quality["invalid_metadata_sites"] += 1; issues.append({"site": code, "issue": "invalid_coordinates_or_closed_site"})
    for code in requested:
        if code not in metadata and not any(i["site"] == code for i in issues):
            quality["missing_metadata_sites"] += 1; issues.append({"site": code, "issue": "missing_metadata"})
    values = defaultdict(dict); conflicts = set()
    for code in requested:
        if code not in metadata: continue
        text = snapshot.get("csv_by_site", {}).get(code)
        if text is None:
            quality["missing_csv_sites"] += 1; issues.append({"site": code, "issue": "source_request_failed_or_missing", "detail": snapshot.get("request_errors", {}).get(code)}); continue
        reader = csv.DictReader(io.StringIO(text)); headers = reader.fieldnames or []
        if "MeasurementDateGMT" not in headers: raise ValueError("No explicit GMT measurement column")
        columns = {}
        for header in headers:
            match = re.search(r": (.+) \(([^)]+)\)$", header)
            if not match or match.group(1) not in POLLUTANTS: continue
            species = POLLUTANTS[match.group(1)]; unit = match.group(2)
            if unit not in ("ug/m3", "µg/m³", "μg/m³"):
                quality["unsupported_unit_columns"] += 1; issues.append({"site": code, "pollutant": species, "issue": "unsupported_unit", "unit": unit}); continue
            if species in columns.values(): raise ValueError("Ambiguous duplicate pollutant columns")
            columns[header] = species
        for row in reader:
            quality["input_csv_rows"] += 1
            try:
                stamp = datetime.fromisoformat(row["MeasurementDateGMT"])
                stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
            except (ValueError, TypeError): quality["invalid_timestamp_rows"] += 1; continue
            if stamp not in expected: quality["outside_window_rows"] += 1; continue
            for header, species in columns.items():
                raw = row.get(header, ""); key = (code, species); record_key = (code, species, stamp)
                if raw is None or raw.strip() == "": quality["missing_values"] += 1; continue
                try:
                    value = float(raw)
                    if not math.isfinite(value) or value < 0: raise ValueError("Invalid concentration")
                except ValueError: quality["invalid_values"] += 1; continue
                if record_key in conflicts: continue
                if stamp in values[key]:
                    if values[key][stamp] == value: quality["identical_duplicates"] += 1
                    else:
                        quality["conflicting_duplicate_keys"] += 1; conflicts.add(record_key); del values[key][stamp]
                else: values[key][stamp] = value
    stations = []
    for code in requested:
        if code not in metadata: continue
        for species in POLLUTANTS.values():
            observed = values[(code, species)]; numbers = list(observed.values()); fraction = len(numbers)/24
            stations.append({**metadata[code], "pollutant": species, "unit": "ug/m3", "valid_hours": len(numbers), "expected_hours": 24, "coverage": fraction,
                             "eligible": fraction >= coverage_threshold, "mean_available": statistics.mean(numbers) if numbers else None,
                             "max_available": max(numbers) if numbers else None, "latest_observation_utc": max(observed).isoformat() if observed else None,
                             "common_hours": 0, "mean_common_hours": None, "nearest_eligible_site": None, "nearest_distance_km": None})
    common_summary = {}; groups = []
    for species in POLLUTANTS.values():
        eligible = [s for s in stations if s["pollutant"] == species and s["eligible"]]
        common = set.intersection(*(set(values[(s["site"], species)]) for s in eligible)) if eligible else set()
        common_summary[species] = {"eligible_sites": len(eligible), "common_hours": len(common), "timestamps_utc": [t.isoformat() for t in sorted(common)]}
        for s in eligible:
            s["common_hours"] = len(common); s["mean_common_hours"] = statistics.mean(values[(s["site"], species)][t] for t in common) if common else None
            neighbours = [(haversine(s["lat"], s["lon"], n["lat"], n["lon"]), n["site"]) for n in eligible if n["site"] != s["site"]]
            if neighbours: s["nearest_distance_km"], s["nearest_eligible_site"] = min(neighbours)
        # Separate site types rather than claim a roadside/background comparison
        # measures neighbourhood health or population exposure.
        for site_type in sorted({s["site_type"] for s in eligible}):
            subset = [s for s in eligible if s["site_type"] == site_type and s["mean_common_hours"] is not None]
            groups.append({"pollutant": species, "site_type": site_type, "sites": len(subset), "common_hours": len(common), "mean_of_station_means": statistics.mean(s["mean_common_hours"] for s in subset) if subset else None, "unit": "ug/m3"})
    quality["valid_measurements"] = sum(len(v) for v in values.values()); quality["requested_sites"] = len(requested); quality["metadata_sites_usable"] = len(metadata)
    result = {"window_start_utc": start.isoformat(), "window_end_utc": end.isoformat(), "data_mode": snapshot["mode"], "retrieved_at_utc": snapshot["retrieved_at_utc"],
              "coverage_threshold": coverage_threshold, "quality": dict(quality), "issues": issues, "stations": stations, "common_hour_coverage": common_summary, "site_type_groups": groups,
              "attribution": ATTRIBUTION, "limitations": "Selected monitoring sites only; no citywide interpolation, population exposure or health advice. Recent observations can be provisional. A 24h summary is not an annual-limit compliance test. No source value is fabricated or filled."}
    return result


def write_outputs(result, output):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    (output/"summary.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    rows = result["stations"]
    with (output/"stations.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["site"]); writer.writeheader(); writer.writerows(rows)
    geo = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]}, "properties": {k:v for k,v in s.items() if k not in ("lat", "lon")}} for s in rows]}
    (output/"observations.geojson").write_text(json.dumps(geo, indent=2, allow_nan=False)+"\n")
    table = "".join("<tr>"+"".join("<td>"+html.escape(str(s[k]) if s[k] is not None else "missing")+"</td>" for k in ("site", "site_type", "pollutant", "coverage", "mean_available", "mean_common_hours", "common_hours"))+"</tr>" for s in rows)
    panels = []
    min_lon = min((s["lon"] for s in rows), default=-.4)-.025; max_lon = max((s["lon"] for s in rows), default=.2)+.025
    min_lat = min((s["lat"] for s in rows), default=51.4)-.02; max_lat = max((s["lat"] for s in rows), default=51.65)+.02
    for species in POLLUTANTS.values():
        dots = []
        for s in rows:
            if s["pollutant"] != species: continue
            x = 40+(s["lon"]-min_lon)/(max_lon-min_lon)*540; y = 270-(s["lat"]-min_lat)/(max_lat-min_lat)*230
            colour = "#327c65" if s["eligible"] else "#a0a5a0"
            dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="{colour}"><title>{html.escape(s["site"]+": "+str(s["mean_common_hours"])+" ug/m3; coverage="+str(s["coverage"]))}</title></circle><text x="{x+9:.2f}" y="{y+3:.2f}">{html.escape(s["site"])}</text>')
        panels.append('<h2>'+species+'</h2><svg viewBox="0 0 650 320" role="img" aria-label="Station locations in longitude and latitude"><path d="M40 15V275H620" stroke="#8b9a91" fill="none"/>'+"".join(dots)+'<text x="270" y="310">Longitude (degrees)</text><text x="45" y="20">Latitude (degrees); schematic, no basemap</text></svg>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Observed London air: coverage and space</title><style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#f5f7f3;color:#163d37}svg{max-width:700px;background:white;border:1px solid #ddd}text{font:11px system-ui}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}</style><h1>Observed London air quality</h1><p>'+html.escape(result["window_start_utc"]+' to '+result["window_end_utc"]+'; '+result["data_mode"])+'</p><p>Green: meets coverage threshold. Grey: insufficient data. Points are monitored sites, not an interpolated pollution surface.</p>'+"".join(panels)+'<table><tr><th>Site</th><th>Type</th><th>Pollutant</th><th>Coverage</th><th>Available mean</th><th>Matched-hour mean (ug/m3)</th><th>Common hours</th></tr>'+table+'</table><p>'+html.escape(result["limitations"])+'</p><p>'+html.escape(ATTRIBUTION)+'</p></html>'
    (output/"report.html").write_text(page)


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--input", default="examples/source_snapshot.json"); p.add_argument("--output", default="outputs"); p.add_argument("--live", action="store_true")
    p.add_argument("--date", default=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()); p.add_argument("--sites", default=",".join(DEFAULT_SITES)); p.add_argument("--minimum-coverage", type=float, default=.75)
    a = p.parse_args()
    if a.live:
        output = Path(a.output); output.mkdir(parents=True, exist_ok=True); snapshot = capture(a.date, a.sites.split(","), output/"source_snapshot.json")
    else:
        snapshot = json.loads(Path(a.input).read_text()); snapshot["mode"] = "Explicit replay of a real saved delayed-observation response; not current live data"
    result = analyse(snapshot, a.minimum_coverage); write_outputs(result, a.output)
    print(json.dumps({"quality": result["quality"], "common_hour_coverage": result["common_hour_coverage"], "site_type_groups": result["site_type_groups"]}, indent=2))
