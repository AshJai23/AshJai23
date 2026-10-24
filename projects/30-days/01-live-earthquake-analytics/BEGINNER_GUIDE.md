# Hazard Explorer, explained from the beginning

## What data means

Data is information written down so a computer can work with it. A notebook
entry saying “London, 1 January 2025, maximum wind 24 km/h” is one data record.
A collection of those entries is a dataset. A table has rows (individual entries)
and columns (date, place, wind speed and other measurements).

This project turns public datasets into a website-style dashboard. It has three
jobs: show reported earthquakes, show a weather provider's near-term forecast,
and estimate typical monthly wind conditions for a chosen year.

## What has been built

- A country/area selector with 177 mapped regions.
- A year selector for historical exploration and monthly model outlooks.
- Country-filtered earthquake tables and a world map, including zero-result states.
- Local weather coordinates, with a default city or representative point.
- Daily wind, gust, precipitation and provider thunderstorm-code displays.
- A Predict selected year button, monthly chart, baseline comparison and error bands.
- CSV exports, readable source links, data caching and useful input-error messages.
- Saved real examples for London and New Delhi, tests and reproducible code.

The country is the context. Weather is calculated at one selected location inside
it. London cannot represent every part of the UK, and New Delhi cannot represent
all of India. Country-wide weather analysis would need many sampled locations.
The border map is coarse and excludes offshore earthquakes from country filters.

## Where the information comes from

| Source | What it provides | How the app uses it |
|---|---|---|
| USGS | Earthquake event times, magnitudes, locations and depths | Past-day or selected-year records filtered by mapped land borders |
| Open-Meteo historical API | Daily model-based weather reconstructions | The input dataset for the yearly wind model |
| Open-Meteo forecast API | Weather-model forecasts for the coming days | The 7/16-day wind and thunderstorm display |
| Natural Earth | Approximate country/area boundary shapes | The selector, map and country coordinate checks |

An API is an agreed way for one program to request information from another
service. Our Python program asks a public API for data, checks the response,
and sends a smaller, useful result to the browser.

Historical reanalysis is not a thermometer reading from every street. It is a
reconstruction of past weather using observations and weather models on a grid.
It has uncertainty and a limited spatial resolution. Data source links and
attribution are in the project README and saved example files.

## Two different kinds of weather prediction

**The next 7/16 days:** this comes from Open-Meteo and its underlying numerical
weather models. Our app retrieves, organises and displays those forecasts.
We did not train those large weather models.

**The selected calendar year:** this is our own small statistical model. It
estimates each month's average daily maximum wind, average daily maximum gust,
and the fraction of days with gusts above the selected threshold. A month might
be estimated to have 2.4 high-gust days on average; it does not identify which
2 days will have storms.

A gust is a short burst of stronger wind. A high gust does not automatically mean
a thunderstorm. The short-term thunderstorm label uses the provider's WMO weather
codes 95, 96 or 99. The yearly model does not have trustworthy thunderstorm-event
labels, so it uses the clearly named high-gust-day proxy instead. It cannot
predict exact future storm dates, named cyclone tracks or earthquakes.

## What training means

Training means letting a mathematical rule learn patterns from earlier examples.
Our rule is called Ridge regression. Think of it as a restrained line-fitting
method: it learns which months tend to be windy and whether the years show a
small trend, while discouraging unnecessarily large coefficients.

For the saved London and New Delhi runs:

| Step | Actual data used |
|---|---|
| Historical period downloaded | 1 January 2017–31 December 2025: nine years |
| Daily records per location | 3,287 |
| Monthly records after aggregation | 108 |
| Initial training period | 2017–2023: 84 months |
| Unseen test period | 2024–2025: 24 months |
| Final fit for the 2027 outlook | All 108 monthly records from 2017–2025 |

A fair test keeps later data away from the first training step. Otherwise the
computer could effectively see the answers beforehand. The code also excludes
the target year and later years when making a historical-year hindcast.

The final London fit took **0.90 milliseconds** on
this runtime. Preparing the monthly data, testing and fitting together took
**15.55 milliseconds**. The first full London
prediction request took about **5.2 seconds**, mostly downloading data. Those are
measured examples, not promised speeds for every computer or hosting service.

“Nine years of training data” and “one millisecond of model fitting” describe two
different things. A small model with 108 monthly examples is quick to fit; this
is not a large neural network trained on a GPU for hours. No deep learning is
used in this particular project.

## How good is the model?

A baseline is a simple method to compare against. Here it is the average for the
same month in earlier training years. Any complicated model should earn its
place by doing better than that simple comparison.

MAE means mean absolute error: the average size of a wrong estimate, ignoring
whether the guess was too high or too low. Lower is better.

| London test target | Ridge MAE | Seasonal baseline MAE |
|---|---:|---:|
| Monthly average daily maximum wind | 4.57 km/h | 4.48 km/h |
| Monthly average daily maximum gust | 4.34 km/h | 4.40 km/h |

The baseline was slightly better for wind. Ridge was slightly better for gusts.
In New Delhi, wind MAE was 3.39 km/h
for Ridge and 3.08 km/h
for the baseline. There is no evidence here that the model is consistently
superior. We do not report an invented “accuracy percentage.”

These errors are for monthly summaries, not individual storm warnings or exact
daily forecasts. Only two years were held out. The displayed wind error band
uses previous held-out errors; it is not a calibrated 90% probability guarantee.

## Tools used

| Tool | Plain-English role |
|---|---|
| Python | The main programming language; retrieves data and runs the analysis |
| HTML and CSS | The page structure, colours, controls and layout |
| JavaScript and SVG | Buttons, tables, charts, maps and CSV downloads in the browser |
| pandas | Organises daily records into monthly tables and checks dates |
| NumPy | Handles the numerical arrays used by the model |
| scikit-learn | Supplies Ridge regression and the error calculation |
| SQLite and SQL | Store and analyse the original earthquake snapshot pipeline |
| GitHub | Keeps the source code, history, datasets, examples and documentation |
| unittest and Linkedom | Check Python logic, local HTTP routes and browser-DOM interactions |

Power BI and Tableau are **not** used to run this dashboard. Its CSV downloads
can be imported into those tools. Streamlit, TensorFlow, PyTorch, Docker and a
cloud hosting service have not been added to this project. Listing a tool in
my GitHub profile is different from using it in this specific implementation.

## Strengths

- Real, source-attributed data and saved inputs make the results inspectable.
- Country and year options make the project more useful than a single static report.
- The app separates near-term forecasts from annual statistical estimates.
- Cheap, small models run on a normal CPU; no GPU is needed.
- Baselines, time-separated tests and negative results improve credibility.
- Empty data, missing values, invalid locations and stale responses are handled.
- The local app can be extended without rebuilding a large framework project.

## Limitations

- The model is simple and does not consistently beat the baseline.
- It has only 108 monthly examples per location, so rare extreme events are poorly represented.
- A single point does not describe an entire country; mountains and coastal
  locations can have very different weather.
- Gridded reanalysis is approximate and may change source models over time.
- The year-trend model cannot capture all future changes in weather or climate.
- High-gust frequency is not an annual thunderstorm probability or a named-storm forecast.
- Borders are coarse; some small areas and offshore events are omitted.
- Public APIs can be delayed, unavailable or rate-limited. Large historical
  requests consume more than one provider quota unit.
- The Python HTTP server and in-memory cache are for development. There is no
  public hosting, HTTPS, account system, production rate limiting or uptime guarantee.

## Should this become a website?

**Yes, as an educational or portfolio demonstration**, provided the data/API
licence and service terms fit the use. It shows a complete path from public data
to analysis, a tested model and a usable interface. Students and recruiters can
inspect both the results and the reasoning.

It is currently a prototype, not a reliable public warning or commercial weather
prediction service. Before public launch, it needs a production Python backend,
HTTPS hosting, rate limits, persistent caching, monitoring, browser/mobile QA,
and clearer city search and official-alert links. The existing simple model
also needs evaluation across more locations and more time windows.

GitHub stores code. GitHub Pages can host static pages but cannot run this Python
prediction backend. The backend would need a Python-capable hosting service.
No paid account, domain, hosting or public deployment has been created.

Open-Meteo's current free API is restricted to non-commercial use and quotas.
Commercial or promotional uses need a review of the current service terms and
appropriate access. Publicly available data does not mean unlimited free service
for every use. Sources: https://open-meteo.com/en/terms and
https://open-meteo.com/en/pricing .

## Try it

Follow the README to install the three Python dependencies and start
`python dashboard.py --port 8501`. Open `http://127.0.0.1:8501` on the same
computer. Choose a country, adjust the year/location if needed, then click the
button for the analysis you want. The app is local; running it here did not
install or open it on your own computer.

For reproducibility, the project includes real saved UK/India examples, raw
historical weather responses, 24 passing Python tests, DOM interaction tests and
a log of ten successful live-data analyses. Future forecasts and example values
can change; always inspect their timestamps.
