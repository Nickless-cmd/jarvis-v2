---
status: foreslaaet
slags: arkitektur
dato: 2026-10-07
anmelder: jarvis
spec: ../../../specs/2026-10-07-agentorkestrering-og-subagenter.md
metode: hver påstand i spec §3 og DSH-noten er efterprøvet mod koden på main (9a642a618)
---

# Review: agentorkestrering og subagenter

Status: foreslaaet

## Problem

Spec'en `docs/specs/2026-10-07-agentorkestrering-og-subagenter.md` er skrevet til
gennemgang. Den beskriver en fejlsikker agentlivscyklus med varig inbox/outbox,
leases og `outcome_unknown` for muligvis-udført fjernskrivning.

Spørgsmålet er ikke om beskrivelsen er god — den er den mest præcise jeg har læst
i dette repo. Spørgsmålet er om dens **påstande om dagens kode holder**, og om
der er huller der skal lukkes før implementeringen starter.

Jeg efterprøvede hver påstand i §3 og i DSH-noten mod koden på main.

**Alle påståede filer findes, alle påståede funktioner findes, og hver enkelt
påstand om dagens kode holder.** Det er usædvanligt og værd at sige højt: noten
påstår ikke noget den ikke har læst.

**Rettelse (samme dag, målt efter Bjørns indvending).** Jeg havde først også
listet `agent_loop.py:909` som en påstand fra §3 og kaldt den «en sikkerhedsfejl
i koden i dag». Begge dele var forkerte:

- `agent_loop.py` **er ikke** en påstand i spec'ens §3. Linjen var min egen
  tilføjelse, sat ind i en tabel der hedder at §3's påstande holder.
- Ruten er **ubenyttet**. `/v1/agent/step` har **1 kald på 7 døgn**; ingen klient
  i `apps/jarvis-desk` eller `apps/mobile` kalder den. Klienten der ejede loopet
  (`jarvis-code`) er droppet — Bjørn: «vi arbejder kun i desk og containeren».

Fund 1 er derfor et **latent** hul i ikke-ibrugtaget kode, ikke en levende fejl.
Det ændrer alvoren, ikke kendsgerningen — og rækkefølgen: hullet skal lukkes
*før* nogen genopliver ruten, ikke straks.

**Agent-systemet selv er derimod i drift.** Målt i DB: `agent_runs` 1.540 rækker,
`agent_registry` 363, `agent_messages` 2.359, `session_inbox` 69. Desk læser dem
via `/cowork/agents`. Så §3's grundlag lever — det er kun `agent_loop.py` og
`agent_pool_router`-stien der ikke gør.

**Målt — påstandene holder:**

| Påstand | Målt |
|---|---|
| `agent_runtime_spawn.py` opretter agenter med rolle/model/budget/parent | ✅ 1654 linjer, `_scout_maa_betale()` linje 112 |
| `agent_runtime_base.py` har værktøjsløkke bag flag | ✅ 675 linjer |
| `agent_message_receipt.py` kan kvittere og vække | ✅ 308 linjer |
| `agent_transcript.py` skriver JSONL med flush/fsync | ✅ 389 linjer |
| `jarvisx_bridge.py` ruter via WS med korrelations-id | ✅ 828 linjer |
| `CodeView.tsx` har workspace-valg + Miljø-felt + inspector | ✅ 1320 linjer |
| `coworkApi.ts` læser faktiske `agent_runs` | ✅ 564 linjer |
| `agent_pool_router.route_agent_task()` kalder `central_route(lane="agent")` | ✅ 100 linjer |

**Fund 1 — latent hul i ubenyttet kode.** `apps/api/jarvis_api/routes/agent_loop.py:909`:

```python
if not provider or not model:
    provider, model = "deepseek", "deepseek-v4-flash"  # jarvis-code chat-default (owner)
```

Kommentaren siger «(owner)». **Koden håndhæver det ikke.** Faldet ligger efter
`_resolve_visible_target()`, som er rolle-bevidst (member → ollama, aldrig
DeepSeek) — men den er pakket i `try/except` der sætter `("", "")` ved fejl, og
så rammer en **member** DeepSeek. Det er præcis hvad §7.1 forbyder.

**Men ruten kaldes ikke.** Målt: 1 kald på 7 døgn, nul klienter i desk eller
mobil. Så i dag er der ingen der betaler. Hullet er latent — og bliver levende i
samme øjeblik nogen kalder `/v1/agent/step` igen. Det er grunden til at det skal
lukkes *før* en genoplivning, ikke at det kan vente i det uendelige.

**Fund 2 — `route_agent_task()` kender ikke ejeren.** Målt signatur tager kun
`kind`, `min_tokens`, `quality_threshold`, `allow_paid`, `exclude`. Ingen
`owner_user_id`, ingen `session_id`, ingen budget-kontekst. §7.1 kræver at
beslutningen gemmes med autentificeret ejer og `route_source` — det kan
funktionen ikke levere i dag, den har ikke inputtet.

**Fund 3 — fitnessvagten sluger fejl.** `agent_pool_router.py` linje ~66 har
`except Exception: pass`. Den kan ikke skelne mellem «fitness-tabellen er tom»
(ukendt → tilladt, korrekt) og «fitness-kontrollen er i stykker» (bør logges).
Begge ender i samme gren — samme fejlform som `_BILLEDVAERKTOEJ`-sagen 7/10.

**Fund 2 og 3 er bag et flag der er slukket.** `agent_pool_router_enabled` står
ikke i `runtime.json`, og docstringen i `agent_loop.py` siger selv «default OFF».
Målt: flaget er fraværende, altså OFF. Så begge fund er latente på samme måde som
fund 1 — de bliver levende den dag flaget tændes eller ruten tages i brug. Det
gør dem ikke mindre vigtige for spec'en, som netop bygger på denne sti; det gør
dem billigere at rette nu end efter første rigtige agentkørsel.

**Fund 4 — nul testdækning af ejer-grænsen.** Jeg søgte efter
`MODEL_UNAVAILABLE`, `owner_deepseek_fallback` og `route_source` i `tests/`,
`core/` og `apps/`. **Nul træf.** Den mest sikkerhedskritiske del af spec'en har
ingen eksisterende dækning at bygge på.

**Og en ting spec'en ikke nævner:** DB har allerede `agent_registry`,
`agent_runs`, `agent_messages`, `session_inbox`, `session_write_leases` og
`cheap_lane_admission_leases`. Afsnit 4's fire identiteter er **delvist bygget** —
det er en migrering af levende data, ikke et grønt felt.

## Beslutning

Reviewet konkluderer: **spec'en er moden til implementeringsplan**, men fire ting
skal afgøres først, og de tre første kan gøres uafhængigt:

1. **Luk DeepSeek-faldet i `agent_loop.py:909` — før ruten genoplives, ikke
   straks.** Grænsen skal ligge ved providerkaldet, ikke kun i routeren — som
   spec'en selv kræver. Og den skal være en hård fejl (`MODEL_UNAVAILABLE`),
   ikke et stiltiende fald til en model brugeren ikke har ret til.
   **Prioritering ændret:** ruten er ubenyttet (1 kald/7 døgn), så der er ingen
   der betaler i dag. Det gør rettelsen billig men ikke hastende — og den bør
   følge en beslutning om `agent_loop.py` overhovedet skal leve. Er klienten
   droppet for good, er den rigtige handling at **fjerne ruten**, ikke at
   patche den. Det er en beslutning for Bjørn, ikke en opgave for mig.
2. **Ejerparameter ind i `route_agent_task()`** + `route_source` i returværdien.
   Skal ske **før** nogen anden leverance rører modelvalg — ellers bygger vi
   fallback-logik oven på en funktion der ikke kan se hvem den arbejder for.
3. **Fitnessvagten logger i stedet for `pass`**, med `fitness_ukendt=True` i
   returværdien, så kaldstedet kan se forskel.
4. **Beslut §12's åbne valg** — især `outcome_unknown`-udløb og
   artefakt-retention, som hænger sammen.

Derefter leverance A→G som skitseret i §11.

**Det der er stærkt og ikke bør ændres:** §6's skelnen mellem `accepted` /
`delivered` / `claimed_by_model_step` / `acknowledged` — og sætningen om at
recovery «genbruger id og registrerer gentagen eksponering frem for at love
global præcis-én-gang modelbehandling». Den lover ikke mere end den kan.
§8's `outcome_unknown` for muligvis-udført fjernskrivning. §6's manuelle
brugerstop, hvor accepterede børn arbejder færdig og afleverer uden at vække
parenten, og resultatet markeres ubehandlet frem for at blive tilskrevet et svar
parenten aldrig gav. Og §11.1's sidste linje: *«Ingen E2E-test må nøjes med at se
en klikbar knap eller en HTTP 200.»*

## Overvejede alternativer

- **Godkende spec'en uden at efterprøve §3.** Det er den hurtige vej, og den
  havde været fristende: noten læser troværdigt. Fravalgt fordi påstande om
  dagens kode er præcis den slags der bliver til to sandheder — og fordi
  `agent_loop.py:909` er en sikkerhedsfejl der kun findes ved at læse koden.
- **Kræve spec'en omskrevet før implementering.** Fravalgt: de fire fund er
  mindre rettelser og tilføjelser, ikke en anden arkitektur. At sende den
  tilbage ville koste mere end det gavner.
- **Lukke DeepSeek-faldet med det samme i denne runde.** Fravalgt fordi det er
  en ændring i modelvalg, og Bjørn har bedt om review — ikke om en ændring.
  Fundet er beskrevet præcist nok til at næste skridt er mekanisk.
- **Behandle `agent_pool_router`-fitnessvagten som kosmetisk.** Fravalgt: den er
  samme fejlform som `_BILLEDVAERKTOEJ`-sagen, og den skjuler at en måling ikke
  kørte.

## Konsekvenser

- **Punkt 1–3 er små og kan ligge før implementeringsplanen.** Punkt 4 er Bjørns
  beslutning, ikke min. Men punkt 1 er nu betinget: det afhænger af om
  `agent_loop.py` skal leve eller fjernes.
- **Navnet «jarvis-code» er forældet terminologi, 40+ steder i aktiv kode.**
  Målt: `agent_loop.py` (15), `chat_stream_v2.py` (6), `chat.py` (3),
  `core/runtime/profiles.py` og `run_profile.py` (2) m.fl. Koden selv skriver
  det rigtige i `agent_loop.py:1313` — «Klienten (jarvis-code/desk)» — altså
  **desk**. Profilnavnet `jarvis-code` returneres stadig af
  `run_profile.py:38` når `local_tool_exec` er sand, og det flag **er** i brug:
  sat i `chat_stream_v2.py:411` (`and _tool_scope == "code"`). Så mekanikken
  lever, kun klienten og navnet er døde. Det er oprydning, ikke en fejl — men
  det bør ikke stå ubenævnt i en spec der skal beskrive dagens system.
- **Den mest sikkerhedskritiske del af spec'en har ingen eksisterende
  testdækning.** §11.1's modelscenarier skal skrives fra nul. Det bør stå som en
  selvstændig risiko i planen, ikke som en detalje.
- **`outcome_unknown` mangler en udløbsregel.** §4 siger den blokerer arbejde
  «indtil udfaldet er verificeret eller afgjort» — men hvem afgør, og efter hvor
  lang tid? Et run der står der for evigt er en blokeret assignment uden
  deadline, præcis den «permanent usynligt parkeret»-tilstand §8 forbyder for
  `queued`. Hører i §12.
- **Retention og recovery hænger sammen.** Artefakter er den fulde redningskopi;
  rydder vi dem for tidligt, mister vi evnen til at genoptage et
  `outcome_unknown`-run. De to valg bør træffes sammen, ikke hver for sig.
- **Råd-modellen er ikke entydig.** §6 siger ét assignment → én terminal besked;
  §5 siger råd leverer hvert medlems udfald. Er et råd ét assignment med flere
  runs, eller N assignments med en syntese ovenpå? Det afgør hvordan
  `alle_terminal` tælles, og bør stå eksplicit.
- **Det jeg IKKE kan love:** at spec'ens garantier holder i drift. Jeg har
  verificeret dens påstande om koden og fundet fire huller — ikke bygget noget.
  Reviewet er en måling, ikke en implementering.
