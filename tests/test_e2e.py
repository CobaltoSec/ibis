"""
E2E pipeline tests — framework → register_finding → classify → GHSA → publish.

Covers:
  A. Corvus: register finding → advisory in DB → publish
  B. Shrike: existing GHSA → sync to DB → publish (no GHSA creation)
  C. Multiple findings from one Corvus scan → separate advisories
  D. Tier D → publish_by == created_at
  E. Publish already-published advisory is idempotent
  F. Cross-source same package → two separate advisories
"""
from __future__ import annotations
import subprocess
import pytest
from typer.testing import CliRunner
from ibis.cli import app
from ibis import db, ghsa, resolver
from ibis.core import register_finding
from ibis.models import AdvisoryState, AdvisorySource, VendorTier

runner = CliRunner()

GHSA_CORVUS = "GHSA-e2e-corvus-0001"
GHSA_SHRIKE = "GHSA-e2e-shrike-0001"


@pytest.fixture
def mock_ghsa_corvus(monkeypatch):
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: GHSA_CORVUS)


@pytest.fixture
def mock_resolver_no_repo(monkeypatch):
    monkeypatch.setattr(resolver, "resolve_repo", lambda *a, **kw: None)
    monkeypatch.setattr(resolver, "resolve_top_contributor", lambda r: None)


@pytest.fixture
def mock_resolver_with_collab(monkeypatch):
    monkeypatch.setattr(resolver, "resolve_repo", lambda *a, **kw: "letta-ai/letta")
    monkeypatch.setattr(resolver, "resolve_top_contributor", lambda r: "letta-maintainer")


@pytest.fixture
def mock_gh_publish(monkeypatch):
    class _Ok:
        returncode = 0
        stdout = '{"state": "published"}'
        stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _Ok())


# ── A: Corvus → register → publish ──────────────────────────────────────────

def test_corvus_pipeline_register_to_publish(
    test_db, no_npm, mock_ghsa_corvus, mock_resolver_no_repo, mock_gh_publish
):
    result = register_finding(
        package="glimind-mcp",
        severity="high",
        description="Prompt injection via tool response manipulation",
        source="corvus",
        ecosystem="mcp",
    )
    assert result["ghsa_id"] == GHSA_CORVUS
    assert result["tier"] == VendorTier.D.value  # no collaborator → Tier D

    advisory = db.get(GHSA_CORVUS)
    assert advisory.state == AdvisoryState.draft
    assert advisory.ecosystem == "mcp"
    assert advisory.source == AdvisorySource.corvus
    assert advisory.publish_by == advisory.created_at  # Tier D = immediate

    cli = runner.invoke(app, ["publish", GHSA_CORVUS, "--yes"])
    assert cli.exit_code == 0, cli.output
    assert db.get(GHSA_CORVUS).state == AdvisoryState.published


# ── B: Shrike existing GHSA → sync to DB → publish ──────────────────────────

def test_shrike_pipeline_existing_ghsa_to_publish(
    test_db, no_npm, mock_resolver_with_collab, mock_gh_publish, monkeypatch
):
    called = []
    monkeypatch.setattr(ghsa, "create_draft", lambda adv: called.append(adv) or "GHSA-unused")

    result = register_finding(
        package="letta",
        severity="critical",
        description="Arbitrary file write via path traversal",
        source="shrike",
        target_repo="letta-ai/letta",
        ecosystem="pip",
        ghsa_id=GHSA_SHRIKE,
    )
    assert called == []  # GHSA creation skipped — shrike already created it
    assert result["ghsa_id"] == GHSA_SHRIKE
    assert result["collaborator"] == "letta-maintainer"

    advisory = db.get(GHSA_SHRIKE)
    assert advisory.state == AdvisoryState.draft
    assert advisory.source == AdvisorySource.shrike
    assert "letta-maintainer" in advisory.collaborators

    cli = runner.invoke(app, ["publish", GHSA_SHRIKE, "--yes"])
    assert cli.exit_code == 0, cli.output
    assert db.get(GHSA_SHRIKE).state == AdvisoryState.published


# ── C: Multiple findings from one scan → separate advisories ────────────────

def test_corvus_multiple_findings_registered(
    test_db, no_npm, mock_resolver_no_repo, monkeypatch
):
    counter = [0]
    def _create(adv):
        counter[0] += 1
        return f"GHSA-multi-{counter[0]:04d}-xxxx"
    monkeypatch.setattr(ghsa, "create_draft", _create)

    for sev, desc in [("critical", "Prompt injection"), ("high", "Tool response manipulation")]:
        register_finding(
            package="glimind-mcp",
            severity=sev,
            description=desc,
            source="corvus",
            ecosystem="mcp",
        )

    all_advisories = db.list_all()
    assert len(all_advisories) == 2
    severities = {a.severity for a in all_advisories}
    assert severities == {"critical", "high"}


# ── D: Tier D → publish_by == created_at ────────────────────────────────────

def test_tier_d_publish_by_equals_created_at(
    test_db, no_npm, mock_ghsa_corvus, mock_resolver_no_repo
):
    result = register_finding(
        package="unknown-mcp-server",
        severity="high",
        description="No maintainer contact",
        source="corvus",
        ecosystem="mcp",
    )
    advisory = db.get(result["ghsa_id"])
    assert advisory.tier == VendorTier.D
    assert advisory.publish_by == advisory.created_at


# ── E: Publish already-published advisory exits cleanly ─────────────────────

def test_publish_already_published_idempotent(
    test_db, no_npm, mock_ghsa_corvus, mock_resolver_no_repo, mock_gh_publish
):
    register_finding(
        package="glimind-mcp",
        severity="high",
        description="Finding",
        source="corvus",
        ecosystem="mcp",
    )
    runner.invoke(app, ["publish", GHSA_CORVUS, "--yes"])
    cli = runner.invoke(app, ["publish", GHSA_CORVUS, "--yes"])
    assert cli.exit_code == 0
    assert "already published" in cli.output


# ── F: Cross-source same package → two separate advisories ──────────────────

def test_cross_source_same_package_two_advisories(
    test_db, no_npm, mock_resolver_no_repo, monkeypatch
):
    counter = [0]
    def _create(adv):
        counter[0] += 1
        return f"GHSA-cross-{counter[0]:04d}-xxxx"
    monkeypatch.setattr(ghsa, "create_draft", _create)

    register_finding(
        package="litellm", severity="high",
        description="Corvus: SSRF via proxy config",
        source="corvus", ecosystem="mcp",
    )
    register_finding(
        package="litellm", severity="critical",
        description="Shrike: arbitrary code execution",
        source="shrike", ecosystem="pip",
        ghsa_id="GHSA-shrike-litellm-0001",
    )

    advisories = db.list_all()
    assert len(advisories) == 2
    sources = {a.source.value for a in advisories}
    assert sources == {"corvus", "shrike"}
