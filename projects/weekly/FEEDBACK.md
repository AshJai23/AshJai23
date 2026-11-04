# User feedback and scope changes

## 29 October 2026 — incorporated

- Replace daily mini-project quotas with one deeper project each week.
- Provide a daily account of actual progress so the user can request changes.
- Choose projects to demonstrate skills relevant to UK hiring.
- Preserve the nine completed prototypes and all existing validation evidence.

## Review choices for W01

The current brief prioritises an analyst/retail hiring story. The user can steer
which KPIs matter most (returns, revenue concentration or retention), the dashboard
style/filters, and the level of ML. Record subsequent feedback here before
changing an affected milestone. No response is required to continue the build.

## 29 October 2026 — AI priority incorporated

User: "give more important to AI, LLM, ML projects use Gen AI, RAG and with large data set"

Replaced the unbuilt analyst-first weekly scopes with two GenAI/RAG systems and
one predictive ML/MLOps service. Kept one project/week, daily feedback, the original
dates and nine completed prototypes. W01 uses the larger Online Retail II source;
W02 has an explicit, unachieved 100k-passage target. No data/model performance is
claimed from replanning. NHS and council analytics remain unscheduled backlog.

## 29 October — deep learning, agents, Hugging Face, Higgsfield and n8n

Incorporated the user's additional stack requests into the existing three weekly builds. Deep learning has an explicit actual-training gate; Hugging Face and local n8n have execution/evidence requirements. Higgsfield is an optional media extension because official API use is metered and the existing no-spend/no-new-credentials constraints remain. No new project dates or completion claims.

## 2 November — runnable local delivery

Recent FastAPI/VS Code assistance concerned the separate SmartInvest project; it does not replace W01, change the weekly schedule or add trading features to this programme. W01 already planned FastAPI. Its new runbook now makes the local-versus-deployed URL distinction explicit, gives exact start/stop commands and keeps unsupported model drafts out of the interface. No public service or operation on the user's own computer is claimed.

## 4 November — actionable retail forecasting priority

User: "predict the future for the retail ... if the sales is low in this week, on which day the sales is weak ... make that day some other ideas". Reframed the W01 main interface around an uploaded recent aggregate daily sales CSV, next-seven-date forecasts, weak-day uncertainty and action hypotheses. Historical public data is retained for reproducible backtests, never presented as the user's current store forecast. A fitted aggregate Ridge method is compared with repeating last week, with calibration-only selection and held-out errors. W03 remains distinct product-week ML/PyTorch/MLOps work; this feature does not count as another completed project. No dates or quotas added.

## 4 November — encoding fix and clearer interface

User reported stray `Â` characters and requested a better CSS/JavaScript interface. Web files are now explicitly decoded as UTF-8 rather than the host default; this addresses the Windows cp1252 mojibake path without deleting valid currency symbols. Reworked the forecast workspace with responsive external CSS, seven-day chart/table, summary cards, uncertainty and action ideas. Added an explicitly fictional 365-day sample and source-labelled CSV export. No current-store data or new model-quality improvement is claimed. Browser preview infrastructure was unavailable; DOM/API checks do not replace graphical or native Windows review.
