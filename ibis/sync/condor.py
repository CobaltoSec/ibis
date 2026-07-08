from __future__ import annotations
import json
from pathlib import Path
from datetime import date, datetime
from rich.console import Console
from .. import db, tiers, npm
from ..models import Advisory, AdvisorySource, AdvisoryState

console = Console()


def _parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def sync(report_path: Path, fetch_npm: bool = True) -> int:
    db.init_db()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    platform = report.get("platform", "unknown")
    target = report.get("target", "")
    findings = report.get("findings", [])
    created_at = _parse_date(report.get("started_at"))
    scan_date = created_at.strftime("%Y%m%d")

    console.print(f"[cyan]Importing {len(findings)} Condor finding(s) from {report_path.name}...[/cyan]")

    dl = None
    if fetch_npm and platform != "unknown":
        dl = npm.get_weekly_downloads(platform)
        if dl is not None:
            console.print(f"  [dim]{platform}: {dl:,} dl/wk[/dim]")

    imported = 0
    for i, finding in enumerate(findings, 1):
        ghsa_id = f"CONDOR-{scan_date}-{i:03d}"
        severity = finding.get("severity", "medium").lower()
        title = finding.get("title", "")
        owasp_id = finding.get("owasp_id", "")

        tier = tiers.classify(platform, [], False, dl)
        publish_by = tiers.publish_deadline(tier, created_at)

        advisory = Advisory(
            ghsa_id=ghsa_id,
            package=platform,
            ecosystem="npm",
            severity=severity,
            source=AdvisorySource.condor,
            tier=tier,
            collaborators=[],
            collaborator_removed=False,
            created_at=created_at,
            publish_by=publish_by,
            state=AdvisoryState.draft,
            notes=f"{title} [{owasp_id}] @ {target}",
        )
        db.upsert(advisory)
        imported += 1
        console.print(f"  [green]✓[/green] {ghsa_id} [{tier.value}] {severity} — {title[:60]}")

    console.print(f"\n[bold green]Imported {imported} Condor finding(s).[/bold green]")
    return imported
