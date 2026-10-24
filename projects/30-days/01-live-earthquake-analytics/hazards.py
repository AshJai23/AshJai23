"""Public earthquake queries and honest wind/storm weather summaries."""
from datetime import date, datetime, timedelta, timezone
import math
from urllib.parse import urlencode

from geography import bounds, country, filter_events
from main import SOURCE_URL, fetch_json, normalise

DAILY = "wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum"


def year_range(year, today=None, *, archive=False):
    today = today or date.today()
    if not 2000 <= int(year) <= today.year:
        raise ValueError("Historical data requires a year between 2000 and the current year")
    start = date(int(year), 1, 1)
    end = min(date(int(year), 12, 31), today - timedelta(days=7) if archive else today)
    if end < start:
        raise ValueError("This year's archive is not available yet")
    return start, end


def earthquake_data(code="ALL", year=None, minimum=2.5, fetcher=fetch_json):
    feature = country(code)
    minimum = float(minimum)
    if not math.isfinite(minimum) or not -2 <= minimum <= 9:
        raise ValueError("Minimum magnitude must be between -2 and 9")
    urls, features, truncated = [], [], False
    if year is None:
        payload = fetcher(SOURCE_URL)
        features = payload.get("features", [])
        urls.append(SOURCE_URL)
        label = "Latest past-day USGS snapshot"
    else:
        start, end = year_range(year)
        query = {"format": "geojson", "starttime": start.isoformat(),
                 "endtime": (end + timedelta(days=1)).isoformat(), "minmagnitude": minimum,
                 "eventtype": "earthquake", "orderby": "time-asc", "limit": 10000}
        if feature is not None:
            west, south, east, north = bounds(feature)
            # A region crossing the date line can have a near-global bounding box.
            if east - west < 180:
                query.update(minlatitude=south, maxlatitude=north, minlongitude=west, maxlongitude=east)
        for page in range(4):
            query["offset"] = page * 10000 + 1
            url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urlencode(query)
            urls.append(url)
            batch = fetcher(url).get("features", [])
            features.extend(batch)
            if len(batch) < 10000:
                break
        else:
            truncated = True
        label = f"Historical catalogue: {start.isoformat()} to {end.isoformat()} inclusive"
    rows, quality = normalise({"type": "FeatureCollection", "features": features})
    if year is not None:
        rows = [r for r in rows if start.isoformat() <= r["time_utc"][:10] <= end.isoformat()]
    rows = [r for r in rows if r["magnitude"] is not None and r["magnitude"] >= minimum]
    selected = filter_events(rows, code)
    return {"mode": "earthquakes", "country": feature["properties"]["name"] if feature else "All countries / areas",
            "period": label, "source_urls": urls, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "quality": quality, "count": len(selected), "truncated": truncated,
            "boundary_note": "Approximate Natural Earth 1:110m land boundaries; offshore events are excluded for country selections.",
            "events": selected}


def daily_rows(payload, threshold=60.0):
    threshold = float(threshold)
    if not math.isfinite(threshold) or not 20 <= threshold <= 250:
        raise ValueError("Choose a high-gust threshold between 20 and 250 km/h")
    daily = payload.get("daily")
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise ValueError("Weather provider did not return daily data")
    units = payload.get("daily_units", {})
    for key in ["wind_speed_10m_max", "wind_gusts_10m_max"]:
        if units.get(key) != "km/h":
            raise ValueError("Weather wind units must be km/h")
    keys = ["wind_speed_10m_max", "wind_gusts_10m_max", "precipitation_sum"]
    if any(not isinstance(daily.get(k), list) or len(daily[k]) != len(daily["time"]) for k in keys):
        raise ValueError("Weather arrays have inconsistent lengths")
    if "weather_code" in daily and (not isinstance(daily["weather_code"], list) or len(daily["weather_code"]) != len(daily["time"])):
        raise ValueError("Weather code array has an inconsistent length")
    rows = []
    for i, stamp in enumerate(daily["time"]):
        date.fromisoformat(stamp)
        values = {}
        for key in keys:
            value = daily[key][i]
            if value is not None:
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Invalid weather observation")
            values[key] = value
        code = daily.get("weather_code", [None] * len(daily["time"]))[i]
        gust = values["wind_gusts_10m_max"]
        rows.append({"date": stamp, **values, "weather_code": code,
                     "high_gust_indicator": gust >= threshold if gust is not None else None,
                     "provider_thunderstorm": code in [95, 96, 99] if code is not None else None})
    return rows


def forecast(latitude, longitude, days=7, threshold=60.0, fetcher=fetch_json):
    days = int(days)
    if not 1 <= days <= 16:
        raise ValueError("The provider forecast supports 1 to 16 days")
    query = {"latitude": latitude, "longitude": longitude, "daily": DAILY + ",weather_code",
             "wind_speed_unit": "kmh", "timezone": "UTC", "forecast_days": days}
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(query)
    data = fetcher(url)
    return {"mode": "provider_forecast", "source_url": url, "rows": daily_rows(data, threshold),
            "retrieved_at_utc": data.get("_retrieved_at_utc", datetime.now(timezone.utc).isoformat()), "gust_threshold_kmh": threshold,
            "location_scope": "Weather at the selected coordinates, not a country-wide forecast",
            "storm_note": "Thunderstorm flags use provider WMO codes 95/96/99. High gust is a separate configurable indicator, not an official storm warning."}


def archive(latitude, longitude, start, end, threshold=60.0, fetcher=fetch_json):
    if start > end or end > date.today() - timedelta(days=7):
        raise ValueError("Archive dates must end at least 7 days ago")
    query = {"latitude": latitude, "longitude": longitude, "start_date": start.isoformat(),
             "end_date": end.isoformat(), "daily": DAILY, "wind_speed_unit": "kmh", "timezone": "UTC"}
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(query)
    data = fetcher(url)
    return {"mode": "historical_reanalysis", "source_url": url, "rows": daily_rows(data, threshold),
            "retrieved_at_utc": data.get("_retrieved_at_utc", datetime.now(timezone.utc).isoformat()),
            "location_scope": "Gridded model reanalysis at the selected coordinates; not station observations",
            "gust_threshold_kmh": threshold}
