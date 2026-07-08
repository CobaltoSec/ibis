from __future__ import annotations
import subprocess
import json
import uuid
from datetime import date
from typing import Optional
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich import box
from . import db, tiers, npm
from .models import Advisory, AdvisorySource, AdvisoryState, VendorTier, TIER_DAYS, TIER_LABELS
from .sync.ghsa import sync as _sync_ghsa

app = typer.Typer(help="Ibis — CobaltoSec disclosure management")
console = Console(force_terminal=True, width=140)

SEVERITY_COLOR = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "green",
}

TIER_COLOR = {
    VendorTier.A: "cyan",
    VendorTier.B: "blue",
    VendorTier.C: "yellow",
    VendorTier.D: "red",
}


@app.command()
def sync(
    source: str = typer.Option("ghsa", "--source", "-s", help="Source: ghsa | condor | shrike"),
    results: Optional[Path] = typer.Option(None, "--results", "-r", help="Condor report.json path"),
    findings_dir: Optional[Path] = typer.Option(None, "--dir", "-d", help="Shrike findings/ directory"),
    no_npm: bool = typer.Option(False, "--no-npm", help="Skip npm download lookup"),
):
    """Pull advisories from a source and classify by tier."""
    if source == "ghsa":
        _sync_ghsa(fetch_npm=not no_npm)
    elif source == "condor":
        if not results:
            console.print("[red]--results <report.json> required for --source condor[/red]")
            raise typer.Exit(1)
        from .sync.condor import sync as _sync_condor
        _sync_condor(results, fetch_npm=not no_npm)
    elif source == "shrike":
        if not findings_dir:
            console.print("[red]--dir <findings/> required for --source shrike[/red]")
            raise typer.Exit(1)
        from .sync.shrike import sync as _sync_shrike
        _sync_shrike(findings_dir, fetch_npm=not no_npm)
    else:
        console.print(f"[red]Unknown source: {source!r}. Valid: ghsa, condor, shrike[/red]")
        raise typer.Exit(1)


@app.command()
def add(
    package: str = typer.Option(..., "--package", "-p", help="Package name"),
    severity: str = typer.Option(..., "--severity", help="Severity: critical|high|medium|low"),
    source: str = typer.Option("manual", "--source", "-s", help="Source: corvus|condor|shrike|manual"),
    ghsa_id: Optional[str] = typer.Option(None, "--ghsa", help="GHSA ID (auto-generated if omitted)"),
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Force tier (A|B|C|D)"),
    no_npm: bool = typer.Option(False, "--no-npm", help="Skip npm download lookup"),
):
    """Add an advisory directly — push mode for Corvus/Condor/Shrike."""
    db.init_db()

    try:
        source_enum = AdvisorySource(source)
    except ValueError:
        console.print(f"[red]Unknown source: {source!r}. Valid: corvus, condor, shrike, manual[/red]")
        raise typer.Exit(1)

    if not ghsa_id:
        ghsa_id = f"{source.upper()}-{uuid.uuid4().hex[:8]}"

    dl = None if no_npm else npm.get_weekly_downloads(package)

    if tier:
        try:
            tier_enum = VendorTier(tier.upper())
        except ValueError:
            console.print(f"[red]Invalid tier: {tier!r}. Valid: A, B, C, D[/red]")
            raise typer.Exit(1)
    else:
        tier_enum = tiers.classify(package, [], False, dl)

    publish_by = tiers.publish_deadline(tier_enum, date.today())

    advisory = Advisory(
        ghsa_id=ghsa_id,
        package=package,
        ecosystem="npm",
        severity=severity.lower(),
        source=source_enum,
        tier=tier_enum,
        collaborators=[],
        created_at=date.today(),
        publish_by=publish_by,
        state=AdvisoryState.draft,
    )
    db.upsert(advisory)

    tier_color = TIER_COLOR.get(tier_enum, "white")
    console.print(
        f"[bold green]✓[/bold green] {ghsa_id} "
        f"[{tier_color}][{tier_enum.value}][/{tier_color}] "
        f"{package} ({severity.lower()})"
    )


@app.command()
def status(
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Filter by tier (A/B/C/D)"),
    state: Optional[str] = typer.Option("draft", "--state", "-s", help="Filter by state (draft/published/all)"),
):
    """Show all advisories with tier, deadline, and contact status."""
    db.init_db()
    advisories = db.list_all(state=None if state == "all" else state)

    if tier:
        advisories = [a for a in advisories if a.tier.value == tier.upper()]

    today = date.today()

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold", expand=False)
    table.add_column("GHSA", style="dim", min_width=22, no_wrap=True)
    table.add_column("Package", min_width=28, no_wrap=True)
    table.add_column("Severity", min_width=8, no_wrap=True)
    table.add_column("Tier", min_width=5, no_wrap=True)
    table.add_column("Publish by", min_width=12, no_wrap=True)
    table.add_column("Days", min_width=6, no_wrap=True)
    table.add_column("Contactos", min_width=22)

    for a in advisories:
        delta = (a.publish_by - today).days
        if delta < 0:
            days_str = f"[bold red]{delta}d[/bold red]"
        elif delta <= 7:
            days_str = f"[yellow]{delta}d[/yellow]"
        else:
            days_str = f"[dim]{delta}d[/dim]"

        sev_color = SEVERITY_COLOR.get(a.severity, "white")
        tier_color = TIER_COLOR.get(a.tier, "white")

        if a.collaborator_removed:
            contact = "[red]⚠ removido[/red]"
        elif not a.collaborators:
            contact = "[red]ninguno[/red]"
        else:
            contact = ", ".join(a.collaborators[:2])
            if len(a.collaborators) > 2:
                contact += f" +{len(a.collaborators)-2}"

        table.add_row(
            a.ghsa_id,
            a.package,
            f"[{sev_color}]{a.severity}[/{sev_color}]",
            f"[{tier_color}]{a.tier.value} ({TIER_DAYS[a.tier]}d)[/{tier_color}]",
            a.publish_by.isoformat(),
            days_str,
            contact,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(advisories)} | Today: {today}[/dim]")
    console.print(
        "[dim]Tiers: "
        "[cyan]A[/cyan]=Enterprise 90d  "
        "[blue]B[/blue]=Mid 45d  "
        "[yellow]C[/yellow]=Long-tail 30d  "
        "[red]D[/red]=No-contact 21d[/dim]"
    )


@app.command()
def due(
    days: int = typer.Option(7, "--days", "-d", help="Show advisories due within N days"),
):
    """Show advisories due to publish within N days."""
    db.init_db()
    advisories = db.list_all(state="draft")
    today = date.today()

    urgent = [a for a in advisories if (a.publish_by - today).days <= days]

    if not urgent:
        console.print(f"[green]No advisories due in the next {days} days.[/green]")
        return

    console.print(f"[bold yellow]Advisories due within {days} days:[/bold yellow]\n")
    for a in urgent:
        delta = (a.publish_by - today).days
        if delta < 0:
            label = f"[bold red]OVERDUE {abs(delta)}d[/bold red]"
        elif delta == 0:
            label = "[bold red]DUE TODAY[/bold red]"
        else:
            label = f"[yellow]in {delta}d[/yellow]"

        collab_note = ""
        if a.collaborator_removed:
            collab_note = " [red]⚠ collab removed[/red]"
        elif not a.collaborators:
            collab_note = " [red]⚠ no contact[/red]"

        console.print(
            f"  {label}  [dim]{a.ghsa_id}[/dim]  {a.package}  "
            f"[{SEVERITY_COLOR.get(a.severity,'white')}]{a.severity}[/{SEVERITY_COLOR.get(a.severity,'white')}]"
            f"  tier [{TIER_COLOR[a.tier]}]{a.tier.value}[/{TIER_COLOR[a.tier]}]{collab_note}"
        )

    console.print(f"\n[dim]Run [bold]ibis publish <GHSA>[/bold] to publish.[/dim]")


@app.command()
def publish(
    ghsa_id: str = typer.Argument(..., help="GHSA ID to publish"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Publish a draft advisory to public."""
    db.init_db()
    advisory = db.get(ghsa_id)
    if not advisory:
        console.print(f"[red]Not found in DB: {ghsa_id}. Run ibis sync first.[/red]")
        raise typer.Exit(1)

    if advisory.state == AdvisoryState.published:
        console.print(f"[yellow]{ghsa_id} is already published.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Publishing:[/bold] {ghsa_id}")
    console.print(f"  Package:  {advisory.package}")
    console.print(f"  Severity: {advisory.severity}")
    console.print(f"  Tier:     {advisory.tier.value} — {TIER_LABELS[advisory.tier]}")
    console.print(f"  Contacts: {advisory.collaborators or 'ninguno'}")

    if not yes:
        typer.confirm("\n¿Publicar?", abort=True)

    result = subprocess.run(
        ["gh", "api", f"repos/CobaltoSec/advisories/security-advisories/{ghsa_id}",
         "-X", "PATCH", "-H", "Content-Type: application/json",
         "--input", "-"],
        input=json.dumps({"state": "published"}),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        console.print(f"[red]Error: {result.stderr}[/red]")
        raise typer.Exit(1)

    db.update_state(ghsa_id, AdvisoryState.published)
    console.print(f"[bold green]✓ Published {ghsa_id}[/bold green]")


@app.command()
def mark_removed(
    ghsa_id: str = typer.Argument(..., help="GHSA ID"),
    note_text: Optional[str] = typer.Option(None, "--note", "-n", help="Optional note"),
):
    """Mark a collaborator as removed — forces Tier D and flags for escalation."""
    db.init_db()
    advisory = db.get(ghsa_id)
    if not advisory:
        console.print(f"[red]Not found: {ghsa_id}. Run ibis sync first.[/red]")
        raise typer.Exit(1)

    db.mark_collab_removed(ghsa_id)
    if note_text:
        db.update_notes(ghsa_id, note_text)

    from .tiers import publish_deadline
    from .models import VendorTier
    new_deadline = publish_deadline(VendorTier.D, advisory.created_at)
    console.print(f"[yellow]⚠ {ghsa_id} → Tier D (no contact)[/yellow]")
    console.print(f"  Package:      {advisory.package}")
    console.print(f"  Publish by:   {new_deadline} (21d from {advisory.created_at})")
    if note_text:
        console.print(f"  Note:         {note_text}")


@app.command()
def note(
    ghsa_id: str = typer.Argument(...),
    text: str = typer.Argument(...),
):
    """Add a note to an advisory."""
    db.init_db()
    db.update_notes(ghsa_id, text)
    console.print(f"[green]Note saved for {ghsa_id}[/green]")


@app.command()
def db_show(
    limit: int = typer.Option(10, "--limit", "-n"),
    tier: Optional[str] = typer.Option(None, "--tier", "-t"),
    ghsa: Optional[str] = typer.Option(None, "--ghsa"),
):
    """Show raw DB content — schema, rows, and a specific advisory in full."""
    import sqlite3, json
    from pathlib import Path

    db_path = Path.home() / ".ibis" / "ibis.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Schema
    console.print("\n[bold cyan]Schema[/bold cyan]")
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table'"
    ).fetchone()
    if schema:
        console.print(f"[dim]{schema[0]}[/dim]\n")

    # Full advisory if --ghsa
    if ghsa:
        row = conn.execute(
            "SELECT * FROM advisories WHERE ghsa_id = ?", (ghsa,)
        ).fetchone()
        if row:
            console.print(f"[bold]{ghsa}[/bold]")
            for k in row.keys():
                console.print(f"  [cyan]{k}[/cyan]: {row[k]}")
        else:
            console.print(f"[red]Not found: {ghsa}[/red]")
        return

    # Row sample
    query = "SELECT ghsa_id, package, tier, severity, publish_by, state, collaborators FROM advisories"
    params: list = []
    if tier:
        query += " WHERE tier = ?"
        params.append(tier.upper())
    query += " ORDER BY publish_by LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    console.print(f"[bold cyan]Advisories in DB[/bold cyan] ({db_path})\n")

    t = Table(box=box.SIMPLE, header_style="bold dim")
    t.add_column("GHSA", no_wrap=True)
    t.add_column("Package", no_wrap=True)
    t.add_column("Tier", no_wrap=True)
    t.add_column("Severity", no_wrap=True)
    t.add_column("Publish by", no_wrap=True)
    t.add_column("State", no_wrap=True)
    t.add_column("Collaborators")

    for r in rows:
        collabs = ", ".join(json.loads(r["collaborators"])) or "—"
        t.add_row(
            r["ghsa_id"], r["package"], r["tier"],
            r["severity"], r["publish_by"], r["state"], collabs
        )
    console.print(t)

    total = conn.execute("SELECT COUNT(*) FROM advisories").fetchone()[0]
    console.print(f"[dim]Showing {len(rows)} of {total} total rows. DB: {db_path}[/dim]\n")


@app.command()
def stats():
    """Summary stats across all advisories."""
    db.init_db()
    all_advisories = db.list_all()
    today = date.today()

    total = len(all_advisories)
    drafts = [a for a in all_advisories if a.state == AdvisoryState.draft]
    published = [a for a in all_advisories if a.state == AdvisoryState.published]
    overdue = [a for a in drafts if a.publish_by < today]
    no_contact = [a for a in drafts if not a.collaborators or a.collaborator_removed]

    by_tier = {}
    for t in VendorTier:
        by_tier[t] = len([a for a in drafts if a.tier == t])

    console.print(f"\n[bold]Ibis — Advisory Stats[/bold]\n")
    console.print(f"  Total:       {total}")
    console.print(f"  Drafts:      {len(drafts)}")
    console.print(f"  Published:   {len(published)}")
    console.print(f"  [red]Overdue:     {len(overdue)}[/red]")
    console.print(f"  [yellow]No contact:  {len(no_contact)}[/yellow]")
    console.print()
    for t, count in by_tier.items():
        color = TIER_COLOR[t]
        console.print(f"  Tier [{color}]{t.value}[/{color}] ({TIER_LABELS[t]}): {count} drafts  ({TIER_DAYS[t]}d window)")
    console.print()
