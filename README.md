[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

# Ibis

> Responsible disclosure manager for CobaltoSec security advisories.

Ibis tracks the full lifecycle of security advisories discovered by Corvus, Shrike, and other CobaltoSec tools — from draft creation through coordinated vendor disclosure to public publication. It enforces 90-day embargo windows, sends deadline alerts, and integrates with the CobaltoHQ event hub.

## Install

```bash
cd C:\Proyectos\Ibis
pip install -e .
```

## CLI

```bash
# List all advisories
ibis list

# Show advisories due for disclosure in the next N days
ibis due --days 7

# Publish a ready advisory (lifts embargo, updates GitHub Security Advisory)
ibis publish GHSA-xxxx-xxxx-xxxx

# Sync state from GitHub Security Advisories
ibis sync
```

## Advisory Lifecycle

```
draft → coordinating (vendor notified) → ready → published
                         ↑
                    90-day window
```

- **Draft**: finding logged, GHSA created as private advisory
- **Coordinating**: vendor notified, 90-day clock starts
- **Ready**: embargo expired or vendor patch released, awaiting publication
- **Published**: public advisory live on GitHub

## State

Ibis state is stored as JSON files in `state/`:

```
state/
  advisories.json     # All advisory records
  deadlines.json      # Upcoming embargo deadlines
```

## Integration

Ibis emits events to CobaltoHQ (`cobaltosec-hub`) on key state transitions:

- `ibis.advisory.published` — advisory goes public
- `ibis.deadline.due_soon` — embargo deadline within 3 days

## Current State

<!-- IBIS_STATS_START -->
58 total advisories — 7 published, 51 in active coordinated disclosure.
<!-- IBIS_STATS_END -->

## License

MIT © [CobaltoSec](https://cobalto-sec.tech)
