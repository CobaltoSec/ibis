from __future__ import annotations
import uuid
from datetime import date

from mcp.server.fastmcp import FastMCP

from . import db, tiers, npm, ghsa, resolver
from .ghsa import GHSAError
from .models import Advisory, AdvisorySource, AdvisoryState

mcp = FastMCP("ibis")


@mcp.tool()
def ibis_register_finding(
    package: str,
    severity: str,
    description: str,
    source: str,
    target_repo: str | None = None,
    ecosystem: str = "npm",
) -> dict:
    """
    Register a finding from Corvus/Condor/Shrike.
    Classifies tier, creates GHSA draft in CobaltoSec/advisories, saves to DB.
    Returns ghsa_id, tier, publish_by, collaborator, repo.
    """
    db.init_db()

    try:
        source_enum = AdvisorySource(source)
    except ValueError:
        raise ValueError(f"Invalid source: {source!r}. Valid: corvus, condor, shrike, manual")

    repo = resolver.resolve_repo(package, explicit=target_repo)
    collaborator = resolver.resolve_top_contributor(repo) if repo else None
    collaborators = [collaborator] if collaborator else []

    dl = npm.get_weekly_downloads(package) if ecosystem == "npm" else None
    tier = tiers.classify(package, collaborators, False, dl)
    today = date.today()
    publish_by = tiers.publish_deadline(tier, today)

    advisory = Advisory(
        ghsa_id=f"{source.upper()}-{uuid.uuid4().hex[:8]}",
        package=package,
        ecosystem=ecosystem,
        severity=severity.lower(),
        source=source_enum,
        tier=tier,
        collaborators=collaborators,
        created_at=today,
        publish_by=publish_by,
        state=AdvisoryState.draft,
        notes=description,
    )

    real_ghsa = ghsa.create_draft(advisory)
    advisory = advisory.model_copy(update={"ghsa_id": real_ghsa})
    db.upsert(advisory)

    return {
        "ghsa_id": real_ghsa,
        "tier": tier.value,
        "publish_by": publish_by.isoformat(),
        "collaborator": collaborator,
        "repo": repo,
    }


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
