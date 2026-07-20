from __future__ import annotations
import pytest
from ibis import db, server, ghsa, resolver
from ibis.models import VendorTier


REAL_GHSA = "GHSA-reg0-find-xxxx"


@pytest.fixture
def mock_ghsa_create(monkeypatch):
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: REAL_GHSA)


@pytest.fixture
def mock_ghsa_error(monkeypatch):
    def _raise(adv):
        raise ghsa.GHSAError("GitHub API error")
    monkeypatch.setattr(ghsa, "create_draft", _raise)


@pytest.fixture
def mock_resolver_no_repo(monkeypatch):
    monkeypatch.setattr(resolver, "resolve_repo", lambda *a, **kw: None)
    monkeypatch.setattr(resolver, "resolve_top_contributor", lambda r: None)


@pytest.fixture
def mock_resolver_with_collab(monkeypatch):
    monkeypatch.setattr(resolver, "resolve_repo", lambda *a, **kw: "FlowiseAI/Flowise")
    monkeypatch.setattr(resolver, "resolve_top_contributor", lambda r: "flowise-maintainer")


def test_register_finding_saves_to_db(test_db, no_npm, mock_ghsa_create, mock_resolver_no_repo):
    server.ibis_register_finding(
        package="vuln-pkg",
        severity="high",
        description="RCE via eval",
        source="condor",
    )
    found = db.get(REAL_GHSA)
    assert found is not None
    assert found.package == "vuln-pkg"
    assert found.severity == "high"


def test_register_finding_returns_correct_fields(test_db, no_npm, mock_ghsa_create, mock_resolver_no_repo):
    result = server.ibis_register_finding(
        package="vuln-pkg",
        severity="medium",
        description="SSRF in proxy handler",
        source="shrike",
    )
    assert result["ghsa_id"] == REAL_GHSA
    assert "tier" in result
    assert "publish_by" in result


def test_register_finding_no_repo_gives_tier_d(test_db, no_npm, mock_ghsa_create, mock_resolver_no_repo):
    result = server.ibis_register_finding(
        package="unknown-pkg",
        severity="high",
        description="Path traversal",
        source="condor",
    )
    assert result["tier"] == VendorTier.D.value
    assert result["collaborator"] is None


def test_register_finding_with_collaborator(test_db, no_npm, mock_ghsa_create, mock_resolver_with_collab):
    result = server.ibis_register_finding(
        package="flowise",
        severity="critical",
        description="Arbitrary file write",
        source="shrike",
        target_repo="FlowiseAI/Flowise",
    )
    assert result["collaborator"] == "flowise-maintainer"
    found = db.get(REAL_GHSA)
    assert "flowise-maintainer" in found.collaborators


def test_register_finding_ghsa_error_does_not_pollute_db(test_db, no_npm, mock_ghsa_error, mock_resolver_no_repo):
    with pytest.raises(ghsa.GHSAError):
        server.ibis_register_finding(
            package="vuln-pkg",
            severity="high",
            description="SSRF",
            source="condor",
        )
    assert db.list_all() == []
