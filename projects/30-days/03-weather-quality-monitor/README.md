# Live weather data quality monitor

## Niche, data freshness and how to open

**Niche:** Weather-feed quality for transport and operations.

**Data truth:** METAR observations from a US-operated public API covering UK and Indian stations by default. Choose UK stations explicitly; live pull is one request, not continuous streaming.

**Website status:** runnable locally; no public project website has been deployed.
The GitHub address displays source code. An HTML file in GitHub's file viewer is
not a hosted dashboard.

From this project folder, install its documented dependencies, then run:

```bash
python main.py --live --stations EGLL,EGCC,EGPH --output outputs
```

Open the generated **`outputs/report.html`** from your local output folder.
It is a saved report; it refreshes only when you run the command again.

**Separate repository:** requested; creation is pending. The current folder and
its previous validation evidence remain available. Extraction is not a new
project and does not increase the completed count.

Project 03 of the 30-day portfolio sprint. A small Python data-science prototype
that asks: **is the incoming station weather data complete, recent and internally
consistent enough to inspect?** Built with AI assistance.

A data record is one weather report. This program audits those reports, rather
than predicting weather or learning a model. It is separate from project 01's
wind/storm dashboard: it uses observed METAR station reports, not gridded weather
forecasts, and focuses on quality gates and expected-station coverage.

## Run

Python 3.10+; standard library only. No paid account, API key or third-party
Python package is required.

```bash
cd projects/30-days/03-weather-quality-monitor
python main.py --live --output outputs
python -m unittest discover -s tests -v
```

Open `outputs/report.html` locally, inspect `outputs/quality.json`, or import
`outputs/stations.csv` into Excel, Power BI or Tableau.

This makes **one scoped API request** for the previous three hours. Refresh by
running the command again, respecting the provider's update frequency and rate
limits. There is no background polling, always-on server or public deployment.
Most METARs update hourly, with additional special reports possible.

Default stations:

| ICAO identifier | Location |
|---|---|
| EGLL | London Heathrow, UK |
| EGCC | Manchester, UK |
| EGPH | Edinburgh, UK |
| VIDP | New Delhi, India |
| VABB | Mumbai, India |

Choose 1–20 identifiers with `--stations EGLL,VIDP`. A valid identifier does not
guarantee that a station will return data. Missing expected stations are explicitly
reported as failures. The query is capped in scope to avoid large downloads.

## Rules and outputs

- Freshness uses the observation timestamp, not a newer receipt timestamp.
- Default staleness threshold: 90 minutes; change with `--stale-minutes`.
- A timestamp more than five minutes ahead of the evaluation clock fails.
- Validate finite numeric values, broad plausible ranges, dewpoint no more than
  1°C above temperature, and reported gust no lower than sustained wind.
- Core fields are temperature, wind speed and altimeter setting. Missing core
  fields warn; invalid measurements fail. Optional gusts are allowed to be absent.
- Variable direction (`VRB`) and calm wind are accepted. No gust report is not
  interpreted as a zero gust.
- Different observation times are history, not duplicates. Repeated station/time
  keys are counted; conflicting copies warn, with the first report retained.
- Records without usable timestamps are quarantined, counted and exposed.
- Select the latest timestamp per station, even when its measurement quality is
  bad; an older good observation does not silently hide a newer bad one.

`PASS` means these rules passed, `WARN` means a stale/missing/conflicting-data
condition, and `FAIL` means missing station, unusable time, invalid measurement or
failed consistency rule. CLI exit 0 means analysis completed, **not** all stations
passed. Consumers should inspect `station_status_counts` for a quality gate.

Units are explicit: temperature/dewpoint °C, wind/gust knots, altimeter hPa. The
provider's JSON `altim` field uses hPa; the XML format has different fields/units.
Provider `qcField` is retained without attempting to decode its bitmask.

Outputs:

| File | Contents |
|---|---|
| `quality.json` | Latest station results, audited unique observations, missingness and rejected rows |
| `stations.csv` | One row for each requested station, including missing stations |
| `report.html` | Readable summary with units, timestamps and issues |
| `source_snapshot.json` | Original response, saved when using `--live` |

## Reproduce the recorded example

The checked-in `examples/` contains a real public API response from 25 October
2026, not synthetic observations. Use the exact evaluation timestamp recorded in
`examples/provenance.json` to reproduce the original freshness checks:

```bash
python main.py --input examples/source_snapshot.json \
  --as-of "2026-10-25T09:19:19.485320+00:00" \
  --output outputs
```

Alternatively omit `--as-of` to evaluate the old snapshot against the current
clock; it will correctly become stale over time. The live command does not allow
a custom clock. Synthetic malformed/edge-case records appear only in tests.

See `examples/validation.txt` for the exact replay command, successful tests and
live/replay comparison. No training time, prediction accuracy or baseline model
is applicable: this project is a rule-based data-quality audit, not ML/DL.

## Limitations

Broad plausibility checks cannot certify meteorological accuracy. The latest
report can pass while older records have problems; inspect the full observations
and audit counts as needed. Provider quality flags are not fully interpreted.
Five airport stations do not represent entire countries, and weather/report
availability varies. This three-hour query cannot establish long-term uptime,
daily coverage or a permanent station's expected reporting cadence. First-copy
duplicate retention is transparent but is not a sophisticated revision resolver.

The JSON API currently limits most endpoints to 400 entries. Broad queries can
truncate; this prototype intentionally limits stations and lookback but does not
claim complete coverage for every possible 20-station request. There is no
streaming alert service, cloud deployment, safety certification or aviation
decision support. Data-quality PASS does not mean good or safe weather.

## Primary sources and attribution

- [NOAA/NWS Aviation Weather Center API](https://aviationweather.gov/data/api/)
- [Provider OpenAPI specification](https://aviationweather.gov/data/schema/openapi.yaml)
- [NWS data-use and disclaimer policy](https://www.weather.gov/disclaimer)

Source: NOAA/NWS Aviation Weather Center, with international station reports.
The saved response is unaltered source data. Normalised tables, quality labels
and reports are project-derived outputs and are not official government products.
No NOAA/NWS endorsement or affiliation is implied. Review source timestamps,
provider restrictions and any specifically noted third-party conditions.
