# 30 days of practical data science, ML and deep learning

**24 October–22 November 2026 · 44 planned projects · 8 completed**

A portfolio sprint built with AI assistance. Each completed item contains runnable
code, a source-attributed data example, validation evidence and an honest account
of limitations. The goal is practical skill development, not inflated commit
counts or claims of production experience.

## Repository layout and UK niches

The user requested a separate repository for each project on **27 October**.
[Repository names and niches](REPOSITORIES.md) / [destination manifest](REPOSITORIES.json) lists the requested names and honest
creation status. **No separate repositories have been created yet:** the current
connector cannot create them. The existing completed-project links below remain
valid. Nine implemented projects (including Student Copilot, outside the 44)
are ready for extraction after repository creation is available.

Future work now covers **UK retail, banking, technology, councils and NHS**;
see the revised [roadmap](ROADMAP.md) and [data policy](UK_DATA_POLICY.md).
Completed Dublin/global projects retain their true scope and results.

A GitHub link opens **code**, not a running website. Project READMEs now explain
their niche and the correct local address or generated report.
[HTTP address-check evidence](link-check.json) is separate from functional tests.

## Schedule

- At least **one project every day**.
- Two projects on days **1, 3 and 5 of each seven-day block**, plus two on days
  **29 and 30**. This gives **10 projects per full week** and **44 over 30 days**.
- The remaining work is scheduled for daily morning builds in Europe/London.
- The plan is a target. API failures, inaccessible dependencies or failed tests
  must be reported; incomplete work is not counted as delivered.

[Full 30-day roadmap](ROADMAP.md) · [Machine-readable plan](plan.json) ·
[Progress tracker](progress.json) · [Build guide](BUILD_GUIDE.md)

## Completed projects

| ID | Project | What ran | Evidence |
|---|---|---|---|
| 01 | [Country-wise hazard explorer](01-live-earthquake-analytics/) | Country/year earthquakes, local wind and storm forecasts, statistical yearly wind outlook | [24 passing tests](01-live-earthquake-analytics/examples/dashboard-validation.txt) |
| 02 | [GB carbon-intensity forecasting](02-carbon-intensity-forecast/) | Real 28-day API snapshot; chronological Ridge vs persistence comparison | [6 passing tests](02-carbon-intensity-forecast/examples/validation.txt) |
| 03 | [Live weather quality monitor](03-weather-quality-monitor/) | 30 real station reports; freshness, missingness, duplicates and consistency checks; 5/5 latest station records passed | [12 passing tests + live/replay evidence](03-weather-quality-monitor/examples/validation.txt) |
| 04 | [Bike availability forecast](04-bike-availability-forecast/) | Real station-history replay; 30-minute Ridge vs persistence; baseline wins on 81 held-out rows | [12 passing tests + exact replay](04-bike-availability-forecast/examples/validation.txt) |
| 05 | [Air-quality spatial analytics](05-air-quality-spatial-analytics/) | LAQN observations, units/coverage checks, matched-hour spatial summaries and GeoJSON; partial source outage exposed | [19 passing tests + live/replay evidence](05-air-quality-spatial-analytics/examples/validation.txt) |
| 06 | [RSS topic clustering](06-rss-topic-clustering/) | 60 real publisher headlines; TF-IDF/K-means, story-held-out baselines, freshness and inspectable topic groups; baseline wins | [22 passing tests + exact replay](06-rss-topic-clustering/examples/validation.txt) |
| 07 | [River-level anomaly detection](07-river-level-anomaly-detection/) | Actual EA historical readings; Ridge + calibrated robust innovations; persistence wins; stale observations and no anomaly labels explicit | [14 tests + live-download/replay evidence](07-river-level-anomaly-detection/examples/validation.txt) |
| 08 | [Carbon intensity BI data model](08-carbon-bi-data-model/) | Separate national/regional fact grains; 146 national + 144 regional rows, 50-slot DST day and SQL/CSV BI exports | [20 tests + live-download/replay evidence](08-carbon-bi-data-model/examples/validation.txt) |

### Day-one measured results

- Earthquake pipeline: **185 events** in the
  captured past-day feed. Inspect the [quality summary](01-live-earthquake-analytics/examples/summary.json)
  for source and event timestamps.
- Carbon model: **1344 actual half-hour intervals**,
  **260 held-out predictions**. Ridge MAE:
  **4.556 gCO2/kWh**;
  persistence MAE: **5.096 gCO2/kWh**.
  See the [full metrics](02-carbon-intensity-forecast/examples/metrics.json).

These are measured results from one saved time window. They do not guarantee
future performance. The carbon experiment is a rolling one-step backtest and
does not simulate historical publication delays.

## Focus areas

Data quality, Python/SQL pipelines, Power BI/Tableau-ready datasets, forecasting,
classification, clustering, neural sequence models, NLP/retrieval, containerised
local serving, monitoring and model evaluation. Planned deep-learning work must
train and evaluate real small neural models against simpler baselines.

## Real-time data policy

Prefer public live or regularly refreshed sources. Each README must say whether
the project polls live data, replays historical observations or uses a static
snapshot. Source outages must not be concealed with fabricated data. Test-only
synthetic fixtures are labelled. No paid services or always-on deployment are
part of this sprint.
