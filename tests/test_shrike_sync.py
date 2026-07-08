from __future__ import annotations
import json
from datetime import date
import pytest
from ibis import db
from ibis.sync.shrike import sync as shrike_sync
from ibis.models import AdvisorySource, VendorTier


def test_uses_ghsa_id_when_present(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisory = db.get("GHSA-mf64-cgv4-ppcx")
    assert advisory is not None


def test_synthetic_id_when_no_ghsa(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisories = db.list_all()
    synthetic = [a for a in advisories if a.ghsa_id.startswith("SHRIKE-")]
    assert len(synthetic) == 1
    assert "dify" in synthetic[0].ghsa_id or "no_ghsa" in synthetic[0].ghsa_id


def test_package_is_target(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisory = db.get("GHSA-mf64-cgv4-ppcx")
    assert advisory.package == "playwright-mcp"


def test_source_is_shrike(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisories = db.list_all()
    assert all(a.source == AdvisorySource.shrike for a in advisories)


def test_severity_lowercase(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisory = db.get("GHSA-mf64-cgv4-ppcx")
    assert advisory.severity == "high"


def test_collaborator_sets_not_tier_d(test_db, no_npm, shrike_dir_with_collaborator):
    shrike_sync(shrike_dir_with_collaborator)
    advisory = db.get("GHSA-m2m9-fp87-72m8")
    assert advisory is not None
    assert advisory.tier != VendorTier.D


def test_no_collaborator_tier_d(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisories = db.list_all()
    no_collab = [a for a in advisories if not a.collaborators]
    assert all(a.tier == VendorTier.D for a in no_collab)


def test_collaborator_stored(test_db, no_npm, shrike_dir_with_collaborator):
    shrike_sync(shrike_dir_with_collaborator)
    advisory = db.get("GHSA-m2m9-fp87-72m8")
    assert advisory.collaborators == ["sonichi"]


def test_created_at_from_submitted_at(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisory = db.get("GHSA-mf64-cgv4-ppcx")
    assert advisory.created_at == date(2026, 6, 25)


def test_skips_invalid_json(test_db, no_npm, tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    (findings_dir / "bad.json").write_text("not valid json{{{")
    count = shrike_sync(findings_dir)
    assert count == 0
    assert db.list_all() == []


def test_empty_dir_returns_zero(test_db, no_npm, tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    count = shrike_sync(findings_dir)
    assert count == 0


def test_upsert_idempotent(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    shrike_sync(shrike_dir_two_findings)
    assert len(db.list_all()) == 2


def test_notes_contain_title(test_db, no_npm, shrike_dir_two_findings):
    shrike_sync(shrike_dir_two_findings)
    advisory = db.get("GHSA-mf64-cgv4-ppcx")
    assert "Path Traversal" in advisory.notes
