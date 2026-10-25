"""Fixed GOV.UK sources; no visitor URL fetching or generated legal claims."""
import hashlib
import json
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
CARDS = {
    "graduate": {
        "title": "Plan your post-study next step", "path": "/graduate-visa",
        "terms": ["graduate", "graduation", "post study", "post-study", "psw", "2027", "2026", "masters", "phd", "finish my course"],
        "summary": "The published Graduate visa guidance distinguishes applications made by 31 December 2026 (two years) from those made from 1 January 2027 (18 months). Doctoral qualifications have a three-year duration. This is general guidance, not a decision on your eligibility.",
        "actions": ["Read the eligibility and application sections on GOV.UK.", "Ask your university when it can report successful completion and discuss your own visa expiry with its international adviser."],
        "checks": [r"2 years if you apply on or before 31 December 2026", r"18 months if you apply on or after 1 January 2027", r"doctoral qualification"],
    },
    "work": {
        "title": "Check before accepting work", "path": "/student-visa",
        "terms": ["work", "job", "hours", "freelance", "self employed", "self-employed", "deliveroo", "uber", "employment", "dissertation", "internship", "term time", "term-time"],
        "summary": "Student work permissions depend on your course and circumstances. Check your own permission and your university's term dates before accepting work. The Student visa overview lists self-employment among restricted activities; exceptions and other employment conditions need qualified advice.",
        "actions": ["Check your eVisa or decision letter for your work condition.", "Ask your university adviser about term time, dissertation periods, multiple jobs and any proposed freelance work."],
        "checks": [r"self.employed", r"work"],
    },
    "housing": {
        "title": "Protect your accommodation deposit", "path": "/tenancy-deposit-protection",
        "terms": ["rent", "rental", "landlord", "deposit", "accommodation", "room", "housing", "flat", "place to stay"],
        "summary": "Deposit protection depends on the tenancy and UK nation. Use the official guide to check the applicable scheme and ask your university accommodation team before paying or signing something you do not understand.",
        "actions": ["Check your tenancy type and the appropriate deposit scheme.", "Have the university accommodation team review an unfamiliar offer; this assistant cannot verify a landlord or listing."],
        "checks": [r"deposit", r"Scotland", r"Northern Ireland"],
    },
    "tax": {
        "title": "Understand a Council Tax bill", "path": "/council-tax/discounts-for-full-time-students", "base_path": "/council-tax",
        "terms": ["council tax", "council", "exemption", "tax bill", "household", "student discount"],
        "summary": "The GOV.UK guide describes Council Tax exemptions for households entirely made up of qualifying full-time students. Mixed households can be treated differently. This is not a guarantee that your bill is wrong; check with the council.",
        "actions": ["Request evidence of student status from your university.", "Ask your council about the exemption or discount process for your household."],
        "checks": [r"everyone.s a full.time student", r"someone in your household"],
    },
    "scams": {
        "title": "Pause an unexpected payment demand", "path": "/government/publications/frauds-tricks-and-scams/fraud-tricks-and-scams",
        "terms": ["scam", "fraud", "fine", "deport", "threat", "home office call", "moneygram", "gift card", "guaranteed visa", "suspicious", "pay immediately"],
        "summary": "Unexpected contacts claiming to be the Home Office and demanding money or personal details may be scams. Do not pay or share information with the caller. Use independently found official channels and your university's student support team to check the demand.",
        "actions": ["Stop contact and avoid using links or callback details supplied in the message.", "Open the official guidance and show the message to your university adviser. If money was sent, contact your bank through its official channel."],
        "checks": [r"unexpected email", r"never contact you to ask for money"],
    },
}
NOTICE = "General information and source navigation only. No individual immigration, legal or financial eligibility decisions. Do not enter passport numbers, account details or other sensitive information."


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden: self.hidden -= 1
        if tag in ("p", "li", "h2", "h3", "div"): self.parts.append(" ")
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def content_text(item):
    """Content API guide parts and publication bodies; never execute HTML."""
    details = item.get("details", {})
    chunks = [item.get("title", ""), item.get("description", ""), details.get("body", "")]
    chunks += [p.get("body", "") for p in details.get("parts", [])]
    parser = TextParser(); parser.feed(" ".join(str(c) for c in chunks))
    return " ".join(" ".join(parser.parts).split())


def lexical(question):
    q = question.lower()
    scores = {k: sum(1 + (" " in t) for t in c["terms"] if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", q)) for k, c in CARDS.items()}
    return sorted([k for k in CARDS if scores[k]], key=lambda k: scores[k], reverse=True), scores


class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlparse
        u = urlparse(newurl)
        if u.scheme != "https" or u.netloc != "www.gov.uk": raise ValueError("Off-host redirect blocked")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SourceStore:
    def __init__(self, mode="live", snapshot=None, ttl=900):
        if mode not in ("live", "replay"): raise ValueError("mode must be live or replay")
        self.mode = mode; self.ttl = ttl; self.cache = {}; self.lock = threading.Lock()
        self.snapshot = json.loads(Path(snapshot or ROOT / "examples/source_snapshot.json").read_text()) if mode == "replay" else None
        self.reviewed = json.loads((ROOT / "reviewed_sources.json").read_text())

    def get(self, topic):
        if topic not in CARDS: raise ValueError("Unknown source")
        with self.lock:
            now = time.monotonic()
            if topic in self.cache:
                saved, result = self.cache[topic]
                if now - saved < (self.ttl if result["status"] != "unavailable" else 60):
                    return {**result, "transport": "cache", "cache_age_seconds": round(now - saved, 2)}
            card = CARDS[topic]; url = "https://www.gov.uk" + card["path"]
            record = {"topic": topic, "url": url, "api_url": "https://www.gov.uk/api/content" + card["path"], "mode": self.mode}
            try:
                if self.mode == "replay":
                    saved = self.snapshot[topic]; item = saved["item"]; checked = saved["checked_at_utc"]
                else:
                    req = urllib.request.Request(record["api_url"], headers={"User-Agent": "UKStudentCopilot-Portfolio/0.1", "Accept": "application/json"})
                    with urllib.request.build_opener(SameHostRedirect()).open(req, timeout=12) as response:
                        raw = response.read(2_000_001)
                    if len(raw) > 2_000_000: raise ValueError("Source too large")
                    item = json.loads(raw); checked = datetime.now(timezone.utc).isoformat()
                if item.get("base_path") != card.get("base_path", card["path"]) or item.get("withdrawn_notice") or item.get("withdrawn"):
                    raise ValueError("Source moved, missing or withdrawn")
                text = content_text(item)
                if len(text) < 100: raise ValueError("Empty source body")
                checks = [bool(re.search(p, text, re.I)) for p in card["checks"]]
                digest = hashlib.sha256(text.encode()).hexdigest()
                unchanged = digest == self.reviewed[topic]["sha256"]
                record.update(status="verified" if all(checks) and unchanged else "review_required", checked_at_utc=checked,
                              public_updated_at=item.get("public_updated_at"), sha256=digest, matches_reviewed_source=unchanged,
                              checks_passed=checks, transport="snapshot" if self.mode == "replay" else "network", cache_age_seconds=0)
            except Exception as exc:
                # No snapshot or stale answer is silently substituted for a failed live request.
                record.update(status="unavailable", error_type=type(exc).__name__, transport="failed", cache_age_seconds=0)
            self.cache[topic] = (now, record)
            return dict(record)

    def capture(self, destination):
        """Explicit collection command; preserve full public JSON with retrieval time."""
        records = {}
        for topic, card in CARDS.items():
            req = urllib.request.Request("https://www.gov.uk/api/content" + card["path"], headers={"User-Agent": "UKStudentCopilot-Portfolio/0.1"})
            with urllib.request.build_opener(SameHostRedirect()).open(req, timeout=20) as r:
                raw = r.read(2_000_001)
            if len(raw) > 2_000_000: raise ValueError("Source too large")
            item = json.loads(raw)
            # Store only the selected public content fields, not navigation trees.
            item = {k: item[k] for k in ("base_path", "title", "description", "details", "public_updated_at") if k in item}
            records[topic] = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "item": item}
        Path(destination).write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--capture", required=True)
    SourceStore().capture(p.parse_args().capture)
