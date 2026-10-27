# RSS topic clustering: inspectable groups, measured limitations

## Niche, data freshness and how to open

**Niche:** Science and technology headline organisation.

**Data truth:** NASA, NOAA and NIST public headline metadata. Live fetch obtains published feed entries; stories may be old. Saved training results are a historical snapshot, NOT UK technology results.

**Website status:** runnable locally; no public project website has been deployed.
The GitHub address displays source code. An HTML file in GitHub's file viewer is
not a hosted dashboard.

From this project folder, install its documented dependencies, then run:

```bash
python main.py --live --output outputs
```

Open the generated **`outputs/report.html`** from your local output folder.
It is a saved report; it refreshes only when you run the command again.

**Separate repository:** requested; creation is pending. The current folder and
its previous validation evidence remain available. Extraction is not a new
project and does not increase the completed count.

A runnable NLP/ML prototype that captures public RSS headline metadata, groups
near-duplicate stories, fits **TF-IDF + K-means**, and exports human-readable
cluster inspection with original source links. It actually trains a clustering
model and evaluates separate story groups against simple baselines.

**Result:** this small headline-only model did not beat the single-centroid
baseline on held-out compactness. It is a learning prototype, not a validated
news taxonomy, semantic search service, fact checker or production deployment.

## Run

Python 3.10+. Tested with Python 3.12, NumPy 2.3.5 and scikit-learn 1.8.0.

```bash
python -m pip install -r requirements.txt
# Reproduce the saved real capture without a network request:
python main.py --input examples/source_snapshot.json --output outputs
python -m unittest discover -s tests -v
# Make one bounded live pull of each of the three publisher feeds:
python main.py --live --output outputs/live
```

Open `outputs/report.html`. Other outputs:

- `metrics.json`: quality, source freshness, split details, measured errors,
  cluster terms, counts and representative training/held-out headlines.
- `assignments.csv`: every retained headline, its original link, story group,
  train/held-out designation, assigned cluster and squared distance.
- `model.json`: fitted vocabulary, IDF weights and centroids in inspectable JSON,
  plus disjoint training and held-out groups. No pickle or large neural weights.
- A live run additionally saves the real `source_snapshot.json`. The checked-in
  snapshot retains titles, reported dates and links, with original XML hashes;
  it omits descriptions, article bodies, images and logos.

`--live` performs a pull when invoked. It does not install a schedule, keep a
service running or stream publications. Offline replay is labelled separately.
Failures are saved with source/status metadata. Fewer than two working feeds,
30 usable headlines or 20 story groups stops the fit; no fabricated fallback is
substituted. Providers can change their feed lengths or formats.

## Real source capture

On **27 October 2026**, the three public feeds returned **60 headlines**:

| Publisher feed | Retained headlines | Latest feed-reported publication |
|---|---:|---|
| NASA | 10 | 27 October 2026 |
| NOAA | 10 | 14 October 2026 |
| NIST | 40 | 16 October 2026 |

All 60 had usable dated metadata; no exact duplicates, future dates or items
older than the 365-day bound were removed in this capture. NASA was recent;
NOAA and NIST were already more than seven days old at retrieval. A successful
feed request does not mean its content is current. Feed dates can describe an
update/republication rather than when an event first occurred. This is an
unbalanced source sample spanning multiple months, not a representative news
corpus or a live account of world events.

Sources are fixed official feed URLs, with no login or API key:

- `https://www.nasa.gov/feed/`
- `https://www.noaa.gov/rss.xml`
- `https://www.nist.gov/news-events/news/rss.xml`

## Method and split controls

1. Parse RSS 2.0 or Atom metadata, with bounded responses and entry counts.
   Reject DTD/entity declarations and non-feed responses. Strip title markup
   and reject unsafe article URL schemes/credentials, missing time zones,
   future dates beyond five minutes and records more than 365 days old.
2. Normalise links by removing fragments and tracking parameters while retaining
   meaningful query parameters. Collapse normalised exact-title copies, keeping
   source and URL aliases. Related title revisions remain separate records.
3. Group canonical-URL aliases or titles with token-set Jaccard overlap of at
   least 0.80, including transitive matches. Split **whole story groups** using
   a fixed seed of 42, approximately 80/20. Grouping is a text/URL heuristic and
   cannot guarantee detection of every semantically related story.
4. Fit the TF-IDF vocabulary and IDF on training headlines only. Use English
   stop words, accent normalisation, word/bigram features, a 5,000-feature cap
   and maximum document frequency 0.95. Only the title is modelled; source IDs,
   URLs and dates are excluded, and NASA/NOAA/NIST name tokens are removed.
   Other publisher style cues can remain.
5. Fit `KMeans(n_clusters=4, n_init=20, random_state=42)` on training vectors.
   Four clusters and all settings were fixed before inspecting held-out scores.
   Seed 7 is a training-only sensitivity check, not a selected replacement.
6. Transform held-out titles with the existing vocabulary and assign the nearest
   centroid. A zero-vocabulary title is explicitly **unassigned (`-1`)** and
   gets loss 1 rather than falsely receiving perfect zero-vector similarity.

The published split has **48 training headlines and 12 held-out headlines**,
with 60 distinct groups and no train/test group overlap. This is a **grouped
topic-discovery test**, not a chronological forecast of future headlines.
The model is never refitted on held-out text. No topic labels or publisher IDs
are used as supervised targets. There is no ground-truth topic accuracy claim.

## Actual measured result

The primary measure is mean squared Euclidean distance to a selected centroid
in the training-fitted TF-IDF space, including the declared penalty for
unrepresented held-out titles. **Lower is better for compactness**, but it does
not establish semantic correctness.

| Held-out representation | Mean squared distance |
|---|---:|
| Fitted four-cluster K-means | 0.994561 |
| Single training-mean centroid baseline | **0.993707** |
| Four seeded random training-headline prototypes | 1.708960 |

The single centroid performs slightly better than K-means. No significance or
future-performance claim is made from this 12-item test. Training the vectoriser
and main model took roughly **0.03–0.05 seconds on CPU**, excluding feed requests
and the separate sensitivity fit.

Additional findings:

- Training cluster sizes were **37, 2, 3 and 6**. All **10 represented held-out
  headlines** landed in the large diffuse cluster; **2/12** had no training
  vocabulary overlap and remained unassigned.
- Held-out cosine silhouette is **undefined**, because represented held-out
  items occupied only one cluster. It is saved as `null`, not zero or a good
  score.
- Seed-42 versus seed-7 training assignments had adjusted Rand index **0.09745**,
  indicating substantial sensitivity on this small, sparse sample.
- One tiny group contains related NEO Surveyor hardware-inspection headlines.
  Another groups winter-outlook stories with an astronomy title through the
  word “October”: an example of lexical grouping that is not a coherent topic.

See [inspection.md](examples/inspection.md) for the actual representative titles
and an AI-assisted qualitative review. That review is not an independent human
labelled evaluation. All negative results and individual assignments are saved.
The next experiment should use a larger, more balanced corpus and a separately
reserved evaluation window; this held-out sample must not be tuned into success.

## Validation and limitations

The tests cover RSS/Atom formats, missing time zones, old/future dates, unsafe
URLs, markup removal, exact-title preservation, URL-alias grouping, no story
overlap across splits, reproducible grouping, test-only vocabulary exclusion,
publisher-name removal, unrepresented-title handling, the training-mean
baseline, failure without synthetic replacement and safe finite exports.
Test fixtures are explicitly synthetic; the experiment uses actual feed data.

Saved replay reproduces the fitted parameters, assignments and numeric results;
build timestamps and measured fit durations naturally change. Inspect
[validation.txt](examples/validation.txt) for exact executed commands and output.
The HTML is a generated report, not a browser-tested hosted application.

Important limits: only three publishers, 60 short English headlines and 12
held-out examples; substantial source imbalance; weak cluster generalisation;
no article bodies, embeddings, semantic ground truth, sentiment or fact checking.
The code does not summarise medical, legal or security recommendations. A
provider may expose older or revised material with a newer feed date.

## Primary sources, reuse and attribution

The tool includes factual metadata obtained from the NASA, NOAA and NIST public
feeds. Original headlines link to their publishers. Model-generated top terms,
cluster headings and assignments are **our machine-generated analysis**, not
publisher statements, and imply no affiliation, permission review, endorsement
or agency guarantee of accuracy. NASA is not responsible for model outputs.

Only headline metadata is retained: no third-party images, logos, article bodies
or descriptions. Do not infer that every item on a government website has an
unrestricted licence; publisher exceptions and third-party credits still apply.
No blanket Creative Commons licence is claimed for the combined metadata.

Verified primary documentation:

- [NASA RSS directory](https://www.nasa.gov/rss-feeds/)
- [NASA usage guidelines, including AI source disclosure](https://www.nasa.gov/nasa-brand-center/images-and-media/)
- [NOAA RSS overview](https://www.noaa.gov/rss-feeds)
- [NOAA content-use and attribution guidance](https://www.noaa.gov/office-education/outreach-communication/faq)
- [NIST RSS directory](https://www.nist.gov/coo/nist-rss-feeds)
- [NIST public-information reuse and exceptions](https://www.nist.gov/copyrights-disclaimers)
- [TF-IDF official documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [K-means official documentation](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)

Built with AI assistance for the portfolio sprint. No paid services, external
messages or always-on deployment were used.
