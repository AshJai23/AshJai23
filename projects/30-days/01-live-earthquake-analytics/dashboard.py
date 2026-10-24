"""Local country-wise earthquake, wind/storm and calendar-year outlook dashboard."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
import time
from urllib.parse import parse_qs, urlsplit

from geography import catalogue, validate_location
from hazards import archive, earthquake_data, forecast, year_range
from main import fetch_json
from outlook import predict_year

ROOT = Path(__file__).parent
_cache = {}
_cache_lock = Lock()


def cached_fetch(url):
    ttl = 86400 if "archive-api.open-meteo.com" in url else 300
    with _cache_lock:
        cached = _cache.get(url)
        if cached and cached[0] > time.monotonic():
            return cached[1]
    data = fetch_json(url)
    data = dict(data)
    data["_retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    with _cache_lock:
        if len(_cache) >= 64:
            _cache.pop(next(iter(_cache)))
        _cache[url] = (time.monotonic() + ttl, data)
    return data


def api(path, query, fetcher=cached_fetch):
    get = lambda key, default=None: query.get(key, [default])[0]
    if path == "/api/config":
        return {"countries": catalogue(), "current_year": date.today().year,
                "minimum_year": 2000, "maximum_predict_year": date.today().year + 3,
                "boundary_resolution": "Natural Earth 1:110m; small islands and offshore events may be missing"}
    if path == "/api/map":
        return json.loads((ROOT / "data/countries.geojson").read_text())
    code = get("country", "GBR")
    if path == "/api/earthquakes":
        period = get("period", "day")
        if period not in ["day", "year"]:
            raise ValueError("Select past-day or selected-year earthquake history")
        return earthquake_data(code, int(get("year")) if period == "year" else None,
                               float(get("minimum", 2.5)), fetcher=fetcher)
    if path not in ["/api/weather", "/api/predict"]:
        raise ValueError("Unknown API endpoint")
    latitude, longitude = validate_location(code, get("latitude"), get("longitude"))
    threshold = float(get("threshold", 60))
    if not 20 <= threshold <= 250:
        raise ValueError("Choose a high-gust threshold from 20 to 250 km/h")
    if path == "/api/weather":
        mode = get("mode", "forecast")
        if mode == "forecast":
            result = forecast(latitude, longitude, int(get("days", 7)), threshold, fetcher)
        elif mode == "history":
            start, end = year_range(int(get("year")), archive=True)
            result = archive(latitude, longitude, start, end, threshold, fetcher)
        else:
            raise ValueError("Select forecast or historical weather")
    else:
        target = int(get("year"))
        if not 2000 <= target <= date.today().year + 3:
            raise ValueError("Choose a supported prediction year")
        end_year = min(target - 1, date.today().year - 1)
        history = archive(latitude, longitude, date(end_year - 8, 1, 1), date(end_year, 12, 31), threshold, fetcher)
        result = predict_year(history["rows"], target, threshold)
        result["source_url"] = history["source_url"]
        result["retrieved_at_utc"] = history["retrieved_at_utc"]
        result["data_kind"] = "Historical model reanalysis; no target-year observations used"
    result["country_code"] = code
    result["latitude"] = latitude
    result["longitude"] = longitude
    return result


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        requested = urlsplit(self.path)
        if requested.path.startswith("/api/"):
            try:
                result = api(requested.path, parse_qs(requested.query))
                body = json.dumps(result, allow_nan=False).encode()
                self.send(200, body, "application/json; charset=utf-8")
            except (ValueError, TypeError, KeyError) as error:
                self.send(400, json.dumps({"error": str(error)}).encode(), "application/json")
            except OSError as error:
                self.send(502, json.dumps({"error": f"Data source request failed: {error}"}).encode(), "application/json")
            except Exception as error:
                self.log_error("Request failed: %s", error)
                self.send(500, json.dumps({"error": "The analysis could not complete; check the server log"}).encode(), "application/json")
            return
        if requested.path in ["/", "/index.html"]:
            self.send(200, (ROOT / "static/index.html").read_bytes(), "text/html; charset=utf-8")
        elif requested.path == "/favicon.ico":
            self.send(204, b"", "image/x-icon")
        else:
            self.send(404, b"Not found", "text/plain")

    def send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Hazard Explorer: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
