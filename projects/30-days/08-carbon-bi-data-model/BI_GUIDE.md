# Import into Power BI or Tableau

These CSV tables and the SQL warehouse are tested outputs. No `.pbix`/Tableau
workbook was built or opened; the DAX and Tableau expressions below are import
templates, not claims of application-level validation.

## Business model and grain

For a council sustainability analyst: inspect published GB electricity intensity
and compare selected DNO-region provider forecasts. A DNO region is not a council
boundary. No council consumption or emissions inventory is included.

| Table | Grain/key | Purpose |
|---|---|---|
| dim_time | one UTC start, including missing fact intervals | UTC join key, offset-preserving London display, DST fold, settlement period, full local-day expected slots |
| dim_region | one selected region_id | North Scotland, South Wales and London; deliberately no overlapping countries |
| fact_national | one GB UTC half-hour | actual estimate and provider forecast, both gCO2/kWh |
| fact_regional_forecast | UTC half-hour + region_id | provider forecast only; never labelled actual |
| v_national_daily | London date | executed SQL mean, counts and paired error; missing values excluded |

In Power BI: Get Data → Text/CSV, import the four base tables. Keep `utc_start`
as text in every table to preserve the exact matching key; `local_start_with_offset`
is a display label, not a unique timestamp. Use `local_date` as a date and
`settlement_period` as an integer. Import blank numeric CSV fields as null, not
zero. Disable automatic relationships that connect the two fact tables.

Create single-direction relationships:

- dim_time[utc_start] → fact_national[utc_start] (one-to-many; the national fact happens to have unique keys in this sample).
- dim_time[utc_start] → fact_regional_forecast[utc_start] (one-to-many).
- dim_region[region_id] → fact_regional_forecast[region_id] (one-to-many).

Use dimension fields for slicers. Do not physically join both fact tables on
UTC start: doing so repeats national rows for every region. National measures
must not appear to respond to a regional slicer. Load `measures.dax` one measure
at a time. It explicitly requires one region for the regional mean.

Tableau: relate the tables logically using the same keys. In a national sheet
use `AVG(actual_g)` and `COUNT(actual_g)`; null is excluded and zero is counted.
For paired absolute error use `IF NOT ISNULL([actual_g]) AND NOT
ISNULL([forecast_g]) THEN ABS([actual_g]-[forecast_g]) END`, then average that
expression. A regional sheet must select one `region_id`; never sum intensities
across regions. For day coverage use `actual_count / expected_local_slots` from
summary.json or calculate one expected-slot value per date before summing.

## Measures and interpretation

National mean = sum of available actual estimates / count of available estimates.
All intervals are 30 minutes so this is a time mean. Null actuals remain missing;
a zero intensity is valid. Paired mean absolute error uses only intervals with
both values; it is a descriptive discrepancy in the downloaded API history,
not an as-issued forecast-skill backtest because no forecast-vintage archive is
available. Regional actuals are not inferred from forecasts.

Coverage = non-null national observations / full London-day expected slots.
The repeated hour on 25 October 2026 gives 50 slots; 26 and 27 October have 48.
Partial-day requests remain partial. A complete requested UTC scaffold prevents
missing intervals disappearing from the time axis. A within-day time slicer
makes full-day coverage intentionally partial.

Do not sum gCO2/kWh as if it were tonnes. Actual electricity consumption would be
needed for emissions, with unit conversion and an appropriate accounting method.
The provider's national 'actual' is itself an estimate based on metered generation;
it is not a measured council footprint or a billing-grade carbon accounting value.

Useful first report: date/period coverage, national estimate/forecast line, and a
separate single-region forecast panel. Always show capture time and window end.
Refresh by rerunning the CLI and importing the regenerated files; no scheduled
refresh or public service has been installed.

Primary references checked 28 October 2026:
[Microsoft star-schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema),
[DAX AVERAGE/null handling](https://learn.microsoft.com/en-us/dax/average-function-dax),
[SQLite foreign keys](https://www.sqlite.org/foreignkeys.html),
[Python zoneinfo/fold](https://docs.python.org/3/library/zoneinfo.html).
