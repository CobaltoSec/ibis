from __future__ import annotations
import pytest
from typer.testing import CliRunner
from ibis.cli import app
from ibis import db
from ibis.models import AdvisorySource, VendorTier

runner = CliRunner()


def test_add_with_ghsa(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-xxxx-yyyy-zzzz",
        "--package", "lodash", "--severity", "high", "--source", "corvus",
    ])
    assert result.exit_code == 0, result.output
    advisory = db.get("GHSA-xxxx-yyyy-zzzz")
    assert advisory is not None
    assert advisory.package == "lodash"
    assert advisory.severity == "high"


def test_add_without_ghsa_generates_id(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--package", "some-pkg", "--severity", "medium", "--source", "shrike",
    ])
    assert result.exit_code == 0, result.output
    advisories = db.list_all()
    assert len(advisories) == 1
    assert advisories[0].ghsa_id.startswith("SHRIKE-")


def test_add_source_corvus(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-aaaa-bbbb-cccc",
        "--package", "pkg", "--severity", "low", "--source", "corvus",
    ])
    assert result.exit_code == 0, result.output
    assert db.get("GHSA-aaaa-bbbb-cccc").source == AdvisorySource.corvus


def test_add_source_shrike(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-1111-2222-3333",
        "--package", "pkg", "--severity", "critical", "--source", "shrike",
    ])
    assert result.exit_code == 0, result.output
    assert db.get("GHSA-1111-2222-3333").source == AdvisorySource.shrike


def test_add_explicit_tier_a(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-tier-aaaa-test",
        "--package", "some-pkg", "--severity", "high", "--source", "manual", "--tier", "A",
    ])
    assert result.exit_code == 0, result.output
    advisory = db.get("GHSA-tier-aaaa-test")
    assert advisory.tier == VendorTier.A


def test_add_no_collaborators_tier_d_despite_downloads(test_db, npm_enterprise):
    # No collaborators → always Tier D (no contact), regardless of npm downloads
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-npm-auto-tier",
        "--package", "popular-pkg", "--severity", "high", "--source", "manual",
    ])
    assert result.exit_code == 0, result.output
    advisory = db.get("GHSA-npm-auto-tier")
    assert advisory.tier == VendorTier.D


def test_add_prints_id(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-print-test-xxxx",
        "--package", "pkg", "--severity", "medium", "--source", "condor",
    ])
    assert "GHSA-print-test-xxxx" in result.output


def test_add_invalid_source(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--package", "pkg", "--severity", "high", "--source", "invalid",
    ])
    assert result.exit_code == 1


def test_add_invalid_tier(test_db, no_npm):
    result = runner.invoke(app, [
        "add", "--ghsa", "GHSA-test-tier-fail",
        "--package", "pkg", "--severity", "high", "--source", "manual", "--tier", "Z",
    ])
    assert result.exit_code == 1


def test_add_severity_stored_lowercase(test_db, no_npm):
    runner.invoke(app, [
        "add", "--ghsa", "GHSA-case-test-xxxx",
        "--package", "pkg", "--severity", "HIGH", "--source", "manual",
    ])
    advisory = db.get("GHSA-case-test-xxxx")
    assert advisory.severity == "high"
