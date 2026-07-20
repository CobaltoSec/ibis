from __future__ import annotations
import json
import subprocess
import pytest
from datetime import date
from typer.testing import CliRunner
from ibis.cli import app
from ibis import db
from ibis.models import Advisory, AdvisorySource, AdvisoryState, VendorTier

runner = CliRunner()

CONDOR_ID = "CONDOR-20260101-001"
REAL_GHSA = "GHSA-new0-real-ghsa"


def _make_advisory(ghsa_id=CONDOR_ID, source=AdvisorySource.condor, collaborators=None, notes=""):
    return Advisory(
        ghsa_id=ghsa_id,
        package="vuln-pkg",
        ecosystem="npm",
        severity="high",
        source=source,
        tier=VendorTier.D,
        collaborators=collaborators or [],
        created_at=date(2026, 1, 1),
        publish_by=date(2026, 1, 1),
        state=AdvisoryState.draft,
        notes=notes,
    )


@pytest.fixture
def mock_gh_create(monkeypatch):
    response = json.dumps({"ghsa_id": REAL_GHSA, "state": "draft"})

    class FakeResult:
        returncode = 0
        stdout = response
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult())


@pytest.fixture
def mock_gh_create_error(monkeypatch):
    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "HTTP 422: Unprocessable Entity"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult())


def test_rename_ghsa(test_db):
    db.upsert(_make_advisory())
    db.rename_ghsa(CONDOR_ID, REAL_GHSA)
    assert db.get(CONDOR_ID) is None
    found = db.get(REAL_GHSA)
    assert found is not None
    assert found.package == "vuln-pkg"
    assert found.severity == "high"


def test_rename_ghsa_preserves_all_fields(test_db):
    adv = _make_advisory(notes="RCE via upload", collaborators=["maintainer"])
    db.upsert(adv)
    db.rename_ghsa(CONDOR_ID, REAL_GHSA)
    found = db.get(REAL_GHSA)
    assert found.notes == "RCE via upload"
    assert found.collaborators == ["maintainer"]


def test_create_ghsa_happy_path(test_db, mock_gh_create):
    db.upsert(_make_advisory())
    result = runner.invoke(app, ["create-ghsa", CONDOR_ID, "--yes"])
    assert result.exit_code == 0, result.output
    assert REAL_GHSA in result.output
    assert db.get(CONDOR_ID) is None
    assert db.get(REAL_GHSA) is not None


def test_create_ghsa_not_found(test_db, mock_gh_create):
    result = runner.invoke(app, ["create-ghsa", "CONDOR-notexist-000", "--yes"])
    assert result.exit_code == 1


def test_create_ghsa_rejects_real_ghsa_id(test_db, mock_gh_create):
    db.upsert(_make_advisory("GHSA-real-xxxx-yyyy"))
    result = runner.invoke(app, ["create-ghsa", "GHSA-real-xxxx-yyyy", "--yes"])
    assert result.exit_code == 1
    assert "synthetic" in result.output.lower() or "prefix" in result.output.lower()


def test_create_ghsa_api_error_leaves_db_unchanged(test_db, mock_gh_create_error):
    db.upsert(_make_advisory())
    result = runner.invoke(app, ["create-ghsa", CONDOR_ID, "--yes"])
    assert result.exit_code == 1
    assert db.get(CONDOR_ID) is not None


def test_create_ghsa_shrike_id(test_db, mock_gh_create):
    db.upsert(_make_advisory("SHRIKE-vuln-pkg", source=AdvisorySource.shrike))
    result = runner.invoke(app, ["create-ghsa", "SHRIKE-vuln-pkg", "--yes"])
    assert result.exit_code == 0, result.output
    assert db.get("SHRIKE-vuln-pkg") is None
    assert db.get(REAL_GHSA) is not None


def test_create_ghsa_source_id(test_db, mock_gh_create):
    db.upsert(_make_advisory("SOURCE-abc12345"))
    result = runner.invoke(app, ["create-ghsa", "SOURCE-abc12345", "--yes"])
    assert result.exit_code == 0, result.output
    assert db.get(REAL_GHSA) is not None


def test_create_ghsa_with_collaborators(test_db, mock_gh_create):
    db.upsert(_make_advisory(collaborators=["testmaintainer"]))
    result = runner.invoke(app, ["create-ghsa", CONDOR_ID, "--yes"])
    assert result.exit_code == 0, result.output


def test_create_ghsa_shows_notes_in_preview(test_db, mock_gh_create):
    db.upsert(_make_advisory(notes="Arbitrary file write via upload handler"))
    result = runner.invoke(app, ["create-ghsa", CONDOR_ID, "--yes"])
    assert result.exit_code == 0, result.output
    assert "Arbitrary file write" in result.output
