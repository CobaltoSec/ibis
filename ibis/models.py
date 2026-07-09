from __future__ import annotations
from enum import Enum
from datetime import date
from typing import Optional
from pydantic import BaseModel


class VendorTier(str, Enum):
    A = "A"  # Enterprise / major OSS — 90d
    B = "B"  # Mid-tier startup / active maintainer — 45d
    C = "C"  # Long tail indie — 30d
    D = "D"  # No contact / removed — 21d


class AdvisorySource(str, Enum):
    corvus = "corvus"
    condor = "condor"
    shrike = "shrike"
    manual = "manual"


class AdvisoryState(str, Enum):
    draft = "draft"
    published = "published"
    withdrawn = "withdrawn"
    closed = "closed"


TIER_DAYS = {
    VendorTier.A: 90,
    VendorTier.B: 45,
    VendorTier.C: 30,
    VendorTier.D: 21,
}

TIER_LABELS = {
    VendorTier.A: "Enterprise / major OSS",
    VendorTier.B: "Mid-tier",
    VendorTier.C: "Long tail",
    VendorTier.D: "No contact",
}


class Advisory(BaseModel):
    ghsa_id: str
    package: str
    ecosystem: str = "npm"
    severity: str
    source: AdvisorySource = AdvisorySource.manual
    tier: VendorTier = VendorTier.C
    collaborators: list[str] = []
    collaborator_removed: bool = False
    created_at: date
    publish_by: date
    state: AdvisoryState = AdvisoryState.draft
    npm_downloads: Optional[int] = None
    notes: str = ""
