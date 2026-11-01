# Batch CSV screening — 0.3.0

Use **Batch CSV review** below the single-offer form. Download the explicitly
synthetic template, replace it with data you are permitted to process, upload it
and select **Screen CSV**. No websites are visited and no firms are verified.

## Input

UTF-8 (optional BOM), at most **2 MiB / 500 logical data rows**. Use unique,
case-sensitive headers from this allowlist:

| Column | Required | Use |
|---|---|---|
| offer_text | At least this or website_url | Message, maximum 10,000 characters |
| website_url | At least this or offer_text | Optional manually supplied URL, maximum 2,048 characters; never fetched |
| claimed_firm | No | Optional claim, maximum 200 characters; not a verified identity |
| sample_id | No | Optional source identifier; deliberately excluded from returned summaries |

CSV quoting and multiline cells are supported. Extra/duplicate headers,
non-UTF-8 bytes, NULs, malformed CSV, oversized files or batches exceeding 500
records reject the whole upload; no partial result is returned. A structurally
valid CSV may contain row-level validation errors (empty offers, inconsistent
column counts or oversized fields). Those rows are marked input_error while
valid records are screened. No row is silently described as a successful scan.

## Review and exports

The dashboard shows rows screened, rows with configured indicators, input errors,
a per-row table and indicator counts across rows. Indicators are not mutually
exclusive, so their counts can sum above the number of records. No probability,
confidence percentage, safety certification or verified-fraud label is assigned.

**Download batch summary (CSV)** contains only generated row numbers, screening
status, not_checked verification status, indicator count/codes and generic input
errors. Raw messages, firms, URLs, supplied sample IDs and matched excerpts are
not returned by batch summaries. This also prevents spreadsheet formulas hidden
in user-supplied IDs/text from reaching the exported CSV. Row numbers refer to
logical data records excluding the header; keep the original input separately
under appropriate controls if you need to reconcile them.

Uploads and reports stay in Streamlit session memory, not a scan database or file
log. **Clear batch report and upload** clears that session's batch controls and
summary. Exports saved by the user are separate files under their control. Do not
upload credentials or private financial information. A local prototype is not a
public-service privacy/security guarantee.

## API

POST `/v1/batch-scans` with JSON:

```json
{"csv_text":"offer_text,website_url\nGuaranteed returns,\nRead the prospectus,\n"}
```

The same byte/row/field rules apply. Response contains summary metadata only;
invalid upload schema returns HTTP 422. API request validation errors omit
submitted values, including values under unknown fields. Raw messages are not
logged by the engine. Production body limits/rate limiting and deployment
hardening remain future work.

## Research boundary

The template and tests are synthetic behaviour fixtures, not a collected or
labelled dataset. Screening outcomes are not ground truth for a scam classifier.
Follow DATA_PROVENANCE.md and EVALUATION_PROTOCOL.md before acquiring real data,
making labels or fitting a model. verification_status remains not_checked.
