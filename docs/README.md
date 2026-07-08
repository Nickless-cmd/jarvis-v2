# Jarvis V2 — Documentation

Jarvis V2 is a **persistent digital entity** — an AI assistant that lives on its own machine. It is identity-first, LLM-led and runtime-governed: the LLM does the work, the runtime sets boundaries, policy, budget, event flow and observability, and the **Central** (Mission Control's truth/control plane) sits over it all.

This is the documentation index. Every doc has been classified against **git + runtime** (the only real sources of truth) — see [`DOCS_MANIFEST.md`](DOCS_MANIFEST.md) for each doc's status (`færdig` / `forældet` / `droppet`) and the evidence behind it.

> **Freshness policy:** files under `reference/` and "Generated" are produced from code — **regenerate, don't hand-edit**. Anything under `design-history/`, `superpowers/`, or `_archive/` is historical record, not current truth.

## Getting started
- [`INSTALL.md`](INSTALL.md) — **from an empty machine to a running Jarvis** (deps, config, run the two processes, verify)
- [`USER_GUIDE.md`](USER_GUIDE.md) — using Jarvis
- `requirements.txt` (repo root) — the curated runtime dependencies

## Operations & security
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — production: systemd units, HTTPS, encryption, upgrade flow
- [`SECURITY.md`](SECURITY.md) — secrets, auth/roles/gates, egress/privacy tiers
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev workflow, tests, the four gates, code rules, Boy-Scout rule
- [`reference/CONFIG.md`](reference/CONFIG.md) — the `runtime.json` schema (28 keys, placeholders only)

## Architecture
- [`architecture/OVERVIEW.md`](architecture/OVERVIEW.md) — **start here**: directory structure, subsystems, request flow, the four sources of truth
- [`CENTRAL.md`](CENTRAL.md) — the Central (Jarvis' nervous system / control plane) — the freshest architecture truth
- [`BACKEND_OVERVIEW.md`](BACKEND_OVERVIEW.md) — backend overview
- [`project_reasoning_layer.md`](project_reasoning_layer.md) · [`streaming-production-grade-spec.md`](streaming-production-grade-spec.md) — runtime deep-dives

## Reference (generated from code — do not hand-edit)
- [`reference/API_REFERENCE.md`](reference/API_REFERENCE.md) — every HTTP route (`python scripts/api_reference_gen.py`)
- [`reference/CAPABILITIES.md`](reference/CAPABILITIES.md) — every tool + mutating flag (`python scripts/capabilities_gen.py`)
- [`capability_matrix.md`](capability_matrix.md) — service liveness audit (`python scripts/capability_audit.py`)

## Operations
- [`MODEL_STRATEGY.md`](MODEL_STRATEGY.md) — model/lane strategy
- [`TRANSPORTS.md`](TRANSPORTS.md) · [`CHANNELS.md`](CHANNELS.md) — transports (SSE/WS) & channels
- [`CLI_SPEC.md`](CLI_SPEC.md) — the `jc` CLI
- [`llm_privacy_tier_audit.md`](llm_privacy_tier_audit.md) — privacy tiers / egress

## Identity & governance
- [`JARVIS_MANIFESTO.md`](JARVIS_MANIFESTO.md) · [`JARVIS_V2_LOCKED_CHARTER.md`](JARVIS_V2_LOCKED_CHARTER.md) · [`JARVIS_V2_BUILD_RULES.md`](JARVIS_V2_BUILD_RULES.md)

## Generated (regenerable, kept in place)
- [`capability_matrix.md`](capability_matrix.md) · [`central_connectivity_matrix.md`](central_connectivity_matrix.md) · [`god_file_map.md`](god_file_map.md) · [`DOCS_MANIFEST.md`](DOCS_MANIFEST.md)
- `central_connectivity_matrix.json` is **runtime-load-bearing** (read by `core/services/central_coverage.py`) — do not move it.

## Design history (record, not current truth)
- [`superpowers/`](superpowers/) — every design spec + implementation plan (the spec→plan→build history)
- [`design-history/`](design-history/) — dated snapshots and superseded audits
- [`_archive/`](_archive/) — docs classified `forældet`/`droppet` by the SP1 audit

## Known documentation gaps (→ docs programme SP4)
Live capabilities that still lack dedicated narrative docs: prompt architecture, the memory system (daily/weekly/monthly layers), agents & council, cost accounting, testing strategy, security posture, a debugging guide. SP4 (per-file/function reference) fills these; the `mangler` section of `DOCS_MANIFEST.json` tracks them.

## Regenerating the generated docs
```bash
conda activate ai
python scripts/api_reference_gen.py      # → reference/API_REFERENCE.md
python scripts/capabilities_gen.py       # → reference/CAPABILITIES.md
python scripts/capability_audit.py       # → capability_matrix.md
python scripts/docs_audit.py             # → docs_audit_raw.json (doc classification)
```

## Conventions
- Markdown + UTF-8. Danish + English mixed is fine (Jarvis is bilingual).
- Dated filenames use ISO (`YYYY-MM-DD-topic.md`).
- New docs are linked here or from `architecture/OVERVIEW.md`, else they're invisible.
