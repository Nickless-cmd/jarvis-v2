# Mission Control — drift-sonde (kan det gamle vindue lyse igen?)

**Spørgsmål:** Det gamle MC (ved `b8c98551^`) kaldte en flade af `/mc/*`-endpoints.
Efter "Fase E" (MC revet ud af web-UI, datalag re-pegged) — hvor mange af dem svarer
stadig i dagens backend? Dvs. hvor stort er genopbygnings-arbejdet reelt?

**Dato:** 2026-08-16.

## Resultat: 96 % lever stadig

| Mål | Tal |
|---|---|
| Nuværende `/mc`-ruter i backend | **205** |
| Gamle stier fundet i old MC total | 197 (heraf 82 provenance-labels, ikke rigtige endpoints) |
| Rigtige gamle endpoint-kandidater | **112** |
| ✅ Lever stadig i dag | **108 (96 %)** |
| ❌ Døde | **4** |

**De 4 døde — små og harmløse:**
- `/mc/cost/summary` → **afløst** af `/mc/costs` + `/mc/costs/daily` (cost-data lever, ny form).
- `/mc/system/git`, `/mc/system/git/commit` → git-status/commit-widget (reelt væk).
- `/mc/system/health` → system-helbreds-flise (reelt væk; delvist dækket af `/mc/memory-health`).

## Den afgørende opdagelse

`/mc/*`-fladen **overlevede Fase E intakt.** Kun web-UI'et blev revet ud (`b8c98551`);
backend-ruterne blev tværtimod pænt modulariseret (den gamle 4605-linjers `mission_control.py`
→ 6-7 feature-moduler, behavior-preserving, **paths uændrede**) og monteres stadig under
`/mc`. Re-peg-commit'en (`96a787a9`) rørte kun **desk-klientens** datalag
(`missionControlApi.ts`), ikke backend.

**Konsekvens for genopbygning:**
- Et genskabt MC kan tale `/mc/*` **direkte** og få **96 % af vinduet til at lyse igen
  med NUL backend-arbejde.** De ~3 manglende ops-widgets (git, system-health) er trivielle
  at gen-tilføje eller re-pointe.
- Koblingen til Centralen (`/central/*`) er derfor **ikke** en forudsætning for paritet —
  den er en *additiv* opgradering til et smartere MC, der oveni viser Centralens nyere
  intelligens. Man kan få øjnene tilbage FØRST (paritet på `/mc/*`), og lægge Central ovenpå
  bagefter.

## Metode & forbehold

- **Liveness = statisk rute-analyse:** de nuværende `@router.<method>("...")`-dekoratorer i
  `mission_control_*.py` blev udtrukket (autoritativt for "findes en handler i dagens kode")
  og krydset mod `/mc/*`-stier udtrukket af det gamle `lib/adapters.js` + `useMissionControlPhaseA.js`.
- **Live-curl var inkonklusiv:** alle kald mod den kørende server (CT105:8080) gav `HTTP 401`
  — inkl. de døde — fordi en global auth-gate afviser *før* routing. 401≠404, så HTTP-koden
  kan ikke skelne levende fra død uden gyldig owner-token. Derfor hviler tallene på den
  statiske analyse, ikke på HTTP-svar.
- Se den fulde felt-for-felt-beskrivelse i [OLD_MC_CARTOGRAPHY.md](OLD_MC_CARTOGRAPHY.md).
