# W01 — UK Retail Commercial Analytics

**Status: scoped, not implemented or completed.** Build window: 30 October–5 November.
Audience: a retail commercial/operations analyst and a UK analytics hiring manager.

## Decision and scope

Build a reproducible decision-support project answering: where are sales value,
returns and customer concentration changing, which product/cohort patterns merit
investigation, and can every dashboard number be reconciled to source records?

Use actual historical UK retailer transactions from UCI (2010–2011) for the
transaction analysis. Treat current ONS retail releases as a separate macro
context panel, not as new transactions from that retailer or evidence of causality.
No live store feed, profit/cost dataset, stock quantity or measured business uplift
has been supplied. Do not fabricate these fields or call historical data real-time.

## Work to deliver

1. Download from the official source, record licence/checksum/capture date, profile
   actual rows, missing IDs, cancellations, duplicate-looking rows and non-merchandise
   entries. Do not assume the catalogue's missingness description matches raw rows.
2. Build an idempotent SQL model with ingestion row identity and audit tables.
   Do not discard repeated invoice/product lines without a justified business rule.
3. Define gross item value, cancellation/return value, net item value, order count,
   average order value, revenue concentration and cohort retention precisely.
   Avoid calling net item value recognised accounting revenue without justification.
4. Build a working dashboard with date/product/country filters, source coverage,
   KPI definitions and explanatory notes. Export a Power BI-compatible semantic
   model and measures; actual Power BI workbook validation is a separate claim.
5. Write meaningful quality/reconciliation/reload tests and verify the actual UI
   or portable report. Add CI where practical, exact commands and a reproducible
   data-download route; do not commit large raw files/caches.
6. Publish a concise business case study: three supported findings, what decision
   each informs, what is uncertain, and what data would be needed to measure impact.
7. Package the runnable demo, tested source, schema/architecture, data dictionary,
   measured validation and truthful CV/interview bullet suggestions for weekly review.

Avoid unnecessary deep learning. A forecast/segmentation extension is optional
only after the core analysis is sound, and must have leakage-safe evaluation and
a baseline. Clear SQL, reconciled business metrics and recommendations come first.

Primary sources checked during scoping:
- https://archive.ics.uci.edu/dataset/352/online+retail
- https://www.ons.gov.uk/businessindustryandtrade/retailindustry/datasets/retailsales

No raw data ingestion, fitted model, dashboard or new project result is claimed yet.
