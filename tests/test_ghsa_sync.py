from __future__ import annotations
import json
import subprocess
import pytest
from ibis import db
from ibis.sync.ghsa import sync as ghsa_sync
from ibis.models import AdvisorySource, AdvisoryState, VendorTier


def _make_ghsa(ghsa_id, package, severity="high", state="draft", collaborators=None, ecosystem="npm"):
    return {
        "ghsa_id": ghsa_id,
        "severity": severity,
        "state": state,
        "published_at": "2026-01-01T00:00:00Z",
        "vulnerabilities": [{"package": {"name": package, "ecosystem": ecosystem}}],
        "collaborating_users": [{"login": u} for u in (collaborators or [])],
    }


def _patch_gh(monkeypatch, payload):
    class FakeResult:
        returncode = 0
        stdout = json.dumps(payload)
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult())


def test_sync_imports_advisories(test_db, no_npm, monkeypatch):
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-aaaa-1111-xxxx", "@microsoft/teams-ai", collaborators=["testuser"])])
    count = ghsa_sync(fetch_npm=False)
    assert count == 1
    advisory = db.get("GHSA-aaaa-1111-xxxx")
    assert advisory is not None
    assert advisory.source == AdvisorySource.corvus


def test_detects_collab_removal(test_db, no_npm, monkeypatch):
    # First sync: has collaborator
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-bbbb-2222-yyyy", "some-pkg", collaborators=["alice"])])
    ghsa_sync(fetch_npm=False)
    assert db.get("GHSA-bbbb-2222-yyyy").collaborators == ["alice"]

    # Second sync: collaborator gone
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-bbbb-2222-yyyy", "some-pkg", collaborators=[])])
    ghsa_sync(fetch_npm=False)

    advisory = db.get("GHSA-bbbb-2222-yyyy")
    assert advisory.collaborator_removed is True
    assert advisory.tier == VendorTier.D


def test_preserves_notes_on_upsert(test_db, no_npm, monkeypatch):
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-cccc-3333-zzzz", "some-pkg", collaborators=["bob"])])
    ghsa_sync(fetch_npm=False)
    db.update_notes("GHSA-cccc-3333-zzzz", "Important note")

    ghsa_sync(fetch_npm=False)
    advisory = db.get("GHSA-cccc-3333-zzzz")
    assert advisory.notes == "Important note"


def test_tier_a_enterprise_scope(test_db, no_npm, monkeypatch):
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-dddd-4444-aaaa", "@microsoft/teams-ai", collaborators=["user"])])
    ghsa_sync(fetch_npm=False)
    assert db.get("GHSA-dddd-4444-aaaa").tier == VendorTier.A


def test_tier_a_high_downloads(test_db, npm_enterprise, monkeypatch):
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-eeee-5555-bbbb", "popular-lib", collaborators=["user"])])
    ghsa_sync(fetch_npm=True)
    assert db.get("GHSA-eeee-5555-bbbb").tier == VendorTier.A


def test_published_state(test_db, no_npm, monkeypatch):
    _patch_gh(monkeypatch, [_make_ghsa("GHSA-ffff-6666-cccc", "some-pkg", state="published", collaborators=["user"])])
    ghsa_sync(fetch_npm=False)
    assert db.get("GHSA-ffff-6666-cccc").state == AdvisoryState.published
