# Changelog

## [RT-IBIS-CURATE] — 2026-07-08 — Modo interactivo de curación de advisories

`ibis curate` para revisar y confirmar tier de findings pendientes tras un sync.

### Nuevo comando
- `ibis curate [--all]` — itera advisories sin curar ordenados por deadline; para cada uno muestra package, severity, tier, deadline, collaborators, downloads y notas
- Acciones: `k` keep (confirmar tier), `t A-D` cambio de tier (recalcula deadline desde `created_at`), `n <texto>` agregar nota, `s` skip, `q` salir
- `--all` incluye advisories ya curados para re-revisión

### DB
- Nueva columna `curated INTEGER DEFAULT 0` — migración automática vía `ALTER TABLE` al iniciar (idempotente)
- `list_uncurated()`, `update_curated()`, `update_tier()` en `db.py`

### Fix
- `Console(highlight=False)` — desactiva el number-highlighting automático de Rich que insertaba ANSI codes en medio de strings (GHSA IDs, contadores), rompiendo las assertions de tests

### Tests (70 tests, 1.43s)
- `tests/test_curate.py` — 13 tests nuevos: DB layer (filtrado, curated flag, tier update) + CLI (keep, tier change, nota, skip, quit anticipado, --all)

## [RT-IBIS-MULTI-SYNC] — 2026-07-07 — Condor/Shrike sync + push mode + tests

Integración de Condor y Shrike como fuentes de advisories, más modo push (`ibis add`) para que cualquier herramienta registre findings directamente. Primera suite de e2e tests.

### Nuevos módulos de sync
- `ibis sync --source condor --results report.json` — importa findings de un Condor `report.json`; package=platform, IDs sintéticos `CONDOR-YYYYMMDD-NNN`, Tier D por defecto (sin collaborators)
- `ibis sync --source shrike --dir findings/` — importa todos los JSONs del directorio de findings de Shrike; usa `ghsa_id` si existe, sino `SHRIKE-{stem}`; collaborator_notified → Tier no-D

### Nuevo comando push
- `ibis add --package pkg --severity sev --source corvus|condor|shrike|manual [--ghsa ID] [--tier T]` — registra un advisory directamente (llamado por Corvus/Condor/Shrike post-GHSA); genera ID sintético con prefijo de source si no se pasa `--ghsa`

### Tests e2e (57 tests, 0.93s)
- `tests/conftest.py` + `tests/fixtures/` — fixtures JSON reales de Condor y Shrike; mocks solo de red (npm, gh api)
- `tests/test_tiers.py`, `test_condor_sync.py`, `test_shrike_sync.py`, `test_add_command.py`, `test_ghsa_sync.py`

### Decisiones de diseño
- IDs sintéticos coexisten con GHSA IDs en la misma tabla (pk es TEXT, no valida formato)
- `classify()` retorna Tier D si no hay collaborators antes de evaluar npm downloads — Condor findings siempre Tier D

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
