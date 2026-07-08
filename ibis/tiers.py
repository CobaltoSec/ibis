from __future__ import annotations
from datetime import date, timedelta
from .models import VendorTier, TIER_DAYS

# Packages / scopes from major organizations → Tier A
ENTERPRISE_SCOPES = {
    "@microsoft", "@azure", "@google", "@anthropic", "@aws", "@amazon",
    "@notionhq", "@heroku", "@sap-ux", "@sap", "@atlassian", "@mozilla",
    "@docker", "@elastic", "@hashicorp", "@grafana", "@mongodb", "@redis",
    "@kubeflow", "@langchain", "@upstash",
}

# Unscoped packages with known enterprise backing → Tier A
ENTERPRISE_PACKAGES = {
    "playwright-mcp", "markitdown-mcp", "autogen", "kubeflow-pipelines",
    "mcp-server-sqlite", "server-everything",
}

# Known mid-tier: VC-backed startups, established OSS → Tier B
MIDTIER_PACKAGES = {
    "letta", "nx-mcp", "llama_index", "langsmith-mcp-server",
    "milvus", "vanna", "lobe-chat", "MaxKB", "DocsGPT",
    "cheshire-cat-ai", "kotaemon", "superagi",
    "@agent-infra/mcp-server-browser", "@browserbasehq/mcp",
    "@pulsemcp/pulse-fetch", "@get-technology-inc/jamf-docs-mcp-server",
    "european-parliament-mcp-server",
}

# Download thresholds (weekly npm)
ENTERPRISE_DL_THRESHOLD = 50_000
MIDTIER_DL_THRESHOLD = 5_000


def classify(
    package: str,
    collaborators: list[str],
    collaborator_removed: bool = False,
    npm_downloads: int | None = None,
) -> VendorTier:
    # Tier D: no contact at all
    if not collaborators or collaborator_removed:
        return VendorTier.D

    pkg_clean = package.lstrip("@").split("/")[0] if "/" in package else package

    # Tier A: enterprise scope or known package
    scope = f"@{package.split('/')[0].lstrip('@')}" if package.startswith("@") else None
    if scope and scope in ENTERPRISE_SCOPES:
        return VendorTier.A
    if package in ENTERPRISE_PACKAGES or pkg_clean in ENTERPRISE_PACKAGES:
        return VendorTier.A
    if npm_downloads and npm_downloads >= ENTERPRISE_DL_THRESHOLD:
        return VendorTier.A

    # Tier B: mid-tier or high downloads
    if package in MIDTIER_PACKAGES or pkg_clean in MIDTIER_PACKAGES:
        return VendorTier.B
    if npm_downloads and npm_downloads >= MIDTIER_DL_THRESHOLD:
        return VendorTier.B

    return VendorTier.C


def publish_deadline(tier: VendorTier, created_at: date) -> date:
    return created_at + timedelta(days=TIER_DAYS[tier])
