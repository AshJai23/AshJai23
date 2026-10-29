# Weekly build and reporting guide

This is the active programme from 29 October 2026. It supersedes the daily
44-project / ten-per-week targets. Read plan.json, progress.json, FEEDBACK.md,
the latest log, applicable repository instructions and the current branch head.
Use Europe/London dates. Never resume the old daily queue automatically.

## Execution

- Work on one active flagship and the current meaningful milestone. Start W01
  on 30 October; today is the researched plan/scoping checkpoint. Each daily run
  must actually advance code/data/evaluation/docs where feasible, not just remind
  the user. Publish useful tested increments without calling them finished projects.
- Read current conversation feedback and record incorporated changes. Do not
  wait for optional aesthetic feedback; continue independent engineering tasks.
- Verify exact public data/API/licence behaviour when built. Historical UK
  transactions, delayed NHS aggregates and current published documents are
  different modes. Show observation/release/capture dates. No fabricated data
  replacing a failed source, private patient/customer/bank records or invented ROI.
- Focus on clear business questions, SQL, robust data quality, reproducibility,
  useful interfaces and concise stakeholder recommendations. Use ML/DL only when
  useful. Actually fit models if included, with training-only preprocessing,
  chronological/group holdouts, simple baselines and honest measured errors.
- Include source attribution, data dictionary, exact setup/run commands, useful
  outputs, meaningful tests, real-source or labelled replay smoke tests and
  limitations. For APIs include input validation, errors, metrics and a runbook.
- Prefer free local tools. No spend, always-on paid deployment, new credentials,
  external messages or secret exposure. Power BI/Docker/cloud execution may be
  unavailable: provide portable working alternatives and clearly label untested
  templates; never call a workbook/container/deployment complete if not run.

## GitHub and website

Use normal Git history on the latest default branch with an expected-head lease.
Reject conflicts, refresh and merge carefully; never force-overwrite manual work.
Write under projects/weekly/<project-path>/ in AshJai23/AshJai23 while standalone
repository creation remains unavailable. The separate-repository preference is
preserved, but an uncreated repository is not a published destination. Keep
previous projects, photo/banner, legacy evidence and unrelated content intact.
Only edit the marker-delimited data-science-sprint block in root README.md.

Update progress and a dated log after each meaningful increment. A project is
complete only after its acceptance criteria, actual tests/replay, publication
and readback pass. Include actual commit links and failures. If a week overruns,
report and continue the active work; do not inflate counts or silently compress
later projects. On weekly release, update the portfolio with truthful results
when the website workflow is available; do not claim it updated without readback.
No new project dates after 22 November unless the user explicitly extends them.

## Daily update format

Use plain language: Done / Evidence / Blockers / Next / Change options. Include
measured findings where available and clear progress. Keep a cumulative weekly
view in progress.json, but do not re-list all old projects every day. Do not claim
hours of work or activity outside observed execution. End with reviewable choices
that the user may steer, without making optional feedback a permission gate.

On 20–22 November prioritise fixes, demo reproducibility, business case studies,
CV bullets and interview explanations. Do not invent performance improvements or
commercial outcomes. After the final 22 November report, disable the current
automation. Do not create another automation during an automated run.
