# Drifts-flader koblet ind (7/11-2026)

Status: implementeret
Slags: kobling
Fravalg: `tool_intent_approval_runtime.build_sudo_approval_window_surface` er udeladt —
den kræver et positionelt argument og er en vindues-beregning, ikke en tilstands-flade.

## Min tidligere måling var for grov

Jeg rapporterede «202 flader uden læser». Det tal var målt som *ikke kaldt fra `apps/`* —
og det er ikke det samme som død. Målt på tværs af HELE repoet:

- **464** `build_*_surface` i `core/services`
- **202** ikke kaldt fra `apps/`
- **52** ikke refereret fra nogen anden fil end deres egen
- **28** af de 52 nås via registry-tupler (`central_lexicon`, `eventbus_central_bridge`,
  `central_query_tool`) — ikke døde
- **24** havde nul reference uden for deres egen fil

De 150 forskel var flader der kaldes fra `core/` via aggregatorer som `central_hub`,
`cognitive_architecture_surface` og `mission_control_common`. Min oprindelige måling
så dem ikke, fordi den kun kiggede i `apps/`.

Det er samme fejlklasse som `runtime_guard`: målingen erklærede noget for dødt, fordi
den ikke kunne se vejen ind.

## De 24, kaldt før de blev skrevet ind

**23 leverer** en ikke-tom dict. Én gør ikke:

`tool_intent_approval_runtime.build_sudo_approval_window_surface` rejser `TypeError:
missing 1 required positional arg`. Den er udeladt med grund frem for tvunget ind.

## Indgangen

`GET /central/infra-state` — samme mønster som `/central/memory-state` og
`/central/tool-infra`. Owner-gated via `_require_owner()`, READ-ONLY, self-safe pr.
producent, blokerende læsning via `asyncio.to_thread`.

Aggregatoren er `core/services/infra_state_surface.py`.

## Verifikation

- 50 tests i filen, mutationstestet i to retninger: fjernes routen fejler 2 (form + gate),
  fjernes `db_sentinel` fra listen fejler 24. Gendannelsen verificeret med `diff` mod
  backup — ikke med en `&&`-kæde, som fejlede 6/11 da `grep -c` returnerede exit 1 ved
  nul fund.
- Målt i drift: 21 af 23 melder data. Tavse: `cluster_family_scheduler`,
  `session_tool_pin` — begge undersøges separat, ikke skjult.

## Regnskab efter denne runde

85 af de oprindeligt 202 er nu koblet: 35 i Tilstand-fanen, 19 på `/central/memory-state`,
8 på `/agents/approvals/state`, 23 på `/central/infra-state`.
