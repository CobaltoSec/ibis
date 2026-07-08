from __future__ import annotations
from datetime import date
import pytest
from typer.testing import CliRunner
from ibis.cli import app
from ibis import db
from ibis.models import Advisory, AdvisorySource, AdvisoryState, VendorTier
from ibis.tiers import publish_deadline

runner = CliRunner()


def _advisory(ghsa_id: str = "GHSA-test-0001", package: str = "test-pkg",
               tier: VendorTier = VendorTier.C) -> Advisory:
    today = date.today()
    return Advisory(
        ghsa_id=ghsa_id,
        package=package,
        ecosystem="npm",
        severity="medium",
        source=AdvisorySource.manual,
        tier=tier,
        collaborators=[],
        created_at=today,
        publish_by=publish_deadline(tier, today),
        state=AdvisoryState.draft,
    )


# ── DB layer ─────────────────────────────────────────────────────────────────

def test_list_uncurated_filters(test_db):
    db.upsert(_advisory("GHSA-0001"))
    db.upsert(_advisory("GHSA-0002"))
    db.update_curated("GHSA-0001", True)

    result = db.list_uncurated()
    assert len(result) == 1
    assert result[0].ghsa_id == "GHSA-0002"


def test_update_curated(test_db):
    db.upsert(_advisory("GHSA-0001"))
    db.update_curated("GHSA-0001", True)

    # verify via list_uncurated (curated ones are excluded)
    assert db.list_uncurated() == []


def test_update_tier(test_db):
    a = _advisory("GHSA-0001", tier=VendorTier.C)
    db.upsert(a)
    new_deadline = publish_deadline(VendorTier.B, a.created_at)
    db.update_tier("GHSA-0001", VendorTier.B, new_deadline)

    updated = db.get("GHSA-0001")
    assert updated.tier == VendorTier.B
    assert updated.publish_by == new_deadline


# ── CLI: nothing to curate ───────────────────────────────────────────────────

def test_curate_nothing(test_db, no_npm):
    result = runner.invoke(app, ["curate"])
    assert result.exit_code == 0
    assert "Nothing to curate" in result.output


# ── CLI: keep ────────────────────────────────────────────────────────────────

def test_curate_keep(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))

    result = runner.invoke(app, ["curate"], input="k\n")
    assert result.exit_code == 0
    assert "GHSA-0001" in result.output
    assert "Curated 1/1" in result.output
    assert db.list_uncurated() == []


# ── CLI: change tier ─────────────────────────────────────────────────────────

def test_curate_tier_change(test_db, no_npm):
    a = _advisory("GHSA-0001", tier=VendorTier.C)
    db.upsert(a)

    result = runner.invoke(app, ["curate"], input="t B\n")
    assert result.exit_code == 0
    assert "Tier" in result.output
    assert "Curated 1/1" in result.output

    updated = db.get("GHSA-0001")
    assert updated.tier == VendorTier.B
    assert updated.publish_by == publish_deadline(VendorTier.B, a.created_at)
    assert db.list_uncurated() == []


def test_curate_tier_nospace(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001", tier=VendorTier.C))
    result = runner.invoke(app, ["curate"], input="tA\n")
    assert result.exit_code == 0
    assert db.get("GHSA-0001").tier == VendorTier.A


def test_curate_tier_invalid_then_keep(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))
    result = runner.invoke(app, ["curate"], input="t Z\nk\n")
    assert result.exit_code == 0
    assert "Invalid tier" in result.output
    assert db.get("GHSA-0001").tier == VendorTier.C  # unchanged


# ── CLI: note then keep ───────────────────────────────────────────────────────

def test_curate_note_then_keep(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))
    result = runner.invoke(app, ["curate"], input="n Found via manual review\nk\n")
    assert result.exit_code == 0
    assert "Note saved" in result.output

    updated = db.get("GHSA-0001")
    assert updated.notes == "Found via manual review"
    assert db.list_uncurated() == []


def test_curate_note_empty(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))
    result = runner.invoke(app, ["curate"], input="n\nk\n")
    assert result.exit_code == 0
    assert "Usage: n" in result.output


# ── CLI: skip ────────────────────────────────────────────────────────────────

def test_curate_skip(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))
    result = runner.invoke(app, ["curate"], input="s\n")
    assert result.exit_code == 0
    assert "Skipped 1" in result.output
    assert len(db.list_uncurated()) == 1  # still uncurated


# ── CLI: quit early ───────────────────────────────────────────────────────────

def test_curate_quit_early(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))
    db.upsert(_advisory("GHSA-0002"))
    db.upsert(_advisory("GHSA-0003"))

    result = runner.invoke(app, ["curate"], input="k\nq\n")
    assert result.exit_code == 0
    assert "Curated 1" in result.output
    assert len(db.list_uncurated()) == 2  # 2 not curated


# ── CLI: --all flag ──────────────────────────────────────────────────────────

def test_curate_all_includes_curated(test_db, no_npm):
    db.upsert(_advisory("GHSA-0001"))
    db.upsert(_advisory("GHSA-0002"))
    db.update_curated("GHSA-0001", True)

    # --all should show both
    result = runner.invoke(app, ["curate", "--all"], input="k\nk\n")
    assert result.exit_code == 0
    assert "2/2" in result.output
