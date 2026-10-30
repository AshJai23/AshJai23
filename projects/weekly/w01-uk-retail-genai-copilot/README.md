# UK Retail GenAI Analytics Copilot — W01

**In progress. Published milestone: real-data warehouse, quality audit and
deterministic read-only SQL baseline. The LLM/RAG/agent/UI/n8n integration is not
implemented yet.** Target weekly release: 5 November 2026.

The intended user is a retail analyst/manager who wants evidence-backed answers
to plain-English commercial questions. Numerical answers will use constrained
SQL, with RAG for source/schema context and a local LLM for explanations. This
first increment establishes trustworthy numbers before adding generation.

## Actually run on 30 October

| Measure | Observed result |
|---|---|
| Real source rows | 1,067,371 across both workbook sheets |
| Rows after exact normalised-field deduplication | 1,033,036 |
| Duplicate rows removed | 34,335; policy assumption, not proof each is erroneous |
| Missing customer IDs after deduplication | 235,151; retained in overall totals |
| Missing descriptions after deduplication | 4,275 |
| Countries / distinct stock codes | 43 / 5,304; codes include adjustments/charges |
| Distinct nonempty descriptions | 5,655 candidates, **zero indexed RAG documents** |
| Observation dates | 1 December 2009–9 December 2011 |
| Ingest + profile time | 57.093 s on recorded Linux/Python CPU environment |
| Peak process RSS | 379.39 MiB; includes workbook stream and database work |
| Parquet output | 12,758,252 bytes, local only |

Eight unit tests pass, including explicit synthetic edge cases for duplicates,
returns, missingness, schema drift, invalid numeric/date inputs, both-sheet
ingestion, repeat loading and SQL-injection-as-data. A separate **real full-source
smoke/reload** checks catalogue row count, independent Python Decimal versus SQL
sum, country subtotal reconciliation and Parquet row count. See actual results in
[evidence](evidence/) and [validation JSON](evidence/real-source-validation.json).
GitHub Actions has not been added/run yet.

## Exact local commands

From this project directory, Python 3.12 was exercised:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python retail.py fetch
python retail.py build
python validate_source.py
python metrics.py --metric signed_value --country 'United Kingdom'
```

`fetch` makes one public UCI download (~45.6 MB archive), verifies ZIP integrity,
saves capture time/checksum/HTTP status and refuses to overwrite an existing
capture silently. `build` streams both Excel sheets, validates schema/types,
stages CSV, replaces the local raw/deduplicated DuckDB tables and exports Parquet.
It does not append duplicate data on reruns. Source failures raise errors; no
fabricated fallback exists. Installation needs network access, disk and permission
to create a local venv. Output data/models are ignored by Git. Budget roughly
300 MB for current raw/staging/database files plus dependencies; future models
will require more. No cloud service or account is needed for this milestone.

`metrics.py` only exposes four fixed aggregate expressions and a parameterised
country filter through a read-only database connection. It accepts no free SQL.
This is a deterministic baseline, not an AI agent. See
[sample query output](evidence/sample-query.json). Missing/unknown country
returns zero line count and null sums; the later UI must explain that distinction.

## Understand the data

A row is one line of an old invoice, such as a quantity of an item at a price.
Many rows together let us calculate totals. Some rows repeat or cancel earlier
transactions. Missing customer IDs prevent reliable customer-level analysis for
those rows, but they need not disappear from overall totals. The audit makes
these limitations visible so later AI answers can cite the correct population.

These are **actual historical UK-retailer transactions**, not real-time UK sales.
Customer countries include places outside the UK. The source was captured on
30 October 2026; capture date does not make the observations current. There are
no private/live merchant credentials. ONS monthly context is not ingested yet.

Source and attribution: Chen, D. (2012). **Online Retail II** [Dataset]. UCI Machine
Learning Repository. https://doi.org/10.24432/C5CG6D.
[Official source](https://archive.ics.uci.edu/dataset/502/online+retail+ii),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The original archive and public pseudonymous customer IDs are not redistributed
in this repository. [Manifest](evidence/source_manifest.json) contains the exact
download URL and SHA-256 so the same capture can be verified.

## Limits and remaining work

- Read [data/metric definitions](DATA_CONTRACT.md) before calling a value revenue.
  Positive non-cancel line value can include charges; no cost/profit or inventory
  data exists. Deduplication may remove genuinely repeated identical lines.
- Eight passing tests do not establish production safety. Read-only SQL is only
  the first tool boundary; agent budgets, prompt-injection and interface security
  remain to be built/tested. Query timing here is not LLM latency.
- No LLM inference/training, embeddings/index, LangGraph, Hugging Face integration,
  n8n runtime, public website, Docker run or production users are claimed.
- [40-task evaluation contract](EVALUATION.md) is frozen before implementation,
  with deterministic numerical oracle outputs and retrieval/decline rubrics.
  It is AI-authored and not independent human validation. No agent score yet.
- Next: refine non-merchandise code policy, separate development cases, verify a
  free ungated local model/revision/licence and implement the bounded tool/RAG
  workflow. Preserve all negative findings and evaluate before weekly release.

This foundation demonstrates Python streaming, SQL, decimal reconciliation,
quality contracts and reproducibility. It is useful portfolio evidence, but not
yet a launch-ready GenAI product.
