# River-level innovation detection — Kings Mill, Oxford

**Niche:** a council/environment analyst auditing unusual changes in a river feed.
**Geography:** one Environment Agency gauge on the River Cherwell in Oxford,
England, not UK-wide coverage or council-authored flood advice.

**Data mode:** a real EA download captured **28 October 2026, 09:13 UTC**. The
latest returned observation is **13 October, 14:45 UTC**, about **354.5 hours old**.
This is an explicitly **historical replay/backtest**, not a working real-time
warning service. The report displays source age. Built with AI assistance.

## Run and open

Python 3.10+, NumPy and scikit-learn; tested with Python 3.12.14, NumPy 2.3.5
and scikit-learn 1.8.0 on CPU. From this project directory:

```bash
python -m pip install -r requirements.txt
python main.py --input examples/source_snapshot.json --output outputs
python -m unittest discover -s tests -v
# Make two bounded real-source requests, never a synthetic fallback:
python main.py --live --output outputs/latest-download
```

Open `outputs/report.html` from your local file manager. It is a saved HTML
report, not a public website. Rerunning a command refreshes the download; it does
not guarantee newer observations. No server, background polling, account or API
key is installed. Failed requests or insufficient training data raise errors.

## What data and training mean

A row is one measured water height at one time. Here the unit is **metres above
station datum (mASD)**, not sea-level elevation. The exact measure is
`1491TH-level-stage-i-15_min-mASD`; other measures/datum units are not mixed.

The API returned **1,400 actual readings**, from 29 September to 13 October.
Four missing 15-minute slots are left missing. Five-row windows must contain
four genuinely consecutive prior observations and the target; **1,380 complete
windows** survive. Invalid/nonfinite values and future readings are rejected;
conflicting duplicates fail. Negative local-datum heights can be valid.

The model tries to predict the next 15-minute height from earlier levels, their
last change and prior mean. `StandardScaler` and `Ridge(alpha=1)` fit only the
first **828** windows. The next **276** calibrate thresholds; the last **276**
are held out. Both boundaries are chronological; earlier targets are allowed as
later forecast inputs once observed. Historical publication delays are not
simulated. No parameters or thresholds are tuned against the test rows.

An innovation is the observed height minus its prediction. The anomaly score
uses a training residual median/MAD, with a 1 mm scale floor. The flag threshold
is the greater of 3 and the calibration score's 99th percentile. Persistence
(repeat the last level) has its own equally calibrated scoring baseline.
A flag is calculated only after a new reading arrives. A high score means surprising relative to this short training period, not a
confirmed bad sensor reading or dangerous river.

## Actual measured result

| Held-out metric | Trained Ridge | Persistence baseline |
|---|---:|---:|
| MAE | 0.001166 m | **0.000949 m** |
| RMSE | 0.001602 m | **0.001537 m** |
| Flagged observations | 3 / 276 | 1 / 276 |

**The baseline wins.** Ridge's score threshold is 6.5205; the baseline's is
5.3959. Only one flagged observation overlaps. Model fitting takes milliseconds
on this CPU; the exact timed scaler/model fit is saved in `examples/metrics.json`
and excludes downloading. This is a fitted linear ML model, not deep learning.

There are **no verified anomaly labels**, so precision, recall, false-alarm rate
and flood-detection accuracy cannot be honestly reported. The forecast errors
above measure next-observation prediction, not anomaly correctness.

[Inspected real cases](examples/inspection.md) include all three flagged test
observations and five near-threshold cases. This is AI-assisted numerical review,
not independent human/hydrologist validation. No test-case-driven tuning followed.

## Outputs and checks

- `metrics.json`: quality, source age, split boundaries and measured baselines.
- `model.json`: actual fitted coefficients/scaler, robust calibration parameters.
- `scored_observations.csv`: train/calibration/test predictions and flags.
- `inspection.json` and `report.html`: inspectable cases and limitations.
- [Actual validation evidence](examples/validation.txt): 14 tests, real download,
  two replay runs and deterministic checks. Synthetic fixtures are test-only.

Pros: small CPU model, explicit missingness, useful source-age warning, inspectable
scores and reproducible evidence. Cons: one stale gauge, a short/quiet record,
small height changes, inferior model MAE, no independently verified anomalies,
and no demonstrated transfer to other seasons/gauges. An operational website
would need fresh multi-gauge ingestion, domain review, monitoring and calibrated
alerts. This prototype is not ready to provide flood warnings.

## Source and attribution

[EA API reference](https://environment.data.gov.uk/flood-monitoring/doc/reference)
and [station](https://environment.data.gov.uk/flood-monitoring/id/stations/1491TH).
The code requests station metadata and up to 1,500 latest sorted measure readings,
follows HTTP redirects, and records raw-response SHA-256 hashes and request URLs.
The retained snapshot is the actual returned data, not manufactured examples.

Required attribution: **this uses Environment Agency flood and river level data
from the real-time data API (Beta)**. Source data is under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Readings may be measured every 15 minutes yet transferred much less often; the
API has no safety-critical service guarantee. Documentation checked 28 October.
[Official Ridge documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html).
