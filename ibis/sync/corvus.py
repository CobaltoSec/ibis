from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlparse
from rich.console import Console
from .. import db, tiers
from ..models import Advisory, AdvisorySource, AdvisoryState

console = Console()

# Matches: ### F01 — GHSA-7rqv-4g54-hcxh — CRITICAL — Title text here
# Handles em-dash (—) and regular dash (-) as separators
_HEADING_RE = re.compile(
    r"^###\s+F\d+\s+[—\-]+\s+(GHSA-[\w-]+)\s+[—\-]+\s+(CRITICAL|HIGH|MEDIUM|LOW)\s+[—\-]+\s+(.+)$",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\*\*Date:\*\*\s+(\d{4}-\d{2}-\d{2})")
# Matches: **Service:** Glimind Oracle MCP (`glimind-oracle` v0.1.0, `https://...`)
# Captures the first backtick-quoted token (package slug)
_SERVICE_PKG_RE = re.compile(r"\*\*Service:\*\*[^`]*`([^`\s][^`]*)`")


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return date.today()


def _package_from_title(title: str) -> str:
    """Best-effort package name from finding title (first word, strip trailing punctuation)."""
    return title.split()[0].rstrip(".,:")


def sync_curated(curated_path: Path) -> int:
    """Import findings from a Corvus findings-curated-cs*.md file.

    Each '### FNN — GHSA-xxx — SEVERITY — Title' heading becomes one advisory.
    Uses the real GHSA ID from the heading (idempotent via upsert).
    """
    db.init_db()
    text = curated_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    created_at = date.today()
    for line in lines[:25]:
        m = _DATE_RE.search(line)
        if m:
            created_at = _parse_date(m.group(1))
            break

    console.print(f"[cyan]Importing Corvus curated findings from {curated_path.name}...[/cyan]")

    imported = 0
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line.strip())
        if not m:
            continue

        ghsa_id = m.group(1)
        severity = m.group(2).lower()
        title = m.group(3).strip()

        # Try **Service:** line in the next 10 lines for a better package name
        package = _package_from_title(title)
        for j in range(i + 1, min(i + 12, len(lines))):
            svc_m = _SERVICE_PKG_RE.search(lines[j])
            if svc_m:
                package = svc_m.group(1).strip()
                break

        tier = tiers.classify(package, [], False, None)
        publish_by = tiers.publish_deadline(tier, created_at)

        advisory = Advisory(
            ghsa_id=ghsa_id,
            package=package,
            ecosystem="mcp",
            severity=severity,
            source=AdvisorySource.corvus,
            tier=tier,
            collaborators=[],
            collaborator_removed=False,
            created_at=created_at,
            publish_by=publish_by,
            state=AdvisoryState.draft,
            notes=title,
        )
        db.upsert(advisory)
        imported += 1
        console.print(
            f"  [green]✓[/green] {ghsa_id} [{tier.value}] {severity} — {title[:60]}"
        )

    console.print(f"\n[bold green]Imported {imported} Corvus finding(s).[/bold green]")
    return imported


def sync_report(
    report_path: Path,
    min_severity: str = "high",
    min_confidence: int = 60,
) -> int:
    """Import high-confidence findings from a raw Corvus report.json as synthetic drafts.

    Creates CORVUS-<slug>-NNN advisory IDs. Use 'ibis create-ghsa' to promote to real GHSAs.
    """
    db.init_db()
    data = json.loads(report_path.read_text(encoding="utf-8"))

    target = data.get("target", "unknown")
    parsed = urlparse(target)
    package = parsed.netloc or target.split()[0]

    findings = data.get("findings", [])
    created_at = date.today()

    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    threshold = sev_rank.get(min_severity.lower(), 1)
    eligible = [
        f for f in findings
        if sev_rank.get(f.get("severity", "info"), 4) <= threshold
        and f.get("confidence", 0) >= min_confidence
    ]

    slug = re.sub(r"[^a-z0-9]", "-", package.lower())[:20].strip("-")
    console.print(
        f"[cyan]Importing {len(eligible)} Corvus finding(s) from {report_path.name} "
        f"(target: {package}, {len(findings)} total)...[/cyan]"
    )

    imported = 0
    for idx, finding in enumerate(eligible, 1):
        ghsa_id = f"CORVUS-{slug}-{idx:03d}"
        severity = finding.get("severity", "medium").lower()
        title = finding.get("title", "")
        owasp = finding.get("owasp_category", "")
        desc = finding.get("description", "")
        notes = f"{title} [{owasp}] — {desc[:120]}"

        tier = tiers.classify(package, [], False, None)
        publish_by = tiers.publish_deadline(tier, created_at)

        advisory = Advisory(
            ghsa_id=ghsa_id,
            package=package,
            ecosystem="mcp",
            severity=severity,
            source=AdvisorySource.corvus,
            tier=tier,
            collaborators=[],
            collaborator_removed=False,
            created_at=created_at,
            publish_by=publish_by,
            state=AdvisoryState.draft,
            notes=notes,
        )
        db.upsert(advisory)
        imported += 1
        console.print(
            f"  [green]✓[/green] {ghsa_id} [{tier.value}] {severity} — {title[:60]}"
        )

    console.print(f"\n[bold green]Imported {imported} Corvus candidate(s).[/bold green]")
    return imported
