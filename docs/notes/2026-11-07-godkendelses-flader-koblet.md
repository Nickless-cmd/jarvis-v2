# Godkendelses-flader koblet ind (7/11-2026)

Status: implementeret
Slags: kobling
Fravalg: `veto_gate` er med, selv om navnet lyder som en gate og ikke en flade — den melder
lag, tærskler og seneste events, altså tilstand, ikke en beslutning.

## Målingen

202 `build_*_surface` i `core/services` blev aldrig kaldt fra `apps/`. Denne bunke er
godkendelse og samtykke — den gruppe hvor en manglende læser koster mest, fordi tilstanden
«en godkendelse venter», «en anmodning er udløbet» og «en grænse er sat» kan ligge i
månedsvis uden at nogen ser den. Det er samme fejlform som de 48 initiativer der aldrig fik
et svar fordi spørgsmålet ikke nåede en knap.

Kandidaterne blev **kaldt før de blev skrevet ind**, ikke antaget:

| Flade | Felter | Leverer |
|---|---|---|
| `approval_runtime` | 5 | nej — `pending: 0`, ærligt |
| `approval_outbox` | 4 | ja |
| `approval_expiry_daemon` | 4 | ja |
| `approval_feedback_subscriber` | 4 | ja |
| `agent_approval_notify` | 4 | ja |
| `agent_approval_gate` | 4 | ja |
| `consent_registry` | 6 | ja |
| `veto_gate` | 7 | ja |

`approval_runtime` melder `active: False` med årsagen «ingen ventende godkendelses-kort på
disken». Det er ikke en fejl — fladen gør præcis det den skal, og aggregatoren fører den
korrekt til `silent`. En tavs flade der melder sin grund er mere værd end en der påstår liv.

## Indgangen

`GET /agents/approvals/state` — samme rute som Desk's godkendelses-flade allerede kalder
(`/agents/approvals`), owner-gated via `_bruger()` som resten af filen. Listen over ventende
kort viste *hvad* der venter, ikke om maskineriet bag det virker.

Aggregatoren er `core/services/approval_state_surface.py`, mønster fra
`memory_state_surface` og `central_tool_infra_surface`: deklarativ `_PRODUCERS`, READ-ONLY,
self-safe pr. producent.

## Verifikation

- 35 tests i de to filer, 86 i den berørte flade.
- **Mutationstestet i to retninger:** fjernes routen, fejler 3 tests (mount, form, gate);
  fjernes `veto_gate` fra listen, fejler 9. Gendannelsen verificeret med `diff` mod backup —
  ikke med en `&&`-kæde, som fejlede i går da `grep -c` returnerede exit 1 ved nul fund.
- Route-testene ligger i `tests/test_agent_approvals_route.py` efter husets
  ét-testfil-pr-route-mønster; aggregatoren testes i `tests/test_approval_state_surface.py`.
