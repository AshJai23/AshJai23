"""Calendar-year statistical wind outlook, never a dated storm forecast."""
import calendar
from datetime import date
import math
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

TARGETS = ["mean_daily_max_wind_kmh", "mean_daily_max_gust_kmh", "high_gust_day_fraction"]


def design(years, months, origin):
    years = np.asarray(years, dtype=float)
    months = np.asarray(months, dtype=int)
    one_hot = np.eye(12)[months - 1]
    return np.column_stack([(years - origin) / 10.0, one_hot])


def monthly_table(rows, threshold):
    data = pd.DataFrame(rows)
    if data.empty:
        raise ValueError("No historical weather data to fit")
    data["date"] = pd.to_datetime(data["date"], utc=True)
    data = data.drop_duplicates("date", keep="last").sort_values("date")
    data = data.dropna(subset=["wind_speed_10m_max", "wind_gusts_10m_max"])
    data["year"] = data["date"].dt.year
    data["month"] = data["date"].dt.month
    data["high_gust"] = (data["wind_gusts_10m_max"] >= threshold).astype(float)
    table = data.groupby(["year", "month"]).agg(
        mean_daily_max_wind_kmh=("wind_speed_10m_max", "mean"),
        mean_daily_max_gust_kmh=("wind_gusts_10m_max", "mean"),
        high_gust_day_fraction=("high_gust", "mean"),
        available_days=("date", "size")).reset_index()
    complete = [count >= math.ceil(calendar.monthrange(int(year), int(month))[1] * .9)
                for year, month, count in table[["year", "month", "available_days"]].itertuples(index=False, name=None)]
    return table.loc[complete].copy()


def predict_year(rows, target_year, threshold=60.0, today=None):
    analysis_started = perf_counter()
    today = today or date.today()
    target_year = int(target_year)
    if not 2000 <= target_year <= today.year + 3:
        raise ValueError("Choose a target year from 2000 through three years ahead")
    training_end = min(target_year - 1, today.year - 1)
    table = monthly_table(rows, threshold)
    table = table[(table["year"] <= training_end) & (table["year"] >= training_end - 8)].copy()
    valid_years = sorted(int(y) for y, group in table.groupby("year") if len(group) == 12)
    if len(valid_years) < 6:
        raise ValueError("Year prediction needs at least six complete historical years; missing months are not invented")
    table = table[table["year"].isin(valid_years)]
    holdout_years = valid_years[-2:]
    train = table[table["year"] < holdout_years[0]]
    test = table[table["year"].isin(holdout_years)]
    origin = int(train["year"].min())
    fit_started = perf_counter()
    model = Ridge(alpha=1.0).fit(design(train["year"], train["month"], origin), train[TARGETS])
    backtest_fit_seconds = perf_counter() - fit_started
    held_prediction = model.predict(design(test["year"], test["month"], origin))
    held_prediction[:, :2] = np.maximum(0, held_prediction[:, :2])
    held_prediction[:, 2] = np.clip(held_prediction[:, 2], 0, 1)
    climatology = train.groupby("month")[TARGETS].mean()
    baseline = climatology.loc[test["month"]].to_numpy()
    metrics = {target: {"ridge_mae": float(mean_absolute_error(test[target], held_prediction[:, i])),
                        "seasonal_baseline_mae": float(mean_absolute_error(test[target], baseline[:, i])),
                        "unit": "fraction of days" if i == 2 else "km/h"}
               for i, target in enumerate(TARGETS)}
    residuals = np.abs(test[TARGETS].to_numpy() - held_prediction)
    error_band = np.quantile(residuals, .9, axis=0)
    # Refit only after held-out results have been measured. Target-year values never enter training.
    fit_started = perf_counter()
    final = Ridge(alpha=1.0).fit(design(table["year"], table["month"], origin), table[TARGETS])
    final_fit_seconds = perf_counter() - fit_started
    means = final.predict(design([target_year] * 12, range(1, 13), origin))
    means[:, :2] = np.maximum(0, means[:, :2])
    means[:, 2] = np.clip(means[:, 2], 0, 1)
    predictions = []
    for month in range(1, 13):
        i = month - 1
        predictions.append({"month": month, "month_name": calendar.month_abbr[month],
            "mean_daily_max_wind_kmh": float(means[i, 0]),
            "mean_daily_max_gust_kmh": float(means[i, 1]),
            "high_gust_day_fraction": float(means[i, 2]),
            "expected_high_gust_days": float(means[i, 2] * calendar.monthrange(target_year, month)[1]),
            "wind_error_band_low": float(max(0, means[i, 0] - error_band[0])),
            "wind_error_band_high": float(means[i, 0] + error_band[0])})
    return {"mode": "statistical_year_outlook", "target_year": target_year,
            "training_years": valid_years, "training_end_year": training_end,
            "training_daily_rows": int(table["available_days"].sum()),
            "training_monthly_rows": len(table), "backtest_training_months": len(train),
            "timing": {"backtest_fit_seconds": backtest_fit_seconds,
                       "final_fit_seconds": final_fit_seconds,
                       "total_analysis_seconds": perf_counter() - analysis_started},
            "holdout_years": holdout_years, "holdout_months": len(test), "metrics": metrics,
            "gust_threshold_kmh": threshold, "months": predictions,
            "interpretation": "Monthly seasonal estimates from historical reanalysis and a regularised year trend; not exact storm dates or a country-wide weather forecast.",
            "band_note": "Wind bands use the held-out 90th percentile absolute error from 24 months. They are empirical error bands, not calibrated forecast probabilities.",
            "storm_note": "High-gust-day frequency is a threshold proxy. Historical weather codes do not provide reliable thunderstorm labels; no annual thunderstorm probability is fitted."}
