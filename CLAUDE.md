# CLAUDE.md — Ibis

Disclosure management tool para CobaltoSec. Trackea, clasifica y publica security advisories generados por Corvus, Condor y Shrike.

## Stack
- Python 3.11+, `hatchling`, `httpx`, `pydantic v2`, `typer`, `rich`, `mcp`
- CLI entry point: `ibis` → `ibis/cli.py`
- MCP server entry point: `ibis-server` → `ibis/server.py`
- DB: SQLite en `~/.ibis/ibis.db`
- Tests: `pytest` — dev install: `.venv\Scripts\pip install -e .`
- Venv: `.venv/` — usar `.venv\Scripts\ibis.exe`

## Comandos
- `ibis sync [--source ghsa|condor|shrike]` — pull desde fuente (default: ghsa)
  - `--source condor --results report.json` — importa Condor report.json
  - `--source shrike --dir findings/` — importa directorio de findings de Shrike
- `ibis add --package pkg --severity sev --source corvus|condor|shrike|manual [--ghsa ID] [--tier A|B|C|D]` — push mode
- `ibis create-ghsa <CONDOR-xxx|SHRIKE-xxx|SOURCE-xxx>` — crea GHSA draft real en GitHub y reemplaza el ID sintético en la DB
- `ibis curate [--all]` — modo interactivo: revisar/confirmar tier, cambiar tier, agregar notas (k/t/n/s/q)
- `ibis status` — tabla completa con tier, deadline, contactos
- `ibis due [--days N]` — advisories que vencen en N días (default 7); OVERDUE en rojo
- `ibis publish <GHSA>` — publica draft a público via gh api; emite `ibis.advisory.published` a CobaltoHub
- `ibis note <GHSA> "texto"` — agrega nota a un advisory
- `ibis close <GHSA> [--reason texto]` — cierra advisory (vendor rejected, not reproducible, withdrawn)
- `ibis stats` — resumen por tier
- `ibis mark-removed <GHSA> [--note texto]` — marca collaborator_removed=1, fuerza Tier D
- `ibis db-show [--ghsa ID] [--tier X] [-n N]` — inspección raw de DB (schema + rows + advisory full)

## Tests
- `.venv\Scripts\pytest tests/ -v`
- Test individual: `.venv\Scripts\pytest tests/test_condor_sync.py::test_imports_findings -v`

## Tiers de disclosure

| Tier | Tipo | Window |
|------|------|--------|
| A | Enterprise / major OSS | 90 días |
| B | Mid-tier startup / OSS activo | 45 días |
| C | Long tail indie | 30 días |
| D | Sin contacto / collab removido | Inmediato (0 días) |

Lógica en `ibis/tiers.py`. Enterprise = scope conocido (@microsoft, @notionhq, etc.) OR >50k dl/wk.
`classify()` retorna Tier D si `not collaborators` antes de evaluar downloads — Condor e `ibis add` sin collaborators siempre son Tier D.

## Modelo de integración

**Pull:** `ibis sync --source ghsa|condor|shrike` — cada fuente tiene su módulo en `ibis/sync/`.
**Push manual:** `ibis add` — llamado por Corvus/Condor/Shrike después de crear un GHSA; `--ghsa` opcional (genera ID sintético si se omite).
**MCP (hub):** `ibis-server` expone `ibis_register_finding(package, severity, description, source, target_repo?, ecosystem?)` — clasifica tier, resuelve repo/collab, crea GHSA en GitHub y guarda en DB en una sola llamada. D4 (migración de frameworks a este modelo) pendiente.

## Estructura

```
ibis/
  models.py     — Advisory, VendorTier, AdvisorySource, AdvisoryState
  db.py         — SQLite CRUD (~/.ibis/ibis.db); incluye rename_ghsa()
  tiers.py      — clasificación tier + deadline
  npm.py        — weekly downloads via npmjs.org API
  ghsa.py       — create_draft(advisory) → ghsa_id real via gh api; GHSAError
  resolver.py   — REPO_MAP (55 targets AI/ML) + resolve_repo() + resolve_top_contributor()
  server.py     — FastMCP("ibis") con ibis_register_finding tool
  sync/
    ghsa.py     — pull desde CobaltoSec/advisories (gh api)
    condor.py   — importa Condor report.json → IDs CONDOR-YYYYMMDD-NNN
    shrike.py   — importa findings/*.json de Shrike → usa ghsa_id o SHRIKE-{stem}
  cli.py        — CLI principal
tests/
  conftest.py   — fixtures: test_db (SQLite tmp), no_npm/npm_enterprise, mock_gh_api
  fixtures/     — JSONs de Condor y Shrike para tests
  test_*.py     — e2e tests por módulo (96 total)
```

## IDs sintéticos
Findings sin GHSA usan IDs sintéticos en la misma tabla: `CONDOR-YYYYMMDD-NNN`, `SHRIKE-{file-stem}`, `SOURCE-{uuid8}` (ibis add sin --ghsa). La columna `ghsa_id` es TEXT pk sin validación de formato.
