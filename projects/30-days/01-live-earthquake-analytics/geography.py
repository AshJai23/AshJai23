"""Country/area filtering against bundled Natural Earth 1:110m boundaries."""
from functools import lru_cache
import json
import math
from pathlib import Path


@lru_cache(maxsize=1)
def countries():
    data = json.loads((Path(__file__).parent / "data/countries.geojson").read_text())
    return {f["properties"]["code"]: f for f in data["features"]}


def country(code):
    if code == "ALL":
        return None
    try:
        return countries()[code]
    except KeyError:
        raise ValueError("Choose a country/area from the selector") from None


def ring_contains(ring, lon, lat):
    """Ray casting, including a point lying on a boundary segment."""
    inside = False
    for i in range(len(ring)):
        ax, ay = ring[i - 1]
        bx, by = ring[i]
        cross = (lon - ax) * (by - ay) - (lat - ay) * (bx - ax)
        if abs(cross) < 1e-9 and min(ax, bx) - 1e-9 <= lon <= max(ax, bx) + 1e-9 and min(ay, by) - 1e-9 <= lat <= max(ay, by) + 1e-9:
            return True
        if (ay > lat) != (by > lat):
            x = (bx - ax) * (lat - ay) / (by - ay) + ax
            if lon < x:
                inside = not inside
    return inside


def contains(feature, lon, lat):
    if not math.isfinite(lon) or not math.isfinite(lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return False
    geometry = feature["geometry"]
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    return any(ring_contains(polygon[0], lon, lat) and
               not any(ring_contains(hole, lon, lat) for hole in polygon[1:]) for polygon in polygons)


def bounds(feature):
    geometry = feature["geometry"]
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    points = [point for poly in polygons for ring in poly for point in ring]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def filter_events(rows, code):
    feature = country(code)
    if feature is None:
        return rows
    return [row for row in rows if contains(feature, row["longitude"], row["latitude"])]


PRESETS = {
    "GBR": (51.5074, -0.1278, "London"), "IND": (28.6139, 77.2090, "New Delhi"),
    "USA": (38.9072, -77.0369, "Washington, DC"), "JPN": (35.6762, 139.6503, "Tokyo"),
    "FRA": (48.8566, 2.3522, "Paris"), "DEU": (52.52, 13.405, "Berlin"),
    "AUS": (-35.2809, 149.13, "Canberra"), "CAN": (45.4215, -75.6972, "Ottawa"),
    "BRA": (-15.7939, -47.8828, "Brasilia"), "ZAF": (-25.7479, 28.2293, "Pretoria"),
    "GNQ": (2.0, 10.25, "Mainland representative point"),
    "NZL": (-40.3523, 175.6082, "Palmerston North"),
    "TTO": (10.45, -61.3, "Central Trinidad representative point"),
}


def catalogue():
    result = []
    for code, feature in countries().items():
        props = feature["properties"]
        lat, lon, label = PRESETS.get(code, (props["label_lat"], props["label_lon"], "Representative location"))
        result.append({"code": code, "name": props["name"], "latitude": lat, "longitude": lon, "location": label})
    return sorted(result, key=lambda item: item["name"])


def validate_location(code, latitude, longitude):
    latitude, longitude = float(latitude), float(longitude)
    feature = country(code)
    if feature is None:
        raise ValueError("Select a country/area before requesting local weather")
    if not contains(feature, longitude, latitude):
        raise ValueError("The weather point must lie inside the selected country's mapped boundary; choose another point")
    return latitude, longitude
