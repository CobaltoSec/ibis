# CLAUDE.md — Ibis

Disclosure management tool para CobaltoSec. Trackea, clasifica y publica security advisories generados por Corvus, Condor y Shrike.

## Stack
- Python 3.11+, `hatchling`, `httpx`, `pydantic v2`, `typer`, `rich`
- CLI entry point: `ibis` → `ibis/cli.py`
- DB: SQLite en `~/.ibis/ibis.db`
- Tests: `pytest`
- Venv: `.venv/` — usar `.venv\Scripts\ibis.exe`

## Comandos
- `ibis sync` — pull GHSAs desde CobaltoSec/advisories + clasificar por tier
- `ibis status` — tabla completa con tier, deadline, contactos
- `ibis due [--days N]` — advisories que vencen en N días (default 7)
- `ibis publish <GHSA>` — publica draft a público via gh api
- `ibis note <GHSA> "texto"` — agrega nota a un advisory
- `ibis stats` — resumen por tier
- `ibis mark-removed <GHSA> [--note texto]` — marca collaborator_removed=1, fuerza Tier D
- `ibis db-show [--ghsa ID] [--tier X] [-n N]` — inspección raw de DB (schema + rows + advisory full)

## Tiers de disclosure

| Tier | Tipo | Window |
|------|------|--------|
| A | Enterprise / major OSS | 90 días |
| B | Mid-tier startup / OSS activo | 45 días |
| C | Long tail indie | 30 días |
| D | Sin contacto / collab removido | 21 días |

Lógica en `ibis/tiers.py`. Enterprise = scope conocido (@microsoft, @notionhq, etc.) OR >50k dl/wk.

## Modelo de integración (pull vs push)

**Hoy: pull.** `ibis sync` lee de `gh api orgs/CobaltoSec/security-advisories` y actualiza la DB.

**Futuro: push.** Corvus/Condor llaman `ibis add` después de crear un GHSA. Shrike tiene su propio sync.

## Estructura

```
ibis/
  models.py     — Advisory, VendorTier, AdvisorySource, AdvisoryState
  db.py         — SQLite CRUD (~/.ibis/ibis.db)
  tiers.py      — clasificación tier + deadline
  npm.py        — weekly downloads via npmjs.org API
  sync/
    ghsa.py     — pull desde CobaltoSec/advisories (gh api)
    condor.py   — TODO: pull desde Condor scan results
    shrike.py   — TODO: pull desde Shrike findings
  cli.py        — CLI principal
```

## Agregar fuente nueva (Condor, Shrike)
1. Crear `ibis/sync/condor.py` con función `sync() -> int`
2. La función lee findings del output de Condor, crea Advisory con `source=AdvisorySource.condor`
3. Registrar comando en `cli.py`
