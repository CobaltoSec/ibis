from __future__ import annotations
from datetime import date
from ibis.tiers import classify, publish_deadline
from ibis.models import VendorTier


def test_no_collaborators_tier_d():
    assert classify("anything", []) == VendorTier.D


def test_collab_removed_tier_d():
    assert classify("anything", ["user"], collaborator_removed=True) == VendorTier.D


def test_enterprise_scope_microsoft():
    assert classify("@microsoft/teams-ai", ["user"]) == VendorTier.A


def test_enterprise_scope_anthropic():
    assert classify("@anthropic/sdk", ["user"]) == VendorTier.A


def test_enterprise_scope_google():
    assert classify("@google/generative-ai", ["user"]) == VendorTier.A


def test_enterprise_package_playwright_mcp():
    assert classify("playwright-mcp", ["user"]) == VendorTier.A


def test_enterprise_downloads_60k():
    assert classify("some-pkg", ["user"], npm_downloads=60_000) == VendorTier.A


def test_midtier_package_letta():
    assert classify("letta", ["user"]) == VendorTier.B


def test_midtier_package_nx_mcp():
    assert classify("nx-mcp", ["user"]) == VendorTier.B


def test_midtier_downloads_6k():
    assert classify("some-pkg", ["user"], npm_downloads=6_000) == VendorTier.B


def test_default_tier_c_unknown_package():
    assert classify("random-indie-package", ["user"], npm_downloads=100) == VendorTier.C


def test_default_tier_c_no_downloads():
    assert classify("random-indie-package", ["user"]) == VendorTier.C


def test_publish_deadline_tier_a():
    created = date(2026, 1, 1)
    assert publish_deadline(VendorTier.A, created) == date(2026, 4, 1)  # +90d


def test_publish_deadline_tier_b():
    created = date(2026, 1, 1)
    assert publish_deadline(VendorTier.B, created) == date(2026, 2, 15)  # +45d


def test_publish_deadline_tier_c():
    created = date(2026, 1, 1)
    assert publish_deadline(VendorTier.C, created) == date(2026, 1, 31)  # +30d


def test_publish_deadline_tier_d():
    created = date(2026, 1, 1)
    assert publish_deadline(VendorTier.D, created) == created  # immediate (0d)
