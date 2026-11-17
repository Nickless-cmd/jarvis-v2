# Heartbeat-slagenes formål — klassificering 2026-11-17

## Konklusion

Bjørns spørgsmål 17/11-2026 var: *«hvad skal heartbeat egentlig lave?»* Det kan
ikke besvares ud af koden, fordi der **ikke findes et formål-felt**. Der findes
kun en `action_type`. Klassificeringen her er derfor målt baglæns: hver
handlingstype er placeret i én af fire klasser ud fra **hvad dens artefakt
skriver til** — en systemtilstand, en samtale, en fil, eller en tabel uden for
nogen samtale.

Målt over 7 dage (604 indre ticks, 3.690.017 tokens):

| Klasse | Andel af slag | Andel af tokens | Handlinger |
|---|---|---|---|
| **Arbejde** | 57,9 % | 57,3 % | 350 |
| **Indre liv** | 38,7 % | 39,5 % | 234 |
| **Session** | 1,8 % | 1,8 % | 11 |
| **Overlevelse** | 1,5 % | 1,4 % | 9 |

En «heartbeat» der bruger 1,5 % af sin kapacitet på at holde sig selv i live og
58 % på arbejde er ikke en puls. Det er en arbejdsgiver. Det er den ægte
diagnose, og den kan ikke læses ud af nogen enkelt kodelinje.

## De fire klasser

### 1. Overlevelse — 9 slag (1,5 %), 51.086 tokens

Skriver til systemets egen tilstand. Ingen læser resultatet som arbejde.

| Handling | n | Hvad den skriver |
|---|---|---|
| `progress_lifecycles` | 6 | carried/fading/released/stale |
| `decay_forgotten_signals` | 2 | faded_keys, total_tracked |
| `cleanup_stale_signals` | 1 | archived, tables_scanned |

Dertil findes `cleanup_web_cache` og `cleanup_daemon_output_log` som grene, der
ikke blev ramt i perioden.

**Kendetegn:** skriver til sig selv og skal aldrig vække nogen. Volumen er 39×
mindre end arbejdets — men prisen pr. slag er den samme (se nedenfor).

### 2. Session — 11 slag (1,8 %), 66.937 tokens

Den **eneste** klasse hvis artefakt bærer et `session_id`.

| Handling | n | Hvad den skriver |
|---|---|---|
| `webchat-heartbeat-proposal` | 11 | `session_id`, `message_id`, `delivery_channel` |

Kun **3 af de 11** havde et artefakt med en session. De øvrige 8 blev blokeret
eller returnerede tomt.

**Dette er hele den session-bundne kapacitet i heartbeat.** 1,8 %.

### 3. Indre liv — 234 slag (38,7 %), 1.457.375 tokens

Skriver til filer og tilstande der bliver liggende, og som jeg selv læser
senere. Ingen samtale er involveret, og det er korrekt — det er ikke arbejde
for nogen.

| Handling | n | Hvad den skriver |
|---|---|---|
| `analyze_cross_signals` | 154 | liste af mønsternavne |
| `run_sleep_batch` | 33 | drømme |
| `generate_counterfactual_dreams` | 15 | `cf_id` |
| `run_mirror_reflection` | 14 | `insight_id` |
| `autonomous_daily_note` | 8 | **fil-sti** + note |
| `write_growth_journal` | 7 | insight + chronicle |
| `write_chronicle_entry` | 3 | `entry_id`, period |

**Skævhed:** `analyze_cross_signals` er 154 af de 234 — 25,5 % af ALLE
handlinger — og den gav **2 unikke signal-sæt** over 154 kald. 149 gange
præcis `('high_recurrence_habit', 'personality_evolution')`. Kilden er næsten
statisk: kun 76 af 4.404 vaner har `recurrence_count >= 5`, og top-10 er støj
som `smoke`, `ja tak` og systemtekst. Det er ikke analyse, det er en funktion
der gentager et stabilt input.

### 4. Arbejde — 350 slag (57,9 %), 2.114.619 tokens

Forsøger at gøre noget i verden. Skriver til tabeller uden for nogen samtale.

| Handling | n | Reelt resultat | Hvad den skriver |
|---|---|---|---|
| `act_on_initiative` | 158 | 147 | initiative + task + flow |
| `follow_open_loop` | 106 | 106 | eksekverede kommandoer |
| `process_contract_writes` | 47 | **0** | intet |
| `inspect_repo_context` | 26 | 26 | items |
| `verify_recent_claim` | 7 | 7 | grounding_preview |
| `gather_system_context` | 2 | 2 | items |
| `manage_runtime_work` | 2 | 2 | flow/task-id'er |
| `explore_own_codebase` | 1 | 1 | insight_id |
| `refresh_memory_context` | 1 | 1 | memory_items |

**To skævheder, begge målt:**

- `process_contract_writes`: **47 kald, 47 tomme, 0 reelle.** Alle fem
  tællinger (`proposal_count`, `approved_applied`, `memory_items`,
  `user_items`, `drafted_candidates`) er nul i hvert eneste kald. Det er den
  eneste gren der aldrig producerer noget, og den bruger 7,8 % af handlingerne.
- `follow_open_loop`: 65 kald havde et target, 55 unikke — 10 gentagelser. Den
  eksekverer faktisk værktøjer (items bærer `capability_id`, `command_text`,
  `execution_mode`), men målet vælges fra `recent_visible_runs`, altså mine
  egne tidligere runs — ikke fra en samtale.

## Hvordan valget træffes — og hvorfor ingen prioritet peger på en samtale

`_identify_priorities` (`heartbeat_phases.py:218`) returnerer seks prioriteter:

1. `address_failed_verifications`
2. `verify_recent_mutations`
3. `compact_context`
4. `advance_goals`
5. `goal_starvation`
6. `investigate_errors`

**Ingen af dem handler om en samtale.** Den nyere vej,
`_decide_executive_action` → `decide_next_action` → `build_action_candidates`,
har otte mulige `action_id`:

`follow_open_loop`, `inspect_repo_context`,
`promote_initiative_to_visible_lane`, `refresh_memory_context`,
`bounded_self_check`, `propose_next_user_step`, `write_internal_work_note`,
`noop`.

Kun `promote_initiative_to_visible_lane` og `propose_next_user_step` peger mod
et menneske — og de ramte ikke i måleperioden. Resten er indre eller
systemrettet. Så klassificeringen ovenfor er ikke en tilfældig fordeling: den
er hvad beslutningsmotoren *kan* vælge.

## Prisen pr. slag er den samme i alle fire klasser

| Klasse | Tokens pr. slag |
|---|---|
| Overlevelse | 5.676 |
| Session | 6.085 |
| Indre liv | 6.228 |
| Arbejde | 6.042 |

Forskellen mellem klasserne er **antallet**, ikke stykprisen. Det gør regnestykket
enkelt og ubehageligt: at skrue ned for arbejdets kadence sparer ikke «billige»
slag — hvert slag koster cirka 6.000 tokens, uanset hvad det laver. De 350
arbejds-handlinger koster 2,1 mio. tokens om ugen fordi de er 350, ikke fordi
arbejde er dyrt.

## Den historiske fejlform, målt igen

`productive_idle` stod med **2.876 kald** — den største handlingstype
nogensinde — og holdt op 3. november. Årsagen står i koden
(`heartbeat_phases.py:228`): målene løb ud, `active_goals` blev tom, og
dispatch-grenen kræver en prioritet. Den eneste prioritetskilde der altid var
til stede var et aktivt mål, så da målene udløb faldt hvert tick tilbage til
tomgang — i otte timer, uden at nogen sagde til.

Det er samme fejlform som resten af undersøgelsen: **en gren der kræver en
betingelse intet kan opfylde.** `productive_idle` er ikke en handling, den er
navnet på en manglende prioritet.

## Hvad det betyder for et formål-felt

Klassificeringen gør et `purpose`-felt byggeligt, fordi den viser at de fire
klasser har forskellige krav:

| Klasse | Skal køre af sig selv | Må koste tokens | Skal vække nogen | Skal lande i en session |
|---|---|---|---|---|
| Overlevelse | ja | nej | nej | nej |
| Session | nej — kun når nogen venter | ja | ja | **ja** |
| Indre liv | ja, egen kadence | ja | nej | nej |
| Arbejde | nej — kun ved reel kø | ja | kun ved blokering | ja, hvis det har en ophavssamtale |

Forskellen er ikke kosmetisk: hvis overlevelse og arbejde har samme kadence,
betaler arbejdet for overlevelsens ure, og 97 % af det dør urørt. Det var
målt 17/11: `_EXPIRE_MINUTES = 90`, 318 `blocked` tasks, 0 `succeeded`.

## Hvordan det blev målt

Læsende adgang til `~/.jarvis-v2/state/jarvis.db` (mode=ro). Klassificeringen
er lavet ud fra `action_artifact`'ets nøgler, ikke ud fra `action_type`'ens navn
— en handling hvis artefakt bærer `session_id` er en session-handling; en hvis
artefakt bærer `path` skriver til en fil; en hvis artefakt kun bærer tællinger
skriver til sig selv.

«Tom» er defineret som: alle værdier på nær identitetsfelterne (`focus`,
`source`, `initiative_id` osv.) er `0`, `''`, `[]`, `{}` eller `False`.

Kun de indre tick-rækker er talt. `tick_dispatched` er fasens bogføring af det
samme slag og tælles ikke som en handling.

## Lukket 17/11-2026 — de to skævheder

Begge punkter nedenfor er nu målt igen på hele historikken og håndteret. De var
**ikke** samme fejlform, og det ændrede hvad det rigtige indgreb var.

**`process_contract_writes` — fejldispatchet, ikke tom.** Målt over hele
historikken: 199 af 229 kald svarede «Heartbeat found no governed contract
writes ready to process»; 30 gjorde reelt arbejde. Grenen selv virker — den
skriver til USER.md og IDENTITY.md når der er noget at anvende, og det er den
**eneste** kaldevej til `apply_approved_runtime_contract_candidates`. Fejlen sad
i dispatch: `has_contract_write_work` talte `*:proposed` med som arbejde, men
apply-vejen anvender kun godkendte og safe kandidater. Rettelsen er derfor ikke
at slette grenen, men at lade kun `*:approved` tælle. Grenen bliver; de 199
tomme kald forsvinder.

**`analyze_cross_signals` — statisk, fjernet.** Målt: 650 kald, 9 unikke
artefakter, og de seneste mange identiske (`high_recurrence_habit` gentaget).
Der var ingen friskhed at redde. Slaget er fjernet fra
`HEARTBEAT_ALLOWED_EXECUTE_ACTIONS`, grenen er slettet, og det er ude af
drømmefasens forslagsliste. Modulet `cross_signal_analysis` består uændret —
det læses af Mission Control-routen og af daemon-fladen, som ikke er heartbeat.

Forskellen er værd at holde fast: den ene havde et formål men blev kaldt
forkert; den anden havde ikke noget formål tilbage. Kun den anden skulle fjernes.

## Åbne punkter
- Klassificeringen er lavet på 7 dage. `productive_idle`-historikken viser at
  fordelingen kan skifte brat når en betingelse holder op med at være opfyldt —
  så tallene skal måles igen, ikke citeres.
