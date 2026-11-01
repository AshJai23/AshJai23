"""Synthetic split metadata, not a real labelled investment dataset."""
from copy import deepcopy
import pytest
from smartinvest.evaluation import audit_split_manifest


def fixture():
    return {name: [{"sample_id": str(i), "campaign_id": f"campaign-{i}",
                    "observed_at": f"2025-0{i}-01T00:00:00Z", "text_sha256": str(i)*64}]
            for i, name in enumerate(["train", "validation", "test"], 1)}


def test_group_and_time_disjoint_metadata_passes():
    assert audit_split_manifest(fixture())["status"] == "metadata_checks_passed"


def test_campaign_overlap_rejected():
    x=fixture();x['test'][0]['campaign_id']=x['train'][0]['campaign_id']
    with pytest.raises(ValueError, match='Campaign leakage'):audit_split_manifest(x)


def test_duplicate_identity_rejected():
    x=fixture();x['test'][0]['sample_id']='1'
    with pytest.raises(ValueError, match='Repeated sample'):audit_split_manifest(x)


def test_duplicate_text_hash_rejected():
    x=fixture();x['test'][0]['text_sha256']='1'*64
    with pytest.raises(ValueError, match='Duplicate text'):audit_split_manifest(x)


def test_future_leakage_rejected():
    x=fixture();x['train'][0]['observed_at']='2026-01-01T00:00:00Z'
    with pytest.raises(ValueError, match='temporal'):audit_split_manifest(x)


def test_unknown_timezone_rejected():
    x=fixture();x['train'][0]['observed_at']='2025-01-01'
    with pytest.raises(ValueError, match='timezone'):audit_split_manifest(x)


def test_missing_split_rejected():
    x=fixture();del x['test']
    with pytest.raises(ValueError):audit_split_manifest(x)
