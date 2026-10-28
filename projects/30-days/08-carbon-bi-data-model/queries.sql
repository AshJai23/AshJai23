-- Executed against the generated SQLite warehouse. Never join both facts first.
SELECT * FROM v_national_daily ORDER BY local_date;
SELECT r.region_name, COUNT(f.forecast_g) AS available_half_hours,
 AVG(f.forecast_g) AS time_mean_provider_forecast_gco2_per_kwh
FROM dim_region r LEFT JOIN fact_regional_forecast f USING(region_id)
GROUP BY r.region_id,r.region_name ORDER BY r.region_id;
-- All local days, including completely missing national observation days.
SELECT t.local_date, COUNT(n.actual_g) AS valid_actuals,
 MAX(t.expected_local_day_slots) AS expected_full_day,
 COUNT(n.actual_g)*1.0/MAX(t.expected_local_day_slots) AS full_day_coverage
FROM dim_time t LEFT JOIN fact_national n USING(utc_start) GROUP BY t.local_date;
PRAGMA foreign_key_check;
