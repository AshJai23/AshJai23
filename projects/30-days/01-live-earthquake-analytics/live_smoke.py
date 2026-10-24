"""Opt-in live integration check; downloads public data and saves real examples."""
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from time import perf_counter
from urllib.parse import urlencode
from urllib.request import urlopen

from dashboard import Handler


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    output = Path(__file__).parent / "examples"
    output.mkdir(exist_ok=True)

    def country_run(spec):
        code, lat, lon = spec
        results = []
        calls = [("forecast", "/api/weather", {"mode": "forecast", "days": 7}),
                 ("earthquakes", "/api/earthquakes", {"period": "year", "year": 2025, "minimum": 2.5}),
                 ("outlook-2027", "/api/predict", {"year": 2027}),
                 ("outlook-2026", "/api/predict", {"year": 2026}),
                 ("outlook-2028", "/api/predict", {"year": 2028})]
        for name, path, extra in calls:
            query = urlencode({"country": code, "latitude": lat, "longitude": lon,
                               "threshold": 60, **extra})
            started = perf_counter()
            with urlopen(base + path + "?" + query, timeout=150) as response:
                data = json.load(response)
            (output / f"{code.lower()}-{name}.json").write_text(json.dumps(data, indent=2) + "\n")
            result = {"country": code, "analysis": name, "seconds": round(perf_counter() - started, 3),
                      "rows": len(data.get("events", data.get("rows", data.get("months", [])))),
                      "timing": data.get("timing")}
            print(json.dumps(result), flush=True)
            results.append(result)
        return results

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(country_run, [("GBR", 51.5074, -.1278), ("IND", 28.6139, 77.2090)]))
        (output / "live-validation.json").write_text(json.dumps(results, indent=2) + "\n")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
