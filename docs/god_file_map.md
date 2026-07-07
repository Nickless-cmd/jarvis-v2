# God-fil-kort — det fulde overblik

**Genereret read-only af `scripts/god_file_map.py` (7. jul). Re-kør efter hvert snit.**
15 god-filer ≥1500 linjer · **97.257 linjer tilsammen** (db.py alene = 34%).

## Kortet (rangeret efter størrelse)

| # | Fil | linjer | func | blast | Karakter → strategi |
|---|-----|-------:|-----:|------:|---------------------|
| 1 | `core/runtime/db.py` | 33.495 | 676 | 778 | **tabel-skuffe** (171 tabeller) → split pr. domæne ([db_decomposition_plan.md](db_decomposition_plan.md)) |
| 2 | `core/tools/simple_tools.py` | 9.784 | 192 | 129 | **funktions-bibliotek** → split pr. funktionsgruppe |
| 3 | `core/services/heartbeat_runtime.py` | 9.155 | 86 | 55 | funktions-bibliotek → split pr. daemon/fase |
| 4 | `core/services/visible_runs.py` | 8.594 | 93 | 92 | **blandet** (hot-path!) → udskil nærmeste enhed, varsomt |
| 5 | `core/services/runtime_self_model.py` | 5.995 | 161 | 19 | funktions-bibliotek, **lav blast** → tryg tidlig gevinst |
| 6 | `core/services/prompt_contract.py` | 5.802 | 105 | 72 | blandet (hot-path!) → udskil sektionsbyggere |
| 7 | `apps/api/jarvis_api/routes/mission_control.py` | 4.605 | 248 | 31 | route-funktions-bibliotek → split pr. endpoint-gruppe |
| 8 | `core/tools/workspace_capabilities.py` | 3.966 | 61 | 23 | funktions-bibliotek → split pr. capability-gruppe |
| 9 | `core/services/visible_model.py` | 3.031 | 74 | 36 | blandet → udskil adapter/klasser |
| 10 | `core/services/cheap_provider_runtime.py` | 3.028 | 66 | 44 | funktions-bibliotek → split pr. lane/selektion |
| 11 | `apps/central_cli/central_cli/hud.py` | 2.104 | 88 | **2** | **gud-klasse** (1957-linjers klasse) → mixins/view-moduler. Tryggest af alle |
| 12 | `core/services/agent_runtime.py` | 2.096 | 60 | 23 | funktions-bibliotek → split pr. agent-fase |
| 13 | `core/services/visible_followup.py` | 2.024 | 33 | 14 | blandet (12 klasser) → gruppér klasser i moduler |
| 14 | `apps/api/jarvis_api/routes/jarvisx.py` | 1.834 | 58 | **4** | route, lav blast → split pr. endpoint-gruppe |
| 15 | `core/services/internal_cadence.py` | 1.744 | 70 | 61 | blandet → udskil producer-registrerings-grupper (bloatet 6. jul) |

## Strategi pr. karakter-type
- **Tabel-skuffe** (db.py): split pr. tabel-domæne → `db_<domæne>.py` + re-eksport. Plan findes.
- **Funktions-bibliotek** (simple_tools, heartbeat, runtime_self_model, mission_control, workspace_cap,
  cheap_provider, agent_runtime): grupper funktioner efter ansvar → `<navn>_<gruppe>.py` + re-eksport
  fra hoved-filen (imports brækker ikke). Mest mekanisk, lavest risiko.
- **Gud-klasse** (hud.py: én 1957-linjers klasse): udskil metode-grupper til mixins ELLER separate
  view/panel-moduler klassen komponerer.
- **Blandet / hot-path** (visible_runs, prompt_contract, visible_model, visible_followup, jarvisx,
  internal_cadence): udskil nærmeste sammenhængende enhed (Boy Scout). visible_runs + prompt_contract
  er HOT-PATH → ekstra varsomt, kør fuld suite + verificér prompt-assembly efter hvert snit.

## FORESLÅET RÆKKEFØLGE (lav blast-radius = tryggest først → byg rytme)
1. **`hud.py`** (blast 2) — gud-klasse, kun 2 importører. Tryggest mulige første snit.
2. **`jarvisx.py`** (blast 4) — route, lav blast.
3. **`visible_followup.py`** (blast 14) — 12 klasser at gruppere.
4. **`runtime_self_model.py`** (blast 19) — 161 funktioner, lav blast = STOR sikker gevinst tidligt.
5. **`agent_runtime.py`** / **`workspace_capabilities.py`** (blast 23).
6. **`mission_control.py`** (blast 31, 248 endpoints) · **`visible_model.py`** (blast 36).
7. **`cheap_provider_runtime.py`** (blast 44) · **`heartbeat_runtime.py`** (blast 55) · **`internal_cadence.py`** (blast 61).
8. **`prompt_contract.py`** (blast 72) · **`visible_runs.py`** (blast 92) — hot-path, varsomt.
9. **`simple_tools.py`** (blast 129) — 192 funktioner, høj blast.
10. **`db.py`** (blast 778) — monsteret. Egen plan, Fase 1 (32 trygge domæner) + Fase 2 (kerne).

## Disciplin (samme som gældende, [[project_test_suite_cleanup]] af-risikerede den)
Baseline-tests FØR hvert snit · snapshot via central_surgery · flyt → re-eksportér → compile+import+
pytest → sammenlign baseline → commit → re-kør dette script (linjer skal falde). **Test-suiten er nu
GRØN** = pålideligt regressions-net. db_*-isolations-fixet dækker fremtidige db.py-udskillelser generisk.
