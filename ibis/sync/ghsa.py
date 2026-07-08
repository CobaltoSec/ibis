from __future__ import annotations
import subprocess
import json
from datetime import date, datetime
from rich.console import Console
from .. import db, tiers, npm
from ..models import Advisory, AdvisorySource, AdvisoryState, VendorTier

console = Console()

ADVISORY_REPO = "CobaltoSec/advisories"


def _gh_api(path: str) -> list | dict:
    result = subprocess.run(
        ["gh", "api", path, "--paginate"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed: {result.stderr}")
    return json.loads(result.stdout)


def _parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def sync(source: AdvisorySource = AdvisorySource.corvus, fetch_npm: bool = True) -> int:
    db.init_db()

    console.print(f"[cyan]Syncing GHSAs from {ADVISORY_REPO}...[/cyan]")

    data = _gh_api(f"orgs/CobaltoSec/security-advisories?per_page=100")
    if isinstance(data, dict):
        data = [data]

    imported = 0
    for item in data:
        ghsa_id = item.get("ghsa_id", "")
        if not ghsa_id:
            continue

        vulns = item.get("vulnerabilities", [])
        pkg = vulns[0]["package"]["name"] if vulns else "unknown"
        ecosystem = vulns[0]["package"]["ecosystem"] if vulns else "npm"
        severity = item.get("severity", "medium")
        state_raw = item.get("state", "draft")
        state = AdvisoryState.published if state_raw == "published" else AdvisoryState.draft

        collabs = [u["login"] for u in item.get("collaborating_users", [])]

        # Detect if collaborator was removed: check notes field in existing record
        existing = db.get(ghsa_id)
        collab_removed = False
        if existing:
            collab_removed = existing.collaborator_removed
            # If previously had collabs but now has none → mark removed
            if existing.collaborators and not collabs:
                collab_removed = True

        created_at = _parse_date(item.get("published_at") or item.get("created_at"))

        # Fetch npm downloads for tier classification
        dl = None
        if fetch_npm and ecosystem == "npm" and pkg != "unknown":
            dl = npm.get_weekly_downloads(pkg)
            if dl is not None:
                console.print(f"  [dim]{pkg}: {dl:,} dl/wk[/dim]")

        tier = tiers.classify(pkg, collabs, collab_removed, dl)
        publish_by = tiers.publish_deadline(tier, created_at)

        advisory = Advisory(
            ghsa_id=ghsa_id,
            package=pkg,
            ecosystem=ecosystem,
            severity=severity,
            source=source,
            tier=tier,
            collaborators=collabs,
            collaborator_removed=collab_removed,
            created_at=created_at,
            publish_by=publish_by,
            state=state,
            npm_downloads=dl,
        )
        db.upsert(advisory)
        imported += 1
        console.print(f"  [green]✓[/green] {ghsa_id} [{tier.value}] {pkg}")

    console.print(f"\n[bold green]Synced {imported} advisories.[/bold green]")
    return imported
