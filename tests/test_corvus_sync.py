from __future__ import annotations
from datetime import date
from ibis import db
from ibis.sync.corvus import sync_curated, sync_report
from ibis.models import AdvisorySource, AdvisoryState


# --- sync_curated (findings-curated-cs*.md) ---

def test_curated_imports_two_findings(test_db, no_npm, corvus_curated_md):
    count = sync_curated(corvus_curated_md)
    assert count == 2


def test_curated_uses_real_ghsa_ids(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    ids = {a.ghsa_id for a in advisories}
    assert "GHSA-7rqv-4g54-hcxh" in ids
    assert "GHSA-j62x-hg79-www6" in ids


def test_curated_severity_lowercase(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    severities = {a.severity for a in advisories}
    assert "critical" in severities
    assert "high" in severities
    assert "CRITICAL" not in severities


def test_curated_source_is_corvus(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    assert all(a.source == AdvisorySource.corvus for a in advisories)


def test_curated_state_is_draft(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    assert all(a.state == AdvisoryState.draft for a in advisories)


def test_curated_ecosystem_is_mcp(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    assert all(a.ecosystem == "mcp" for a in advisories)


def test_curated_extracts_package_from_service_line(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    packages = {a.package for a in advisories}
    # F01: **Service:** ... `glimind-oracle` ...
    assert "glimind-oracle" in packages


def test_curated_date_from_header(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    advisories = db.list_all()
    assert all(a.created_at == date(2026, 7, 20) for a in advisories)


def test_curated_idempotent(test_db, no_npm, corvus_curated_md):
    sync_curated(corvus_curated_md)
    sync_curated(corvus_curated_md)
    assert len(db.list_all()) == 2


# --- sync_report (raw report.json) ---

def test_report_imports_critical_and_high(test_db, no_npm, corvus_report_json):
    count = sync_report(corvus_report_json)
    assert count == 2  # critical + high; low is below default threshold


def test_report_synthetic_id_format(test_db, no_npm, corvus_report_json):
    sync_report(corvus_report_json)
    advisories = db.list_all()
    for a in advisories:
        assert a.ghsa_id.startswith("CORVUS-")


def test_report_package_from_url(test_db, no_npm, corvus_report_json):
    sync_report(corvus_report_json)
    advisories = db.list_all()
    assert all("glimind.com" in a.package for a in advisories)


def test_report_source_is_corvus(test_db, no_npm, corvus_report_json):
    sync_report(corvus_report_json)
    advisories = db.list_all()
    assert all(a.source == AdvisorySource.corvus for a in advisories)


def test_report_filters_by_confidence(test_db, no_npm, corvus_report_json):
    # min_confidence=90 → only the ssrf finding (confidence=95)
    count = sync_report(corvus_report_json, min_confidence=90)
    assert count == 1


def test_report_idempotent(test_db, no_npm, corvus_report_json):
    sync_report(corvus_report_json)
    sync_report(corvus_report_json)
    assert len(db.list_all()) == 2
