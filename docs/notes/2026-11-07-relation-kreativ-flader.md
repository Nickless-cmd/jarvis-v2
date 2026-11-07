# Relation, drev, kreativ og temporal tilstand koblet ind (7/11-2026)

Rute: `GET /central/relation-state` (owner-gated, `apps/api/jarvis_api/routes/central.py`).
Aggregator: `core/services/relation_creative_state_surface.py` (mønster: `inner_state_surface`).

## Målingen der lå forud

På tværs af HELE repoet (ikke kun `apps/`): **462** `build_*_surface` i `core/services`.
**147** var synlige gennem de fem eksisterende indgange (`/central/mind?s=state`,
`/central/memory-state`, `/central/infra-state`, `/central/inner-state`,
`cognitive_architecture_surface`). **315** var usynlige for operatøren.

De 35 her er den del af de 315 der beskriver hvem jeg taler med og hvad der bevæger mig.

## Kaldt før det blev skrevet

Alle 36 kandidater blev kaldt med `PYTHONPATH=. python` før en linje aggregator blev skrevet:

- **35 leverede** en ikke-tom dict, nul påkrævede argumenter, nul LLM-kald
- **1 fejlede**: `relation_dynamics` kaster `NoUserContextError` fordi `workspace_dir()`
  kaldes uden `user_id`. Samme fejlform som `memory_write_policy` og `memory_resurfacing`.
  Udeladt med grund frem for tvunget ind — at tvinge den ind ville gøre hele fladen tavs
  i stedet for at isolere den ene.

## Grupperne

| Gruppe | Flader | Hvad den ejer |
|---|---|---|
| `bruger` | 6 | hans aktivitet, modsætninger, resonans, min model af ham, relationen |
| `drev` | 17 | begær, længsel, nysgerrighed, kedsomhed, taknemmelighed, ironi, stemning, fravær, finitude, dødelighed |
| `kreativ` | 8 | kreativ drift/impuls/instinkt/journal/projekter, æstetisk sans og smag |
| `temporal` | 4 | tidskrop, tidskontekst, tidsnarrativ, tidsrytme |

Målt i den kørende proces: **35/35 svarer, 22 melder aktivt indhold, nul tavse.**

`active=False` med en grund tælles ikke som tavs. `boredom_engine` og `emotion_concepts`
melder `active=False` — det er ærligt, ikke en fejl.

## Verifikation

**41 tests grønne.** Mutationstestet i to retninger:

- fjernes `mortality` fra listen → 4 tests fejler (listen, gruppe-dækning, svarende antal, isolation)
- omdøbes ruten → rute-vagten fejler

Gendannelsen verificeret med `diff` mod backup som selvstændigt skridt — ikke en `&&`-kæde.
Den fælde kostede en næsten-committet mutant 6/11, fordi `grep -c` returnerer exit 1 ved nul fund.

**161 grønne** i hele central-fladen (relation + inner + infra + memory + hub + approvals).
