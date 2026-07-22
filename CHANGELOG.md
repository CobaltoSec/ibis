# Changelog

## [RT-IBIS-HUB D4 + RT-IBIS-E2E] — 2026-07-22 — Hub completo + tests E2E

- `ibis/core.py` (nuevo) — `register_finding()` como función pública importable sin MCP server. Acepta `ghsa_id` opcional para skip de GHSA creation (cuando el framework ya creó el GHSA).
- `ibis/server.py` — refactorizado como thin wrapper MCP sobre `core.register_finding`
- **D4-Corvus** — `corvus/cli.py` + `batch.py`: `_ibis_report_findings()` post-scan, filtra severity ≥ high + confidence ≥ 60, ecosystem="mcp". `cobaltosec-ibis` instalado en venv de Corvus.
- **D4-Shrike** — `shrike/server.py`: `_ibis_sync()` en `shrike_disclose_github` + `shrike_disclose`, solo `mode=advisory_fallback` (no pvr). `cobaltosec-ibis` instalado en venv de Shrike.
- **D4-Condor** — diferido, Condor en desarrollo activo.
- `tests/test_core.py` — 5 tests para `register_finding` con `ghsa_id`
- `tests/test_e2e.py` — 6 escenarios E2E: Corvus pipeline, Shrike existing GHSA, multi-finding, Tier D, idempotencia, cross-source
- 122 tests pasando (111 → 122)

## [RT-IBIS-HUB] — 2026-07-20 — MCP server + ghsa/resolver modules (D1-D3)

Ibis es ahora un hub central de disclosure: expone `ibis_register_finding` via FastMCP, extrae la lógica de GHSA creation a módulo propio, y porta el REPO_MAP de Shrike.

- `ibis/server.py` — `FastMCP("ibis")` con `ibis_register_finding(package, severity, description, source, target_repo?, ecosystem?)`: clasifica tier, resuelve repo+colaborador, crea GHSA draft en GitHub y guarda en DB en una llamada
- `ibis/ghsa.py` — `create_draft(advisory) → ghsa_id` extraído de `cli.py`; `GHSAError` para fallos de API; incluye `vulnerable_version_range >= 0.0.1` para evitar HTTP 422 en publish
- `ibis/resolver.py` — `REPO_MAP` (55 targets AI/ML portado de Shrike) + `resolve_repo()` + `resolve_top_contributor()` via `gh api`
- `pyproject.toml` — agrega `mcp>=1.0` y entry point `ibis-server`
- D4 (migración de frameworks) diferido — Corvus en desarrollo activo

## [RT-IBIS-CREATE-GHSA] — 2026-07-20 — ibis create-ghsa + db.rename_ghsa()

Pipeline completo para findings de Condor/Shrike con IDs sintéticos.

- `ibis create-ghsa <CONDOR-xxx|SHRIKE-xxx|SOURCE-xxx>` — crea GHSA draft en GitHub con los datos del finding y reemplaza el ID sintético en la DB por el GHSA real
- `db.rename_ghsa(old_id, new_id)` — UPDATE del primary key en SQLite
- `cli.py` `create-ghsa` refactorizado para usar `ghsa.create_draft()` — sin duplicación
- 16 tests nuevos; 96 totales

## [ad-hoc] — 2026-07-13 — ibis close + cierre GHSA-mf64-cgv4-ppcx (MSRC rejection)

- Nuevo comando `ibis close <GHSA> [--reason texto]` — marca `state=closed`, appende reason a notes
- Análisis fuente playwright-mcp@0.0.76: `checkFile()/isPathInside()` presente en playwright-core@1.61.0-alpha-1781023400000 (commit 8f6e433a) — MSRC correctamente rechazó arbitrary-file-write (%2e%2e%2f no decodifica en contexto JSON/MCP)
- GHSA-mf64-cgv4-ppcx cerrado con razón técnica completa

## [RT-IBIS-TIER-D] — 2026-07-10 — Tier D = ventana 0 (publicar inmediatamente)

- `TIER_DAYS[VendorTier.D] = 0` en `models.py` — advisories sin contacto tienen `publish_by = created_at`
- Test `test_publish_deadline_tier_d` actualizado: espera `created` (no `created + 21d`)
- CLAUDE.md: tabla de tiers actualizada (D = "Inmediato (0 días)")

## [RT-IBIS-PUBLIC-POLICY] — 2026-07-08 — Política pública de disclosure + publicación Tier D

### Policy
- Repo público `CobaltoSec/disclosure-policy` con política responsable de disclosure (Tier A/B/C, notificación vía GHSA invite)
- Tier D es concepto interno — no figura en la policy pública; sin maintainer = publicar directamente
- Email de contacto: nicolas@cobalto-sec.tech
- Corvus README actualizado con link a disclosure-policy (commit 9bac5e9)
- Condor README actualizado localmente

### Operacional
- 4 advisories Tier D publicados: GHSA-jgxf (campertunity-ai-tools), GHSA-prc4 (localparse-mcp), GHSA-32vx (emilia-protocol), GHSA-wx78 (@tensorfeed/mcp-server)
- Fix: advisories con `vulnerable_version_range: null` fallaban con HTTP 422 al publicar — parcheados con `>= 0.0.1`
- GHSA-mc5c-pq6j-9ffp (lobe-chat) era duplicado de GHSA-527q-fpmm-3gmc — DB sincronizada a `state=closed`

### Arquitectura futura
- RT-IBIS-HUB diseñado: Ibis como MCP server central; todos los frameworks llaman `ibis_register_finding()`; lógica de GHSA creation migrada desde Shrike

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
