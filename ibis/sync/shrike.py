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
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        return date.today()


def sync(findings_dir: Path, fetch_npm: bool = True) -> int:
    db.init_db()

    json_files = sorted(findings_dir.glob("*.json"))
    console.print(
        f"[cyan]Importing Shrike findings from {findings_dir} ({len(json_files)} file(s))...[/cyan]"
    )

    imported = 0
    for json_file in json_files:
        try:
            finding = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"  [yellow]⚠ Skip {json_file.name}: {e}[/yellow]")
            continue

        ghsa_id = finding.get("ghsa_id") or f"SHRIKE-{json_file.stem}"
        package = finding.get("target", "unknown")
        severity = finding.get("severity", "medium").lower()

        collab = finding.get("collaborator_notified")
        collaborators = [collab] if collab else []

        created_at = _parse_date(finding.get("submitted_at"))

        dl = None
        if fetch_npm and package != "unknown":
            dl = npm.get_weekly_downloads(package)

        tier = tiers.classify(package, collaborators, False, dl)
        publish_by = tiers.publish_deadline(tier, created_at)

        advisory = Advisory(
            ghsa_id=ghsa_id,
            package=package,
            ecosystem="npm",
            severity=severity,
            source=AdvisorySource.shrike,
            tier=tier,
            collaborators=collaborators,
            collaborator_removed=False,
            created_at=created_at,
            publish_by=publish_by,
            state=AdvisoryState.draft,
            notes=finding.get("title", ""),
        )
        db.upsert(advisory)
        imported += 1
        console.print(f"  [green]✓[/green] {ghsa_id} [{tier.value}] {severity} — {package}")

    console.print(f"\n[bold green]Imported {imported} Shrike finding(s).[/bold green]")
    return imported
