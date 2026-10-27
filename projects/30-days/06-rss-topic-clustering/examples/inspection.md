# Cluster inspection — real captured headlines

AI-assisted qualitative inspection of the saved fit; not independent human labels. Publisher facts are not rechecked or summarised here. Group names are model outputs, not publisher classifications.

## Cluster 0: 37 training, 10 held-out

Top terms: ai, new, awards, researchers, releases, national, lasers, help, standards, south

A large mixed group dominated by generic research, AI, funding and release vocabulary. Its representative headlines do not define a single narrow topic. All represented held-out items landed here.

- [Announcing the "AI Agent Standards Initiative" for Interoperable and Secure Innovation](https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure) — nist; 2026-02-17
- [NIST Awards More Than $30 Million for MEP Centers in 11 States and Puerto Rico](https://www.nist.gov/news-events/news/2026/09/nist-awards-more-30-million-mep-centers-11-states-and-puerto-rico) — nist; 2026-09-15
- [NIST Releases New Forensic Genetic Reference Material to Help Crime Laboratories Analyze Challenging Cases](https://www.nist.gov/news-events/news/2026/02/nist-releases-new-forensic-genetic-reference-material-help-crime) — nist; 2026-02-17

## Cluster 1: 2 training, 0 held-out

Top terms: inspected, surveyor, neo surveyor, neo, inspected neo, cells, cells inspected, solar, solar cells, sunshade

The two related NEO Surveyor hardware-inspection headlines form a plausible narrow lexical pair. This tiny training group had no held-out member, so coherence here is not evidence of generalisation.

- [NEO Surveyor’s Sunshade Gets Inspected](https://science.nasa.gov/photojournal/neo-surveyors-sunshade-gets-inspected) — nasa; 2026-10-26
- [Solar Cells Inspected on NASA’s NEO Surveyor](https://science.nasa.gov/photojournal/solar-cells-inspected-on-nasas-neo-surveyor) — nasa; 2026-10-26

## Cluster 2: 3 training, 0 held-out

Top terms: october, outlook, winter outlook, winter, issue, issue winter, outlook october, noctilucent clouds, apod, apod october

Two winter-outlook headlines are grouped with an astronomy image headline through calendar vocabulary such as October. This is a concrete example of a grouping that should not be treated as a coherent semantic topic.

- [NOAA to issue 2026-2027 U.S. Winter Outlook October 15](https://www.noaa.gov/media-advisory/noaa-to-issue-2026-2027-us-winter-outlook-october-15) — noaa; 2026-10-05
- [El Nino looms large over U.S. Winter Outlook](https://www.noaa.gov/news-release/el-nino-looms-large-over-us-winter-outlook) — noaa; 2026-10-14
- [APOD: 2026 October 27 – Noctilucent Clouds over Sweden](https://science.nasa.gov/image-article/apod-2026-october-27-noctilucent-clouds-over-sweden) — nasa; 2026-10-27

## Cluster 3: 6 training, 0 held-out

Top terms: quantum, step, ai, manufacture, manufacture quantum, center drive, unruly molecules, unruly, party, physicists

Quantum-related headlines form a more recognisable training theme, including broad funding/AI language. There were no assigned held-out members for this group.

- [‘Spooky’ Particles Transit DC Suburbs, a Step Toward a Quantum Network](https://www.nist.gov/news-events/news/2026/08/spooky-particles-transit-dc-suburbs-step-toward-quantum-network) — nist; 2026-08-05
- [NIST Allocates Over $3 Million to Small Businesses Advancing AI, Biotechnology, Semiconductors, Quantum and More](https://www.nist.gov/news-events/news/2026/02/nist-allocates-over-3-million-small-businesses-advancing-ai-biotechnology) — nist; 2026-02-10
- [NIST Physicists Bring Unruly Molecules to the Quantum Party](https://www.nist.gov/news-events/news/2025/12/nist-physicists-bring-unruly-molecules-quantum-party) — nist; 2025-12-18

## Held-out and stability findings

K-means distance 0.994561 did not beat the one-centroid baseline 0.993707. These are representation distances, not accuracy percentages. Ten represented held-out headlines went to cluster 0; two were unassigned because every retained token was outside the fitted vocabulary. The held-out silhouette is undefined, and seed sensitivity ARI is 0.09745.

This sample does not support claiming a stable news taxonomy. Do not tune the same held-out set until the score looks good. A later experiment needs independently reserved data and a real relevance/coherence review.
