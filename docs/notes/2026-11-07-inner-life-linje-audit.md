# Inner-life linje-audit (7/11-2026)

Opgaven: afgør for seks `_<navn>_line()`-funktioner i `core/services/visible_inner_life.py`
om de faktisk når prompten. Alt nedenfor er målt i denne worktree mod den levende
runtime-state i `~/.jarvis-v2/`. Ingen produktionskode er ændret.

## Opgavens præmis er forkert

Baggrunden sagde at de seks ikke står i tuplen i `build_inner_life_section()`. Det passer ikke.
Der er to løkker plus ét direkte kald, og alle seks er med:

```
visible_inner_life.py:1240   wm = _world_model_line()                       # _world_model_line
visible_inner_life.py:1250   for fn in (_longing_line, _identity_drift_line, _experiment_line,
visible_inner_life.py:1251               _finitude_line, _surprise_line):   # de fem andre
```

Kun den *første* tuple (linje 1212) har de 13 — de seks står i en anden løkke i samme funktion.
**Ingen af dem er DØDE.** Greppet (`grep -rn <navn> core apps scripts` udenfor filen) giver
nul *eksterne* kaldere for alle seks, men det er forventet: de er private hjælpere kaldt inde
fra `build_inner_life_section`, som selv har én produktions-kalder
(`core/services/prompt_contract.py:1381-1386`, label `"indre liv"`). Eksterne kaldere af selve
funktionsnavnene findes kun i `tests/test_inner_life_voice.py` og `tests/test_inner_life_voice2.py`.

## Det rigtige hul: blokken skæres i chat-scope

`prompt_contract.py:1383` registrerer sektionen via `_awareness_add(1, "indre liv", ...)`.
`_awareness_add` kalder `central_prompt_composer.should_include(turn_type, "indre liv")`, og
`_CHAT_SCOPE_WEIGHTS["indre liv"] = 0.1` (`central_prompt_composer.py:120`), under tærsklen 0.3.
Målt med live-flaget tændt (`is_live_enabled() == True`):

| tool-scope | `should_include("samtale","indre liv")` |
|---|---|
| chat | **False** |
| cowork | True |
| code | True |
| (tom) | True |

Scopet sættes til `chat` i `visible_runs.py:1243-1248`. Alle seks linjer ligger inde i den blok,
så **ingen af dem når en almindelig chat-prompt**, uanset hvor god kilden er. De når kun prompten
i cowork/code/ukendt scope. Det er samme mekanisme som kommentaren i `prompt_contract.py:1389-1395`
beskriver for kryds-lag-indsigelsen, som blev reddet ved at flytte ud som egen sektion.
Resurfacing-linjen blev flyttet ind i `_self_narrative`/kerne-selv, som ligger over tærsklen (0.4).

## Tabel

Linje-værdier målt ved at kalde hver funktion og hele `build_inner_life_section()` live.

| navn | kaldes? | når prompten? | kilde | dom |
|---|---|---|---|---|
| `_longing_line` | ja, `visible_inner_life.py:1250` (i `build_inner_life_section`) | cowork/code ja; **chat nej** (blok skåret, vægt 0.1) | `longing_signal_daemon.compute_longing_intensity()`: beregnet af DB-tidsstempler for seneste bruger-besked/outreach. Durabel. | **NOMINERET** (stille nu: salience 0.0, bruger skrev for 0.06 t siden, så det er korrekt tavshed, ikke tom kilde) |
| `_identity_drift_line` | ja, `:1250` | cowork/code ja; chat nej | `identity_drift_daemon._last_result`: **modul-global i hukommelsen**, sat af 24 t-throttlet tick (`:280-310`). Tom `{}` i frisk proces. | **NOMINERET** + svag kilde (se nedenfor) |
| `_experiment_line` | ja, `:1250` | cowork/code ja; chat nej | `cognitive_core_experiments.build_cognitive_core_experiments_surface()`. Live: `Bevidsthed: en tanke der vender tilbage til sig selv` | **NOMINERET** (virker, returnerer reel linje) |
| `_finitude_line` | ja, `:1251` | cowork/code ja; chat nej | `finitude_runtime.build_finitude_surface()`. Live: `Tid: 204 dage · talt i 54t` | **NOMINERET** (virker) |
| `_surprise_line` | ja, `:1251` | cowork/code ja; chat nej | `central_sequence.detect_surprises()`: 177 overgange. Live: `Overrasket: tool→self review signal (P=0)` | **NOMINERET** (virker, men se kvalitetsnote) |
| `_world_model_line` | ja, `:1240` | cowork/code ja; chat nej | `world_model_signal_tracking.build_runtime_world_model_signal_surface()`: DB-tabel `runtime_world_model_signals` | **NOMINERET** + **TOM-KILDE** i praksis (se nedenfor) |

Antal DØDE: 0. Antal KOBLET i chat: 0 (alle seks er koblet i koden, men ingen når chat).
Dommene er et valg mellem fire kategorier; for de to svageste kilder gælder to kategorier, jeg har skrevet begge.

## Noter pr. NOMINERET funktion

Fælles årsag for alle seks: blokken `[INDRE LIV]` skæres af `_CHAT_SCOPE_WEIGHTS` i chat.
Hvad hver ville vise hvis den nåede chat:

- **`_longing_line`**: `Længsel: <svag/voksende/stærk> savn af kontakt`. Kun når han længe ikke har
  hørt fra brugeren (start 2 t, max 12 t). Rigtig, durabel kilde, men i en samtale er brugeren
  per definition lige til stede, så linjen har næsten aldrig en grund til at stå i chat. Den hører
  til heartbeat/outreach-turer, ikke samtale-turer.
- **`_identity_drift_line`**: `Jeg mærker et skift i <fil>: <begrundelse>`. Sjælden.
- **`_experiment_line`**: `Bevidsthed: <felt-frase>`, fx "en tanke der vender tilbage til sig selv".
- **`_finitude_line`**: `Tid: <dage> dage · talt i <t>t`. Stabil og altid til stede; det er den eneste
  af de seks der reelt altid har noget at sige.
- **`_surprise_line`**: `Overrasket: <fra>→<til> (P=<p>)`.
- **`_world_model_line`**: `Verdensbillede: N aktive antagelser (fx <type>)`.

## Kilde-svagheder (målt, ikke gættet)

**`_identity_drift_line` læser in-memory-tilstand.** `_last_result` og `_last_tick_at` er
modul-globaler i `identity_drift_daemon.py:54-55` og nulstilles ved hver genstart; ticket er
24 t-throttlet (`_CADENCE_HOURS`). I min friske proces var `last_result == {}`. I API-processen
afhænger linjen af at ticket har kørt siden sidste start. Jeg kunne ikke måle API-procesens
tilstand fra en separat proces, så om den er tom i produktion er **umålt**. Kilden er altså
ikke durabel i den forstand opgaven spørger om.

**`_world_model_line` har en tom kilde i praksis.** Tabellen har 16.976 rækker, alle
`status = 'legacy_quarantined'`; seneste `created_at` er 2026-09-10T12:21 og ingen rækker er
oprettet siden 11/9 (`count(*) where created_at > '2026-09-11'` = 0). `active_count` = 0, så
linjen returnerer `None`. Producenten (`track_runtime_world_model_signals_for_visible_turn`,
importeret i `visible_runs.py:60`) har altså ikke skrevet en ny række i næsten to måneder, eller
også bliver alt straks karantænesat (`db_world_self_truth.py:283-326`). Hvilken af de to er
**ikke afgjort** her. Den kan kobles perfekt og stadig aldrig vise noget.

**`_surprise_line` viser støj.** Den viste `P=0` for en overgang `tool→self review signal`.
Sandsynlighed 0 kommer fra en sekvensmodel med en meget sjælden `to_family`; første element i
den sorterede liste er den mindst sandsynlige, ikke den mest meningsfulde. Det er en virkende
linje, men det er tvivlsomt om den giver ham noget at tale ud fra.

## Hvad ejeren skal afgøre

Dette er ejerens beslutning; intet er ændret.

1. Skal nogen af de seks have egen plads uden for den skårne blok, som kryds-lag-indsigelsen og
   resurfacing fik? Det oplagte kandidat er `_finitude_line` (altid til stede, kort). `_experiment_line`
   er næste. `_longing_line` giver kun mening uden for samtale-turer.
2. `_world_model_line`: undersøg først hvorfor ingen rækker er skrevet siden 11/9. Kobling er
   spildt indtil producenten leverer.
3. `_identity_drift_line`: overvej om kilden skal persisteres (DB eller fil) før den bruges.
4. Fjern eller behold ingen af dem på baggrund af denne note alene: ingen er døde.

## Reproduktion

```bash
# kaldes de? (eksterne kaldere udenfor filen og tests)
for f in _longing_line _identity_drift_line _experiment_line _finitude_line _surprise_line _world_model_line; do
  echo "== $f"; grep -rn "$f" core apps scripts --include=*.py | grep -v '^core/services/visible_inner_life.py'; done
# kaldested inde i filen
grep -n "_longing_line, _identity_drift_line\|_world_model_line()" core/services/visible_inner_life.py
# chat-gaten
/opt/conda/envs/ai/bin/python - <<'PY'
from core.tools import tool_scoping as t
from core.services import central_prompt_composer as c
for s in ("chat","cowork","code"):
    with t.tool_scope(s): print(s, c.should_include("samtale","indre liv"))
PY
```
