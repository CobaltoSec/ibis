from __future__ import annotations
import json
from datetime import date
from pathlib import Path
import pytest
from ibis import db
from ibis.sync.condor import sync as condor_sync
from ibis.models import AdvisorySource, VendorTier


def test_imports_findings(test_db, no_npm, condor_flowise_report):
    count = condor_sync(condor_flowise_report)
    assert count == 2
    advisories = db.list_all()
    assert len(advisories) == 2


def test_package_is_platform(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert all(a.package == "flowise" for a in advisories)


def test_synthetic_id_format(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    for a in advisories:
        assert a.ghsa_id.startswith("CONDOR-")
    ids = [a.ghsa_id for a in advisories]
    assert "CONDOR-20260707-001" in ids
    assert "CONDOR-20260707-002" in ids


def test_severity_lowercase(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    severities = {a.severity for a in advisories}
    assert "critical" in severities
    assert "high" in severities
    assert "CRITICAL" not in severities


def test_tier_d_no_collaborators(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert all(a.tier == VendorTier.D for a in advisories)


def test_source_is_condor(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert all(a.source == AdvisorySource.condor for a in advisories)


def test_notes_contain_title_and_owasp(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    notes_all = " ".join(a.notes for a in advisories)
    assert "ASI03" in notes_all
    assert "ASI01" in notes_all
    assert "Unauthenticated access" in notes_all


def test_notes_contain_target_url(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert all("localhost:3002" in a.notes for a in advisories)


def test_empty_report_returns_zero(test_db, no_npm, condor_empty_report):
    count = condor_sync(condor_empty_report)
    assert count == 0
    assert db.list_all() == []


def test_created_at_from_started_at(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert all(a.created_at == date(2026, 7, 7) for a in advisories)


def test_upsert_idempotent(test_db, no_npm, condor_flowise_report):
    condor_sync(condor_flowise_report)
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert len(advisories) == 2


def test_tier_d_despite_enterprise_downloads(test_db, npm_enterprise, condor_flowise_report):
    # No collaborators → always Tier D regardless of npm downloads
    condor_sync(condor_flowise_report)
    advisories = db.list_all()
    assert all(a.tier == VendorTier.D for a in advisories)
