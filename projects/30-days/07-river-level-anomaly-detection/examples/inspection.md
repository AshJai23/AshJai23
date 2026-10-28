# Inspection of real held-out river innovations

AI-assisted numerical review on 28 October 2026; not independent hydrologist labels.
Selected eight largest held-out scores after fixed evaluation. No tuning followed.

| UTC target (13 October) | Observed m | Prior m | Ridge m | Absolute error mm | Score | Ridge flag | Baseline flag |
|---|---:|---:|---:|---:|---:|---|---|
| 12:30 | 1.598 | 1.589 | 1.589878 | 8.122 | 8.209 | True | True |
| 10:30 | 1.586 | 1.592 | 1.593142 | 7.142 | 7.055 | True | False |
| 11:15 | 1.588 | 1.595 | 1.594837 | 6.837 | 6.751 | True | False |
| 13:15 | 1.586 | 1.589 | 1.591493 | 5.493 | 5.407 | False | False |
| 13:00 | 1.589 | 1.592 | 1.594403 | 5.403 | 5.317 | False | False |
| 10:45 | 1.594 | 1.586 | 1.589134 | 4.866 | 4.953 | False | False |
| 08:45 | 1.587 | 1.590 | 1.591058 | 4.058 | 3.971 | False | False |
| 13:45 | 1.590 | 1.585 | 1.586368 | 3.632 | 3.718 | False | False |

The largest case at 12:30 rises 9 mm relative to its prior observation and is
flagged by both detectors. At 10:30 and 11:15, 6–7 mm drops exceed the Ridge
threshold but not the baseline threshold. Several smaller changes remain below
the calibration thresholds, including the 8 mm rise at 10:45 that both detectors
leave unflagged. Statistical thresholds can therefore rank events differently
from raw changes. These are small fluctuations relative to the station datum.

The source contains no verified sensor-fault labels or matched flood events.
The review cannot establish whether any event is a sensor error, normal water
movement or an external intervention, and cannot validate a flood alert. The
late source timestamp also prevents treating these as current alerts.
