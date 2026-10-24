-- Run against outputs/earthquakes.sqlite after the Python pipeline.
SELECT * FROM magnitude_distribution ORDER BY magnitude_band;

-- Null magnitudes are counted separately instead of silently treated as zero.
SELECT COUNT(*) AS events, COUNT(magnitude) AS measured_magnitudes,
       AVG(magnitude) AS mean_magnitude, MAX(magnitude) AS largest_magnitude
FROM events;

SELECT substr(time_utc, 1, 13) || ':00Z' AS hour_utc, COUNT(*) AS event_count
FROM events GROUP BY hour_utc ORDER BY hour_utc;

SELECT event_id, place, magnitude, depth_km, time_utc
FROM events WHERE magnitude IS NOT NULL ORDER BY magnitude DESC LIMIT 10;
