# Daemon- og runtime-flader koblet ind (7/11-2026)

Rute: `GET /central/daemon-state` (owner-gated, `apps/api/jarvis_api/routes/central.py`).
Aggregator: `core/services/daemon_state_surface.py` (mønster: `inner_state_surface`).

## Målingen der gik forud

464 `build_*_surface` i `core/services`. Efter de seks første indgange
(`/central/mind?s=state`, `/central/memory-state`, `/central/infra-state`,
`/central/inner-state`, `/central/relation-state`, `/central/self-state`) stod
**283 uden nogen indgang**.

De 283 blev delt: 70 med modulpræfiks `central_`/`self_`/`dream_`/`private_` gik
til Claude, 213 blev min bunke. Af mine 213 var 106 kandidater efter frasortering
af dem der allerede var dækket.

**105 af 106 svarede med ægte data.** Kun `relational_warmth` blev udeladt:
`build_relational_warmth_surface` kaster `NoUserContextError` uden
bruger-kontekst — samme fejlform som `memory_write_policy` og `relation_dynamics`.

## Grupperingen

Efter hvad laget **gør**, ikke efter mappenavn:

| Gruppe | Flader |
|---|---|
| `daemoner` | 24 — det der kører af sig selv: rytmer, kadence, hvile, sansning |
| `laering` | 15 — vaner, procedurer, sprog, værdier, kompasser |
| `kontinuitet` | 12 — krønike, hukommelse, episoder, beslutningslog |
| `taenkning` | 54 — refleksion, epistemik, modsætninger, agens, værktøjs-routing |

Målt: **105/105 svarer, nul tavse, 69 melder aktivt indhold.**

## Testen

7 tests i `tests/test_daemon_state_surface.py`. Ét kald deles via en
module-scoped fixture — ét kald tager ~6,5 s (105 producenter med DB- og
fil-læsning), så 105 parametriserede kald ville være 11 minutters testtid for
det samme bevis.

**Mutationstestet i to retninger:** fjernes `action_router` fra listen, fejler 3
tests; omdøbes ruten, fejler mount-vagten. Gendannelsen verificeret med `diff`
mod backup — ikke en `&&`-kæde.

**Én test blev rettet undervejs:** den første version af
`test_kastende_producent_isoleres` patchede `_call` til at kaste. Men `_call` er
netop det lag der fanger fejlen — testen målte sin egen patch, ikke isoleringen.
Omskrevet til at patche producenten selv (`action_router.build_action_router_surface`).

## Regnskab

Af de oprindeligt 283 usynlige er nu **105 koblet her** (plus 70 i Claudes bunke).
Tilbage efter begge bunker: de flader der stadig ikke har nogen indgang.
