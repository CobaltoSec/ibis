# Changelog

## [RT-IBIS-BOOTSTRAP] — 2026-07-07 — Bootstrap + CLI UX

Ibis v0.1.0 — disclosure management tool para CobaltoSec. Bootstrap completo con sync desde
CobaltoSec/advisories, clasificación por tiers (A/B/C/D), y CLI operativa.

### Core
- `ibis sync` — pull GHSAs desde CobaltoSec org + clasificación por tier (enterprise/startup/indie/no-contact)
- `ibis status` — tabla paginada con GHSA, package, severity, tier, deadline, días restantes, contactos
- `ibis due [--days N]` — advisories que vencen en N días con etiquetas OVERDUE/DUE TODAY
- `ibis publish <GHSA>` — publica draft a público via `gh api PATCH`
- `ibis note <GHSA> "texto"` — agrega nota al advisory en DB
- `ibis stats` — resumen por tier (drafts, published, overdue, no-contact)

### CLI UX fix
- `Console(force_terminal=True, width=140)` — evita colapso de columnas en PowerShell non-TTY
- `min_width` + `no_wrap=True` en todas las columnas — Sev y Tier ya no aparecen en blanco

### Nuevos comandos
- `ibis db-show [--ghsa ID] [--tier X] [-n N]` — inspección raw de DB: schema + rows + advisory completo
- `ibis mark-removed <GHSA> [--note texto]` — marca collaborator_removed=1, fuerza Tier D, registra nota

### Stack
- Python 3.11+, hatchling, httpx, pydantic v2, typer, rich
- SQLite en `~/.ibis/ibis.db` (8 columnas, `gh api orgs/CobaltoSec/security-advisories`)
- Tier logic: npm downloads via npmjs.org API + scope heuristics (enterprise, indie, etc.)
