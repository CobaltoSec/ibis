from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .core import register_finding
from .ghsa import GHSAError

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
    return register_finding(
        package=package,
        severity=severity,
        description=description,
        source=source,
        target_repo=target_repo,
        ecosystem=ecosystem,
    )


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
