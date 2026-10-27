"""Synthetic test-only metadata; sample outputs use real public RSS captures."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import numpy as np
from main import FEEDS, canonical_url, capture, distances, evaluate, group_split, model_text, parse_feed, plain, prepare, run, stamp


def fixture():
    records=[]
    terms=[("nasa","Lunar spacecraft telescope mission"),("noaa","Coastal ocean hurricane climate"),("nist","Quantum atomic measurement laboratory")]
    variants=["research discovery", "instrument testing", "analysis methods", "experimental results", "program funding", "public workshop", "prototype development", "international collaboration", "laboratory calibration", "field survey", "student education", "data release"]
    for source,base in terms:
        for i,suffix in enumerate(variants):
            records.append({"source":source,"title":base+" "+suffix,"url":f"https://www.{source}.gov/news/{i}","published":f"2026-10-{i+1:02d}T12:00:00+00:00"})
    return {"retrieved_at_utc":"2026-10-27T09:00:00+00:00","mode":"SYNTHETIC TEST FIXTURE ONLY","sources":[{"source":s,"status":"ok"} for s in FEEDS],"records":records}


class TopicTests(unittest.TestCase):
    def test_rss_metadata_parsed_without_article_body(self):
        xml=b'<rss><channel><item><title>Public science headline</title><link>https://example.gov/a</link><pubDate>Tue, 27 Oct 2026 08:00:00 GMT</pubDate><description>not retained</description></item></channel></rss>'
        r=parse_feed(xml);self.assertEqual(len(r),1);self.assertNotIn("description",r[0])
    def test_atom_namespace_dates_and_alternate_links(self):
        xml=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Space station science</title><updated>2026-10-27T08:00:00Z</updated><link rel="self" href="https://example.gov/api"/><link href="https://example.gov/article"/></entry></feed>'
        self.assertEqual(parse_feed(xml)[0]["url"],"https://example.gov/article")
    def test_dtd_and_html_response_rejected(self):
        for raw in [b'<!DOCTYPE rss [<!ENTITY x "value">]><rss/>',b'<html><body>Maintenance</body></html>']:
            with self.assertRaises(ValueError):parse_feed(raw)
    def test_tracking_is_removed_but_content_query_is_retained(self):
        self.assertEqual(canonical_url("https://EXAMPLE.gov/story/?id=4&utm_source=rss#section"),"https://example.gov/story?id=4")
    def test_unsafe_urls_are_not_publishable(self):
        for u in ["javascript:alert(1)","file:///etc/passwd","https://name:secret@example.gov/a","https://example.gov:8000/a","https://example.gov:80/a"]:
            with self.assertRaises(ValueError):canonical_url(u)
    def test_time_zone_is_not_invented(self):
        with self.assertRaises(ValueError):stamp("2026-10-27T08:00:00")
        self.assertEqual(stamp("2026-10-27T09:00:00+01:00").hour,8)
    def test_script_content_and_html_tags_removed(self):
        self.assertEqual(plain("<b>Science</b><script>steal()</script> &amp; discovery"),"Science & discovery")
    def test_future_old_and_malformed_dates_are_reported(self):
        s=fixture();s["records"]+=[{**s["records"][0],"published":d} for d in ["2030-01-01T00:00:00Z","2020-01-01T00:00:00Z","not a date"]]
        _,q=prepare(s);self.assertEqual(q["future_records"],1);self.assertEqual(q["older_than_365_days"],1);self.assertEqual(q["invalid_records"],1)
    def test_wrong_metadata_types_are_rejected_without_inventing_values(self):
        s=fixture();s["records"] += [{**s["records"][0],"published":None},{**s["records"][0],"title":42},{**s["records"][0],"url":None}]
        _,q=prepare(s);self.assertEqual(q["invalid_records"],3)
    def test_exact_duplicate_preserves_source_and_url_aliases(self):
        s=fixture();s["records"].append({**s["records"][0],"source":"noaa","url":"https://www.noaa.gov/copy"})
        rows,q=prepare(s);r=next(r for r in rows if r["title"]==s["records"][0]["title"])
        self.assertEqual(q["exact_duplicates"],1);self.assertEqual(r["sources"],["nasa","noaa"]);self.assertEqual(len(r["urls"]),2)
    def test_different_word_order_not_silently_deleted(self):
        s=fixture();s["records"] += [{"source":"nasa","title":t,"url":f"https://www.nasa.gov/order/{i}","published":"2026-10-20T00:00:00Z"} for i,t in enumerate(["Researcher studies powerful telescope", "Telescope studies powerful researcher"])]
        rows,_=prepare(s);self.assertEqual(sum("powerful" in r["title"] for r in rows),2)
    def test_annual_editions_are_not_deleted_as_exact_copies(self):
        s=fixture();s["records"] += [{"source":"nasa","title":f"Annual science report for {year}","url":f"https://www.nasa.gov/report/{year}","published":"2026-10-20T00:00:00Z"} for year in (2025,2026)]
        rows,_=prepare(s);self.assertEqual(sum("Annual science report" in r["title"] for r in rows),2)
    def test_alias_revision_story_stays_in_one_split(self):
        s=fixture();original=s["records"][0];s["records"] += [{**original,"url":"https://www.noaa.gov/copy","source":"noaa"},{**original,"url":"https://www.noaa.gov/copy","source":"noaa","title":"A substantially rewritten headline about new scientific tools"}]
        rows,_=prepare(s);matching=[r for r in rows if "https://www.noaa.gov/copy" in r["urls"]]
        self.assertEqual(len({r["group"] for r in matching}),1)
    def test_no_group_or_canonical_url_overlap_in_holdout(self):
        rows,_=prepare(fixture());train,test=group_split(rows)
        self.assertFalse({r["group"] for r in train}&{r["group"] for r in test})
        self.assertFalse({u for r in train for u in r["urls"]}&{u for r in test for u in r["urls"]})
    def test_split_is_repeatable_under_input_reordering(self):
        a=fixture();b=copy.deepcopy(a);b["records"].reverse()
        ta,ha=group_split(prepare(a)[0]);tb,hb=group_split(prepare(b)[0]);self.assertEqual([r["group"] for r in ha],[r["group"] for r in hb])
    def test_test_exclusive_word_cannot_enter_fitted_vocabulary(self):
        train,test=group_split(prepare(fixture())[0]);test=copy.deepcopy(test)
        for r in test:r["title"] += " zebrawidgetexclusive"
        _,_,_,a=evaluate(train,test);self.assertNotIn("zebrawidgetexclusive",a["vocabulary"])
    def test_publisher_names_are_not_model_features(self):
        self.assertNotIn("NASA",model_text("NASA studies stars with NOAA and NIST"))
    def test_zero_overlap_holdout_is_unassigned_and_penalised(self):
        train,test=group_split(prepare(fixture())[0]);test=copy.deepcopy(test)
        for r in test:r["title"]="zzqvvv qqzzxx zyxwv"
        m,_,a,_=evaluate(train,test);self.assertEqual(m["zero_vocabulary_heldout"],len(test));self.assertIsNone(m["heldout_cosine_silhouette"])
        self.assertTrue(all(r["cluster"]==-1 and r["squared_distance"]==1 for r in a if r["split"]=="heldout"))
    def test_single_centroid_baseline_is_training_mean(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        train,test=group_split(prepare(fixture())[0]);m,_,_,a=evaluate(train,test)
        v=TfidfVectorizer(stop_words="english",strip_accents="unicode",token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]+\b",ngram_range=(1,2),max_df=.95,max_features=5000)
        x=v.fit_transform([model_text(r["title"]) for r in train]);xt=v.transform([model_text(r["title"]) for r in test]);expected=distances(xt,np.asarray(x.mean(axis=0)))[0].mean()
        self.assertAlmostEqual(m["single_centroid_baseline_distance"],expected)
    def test_small_capture_fails_instead_of_fake_metrics(self):
        with self.assertRaises(ValueError):group_split(prepare(fixture())[0][:10])
    def test_live_total_failure_is_saved_and_never_fabricated(self):
        with tempfile.TemporaryDirectory() as d,patch("urllib.request.urlopen",side_effect=TimeoutError):
            p=Path(d)/"failure.json"
            with self.assertRaises(ValueError):capture(p)
            s=json.loads(p.read_text());self.assertEqual(s["records"],[]);self.assertTrue(all(r["status"]=="failed" for r in s["sources"]))
    def test_export_is_finite_and_report_escapes_metadata(self):
        s=fixture();s["records"][0]["title"]="Experimental study &lt;img src=x onerror=alert(1)&gt; about lunar samples"
        with tempfile.TemporaryDirectory() as d:
            run(s,d);model=json.loads((Path(d)/"model.json").read_text());self.assertEqual(len(model["centers"]),4)
            self.assertNotIn("<img",(Path(d)/"report.html").read_text());self.assertTrue((Path(d)/"assignments.csv").exists())


if __name__=="__main__":unittest.main()
