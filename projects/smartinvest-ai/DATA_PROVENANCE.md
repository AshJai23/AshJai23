# Data provenance and access plan

Research checked **1 November 2026**. No FCA dataset was scraped/downloaded, no
register key was created and no model was trained. Current tests contain clearly
labelled synthetic fixtures. They do not establish investment-scam accuracy.

## Sources and permitted use gates

| Source | What it can support | What it cannot establish / access gate |
|---|---|---|
| [FCA Warning List](https://www.fca.org.uk/consumers/warning-list-unauthorised-firms) | Published concerns about named unauthorised/clone entities, with dates and identifiers | Missing from the list does not mean legitimate. Warnings are selected known cases, not a representative fraud/non-fraud training sample. No automated ingestion without verified permission. |
| [Financial Services Register](https://www.fca.org.uk/firms/financial-services-register) | Regulatory status, permissions and identity details through an approved integration | A public name/FRN is not an identity match or endorsement of a specific message/URL. The API requires registration/key; free individual lookups are distinct from bulk extracts and reuse rights. |
| User/partner-contributed investment messages | Potential real message-level evaluation data | Require lawful collection, documented reuse/consent, de-identification and independent annotation. Do not collect credentials, account identifiers or private case details in this app. |
| Published open research datasets | Possible candidate data, subject to individual licences | Check the actual licence, provenance, dates, labels and relevance. Generic spam/phishing corpora are not automatically investment-scam labels. No candidate has been approved here. |

The FCA's [legal terms](https://www.fca.org.uk/legal) restrict automated access
and incorporation into retrieval systems without permission. Its
[reuse guidance](https://www.fca.org.uk/legal/re-use-public-sector-information-regulations)
also sets conditions for reuse; Register extracts may require a licence/fee.
Do not assume Open Government Licence or blanket training/RAG rights merely
because a page can be read publicly. No permission request was sent for the user.
The [Register service page](https://www.fca.org.uk/firms/financial-services-register)
describes API registration and paid extracts; confirm current terms before any
future integration. This prototype therefore keeps `verification_status=not_checked`.

## Required source register before collection

Record publisher, exact source URL, acquisition method, permission/licence text
and version, permitted retention/redistribution/training uses, observation date,
publication date, acquisition date, revision policy and raw-file SHA-256. Keep a
restricted raw layer separate from de-identified derived features. Public demos
must use consented/licensed examples or explicitly synthetic fixtures.

## Label contract

Define the supervised target before labelling: for example, **a promotion needing
review**, not a declaration that an individual/firm committed fraud. Retain the
actual supporting evidence and adjudication date. A firm warning is not itself
a label for every message mentioning that firm. No warning/register match is not
a negative label. Unknown or disputed cases stay unknown and are excluded from
binary training unless the study explicitly evaluates a suitable weak-label or
positive-unlabelled method with its assumptions.

Use independent reviewers with a written rubric, disagreement measurement and
adjudication. Include benign investment disclosures, legitimate offers, scam
warnings/news, negations, quotations, multilingual content and unrelated messages.
Track entity/campaign groups and duplicates to avoid splitting variants of the
same operation across training and testing. A balanced toy corpus alone does not
represent real deployment prevalence.

## Future firm verification design

Only implement after approved access. Preserve timestamps and distinguish exact
entity match, possible match, no match, source unavailable and not checked. Match
contact details and relevant permissions as well as a name/FRN; clone firms can
copy authorised identities. Source errors must not become a clean check. Never
collapse these states into “safe to invest”. The manual guidance is grounded in
the FCA's [clone-firm explanation](https://www.fca.org.uk/consumers/clone-firms-individuals).
