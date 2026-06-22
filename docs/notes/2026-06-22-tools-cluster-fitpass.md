# Tools-cluster fit-pass (2026-06-22)

Kortlægning af tool-eksekverings-stien til den kommende **Tools**-cluster i Den
Intelligente Central. Fokus: rod-årsag til at native tool-resultater trunkeres,
mens `bash_session` undslipper. Verificeret mod kode (fil:linje nedenfor).

## Rod-årsag: 4-lags trunkerings-pipeline + `{"text"}`-form-asymmetri

Et tool-resultat passerer op til fire successive afkortninger før modellen ser det
i næste runde:

| # | Hvad | Fil:linje | Default |
|---|------|-----------|---------|
| 1 | JSON-fallback i `format_tool_result_for_model` (KUN hvis intet `"text"`-key) | `core/tools/simple_tools.py:9492` | 8000 tegn |
| 2 | `summarize_result` (persisteret summary) | `core/services/tool_result_store.py:12` | 500 tegn |
| 3 | Prompt-render, seneste 20 (`expand=True`) | `core/services/prompt_contract.py:4214` | 4000 tegn |
| 4 | Prompt-render, ældre (`expand=False` → kun summary) | `core/services/prompt_contract.py:4214` | 1200 tegn |

**Den afgørende asymmetri** (`format_tool_result_for_model`, `simple_tools.py:9475`):
```python
text = result.get("text", "")
if not text:
    # ... ellers JSON-dump af hele result, cappet ved _MAX_FALLBACK_CHARS = 8000
```
- Tools der returnerer `{"text": "...", ...}` (fx `bash_session_run`) **springer**
  8000-tegns JSON-cap over og leveres som-er (op til tool'ets eget loft).
- Tools der returnerer struktureret data UDEN `"text"`-key bliver JSON-dumpet og
  cappet ved 8000 — og rammer derefter prompt-render-laget (1200 ældre / 4000 seneste).

**Derfor:** `bash_session` "virker" mekanisk fordi (a) dens `{"text"}`-form skipper
JSON-cap'en og (b) den er typisk det seneste tool (får 4000 / vises fuldt hvis ≤ limit).
Andre native tools rammes af BÅDE JSON-cap'en OG 1200-loftet så snart de ikke længere
er det nyeste resultat. Dette bekræfter Bjørns observation: "medmindre han bruger bash
session bliver alle hans tools results trunkeret."

`bash_session_run` egne lofter: daemon `_OUTPUT_LIMIT_BYTES = 32*1024` (`core/tools/bash_session.py:53`),
one-shot bash `MAX_BASH_OUTPUT_CHARS = 16000` (`simple_tools.py:587`).

## Kandidat-nerver (Tools-cluster)

Gates/filtre/persistens/telemetri på tool-stien — råmateriale til en `central_catalog`
"tools"-sektion (fit pr. nerve = beslutning, ikke afgjort her):

| Nerve | Fil:linje | Mekanisme |
|-------|-----------|-----------|
| veto_gate (pre-exec) | `visible_runs.py:4807` | inline gate |
| decision_gate (pre-exec) | `visible_runs.py:4823` | inline gate |
| tool_scoping (rolle) | `simple_tools.py:3911` | filter |
| workspace_trust (`guard_code_write`) | `simple_tools.py:3931` | gate |
| approval_state | `visible_runs.py:1636` | persistens |
| duplicate_suppression | `visible_runs.py:4770` | de-dup gate |
| result_cache | `visible_runs.py:4784` | cache |
| tool_result_store (`save_tool_result`) | `tool_result_store.py:22` | persistens |
| outcome_learning (`record_outcome`) | `simple_tools.py:3971` | daemon |
| tool_router (`select_tools`) | `visible_runs.py:1688` | filter |
| tool.invoked / .completed events | `simple_tools.py:3939` | telemetri |

## Fejl-/trace-huller (hvor en fælles fejl/flag/trace-kontrakt skal attache)

Steder hvor tool-stien fejler STILLE (`except Exception: pass`, intet spor):

| Locus | Fil:linje | Konsekvens |
|-------|-----------|------------|
| veto_gate | `visible_runs.py:4816` | gate-fejl → fail-open |
| decision_gate | `visible_runs.py:4831` | gate-fejl → fail-open |
| **rolle-håndhævelse** | `simple_tools.py:3925` | gate-fejl → slipper igennem — **SIKKERHED: verificér fail-retning** |
| agentic cache-store | `visible_runs.py:4872` | cache-skrivning tabt stille |
| in-flight tool-mark | `visible_runs.py:4733` | tracking taber tool |
| tool_result_store events | `tool_result_store.py:182` | resultat-events tabt |

## Konklusion → næste skridt

1. **Truncation-fix er en DESIGN-beslutning, ikke en reflex-bump** — at hæve 1200→N
   trader direkte mod prompt-bloat (den dybe omkostnings-driver). Mulige akser:
   normalisér flere tools til `{"text"}`-form (skip JSON-cap), udvid expand-vinduet,
   eller per-tool-loft. Vælg i Tools-cluster-planen.
2. **central_catalog "tools"-sektion** populeres fra nerve-tabellen ovenfor.
3. **Fælles fejl/flag/trace-kontrakt** attaches på de stille fail-open-steder — og
   rolle-håndhævelsens fail-retning (`simple_tools.py:3925`) verificeres som potentiel
   sikkerheds-sag (multi-user north-star).
