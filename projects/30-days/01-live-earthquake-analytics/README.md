# Live earthquake analytics: Python + SQL

A small, runnable data engineering and analytics project that pulls the latest
USGS past-day earthquake feed, validates observations, deduplicates revised events,
and generates a SQLite dataset, CSV export, JSON quality report and HTML report.

**Business question:** what activity has been reported, where are the largest
reported events, and how complete is the incoming data?

## Run

Python 3.10+; Python standard library only. No account or API key is required.
From this project directory:

```bash
python main.py --live --output outputs
python -m unittest discover -s tests -v
```

Open `outputs/report.html` locally. Analyse `outputs/events.csv` in Power BI or
Tableau, or run `analytics.sql` against `outputs/earthquakes.sqlite` using a SQLite
client. The dashboard is a generated snapshot; rerun the command to refresh it.
This is not an always-on streaming service.

Reproduce the checked-in example without network access:

```bash
python main.py --input examples/source_snapshot.json --output outputs
```

## Pipeline and data quality

1. Fetch the public GeoJSON endpoint with a timeout and at most three attempts.
2. Reject invalid geometry, timestamps and non-finite numeric observations.
3. Retain missing magnitudes as null; negative magnitudes and negative depths
   are not automatically discarded.
4. Keep the newest revision when an event ID is repeated.
5. Replace the current database snapshot in one transaction. Repeating a load
   does not create duplicate events. An empty valid-event set does not overwrite
   the previous outputs.
6. Report accepted, rejected, duplicate and missing-value counts alongside SQL
   aggregates. Non-earthquake event types are explicitly counted and excluded.

The six tests cover revised records, missing values, invalid coordinates,
legitimate negative observations, idempotent loads, escaping of external text and
preservation of prior outputs on empty input. Test fixtures are synthetic and
exist only in the test code. `examples/source_snapshot.json` is a real API response.

## Example evidence

See `examples/summary.json`, `examples/report.html`, `examples/events.csv` and
`examples/validation.txt` for the captured run. Counts and timestamps describe
that snapshot, not permanently current activity. Magnitudes may use different
measurement types; the mean is descriptive, not an energy estimate. Event
locations and magnitudes can be revised, and regional detection coverage varies.

This portfolio prototype does not predict earthquakes or provide safety alerts.

## Source and attribution

- [USGS GeoJSON documentation](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)
- [Live past-day feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson)
- [USGS copyright and credit guidance](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)

Source: U.S. Geological Survey. No USGS endorsement is implied.
