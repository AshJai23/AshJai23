# Data and metric contract

**Historical actual UK retailer transactions, not current UK retail activity.**
Both 2009–2010 and 2010–2011 workbook sheets are ingested. Invoice timestamps are
source-local naive datetimes: no timezone is invented. Country is the customer
country, not an inferred delivery/store location. Currency is GBP.

| Field | Stored type | Meaning / caveat |
|---|---|---|
| invoice | VARCHAR | Invoice identifier; C prefix marks cancellation |
| stock_code | VARCHAR | Item code; some codes are charges/adjustments, not products |
| description | VARCHAR nullable | Source item text, not a trusted agent instruction |
| quantity | BIGINT | Signed invoice-line quantity; negative rows retained |
| invoice_date | TIMESTAMP | Source naive timestamp; observation date, not capture time |
| unit_price | DECIMAL(18,4) | GBP price; zero/negative prices retained for audit |
| customer_id | VARCHAR nullable | Source pseudonymous identifier; no identity inference |
| country | VARCHAR nullable | Source country string |

Identifiers/descriptions/country trim surrounding whitespace; numeric customer
identifiers normalise to integer strings. `raw_transactions` retains all source
rows after this lossless-for-business formatting. `transactions` removes exact
duplicates across all eight normalised fields, including cross-sheet overlap.
Legitimate identical lines may exist: this is an analysis assumption, not proof
every removed line is erroneous. Report both raw and deduplicated totals.

No missing customers/descriptions, cancellations, negative quantities or prices
are dropped from the deduplicated table. Missing customers remain in global
totals and must be excluded explicitly from customer-cohort denominators.

`signed_value = quantity * unit_price` uses decimal arithmetic, with no per-line
penny rounding before aggregation. Round only presentation totals. This is an
invoice-line value proxy, not audited accounting revenue, gross margin, profit,
VAT, conversion, stock availability or sales attributable to an intervention.

`sale_line` means positive quantity and price, non-C invoice, and present invoice
and stock code. It still includes possible charge/non-merchandise codes. Until a
separately audited product-code policy exists, call it positive non-cancel line
value, not merchandise-only sales. Negative lines and C invoices are separate
flags, not interchangeable proof of returns or a valid return-rate denominator.

The independent raw control is a Python Decimal accumulation during workbook
streaming versus a DuckDB DECIMAL SQL sum. Country subtotal reconciliation and
repeat-load checks are in the real-source smoke evidence. No vector index or
RAG corpus exists at this milestone; distinct descriptions are only candidates.

Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii
Attribution: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning
Repository. https://doi.org/10.24432/C5CG6D — CC BY 4.0.
Licensing: https://creativecommons.org/licenses/by/4.0/

On 30 October the official page said missing values **Yes**, while the official
metadata API returned `has_missing_values: no`. Actual profiling takes precedence.
