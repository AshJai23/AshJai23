# Dublin bike availability: a 30-minute historical forecast

## Niche, data freshness and how to open

**Niche:** Bike-share operations and station rebalancing.

**Data truth:** Actual Dublin, Ireland station history. This completed experiment is NOT UK data or a real-time service. Historical replay is retained honestly.

**Website status:** runnable locally; no public project website has been deployed.
The GitHub address displays source code. An HTML file in GitHub's file viewer is
not a hosted dashboard.

From this project folder, install its documented dependencies, then run:

```bash
python main.py --input examples/source_snapshot.csv --output outputs
```

Open the generated **`outputs/report.html`** from your local output folder.
It is a saved report; it refreshes only when you run the command again.

**Separate repository:** requested; creation is pending. The current folder and
its previous validation evidence remain available. Extraction is not a new
project and does not increase the completed count.

A small, runnable ML prototype predicting **bikes available at a station 30
minutes later**. It uses real availability snapshots, not journey counts or
invented demand. The checked-in experiment is explicitly **historical replay**.
No current bike-availability forecast or public service is claimed.

## Run

Python 3.10+. Tested with Python 3.12, NumPy 2.3.5, pandas 2.2.3 and scikit-learn
1.8.0. From this directory:

```bash
python -m pip install -r requirements.txt
python main.py --input examples/source_snapshot.csv --output outputs
python -m unittest discover -s tests -v
```

Open `outputs/report.html`, inspect `outputs/metrics.json` and
`outputs/backtest.csv`. To fetch a fresh copy of the same real historical window:

```bash
python main.py --download --start 2026-10-19 --end 2026-10-24 --input outputs/source_snapshot.csv --output outputs
```

Requests are bounded to 2–7 days and five stations. The download reads the public
CSV stream and retains exact records at minutes 00/30 for IDs 10, 100, 11, 12, 13.
No API key is required. A failed/empty source raises an error; it never generates
replacement values. No background polling or always-on service is installed.

## Data and quality

Source: Dublin City Council / Smart Dublin's Dublinbikes historical station API.
The documented endpoint returns historical station status at five-minute
granularity; its public catalogue also lists monthly archives. The service is
regularly refreshed, but the sample is a historical query, not a live snapshot.
The exact request, retrieval time, retained-source SHA-256 and filtering rule are
in [provenance.json](examples/provenance.json). An API contract excerpt is saved
in `examples/api-contract.json`.

On **26 October 2026**, the real query scanned **101,877 source rows** and retained
**731 exact records** from five stations between 19 October 00:30 and 23 October
23:30, using the provider's timestamp labels. Those records have **452 missing
slots** on complete station-specific half-hour grids. Gaps remain gaps. There
were no rejected values, conflicting keys or duplicate keys in this sample.

Checks reject nonfinite, negative or fractional counts; counts above capacity;
bikes plus available docks above capacity; unknown/nonoperational station flags;
bad timestamps; and observations off the declared half-hour grid. Conflicting
duplicates invalidate the key; identical copies are counted and collapsed.
Windows with inconsistent past capacity are skipped; eligibility never uses a
future capacity change. This is data screening, not proof of
sensor accuracy. Available docks can sum to less than capacity because a dock
may be unavailable.

**Clock limitation:** response timestamps are naive and the contract does not
explicitly state their time zone. The implementation preserves that source
clock and does not falsely mark it UTC. The published window ends before the
25 October DST change. Review source clock semantics before using a window
across a clock change or joining these timestamps to another dataset.

## Model and leakage control

- Target: actual available-bike count, half an hour after the forecast origin.
- Features: observations at origin, origin−30 and origin−60 minutes; their mean
  and recent difference; capacity known at origin; target-hour/weekday cycles;
  station identity. Target calendar time is known at prediction time.
- Fixed `Ridge(alpha=10)` after a training-only scaler and station encoder.
- Last 20% of distinct complete target times are held out **globally across
  stations**, not shuffled. All training labels must be available by the first
  test origin. An unseen station is excluded from this known-station test.
- Evaluation is rolling one-step: earlier actual test observations may become
  later test inputs. It is not a blind multi-day forecast. Source publication
  delays and bike rebalancing operations are not simulated.
- No future backfill or interpolation, hyperparameter search, model selection
  on the test set or external pickle files. Missing lags remove the example.
- Ridge predictions are bounded to 0…capacity known at origin, without rounding.
  The baseline simply repeats the most recent observed count.

## Measured result — the baseline wins

| Measurement | Ridge | Last observation baseline |
|---|---:|---:|
| Mean absolute error, bikes | 1.1633 | **0.7407** |
| Root mean squared error, bikes | 1.5961 | **1.2766** |

**433 training examples, 81 held-out examples**, five stations. Training labels
end at 22 October 21:00; the first test origin is that same time and its target
is 21:30. The last test target is 23 October 22:00. The initial measured fit took
about 0.07 seconds on CPU; timings vary on replay.

The useful finding is that this short-window Ridge model does **not** improve
over persistence. It should not be advertised as a better operational forecast.
The dataset is small, has substantial missingness, covers only five stations and
does not establish seasonal or new-station performance. The next experiment
would need longer, better-covered history and a separately reserved evaluation.

Full errors per station and prediction row are saved, not only aggregate scores.
Tests cover leakage canaries, chronological availability, missing slots, invalid
counts/flags, conflicting duplicates, capacity changes, bounded predictions,
training-only scaling and explicit source failure. Test fixtures are synthetic
and never presented as the real training data.

## Primary sources, attribution and licence

- [Dublin City Council / Smart Dublin dataset catalogue](https://data.smartdublin.ie/dataset/dublinbikes-api)
- [Official historical API resource](https://data.smartdublin.ie/dataset/dublinbikes-api/resource/6b2e97bd-3221-40a0-bb76-54c473a91b11)
- [Official machine-readable OpenAPI contract](https://data.smartdublin.ie/dublinbikes-api/bikes/openapi.json)
- [scikit-learn Ridge documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html)
- [scikit-learn OneHotEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html)

Contains Dublin City Council / Smart Dublin Dublinbikes data, used with
attribution under the catalogue's **Creative Commons Attribution (`cc-by`)**
licence. The catalogue does not identify a version; no version is inferred.
Filtering, model outputs and reports are derived work; no provider endorsement.
Created with AI assistance for the portfolio sprint.
