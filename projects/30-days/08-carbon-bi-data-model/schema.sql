PRAGMA foreign_keys=ON;
CREATE TABLE dim_time (
 utc_start TEXT PRIMARY KEY, utc_end TEXT NOT NULL,
 local_date TEXT NOT NULL, local_start_with_offset TEXT NOT NULL,
 local_fold INTEGER NOT NULL CHECK(local_fold IN (0,1)),
 settlement_period INTEGER NOT NULL CHECK(settlement_period BETWEEN 1 AND 50),
 duration_minutes INTEGER NOT NULL CHECK(duration_minutes=30),
 expected_local_day_slots INTEGER NOT NULL CHECK(expected_local_day_slots IN (46,48,50))
);
CREATE TABLE dim_region(region_id INTEGER PRIMARY KEY,region_name TEXT NOT NULL);
-- Grain: one GB national half-hour. NULL means unavailable; zero is a value.
CREATE TABLE fact_national(
 utc_start TEXT PRIMARY KEY REFERENCES dim_time(utc_start),
 actual_g REAL CHECK(actual_g>=0),forecast_g REAL CHECK(forecast_g>=0)
);
-- Grain: one selected DNO region per half-hour; provider forecast only.
CREATE TABLE fact_regional_forecast(
 utc_start TEXT NOT NULL REFERENCES dim_time(utc_start),
 region_id INTEGER NOT NULL REFERENCES dim_region(region_id),
 forecast_g REAL CHECK(forecast_g>=0),PRIMARY KEY(utc_start,region_id)
);
CREATE VIEW v_national_daily AS
SELECT t.local_date,COUNT(n.utc_start) AS rows,COUNT(n.actual_g) AS actual_count,
 AVG(n.actual_g) AS mean_actual_g,AVG(n.forecast_g) AS mean_forecast_g,
 AVG(CASE WHEN n.actual_g IS NOT NULL AND n.forecast_g IS NOT NULL
     THEN ABS(n.actual_g-n.forecast_g) END) AS paired_mae_g
FROM dim_time t LEFT JOIN fact_national n USING(utc_start) GROUP BY t.local_date;
