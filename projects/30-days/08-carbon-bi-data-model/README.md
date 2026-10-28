# GB carbon intensity: an auditable BI data model

**Niche:** council sustainability reporting and energy-data quality, with SQL
facts/dimensions and Power BI/Tableau-ready exports. **Geography:** Great Britain
national data plus North Scotland, South Wales and London DNO regions. DNO regions
are not council boundaries; Northern Ireland is not covered.

**Data mode:** actual API responses captured **28 October 2026, 09:11 UTC**.
National history covers the three London dates **25–27 October**; regional
provider forecasts cover **27 October**. It is an on-demand download of delayed
published estimates/forecasts, followed by saved-source replay. No continuously
running website or live council footprint is claimed. Built with AI assistance.

## Run and open

Python 3.10+ with standard-library SQLite and a timezone database. Tested on
Python 3.12.14; Windows can install the first-party `tzdata` dependency listed
below. From this project directory:

```bash
python -m pip install -r requirements.txt
python main.py --input examples/source_snapshot.json --output outputs
python -m unittest discover -s tests -v
# Download the latest three completed London dates, ending at London midnight:
python main.py --live --output outputs/live
# Re-download the exact checked-in historical window:
python main.py --live --end 2026-10-28T00:00Z --output outputs/history
```

Open `outputs/report.html` locally. It is a saved report, not a hosted app.
The command creates `carbon.sqlite`, `warehouse.sql`, four base-table CSV files,
a daily SQL-view CSV and `summary.json`. No account, key or paid BI service is
needed to generate the exports. No background refresh has been installed.

## What was built

A data row represents either one national half-hour or one region's forecast for
that half-hour. Keeping them in **separate fact tables** prevents repeating
national values when several regions are selected. Time and region dimensions
supply stable keys and labels. SQL foreign keys, unique fact keys and value
constraints are enforced. Exact duplicates collapse; conflicting duplicates fail.

The time dimension scaffolds every requested interval, including missing facts.
UTC keys stay unique through the repeated London hour. Offset, fold, settlement
period and expected full-day slots are explicit. Missing actual estimates remain
NULL; valid zero values remain zero. Forecasts are never used to fill actuals.

This project is distinct from project 02: it builds a relational warehouse,
calendar, two fact grains, BI measures and import instructions. **No model was
trained here.** Regional forecasts are the provider's, and national 'actual' is
NESO's estimate based on metered generation.

## Actual outputs

- **146/146 national half-hours**; all have an actual estimate and forecast.
- **144/144 regional rows**, 48 for each selected region; no regional actuals.
- **25 October:** 50 half-hours, mean national estimate **72.36 gCO2/kWh**.
- **26 October:** 48 half-hours, mean **81.125 gCO2/kWh**.
- **27 October:** 48 half-hours, mean **80.542 gCO2/kWh**.
- Two API boundary rows preceding the requested windows were excluded.
- No missing requested intervals or conflicting duplicates in this capture.

The 25 October clock change is correctly counted as a 25-hour day. The final
national interval ended at 28 October 00:00 UTC, about 9.2 hours before capture.
Regional North Scotland's returned forecast was zero in this window; it is kept
as a provider value, not converted to missing or validated as physical truth.

[BI import and measure guide](BI_GUIDE.md) explains the relationships and
aggregation rules. [DAX templates](measures.dax) and [SQL example queries](queries.sql)
are included. The SQL/CSV outputs were executed and checked; Power BI Desktop,
Tableau and the DAX templates were **not** run here, and no workbook is claimed.

## Validation and limitations

[Evidence](examples/validation.txt): 20 tests cover 46/48/50-slot days, repeated
local times, missing versus zero, duplicate conflicts, future-window rejection,
fact grain, SQL constraints and dump restoration. Real download and two exact
saved-source replays passed. Test fixtures are explicitly synthetic.

Pros: reproducible, free, laptop-sized, clear source provenance and BI-ready
keys; no fabricated consumption. Cons: only three regional examples and three
national days; no live scheduling, meter loads, council inventory or official
carbon-accounting certification. Intensity is a rate: **do not sum it as tonnes**.
Time means are not demand-weighted means. Published-history forecast discrepancy
is not a forecast-vintage backtest. Provider history can be revised.

Useful as a reporting prototype. A public website would need ingestion/error
monitoring, freshness displays, tested hosting and a larger coverage window.
None of that is represented as deployed by this project.

## Sources and reuse

Data: [NESO Carbon Intensity API](https://api.carbonintensity.org.uk/),
[primary API definitions](https://carbon-intensity.github.io/api-definitions/),
[provider methodology overview](https://carbonintensity.org.uk/).
Attribution: **National Energy System Operator (NESO), Carbon Intensity API**;
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
This project filters three DNO regions and transforms responses into SQL/CSV;
it is not endorsed by NESO. Request URLs, capture time and original-response
hashes are retained. Regional generation-mix fields and other regions are omitted
from the saved subset, never replaced by invented values. Documentation checked
28 October 2026; provider forecasts update every 30 minutes, not every request.
