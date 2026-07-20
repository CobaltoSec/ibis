from __future__ import annotations
import json
import subprocess
from datetime import date
import pytest
from ibis import ghsa
from ibis.models import Advisory, AdvisorySource, AdvisoryState, VendorTier


def _advisory(collaborators=None, notes=""):
    return Advisory(
        ghsa_id="CONDOR-20260101-001",
        package="vuln-pkg",
        ecosystem="npm",
        severity="high",
        source=AdvisorySource.condor,
        tier=VendorTier.D,
        collaborators=collaborators or [],
        created_at=date(2026, 1, 1),
        publish_by=date(2026, 1, 1),
        state=AdvisoryState.draft,
        notes=notes,
    )


def _fake_run(ghsa_id="GHSA-test-0001-xxxx", returncode=0, stderr=""):
    response = json.dumps({"ghsa_id": ghsa_id, "state": "draft"}) if returncode == 0 else ""

    class FakeResult:
        pass

    r = FakeResult()
    r.returncode = returncode
    r.stdout = response
    r.stderr = stderr
    return r


def test_create_draft_returns_ghsa_id(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_run())
    result = ghsa.create_draft(_advisory())
    assert result == "GHSA-test-0001-xxxx"


def test_create_draft_payload_structure(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["input"] = kwargs.get("input", "")
        return _fake_run()

    monkeypatch.setattr(subprocess, "run", fake_run)
    ghsa.create_draft(_advisory())

    payload = json.loads(captured["input"])
    assert "vulnerability in vuln-pkg" in payload["summary"]
    assert payload["severity"] == "high"
    vulns = payload["vulnerabilities"]
    assert len(vulns) == 1
    assert vulns[0]["package"]["name"] == "vuln-pkg"
    assert vulns[0]["package"]["ecosystem"] == "npm"
    assert ">= 0.0.1" in vulns[0]["vulnerable_version_range"]


def test_create_draft_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: _fake_run(returncode=1, stderr="HTTP 422")
    )
    with pytest.raises(ghsa.GHSAError, match="HTTP 422"):
        ghsa.create_draft(_advisory())


def test_create_draft_raises_on_missing_ghsa_id(monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = json.dumps({"state": "draft"})  # sin ghsa_id
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    with pytest.raises(ghsa.GHSAError, match="ghsa_id"):
        ghsa.create_draft(_advisory())


def test_create_draft_includes_collaborators(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["input"] = kwargs.get("input", "")
        return _fake_run()

    monkeypatch.setattr(subprocess, "run", fake_run)
    ghsa.create_draft(_advisory(collaborators=["maintainerA"]))

    payload = json.loads(captured["input"])
    assert payload.get("collaborating_users") == ["maintainerA"]
