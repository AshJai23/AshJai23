"""Bounded RSS/Atom metadata ingestion and group-held-out TF-IDF clustering."""
import argparse
import csv
import hashlib
import html
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, pairwise_distances, silhouette_score

FEEDS = {"nasa": "https://www.nasa.gov/feed/", "noaa": "https://www.noaa.gov/rss.xml", "nist": "https://www.nist.gov/news-events/news/rss.xml"}
K = 4


class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden: self.hidden -= 1
        self.parts.append(" ")
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def plain(value):
    if value is not None and not isinstance(value,str): raise ValueError("Text metadata must be a string")
    p = Text(); p.feed(html.unescape(value or "")); return " ".join(" ".join(p.parts).split())


def stamp(value):
    if not isinstance(value,str) or not value.strip(): raise ValueError("Missing publication date")
    try: d = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError: d = parsedate_to_datetime(value.strip())
    if d.tzinfo is None: raise ValueError("Publication date has no time zone")
    return d.astimezone(timezone.utc)


def canonical_url(value):
    if not isinstance(value,str): raise ValueError("Article URL must be a string")
    p = urllib.parse.urlsplit(value.strip())
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password: raise ValueError("Unsafe article URL")
    port = p.port
    if port is not None and port != (443 if p.scheme=="https" else 80): raise ValueError("Unexpected article URL port")
    query = [(k,v) for k,v in urllib.parse.parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in ("gclid", "fbclid")]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.hostname.lower(), p.path.rstrip("/") or "/", urllib.parse.urlencode(sorted(query)), ""))


def parse_feed(raw):
    if len(raw) > 3_000_000: raise ValueError("Feed too large")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper(): raise ValueError("DTD/entities are not accepted")
    root = ET.fromstring(raw); records = []
    if root.tag == "rss":
        items = root.findall("./channel/item")
        for i in items[:100]: records.append({"title": i.findtext("title", ""), "url": i.findtext("link", ""), "published": i.findtext("pubDate", "")})
    elif root.tag == "{http://www.w3.org/2005/Atom}feed":
        ns = {"a":"http://www.w3.org/2005/Atom"}
        for i in root.findall("a:entry", ns)[:100]:
            links = [l.get("href", "") for l in i.findall("a:link", ns) if l.get("rel", "alternate") == "alternate"]
            records.append({"title": "".join(i.find("a:title", ns).itertext()) if i.find("a:title", ns) is not None else "", "url": links[0] if links else "", "published": i.findtext("a:published", i.findtext("a:updated", "", ns), ns)})
    else: raise ValueError("Response is not RSS 2.0 or Atom")
    if not records: raise ValueError("Feed has no entries")
    return records


def capture(destination):
    sources = []; records = []
    for source, url in FEEDS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"PortfolioRSSClustering/1.0", "Accept":"application/rss+xml,application/atom+xml,application/xml"})
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read(3_000_001); final_url = response.url
            items = parse_feed(raw)
            records.extend({"source":source, **r} for r in items)
            sources.append({"source":source, "requested_url":url, "final_url":final_url, "status":"ok", "raw_xml_sha256":hashlib.sha256(raw).hexdigest(), "raw_entries":len(items)})
        except Exception as exc:
            sources.append({"source":source, "requested_url":url, "status":"failed", "error_type":type(exc).__name__, "http_status":getattr(exc,"code",None)})
    snapshot = {"retrieved_at_utc":datetime.now(timezone.utc).isoformat(), "mode":"Live pull of regularly refreshed RSS metadata; not continuous streaming", "sources":sources, "records":records,
                "retention":"Headlines, links and reported dates only; no descriptions, article bodies, logos or images"}
    path = Path(destination); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+"\n")
    if sum(s["status"] == "ok" for s in sources) < 2: raise ValueError("Fewer than two real feeds succeeded; failure snapshot saved, no fabricated fallback")
    return snapshot


def tokens(value): return set(re.findall(r"[a-z]{2,}", plain(value).lower()))
def model_text(title): return re.sub(r"\b(?:nasa|noaa|nist)\b", " ", title, flags=re.I)


def prepare(snapshot):
    as_of = stamp(snapshot["retrieved_at_utc"]); rows = []; quality = Counter({k:0 for k in ("input_records", "invalid_records", "future_records", "older_than_365_days", "exact_duplicates")})
    for item in snapshot["records"]:
        quality["input_records"] += 1
        try:
            title = plain(item["title"]); when = stamp(item["published"]); url = canonical_url(item["url"])
            if not 15 <= len(title) <= 500 or len(tokens(title)) < 3 or item["source"] not in FEEDS: raise ValueError("Bad metadata")
            if when > as_of+timedelta(minutes=5): quality["future_records"] += 1; continue
            if when < as_of-timedelta(days=365): quality["older_than_365_days"] += 1; continue
            rows.append({"title":title, "url":url, "urls":[url], "published_utc":when.isoformat(), "sources":[item["source"]]})
        except (KeyError, ValueError, TypeError, OverflowError): quality["invalid_records"] += 1
    # Exact normalised-title copies collapse; revisions with different titles
    # stay separate but get the same story group by canonical URL below.
    unique = {}
    for row in sorted(rows, key=lambda r:(r["published_utc"],r["url"],r["title"])):
        key = " ".join(re.findall(r"[a-z0-9]+",row["title"].lower()))
        if key in unique:
            quality["exact_duplicates"] += 1; unique[key]["sources"] = sorted(set(unique[key]["sources"]+row["sources"]))
            unique[key]["urls"] = sorted(set(unique[key]["urls"]+row["urls"]))
        else: unique[key] = row
    rows = sorted(unique.values(), key=lambda r:(r["url"],r["title"]))
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    title_tokens = [tokens(r["title"]) for r in rows]
    for i in range(len(rows)):
        for j in range(i):
            union = title_tokens[i] | title_tokens[j]
            if set(rows[i]["urls"]) & set(rows[j]["urls"]) or len(title_tokens[i]&title_tokens[j])/len(union) >= .8:
                parent[find(i)] = find(j)
    members = defaultdict(list)
    for i,r in enumerate(rows): members[find(i)].append(r["url"]+"\n"+r["title"])
    identifiers = {i:hashlib.sha256("\n".join(sorted(v)).encode()).hexdigest()[:20] for i,v in members.items()}
    for i,r in enumerate(rows): r["group"] = identifiers[find(i)]
    quality["usable_headlines"] = len(rows); quality["story_groups"] = len(members)
    return rows, dict(quality)


def group_split(rows):
    groups = sorted({r["group"] for r in rows})
    if len(rows) < 30 or len(groups) < 20: raise ValueError("Need 30 real headlines and 20 distinct story groups")
    order = np.random.default_rng(42).permutation(len(groups)); heldout = {groups[i] for i in order[:max(6,math.ceil(.2*len(groups))) ]}
    train = [r for r in rows if r["group"] not in heldout]; test = [r for r in rows if r["group"] in heldout]
    if len(train) < 20 or len(test) < 6: raise ValueError("Insufficient grouped train/test data")
    return train, test


def distances(x, centers):
    d = pairwise_distances(x, centers, metric="euclidean", squared=True)
    # A headline with no vocabulary overlap is unrepresented, not a perfect
    # zero-vector prediction. Score it as distance 1 to every candidate.
    zero = np.asarray(x.getnnz(axis=1) == 0); d[zero,:] = 1.0
    return d, zero


def evaluate(train, test):
    vectorizer = TfidfVectorizer(stop_words="english", strip_accents="unicode", token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]+\b", ngram_range=(1,2), max_df=.95, max_features=5000)
    started = time.perf_counter(); x = vectorizer.fit_transform([model_text(r["title"]) for r in train]); xt = vectorizer.transform([model_text(r["title"]) for r in test])
    if x.shape[1] < 20 or np.any(x.getnnz(axis=1) == 0): raise ValueError("Insufficient training vocabulary")
    model = KMeans(n_clusters=K, n_init=20, max_iter=300, random_state=42).fit(x)
    fit_seconds = time.perf_counter()-started
    if len(set(model.labels_)) != K: raise ValueError("Degenerate clustering")
    d, zero = distances(xt, model.cluster_centers_); predicted = d.argmin(axis=1); predicted[zero] = -1
    model_error = d.min(axis=1)
    single = np.asarray(x.mean(axis=0)); single_error = distances(xt, single)[0][:,0]
    chosen = np.random.default_rng(42).choice(x.shape[0], size=K, replace=False)
    prototype_error = distances(xt,x[chosen].toarray())[0].min(axis=1)
    usable = ~zero; distinct = len(set(predicted[usable])); n = int(usable.sum())
    silhouette = float(silhouette_score(xt[usable],predicted[usable],metric="cosine")) if 2 <= distinct < n else None
    # Sensitivity uses training data only and never selects a seed on the test.
    other = KMeans(n_clusters=K,n_init=20,max_iter=300,random_state=7).fit(x)
    stability = float(adjusted_rand_score(model.labels_,other.labels_))
    metrics = {"training_headlines":len(train),"heldout_headlines":len(test),"clusters":K,"features":x.shape[1],"fit_seconds":fit_seconds,
               "heldout_mean_squared_distance":float(model_error.mean()),"single_centroid_baseline_distance":float(single_error.mean()),"four_random_training_prototypes_distance":float(prototype_error.mean()),
               "zero_vocabulary_heldout":int(zero.sum()),"heldout_cosine_silhouette":silhouette,"training_seed_stability_ari_42_vs_7":stability,
               "training_cluster_counts":{str(c):int(np.sum(model.labels_==c)) for c in range(K)},"heldout_cluster_counts":{str(c):int(np.sum(predicted==c)) for c in range(-1,K)},
               "heldout_silhouette_note":"Undefined: fewer than two nonzero-vocabulary assigned clusters or too few samples" if silhouette is None else "Cosine silhouette on represented heldout headlines only",
               "kmeans_beats_single_centroid":bool(model_error.mean()<single_error.mean()),"metric_scope":"Unsupervised TF-IDF compactness on story-held-out metadata, not topic accuracy or semantic truth; lower squared distance is better."}
    names = vectorizer.get_feature_names_out(); clusters = []
    train_d, _ = distances(x,model.cluster_centers_)
    for c in range(K):
        indices = [i for i,v in enumerate(model.labels_) if v==c]; indices.sort(key=lambda i:train_d[i,c])
        test_indices = [i for i,v in enumerate(predicted) if v==c]; test_indices.sort(key=lambda i:d[i,c])
        terms = [str(names[i]) for i in np.argsort(model.cluster_centers_[c])[::-1][:10] if model.cluster_centers_[c,i]>0]
        clusters.append({"cluster":c,"top_terms":terms,"training_count":len(indices),"heldout_count":len(test_indices),"representative_training":[train[i] for i in indices[:3]],"representative_heldout":[test[i] for i in test_indices[:2]],
                         "source_counts_training":dict(Counter(s for i in indices for s in train[i]["sources"]))})
    assignments = []
    for split, docs, labels, errors in (("train",train,model.labels_,train_d.min(axis=1)),("heldout",test,predicted,model_error)):
        assignments.extend({**r,"split":split,"cluster":int(label),"squared_distance":float(error)} for r,label,error in zip(docs,labels,errors))
    artifact = {"kind":"TF-IDF and KMeans parameters, inspectable JSON; no pickle", "vocabulary":{k:int(v) for k,v in vectorizer.vocabulary_.items()},"idf":vectorizer.idf_.tolist(),"centers":model.cluster_centers_.tolist(),"training_groups":sorted({r["group"] for r in train}),"heldout_groups":sorted({r["group"] for r in test})}
    return metrics, clusters, assignments, artifact


def run(snapshot, output, mode="replay"):
    rows, quality = prepare(snapshot); train,test = group_split(rows); metrics,clusters,assignments,artifact = evaluate(train,test)
    now = stamp(snapshot["retrieved_at_utc"]); freshness = []
    for s in snapshot["sources"]:
        dates = [stamp(r["published_utc"]) for r in rows if s["source"] in r["sources"]]; age = (now-max(dates)).total_seconds()/86400 if dates else None
        freshness.append({**s,"latest_usable_published_utc":max(dates).isoformat() if dates else None,"age_latest_days":age,"older_than_7_days":age>7 if age is not None else None})
    report = {"built_at_utc":datetime.now(timezone.utc).isoformat(),"data_mode":"Explicit replay of real saved RSS metadata" if mode=="replay" else snapshot["mode"],"captured_at_utc":snapshot["retrieved_at_utc"],"snapshot_canonical_sha256":hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),"quality":quality,"sources":freshness,
              "split":"Seed 42, 80/20 story-group holdout after exact dedup and near-title/canonical-URL grouping. Not a chronological future-news test.","metrics":metrics,"clusters":clusters,
              "limitations":"Small, publisher-imbalanced English headline sample; no semantic ground truth, sentiment, fact checking or full-article analysis. Feed dates can represent updates/republication. Publisher names removed from model text; no claim that this removes all source style. Machine-generated clusters are not official publisher classifications."}
    output = Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"metrics.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    (output/"model.json").write_text(json.dumps(artifact,ensure_ascii=False,allow_nan=False)+"\n")
    with (output/"assignments.csv").open("w",newline="") as f:
        cols=["title","url","urls","published_utc","sources","group","split","cluster","squared_distance"];writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows({**r,"sources":";".join(r["sources"]),"urls":";".join(r["urls"])} for r in assignments)
    cards=[]
    for c in clusters:
        examples="".join('<li><a rel="noreferrer" href="'+html.escape(r["url"],quote=True)+'">'+html.escape(r["title"])+'</a><small> '+html.escape(','.join(r["sources"]))+' · '+html.escape(r["published_utc"][:10])+'</small></li>' for r in c["representative_training"])
        heldout="".join('<li><a rel="noreferrer" href="'+html.escape(r["url"],quote=True)+'">'+html.escape(r["title"])+'</a><small>HELD-OUT · '+html.escape(','.join(r["sources"]))+'</small></li>' for r in c["representative_heldout"])
        cards.append('<section><h2>Cluster '+str(c["cluster"])+': '+html.escape(', '.join(c["top_terms"][:5]))+'</h2><p>'+str(c["training_count"])+' training / '+str(c["heldout_count"])+' held-out headlines</p><ul>'+examples+heldout+'</ul></section>')
    metric_html=html.escape(json.dumps(metrics,indent=2));notes=html.escape(report["limitations"])
    feed_rows="".join('<tr>'+''.join('<td>'+html.escape(str(s.get(key,"n/a")))+'</td>' for key in ("source","status","raw_entries","latest_usable_published_utc","older_than_7_days"))+'</tr>' for s in freshness)
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RSS topic clusters</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px;background:#f3f6f2;color:#163d37}section,pre{background:white;border:1px solid #dce5d8;border-radius:12px;padding:20px;margin:18px 0}h2{font-size:20px}li{margin:12px 0}small{display:block;color:#687568}a{color:#246958}pre{white-space:pre-wrap}table{border-collapse:collapse;font-size:12px}td,th{padding:8px;border-bottom:1px solid #ccd5ca;text-align:left}</style><h1>RSS headlines: machine-generated topic groups</h1><p>'+html.escape(report["data_mode"]+'; captured '+snapshot["retrieved_at_utc"])+'</p><p>Source metadata includes NASA, NOAA and NIST headlines. Group names and assignments are model outputs, not statements or classifications from those agencies. No affiliation, endorsement or accuracy guarantee is implied.</p><h2>Source freshness</h2><table><tr><th>Feed</th><th>Fetch</th><th>Entries</th><th>Latest reported date</th><th>Older than 7 days</th></tr>'+feed_rows+'</table>'+''.join(cards)+'<h2>Measured held-out results</h2><pre>'+metric_html+'</pre><p>'+notes+'</p><p>Links open the original publisher. No article bodies, images or logos are copied.</p></html>'
    (output/"report.html").write_text(page)
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--live",action="store_true");p.add_argument("--input",default="examples/source_snapshot.json");p.add_argument("--output",default="outputs");a=p.parse_args()
    if a.live:
        output=Path(a.output);output.mkdir(parents=True,exist_ok=True);snapshot=capture(output/"source_snapshot.json")
    else: snapshot=json.loads(Path(a.input).read_text())
    result=run(snapshot,a.output,"live" if a.live else "replay");print(json.dumps({"quality":result["quality"],"metrics":result["metrics"]},indent=2))
