"""Audit future dataset splits without loading/logging raw investment messages.

This does not create labels, train models or measure real-world fraud accuracy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def audit_split_manifest(splits: dict) -> dict:
    """Require campaign-disjoint and strictly chronological train/validation/test."""
    if not isinstance(splits, dict) or set(splits) != {"train", "validation", "test"}:
        raise ValueError("Provide exactly train, validation and test splits")
    ids, campaigns, hashes = set(), set(), set()
    bounds, counts = {}, {}
    for name in ("train", "validation", "test"):
        records = splits[name]
        if not isinstance(records, list) or not records:
            raise ValueError("Each split must contain metadata records")
        local_campaigns, dates = set(), []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Records must be metadata objects")
            sample = record.get("sample_id")
            campaign = record.get("campaign_id")
            timestamp = record.get("observed_at")
            if not all(isinstance(x, str) and x.strip() for x in (sample, campaign, timestamp)):
                raise ValueError("sample_id, campaign_id and observed_at are required")
            if sample in ids:
                raise ValueError("Repeated sample identity across or within splits")
            ids.add(sample)
            if campaign in campaigns:
                raise ValueError("Campaign leakage across splits")
            local_campaigns.add(campaign)
            try:
                date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("observed_at must be an ISO datetime") from exc
            if date.tzinfo is None:
                raise ValueError("observed_at needs an explicit timezone")
            dates.append(date.astimezone(timezone.utc))
            fingerprint = record.get("text_sha256")
            if fingerprint is not None:
                if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                    raise ValueError("text_sha256 must be a lowercase SHA-256 digest")
                if fingerprint in hashes:
                    raise ValueError("Duplicate text fingerprint across or within splits")
                hashes.add(fingerprint)
        campaigns.update(local_campaigns)
        bounds[name] = (min(dates), max(dates))
        counts[name] = {"samples": len(records), "campaigns": len(local_campaigns)}
    if not (bounds["train"][1] < bounds["validation"][0] and bounds["validation"][1] < bounds["test"][0]):
        raise ValueError("Strict temporal order is required: train before validation before test")
    return {
        "status": "metadata_checks_passed",
        "splits": {name: {**counts[name], "first_observed": a.isoformat(), "last_observed": b.isoformat()}
                   for name, (a, b) in bounds.items()},
        "limitations": [
            "No labels, licensing, consent, source truth or model performance were validated.",
            "Campaign IDs and observation times must be independently reviewed, not inferred from random rows.",
            "Exact hashes are optional; near-duplicate and shared-domain/entity leakage need additional review.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit metadata-only split manifest; never prints input texts")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_split_manifest(json.loads(args.manifest.read_text())), indent=2))
