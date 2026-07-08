from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import date
from .models import Advisory, VendorTier, AdvisorySource, AdvisoryState

DB_PATH = Path.home() / ".ibis" / "ibis.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS advisories (
                ghsa_id              TEXT PRIMARY KEY,
                package              TEXT NOT NULL,
                ecosystem            TEXT NOT NULL DEFAULT 'npm',
                severity             TEXT NOT NULL,
                source               TEXT NOT NULL DEFAULT 'manual',
                tier                 TEXT NOT NULL DEFAULT 'C',
                collaborators        TEXT NOT NULL DEFAULT '[]',
                collaborator_removed INTEGER NOT NULL DEFAULT 0,
                created_at           TEXT NOT NULL,
                publish_by           TEXT NOT NULL,
                state                TEXT NOT NULL DEFAULT 'draft',
                npm_downloads        INTEGER,
                notes                TEXT NOT NULL DEFAULT '',
                curated              INTEGER NOT NULL DEFAULT 0
            )
        """)
        try:
            conn.execute(
                "ALTER TABLE advisories ADD COLUMN curated INTEGER NOT NULL DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass


def upsert(advisory: Advisory) -> None:
    with _conn() as conn:
        conn.execute("""
            INSERT INTO advisories VALUES (
                :ghsa_id, :package, :ecosystem, :severity, :source, :tier,
                :collaborators, :collaborator_removed, :created_at, :publish_by,
                :state, :npm_downloads, :notes, 0
            )
            ON CONFLICT(ghsa_id) DO UPDATE SET
                package              = excluded.package,
                severity             = excluded.severity,
                tier                 = excluded.tier,
                collaborators        = excluded.collaborators,
                collaborator_removed = excluded.collaborator_removed,
                publish_by           = excluded.publish_by,
                state                = excluded.state,
                npm_downloads        = excluded.npm_downloads,
                notes                = CASE WHEN excluded.notes != '' THEN excluded.notes ELSE advisories.notes END
        """, {
            "ghsa_id": advisory.ghsa_id,
            "package": advisory.package,
            "ecosystem": advisory.ecosystem,
            "severity": advisory.severity,
            "source": advisory.source.value,
            "tier": advisory.tier.value,
            "collaborators": json.dumps(advisory.collaborators),
            "collaborator_removed": int(advisory.collaborator_removed),
            "created_at": advisory.created_at.isoformat(),
            "publish_by": advisory.publish_by.isoformat(),
            "state": advisory.state.value,
            "npm_downloads": advisory.npm_downloads,
            "notes": advisory.notes,
        })


def list_all(state: str | None = None) -> list[Advisory]:
    with _conn() as conn:
        if state:
            rows = conn.execute(
                "SELECT * FROM advisories WHERE state = ? ORDER BY publish_by", (state,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM advisories ORDER BY publish_by"
            ).fetchall()
    return [_row_to_advisory(r) for r in rows]


def get(ghsa_id: str) -> Advisory | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM advisories WHERE ghsa_id = ?", (ghsa_id,)
        ).fetchone()
    return _row_to_advisory(row) if row else None


def update_state(ghsa_id: str, state: AdvisoryState) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE advisories SET state = ? WHERE ghsa_id = ?",
            (state.value, ghsa_id)
        )


def update_notes(ghsa_id: str, notes: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE advisories SET notes = ? WHERE ghsa_id = ?",
            (notes, ghsa_id)
        )


def mark_collab_removed(ghsa_id: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE advisories SET collaborator_removed = 1, tier = 'D' WHERE ghsa_id = ?",
            (ghsa_id,)
        )


def list_uncurated() -> list[Advisory]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM advisories WHERE state = 'draft' AND curated = 0 ORDER BY publish_by"
        ).fetchall()
    return [_row_to_advisory(r) for r in rows]


def update_curated(ghsa_id: str, curated: bool) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE advisories SET curated = ? WHERE ghsa_id = ?",
            (int(curated), ghsa_id)
        )


def update_tier(ghsa_id: str, tier: VendorTier, publish_by: date) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE advisories SET tier = ?, publish_by = ? WHERE ghsa_id = ?",
            (tier.value, publish_by.isoformat(), ghsa_id)
        )


def _row_to_advisory(row: sqlite3.Row) -> Advisory:
    return Advisory(
        ghsa_id=row["ghsa_id"],
        package=row["package"],
        ecosystem=row["ecosystem"],
        severity=row["severity"],
        source=AdvisorySource(row["source"]),
        tier=VendorTier(row["tier"]),
        collaborators=json.loads(row["collaborators"]),
        collaborator_removed=bool(row["collaborator_removed"]),
        created_at=date.fromisoformat(row["created_at"]),
        publish_by=date.fromisoformat(row["publish_by"]),
        state=AdvisoryState(row["state"]),
        npm_downloads=row["npm_downloads"],
        notes=row["notes"] or "",
    )
