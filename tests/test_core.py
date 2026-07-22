from __future__ import annotations
import pytest
from ibis import db, ghsa, resolver
from ibis.core import register_finding
from ibis.models import VendorTier


REAL_GHSA = "GHSA-core-test-xxxx"


@pytest.fixture
def mock_ghsa_create(monkeypatch):
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: REAL_GHSA)


@pytest.fixture
def mock_resolver_no_repo(monkeypatch):
    monkeypatch.setattr(resolver, "resolve_repo", lambda *a, **kw: None)
    monkeypatch.setattr(resolver, "resolve_top_contributor", lambda r: None)


@pytest.fixture
def mock_resolver_with_collab(monkeypatch):
    monkeypatch.setattr(resolver, "resolve_repo", lambda *a, **kw: "letta-ai/letta")
    monkeypatch.setattr(resolver, "resolve_top_contributor", lambda r: "letta-maintainer")


def test_register_finding_direct_call(test_db, no_npm, mock_ghsa_create, mock_resolver_no_repo):
    result = register_finding(
        package="letta",
        severity="high",
        description="SSRF via proxy",
        source="shrike",
    )
    assert result["ghsa_id"] == REAL_GHSA
    assert "tier" in result
    assert "publish_by" in result
    found = db.get(REAL_GHSA)
    assert found is not None
    assert found.package == "letta"


def test_register_finding_with_ghsa_id_skips_create_draft(test_db, no_npm, mock_resolver_no_repo, monkeypatch):
    """When ghsa_id is provided, create_draft must NOT be called."""
    called = []
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: called.append(adv) or "GHSA-unused")
    result = register_finding(
        package="letta",
        severity="high",
        description="Arbitrary file write",
        source="shrike",
        ghsa_id="GHSA-shrike-1234-abcd",
    )
    assert called == []
    assert result["ghsa_id"] == "GHSA-shrike-1234-abcd"


def test_register_finding_with_ghsa_id_saves_to_db(test_db, no_npm, mock_resolver_no_repo, monkeypatch):
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: "GHSA-unused")
    register_finding(
        package="litellm",
        severity="critical",
        description="RCE via eval",
        source="shrike",
        ecosystem="pip",
        ghsa_id="GHSA-shrike-crit-5678",
    )
    found = db.get("GHSA-shrike-crit-5678")
    assert found is not None
    assert found.source.value == "shrike"
    assert found.severity == "critical"
    assert found.ecosystem == "pip"


def test_register_finding_with_ghsa_id_classifies_tier(test_db, no_npm, mock_resolver_with_collab, monkeypatch):
    """Even with existing ghsa_id, tier classification still runs."""
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: "GHSA-unused")
    result = register_finding(
        package="letta",
        severity="high",
        description="Path traversal",
        source="shrike",
        ghsa_id="GHSA-shrike-tier-0001",
    )
    # Has collaborator → should be classified (not automatically Tier D)
    assert result["collaborator"] == "letta-maintainer"
    found = db.get("GHSA-shrike-tier-0001")
    assert "letta-maintainer" in found.collaborators


def test_register_finding_with_ghsa_id_upserts_idempotent(test_db, no_npm, mock_resolver_no_repo, monkeypatch):
    """Calling register_finding twice with same ghsa_id upserts (no error)."""
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: "GHSA-unused")
    for _ in range(2):
        register_finding(
            package="flowise",
            severity="high",
            description="XSS",
            source="shrike",
            ghsa_id="GHSA-shrike-dupe-0001",
        )
    assert len([a for a in db.list_all() if a.ghsa_id == "GHSA-shrike-dupe-0001"]) == 1
