# Observed London air: spatial analytics with coverage checks

## Niche, data freshness and how to open

**Niche:** London council environmental reporting.

**Data truth:** LAQN measured pollution from London sites; delayed observations, missing coverage and request failures are reported. No current-health or live exposure claim.

**Website status:** runnable locally; no public project website has been deployed.
The GitHub address displays source code. An HTML file in GitHub's file viewer is
not a hosted dashboard.

From this project folder, install its documented dependencies, then run:

```bash
python main.py --live --output outputs
```

Open the generated **`outputs/report.html`** from your local output folder.
It is a saved report; it refreshes only when you run the command again.

**Separate repository:** requested; creation is pending. The current folder and
its previous validation evidence remain available. Extraction is not a new
project and does not increase the completed count.

A data-science prototype that joins monitoring-site coordinates to **measured
hourly NO2 and PM10 concentrations**, checks units and coverage, and creates
matched-hour spatial summaries. It does not forecast pollution, interpolate
unmonitored areas, estimate personal exposure or give health advice.

## Run

Python 3.10+ standard library only. No API key or third-party packages are needed.
From this directory:

```bash
# Replay the saved real source responses:
python main.py --input examples/source_snapshot.json --output outputs
python -m unittest discover -s tests -v
# Query actual provider observations for a completed GMT day:
python main.py --live --date 2026-10-25 --output outputs/live
```

Without `--date`, a live query uses yesterday in UTC. Default site codes are MY1,
BL0, CD1, KC1, GR4, GN0, HG1, TH4. `--sites` accepts up to ten distinct codes;
`--minimum-coverage` defaults to 0.75 (18 valid hours out of 24).

Outputs: `report.html` with station-location plots and a coverage table,
`summary.json`, `stations.csv` and GIS-ready `observations.geojson`. Live runs
also save the actual source snapshot, all request URLs, retrieval time and
station-specific request errors. There are no third-party map tiles or external
browser dependencies. The coordinate plot is schematic, not a pollution surface.

## Source selection and data mode

The initial UK-AIR SOS endpoints returned a maintenance page on **26 October
2026**. They are not represented as a successful live source. The permitted
alternative is the official **London Air Quality Network (LAQN) API**, operated
by the Environmental Research Group at Imperial College London.

The sample was downloaded from the live LAQN API on 26 October for measurements
on **25 October 2026, 00:00–24:00 GMT**, a completed 24-hour interval. It is a
download of delayed observations, not streaming data or current conditions.
Offline replay is explicitly labelled. Recent observations may be provisional
and are not claimed to be finally ratified.

Collection is bounded and serial from the server: one metadata request and at
most ten station CSV requests. No retries, background polling or always-on
deployment. Responses are saved and reused for replay. A failed station remains
missing with its error recorded; at least two real responses are required for
a new capture. Total outage raises an error, never a synthetic substitute.

## What was observed

The saved run requested **8 sites**. Seven station CSVs returned; **HG1 returned
HTTP 400**, which is recorded rather than concealed. All eight metadata rows
passed coordinate/open-station checks.

The received CSVs contained **53 valid NO2/PM10 measurements** and **283 blank
measurement cells** in the requested window. Seven extra end-midnight rows were
excluded because the end is exclusive. Only **two sites met the 75% NO2 coverage
threshold**, sharing **20 observed hours**. No site met the PM10 threshold, so
the report does **not** calculate a PM10 spatial comparison.

The NO2 matched-hour means are in the saved results and shown separately by site
type. A kerbside station and a roadside station are not interchangeable samples
of neighbourhood exposure. These sparse data do not justify a London-wide
ranking, a “cleanest area” claim or a conclusion that missing PM10 means zero
pollution. This coverage shortfall is a finding of the project, not hidden data.

## Method and validation

1. Join by station code. Use decimal `@Latitude` and `@Longitude` fields, check
   finite values, geographic bounds, study bounds and closure date. Do not use
   the differently labelled fields containing projected coordinates as degrees.
2. Read concentrations from the provider's wide CSV. Units come from each
   pollutant header: recognised variants of **ug/m3** only. An unexpected unit
   is rejected and reported, never silently mixed with another unit.
3. Honour `MeasurementDateGMT`; represent observations as UTC. The day of the
   DST change still contains 24 GMT hours. Restrict to the half-open date window.
4. Preserve measured zero. Treat blanks as missing; reject nonfinite/negative
   values. Collapse identical duplicates and quarantine conflicting keys.
5. Report every requested station/pollutant with valid-hour coverage, available
   mean/max and eligibility. Unknown or failed data do not become zeros.
6. Compare qualified stations only on their **intersection of observation
   hours**. Keep unmatched available-hour means separately. An empty
   intersection produces no common-hour mean. Summarise site types separately.
7. Compute nearest eligible monitored neighbours using Haversine distances in
   **kilometres**. Export coordinates in GeoJSON order **[longitude, latitude]**.

Tests cover unit mismatches, absent data, nonfinite/negative values, matched-hour
comparisons, bad/projected coordinates, closure/missing metadata, duplicate
conflicts, end boundaries, UTC/DST, distances, coordinate order, HTML escaping
and explicit total/partial source failure. Fixtures in tests are labelled
synthetic; the published example observations are genuine provider responses.

No ML model is trained in this project: the work is spatial data joining,
quality control and descriptive analysis. There is therefore no training-time
or predictive-accuracy claim. It is distinct from the weather monitor and bike
forecast projects.

## Limitations and attribution

Eight selected monitors are not a representative sample of London residents.
Monitor placement, siting and missingness affect comparisons. Available-hour
means are not full-day means when coverage is incomplete. A 24-hour result is
not an annual-limit compliance assessment. Instrument/calibration errors and
publication delays are not corrected by these screening rules.

This information is obtained from the **Environmental Research Group, Imperial
College London**, using **London Air Quality Network** data and licensed under
the **Open Government Licence v2.0**, as specified by the provider API document.
The plots, quality flags and matched-hour calculations are derived work; no
provider endorsement is implied.

Primary sources:

- [LAQN official API overview](https://www.londonair.org.uk/Londonair/API/)
- [Provider API documentation and OGL terms](https://api.erg.ic.ac.uk/AirQuality/Information/Documentation/pdf)
- [Official endpoint reference](https://api.erg.ic.ac.uk/AirQuality/help)
- [Open Government Licence v2.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/2/)
- [UK-AIR maintenance page observed during source selection](https://uk-air.defra.gov.uk/maintenance/)

Created with AI assistance for the portfolio sprint.
