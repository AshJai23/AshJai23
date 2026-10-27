# Country-wise Hazard Explorer

## Niche, data freshness and how to open

**Niche:** Hazard awareness and local weather exposure.

**Data truth:** Global USGS observations; country/year history and Open-Meteo local provider forecasts. UK can be selected; not UK-only. The annual wind outlook is a statistical estimate, not a year-ahead storm warning.

**Website status:** runnable locally; no public project website has been deployed.
The GitHub address displays source code. An HTML file in GitHub's file viewer is
not a hosted dashboard.

From this project folder, install its documented dependencies, then run:

```bash
python dashboard.py --port 8501
```

Open **http://127.0.0.1:8501** on the **same computer** after the server starts.
If it does not open, check the terminal for errors, confirm the port, and keep
the process running. `127.0.0.1` on a phone refers to the phone, not your laptop.

**Separate repository:** requested; creation is pending. The current folder and
its previous validation evidence remain available. Extraction is not a new
project and does not increase the completed count.

An interactive Python web app for **earthquakes by country**, **local wind and
thunderstorm forecasts**, and a **calendar-year statistical wind outlook**.

[Beginner-friendly explanation](BEGINNER_GUIDE.md) ·
[Measured model results](examples/gbr-outlook-2027.json) ·
[Test evidence](examples/dashboard-validation.txt)

## Start the interactive app

Python 3.10+; no Streamlit installation or production API key is needed for a
permitted non-commercial prototype.

```bash
cd projects/30-days/01-live-earthquake-analytics
python -m venv .venv
# Activate .venv for your operating system, then:
python -m pip install -r requirements.txt
python dashboard.py --port 8501
```

Open **http://127.0.0.1:8501** in a browser on the same computer. The server binds
to the local machine only. This repository is not a deployed public website.

## What the controls do

- **Country / area:** 177 mapped Natural Earth regions. Earthquakes are matched
  to actual polygons, not country-name text or bounding rectangles.
- **Year:** select historical earthquake/weather data or a model outlook.
  Historical data requires a past/current year. Outlooks accept 2000 through
  three years beyond the current year; a past target creates a hindcast using
  only earlier years.
- **Weather point:** a default city/representative point in the chosen country,
  with editable latitude/longitude. Weather is local to this point, not a
  prediction for the whole country.
- **Wind & storm forecast:** get 7 or 16 days of Open-Meteo provider forecasts.
  Wind and gusts are in km/h; precipitation is in mm; dates are UTC.
- **High-gust threshold:** defaults to 60 km/h. This is a configurable analytical
  indicator, not a definition of every storm or an official warning threshold.
- **Predict selected year:** estimate 12 monthly mean daily maximum wind/gust
  values and the frequency of high-gust days. Exact storm dates, named storms
  and earthquake prediction are outside this model's capabilities.
- **CSV download:** export the loaded events, daily weather or monthly outlook.
  Changing a selection clears previous results; late responses are ignored so
  a country's data cannot be mistaken for the newly selected country.

## Sources and model

USGS supplies earthquake observations. Open-Meteo supplies gridded historical
weather reanalysis and numerical weather-model forecasts. Natural Earth supplies
the bundled coarse borders; small islands and offshore events can be missed.

The app's own yearly model is **Ridge regression**, with month indicators and a
regularised linear year trend. This project does not train a deep-learning model.
For the checked London and New Delhi examples it uses **2017–2025**, with **3,287
daily records** aggregated to **108 monthly examples** per location. It first fits
2017–2023 and tests 2024–2025, then refits all nine earlier years for a selected
future-year outlook. Metrics include the seasonal-average baseline, even when it
outperforms Ridge. See the beginner guide for measured errors and runtimes.

Weather is fetched server-side. Short-term responses are cached for five minutes
and historical responses for 24 hours in memory. A restart clears the cache.
Missing/incomplete historical years are not fabricated. Model/error bands are
research indicators, not calibrated probabilities of a storm.

## Validation

```bash
python -m unittest discover -s tests -v
# Optional DOM interaction checks (Node 18+):
cd tests
npm install --ignore-scripts
npm test
# From the project directory, opt-in live checks:
python live_smoke.py
```

The validation evidence contains **24 passing Python tests**, DOM interaction
checks and **10 successful local HTTP analyses** backed by live public API calls
for UK/India examples. Unit tests are offline; live checks require internet.
The saved raw inputs `examples/gbr-history-source.json` and
`examples/ind-history-source.json` reproduce the measured yearly model results.
Saved examples are dated snapshots; the app's forecast button fetches current
data rather than silently using them.

## Website readiness

This is suitable for an educational/portfolio prototype. Before public hosting,
replace Python's development HTTP server with a production service, add HTTPS,
rate limiting, persistent caching, monitoring and accessible/mobile browser QA.
The Python backend needs hosting; GitHub Pages alone cannot run it.
Open-Meteo's free endpoint is restricted to non-commercial use and has quotas;
check current terms and an appropriate plan before monetising or using it
commercially. No paid plan, domain or public deployment has been configured.

Sources: [USGS](https://earthquake.usgs.gov/fdsnws/event/1/),
[Open-Meteo forecasts](https://open-meteo.com/en/docs),
[historical weather](https://open-meteo.com/en/docs/historical-weather-api),
[API terms](https://open-meteo.com/en/terms),
[boundary provenance](data/SOURCES.md).

## Original earthquake command-line pipeline


A small, runnable data engineering and analytics project that pulls the latest
USGS past-day earthquake feed, validates observations, deduplicates revised events,
and generates a SQLite dataset, CSV export, JSON quality report and HTML report.

**Business question:** what activity has been reported, where are the largest
reported events, and how complete is the incoming data?

### Run

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

### Pipeline and data quality

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

### Example evidence

See `examples/summary.json`, `examples/report.html`, `examples/events.csv` and
`examples/validation.txt` for the captured run. Counts and timestamps describe
that snapshot, not permanently current activity. Magnitudes may use different
measurement types; the mean is descriptive, not an energy estimate. Event
locations and magnitudes can be revised, and regional detection coverage varies.

This portfolio prototype does not predict earthquakes or provide safety alerts.

### Source and attribution

- [USGS GeoJSON documentation](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)
- [Live past-day feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson)
- [USGS copyright and credit guidance](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)

Source: U.S. Geological Survey. No USGS endorsement is implied.
