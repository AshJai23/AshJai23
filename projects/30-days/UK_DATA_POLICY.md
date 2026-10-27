# UK sector niches and honest freshness

Revised at the user's request on **27 October 2026**. These are source choices
and build requirements, not claims that the future projects are implemented.
The six completed sprint experiments retain their original results and geography.

| Sector | Practical niche | Primary source | Actual freshness |
|---|---|---|---|
| Retail | Category sales trends and forecasting | [ONS Retail Sales Index](https://www.ons.gov.uk/businessindustryandtrade/retailindustry/datasets/retailsales) | Monthly published GB aggregates; not live purchases, inventory or individual transactions |
| Retail / council | Food-business inspection coverage and data quality | [FSA ratings data](https://ratings.food.gov.uk/open-data), supplied by local authorities | Live API changes as authorities publish; downloadable extracts nightly; inspection itself can be much older |
| Banking | Official overnight interest-rate modelling | [Bank of England database](https://www.bankofengland.co.uk/boeapps/iadb/), preferring SONIA | Published daily business-day observations, not streaming bank-account or card data |
| Technology | Public digital-service publications and engineering triage | [GDS Atom feed](https://www.gov.uk/government/organisations/government-digital-service.atom), public alphagov issue metadata | Poll on demand; publisher dates and issue update times retained; public-sector tech scope, not the whole private UK tech industry |
| Council | Local river/environment reporting and inspection analytics | [EA flood monitoring](https://environment.data.gov.uk/flood-monitoring/doc/reference), FSA council records and existing LAQN observations | EA measurements usually every 15 minutes, but transfers may be once/twice daily; show observation age, not only request time |
| NHS | Service-demand forecasting and BI | [NHS England A&E statistics](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/) | Monthly aggregates, usually published the following month; England only, not a live hospital queue |

The ONS page checked on 27 October lists **23 October 2026** as its release and
**20 November 2026** as its next release. Read the current release metadata on
each build; do not assume that a successful HTTP response means new observations.

## Checked behaviour and limits

The portfolio root and its `#projects` URL returned HTTP 200 on 27 October;
the HTML has a `projects` anchor. This confirms the address/anchor, not a complete
browser or project-app test. The EA station endpoint returned JSON. ONS retail,
Bank Rate and NHS statistics landing pages returned HTML; those checks are not
model-ready data integrations. GDS returned Atom XML.

The FSA `/Authorities` endpoint returned JSON using `x-api-version: 2`; Camden
was authority 93, code 506, with 4,293 establishments and a reported last-published
time of `2026-10-27T00:31:52.193` (provider supplies no timezone on this field).
No establishment sample or new model was built during this documentation change.
Use the authority-provided extract URL, not a guessed council dataset address.

## Reuse and primary documentation

- [ONS terms](https://www.ons.gov.uk/help/terms-conditions): most content OGL,
  exceptions apply. Attribute the exact series and release.
- [FSA API help](https://api.ratings.food.gov.uk/Help): public key-free API;
  version header required. [Best practices](https://api.ratings.food.gov.uk/Help/BestPractices)
  recommend nightly open files for whole-authority refreshes.
  [FSA terms](https://ratings.food.gov.uk/terms-and-conditions) place ratings data
  under OGL; retain the update date, pending/appeal states and scheme differences.
  Do not use logos or portray model outputs as official ratings.
- [Bank of England legal terms](https://www.bankofengland.co.uk/legal): database
  generally reusable under OGL, but some exchange-rate/third-party series are
  excluded. Prefer SONIA and retain its required attribution. Do not apply a
  blanket OGL claim to Bank publications or third-party material.
- [EA reference](https://environment.data.gov.uk/flood-monitoring/doc/reference):
  OGL, no registration. Use its requested source attribution. EA observations
  are national-agency data used for a council niche, not data authored by a council.
- GDS/GOV.UK content generally uses OGL except marked material; GitHub issue text
  is user-generated. Verify each source's actual licence before redistributing
  text; retain minimal metadata and links when necessary.
- [NHS England gateway terms](https://data.england.nhs.uk/terms-conditions) describe
  OGL for gateway content. Verify the exact A&E download's own terms and notes;
  do not substitute NHS website patient-advice terms for statistical data terms.

## Required interface and README wording

Show **geography, source, captured time, observation/inspection date, publication
date, cadence and data mode**. Use one of: near-real-time polling, delayed
observations, periodic published data, historical replay, or labelled synthetic
fixture. Never call all of these real time. A failed live request stays visible;
no fabricated fallback. No credentials, private bank/customer/patient data, paid
services or always-on infrastructure are part of this work.

Each README explains the niche, intended user, useful decision, tools, actual
training sample/time/results if applicable, baseline, limitations, and exact
launch instructions. Distinguish a GitHub source URL from a deployed website,
local app and generated HTML report. No public project app URL has been deployed
by this change. `127.0.0.1` works only on the computer running the server.
