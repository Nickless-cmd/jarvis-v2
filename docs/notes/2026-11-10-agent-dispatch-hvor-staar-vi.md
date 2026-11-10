# Agent-dispatch — hvor står vi (10/11-2026)

Status for de fem parallelle måder at køre agenter (Claude Code-modellen), målt i koden
den 10/11-2026 om aftenen. Brainstorm-dokument, ikke en spec — ingen kode er ændret.

## Kort status

| # | Måde | Status | Bevis |
|---|---|---|---|
| 1 | **Subagents** | ✅ Findes og bruges | `Task` + `agent_task_facade.execute()`, kontrakt-v1 |
| 2 | **Agent view (Desk)** | ⚠️ Halvt | Overvågning ja, batch-dispatch nej |
| 3 | **Agent teams** | ❌ Findes ikke | `agent_council.py` (267 linjer) har 0 hits på `shared`/`mailbox`/`peer`/`task_list` |
| 4 | **Dynamic workflows** | ❌ Findes ikke | `agent_dispatch.py` har plan+løkke, men **0 faktiske kald** (19 filer nævner navnet — alle læser *om* den) |
| 5 | **Projects (vedvarende threads)** | ❌ Findes ikke | `sustained_project` er Jarvis' egne projekter, ikke parallelle sky-threads |

## 1. Subagents — den ene der holder

`Task` er ægte: egen kontekst, eget worktree, eget budget, egen returvej. Fem roller:
`researcher`, `critic`, `planner`, `watcher`, `executor`.

**Men døren er smallere end maskineriet.** Skemaet i `core/tools/agent_contract_tools.py:64`
bærer en hårdkodet enum med de fem navne. Eksekveringen validerer den ikke —
`subagent_type` sendes direkte videre til `execute()` (linje 294). Enum'en er altså
**kun en synlig begrænsning i det skema modellen ser**, ikke en håndhævet port.

Konsekvens: udvider vi enum'en, flyder nye navne igennem af sig selv. Men
`agent_runtime_spawn.py:188` falder **tavst tilbage til `researcher`** på et ukendt
rollenavn — en tavs default der skjuler en fejl. Det skal væk før døren åbnes.

## 2. Desk — overvågning, ikke orkestrering

Findes:
- `AgentPoolPanel.tsx` (414 linjer) — start, interrupt, close, followup. **Én agent ad gangen.**
- `AgentWork.tsx` — subagenter som synlige arbejdere: rolle, udfald, model, tokens, pris.
- `missioncontrol/` — `AgentRoster`, `RunsTable`, `CostPanel`, `EventStream`, `RunDetail`, `SummaryBar`.
- `AgentDispatchPane.tsx` (38 linjer) — **viser kun** en plan den får foræret. Kan intet starte.

Mangler: **batch-dispatch** (vælg N opgaver, send afsted samlet) og en flade der viser et
hold som et hold, ikke som N løsrevne rækker.

## 3. Agent teams — det ægte hul

Council er tættest på: selvstændige kontekster, samme fakta, én syntese. Men:

- **All-or-nothing** — der er ingen plads til at starte 2 af 5.
- **Ingen delt opgaveliste** — intet medlem ejer en del af et fælles arbejde.
- **Ingen medlem-til-medlem-kanal** — alle taler kun opad, til Jarvis.

Spec'en (`docs/specs/2026-10-07-agentorkestrering-og-subagenter.md:29`) siger allerede det
rigtige: *"Et råd og en review-kæde er orkestreringsmønstre over den samme motor, ikke
separate LLM-runtimes."* Team skal derfor være et **mønster over `Task`**, ikke en ny motor.

## 4. Dynamic workflows — nul

`core/services/agent_dispatch.py` har hele formen: `decide_dispatch` (inline vs dispatch),
`plan_dispatch` (rolle-plan researcher→planner→executor×N→critic→synthesizer),
parallel-flag og en live-gren. Den er registreret som værktøj `dispatch_code_mode_task`,
scopet og eksporteret.

**Målt: 0 faktiske kald.** Alle 19 filer der nævner navnet er `search`, `read_file`,
`bash` og `recall` der har *læst om* den. Vi byggede orkestratoren og koblede den aldrig
til Jarvis' faktiske vej.

Det er den fejlform Bjørn kalder teater: en mekanisme der ser ud som om den virker,
men hvis indgang aldrig bruges.

## 5. Den vigtigste opdagelse: registeret findes — døren er lukket

`core/services/role_registry.py` implementerer **allerede** præcis det Bjørn foreslog:

```
register_custom_role(role, title, system_prompt, default_tool_policy, extends, tags)
  → ~/.jarvis-v2/config/custom_roles.json
```

- Custom roller kan **arve** fra en indbygget (`extends: "critic"`).
- De kan bære egen tool-policy og tags.
- De overskriver indbyggede ved navnekollision.
- Værktøjerne `list_agent_roles` og `register_custom_role` findes.

**Men filen findes ikke** — registeret er tomt. Og `register_custom_role`s egen
beskrivelse siger: *"The model-facing Task contract intentionally accepts only its bounded
built-in subagent types."* Døren er altså lukket **med vilje**, ikke af glemsomhed.

## Bjørns forslag, oversat til det vi har

> "én dør, to tilstande (single/team), roller afledt af behov"

- **Én dør** = `Task` bliver den eneste indgang. `dispatch_code_mode_task` og de gamle
  agent-værktøjer fjernes fra fladen, så der ikke kan kaldes ved en fejl.
- **To tilstande** = `mode: "single" | "team"` som parameter på samme kald.
- **Roller afledt af behov** = team-tilstanden tager en liste af `{role, task}`; rollen er
  et svar på behovet, ikke et valg fra en fast liste. `register_custom_role` er allerede
  mekanismen der gør et nyt rollenavn gyldigt — den skal blot kobles på `Task`.

## Åbne beslutninger før nogen bygger

1. **Skal team være council udvidet, eller en ny kørselstype under `Task`?**
   Council har den rigtige form (isolerede kontekster, fælles fakta, én syntese). Det der
   mangler er kun delt liste + indbyrdes kanal — to tilføjelser, ikke et nyt system.
2. **Kan `Task` bære en liste af børn med en fælles ressource?** Hvert barn får i dag sit
   eget isolerede worktree. En delt opgaveliste kræver en ressource uden for worktreet.
   Det er den måling der afgør om council-vejen er billig eller dyr.
3. **Hvad sker der med de 45 ryddede worktrees-regler** når N børn deler et mål?
   `d4d66f400` gjorde worktree-kravet synligt — det arbejde skal bæres videre.
4. **Tavs fallback til `researcher`** skal erstattes af en tydelig fejl før enum'en åbnes.

## Rækkefølge, hvis vi bygger

1. **Kobl det vi har** — `agent_dispatch.py` på Jarvis' vej, eller fjern den. En død
   orkestrator er værre end ingen.
2. **Batch i pool-panelet** — Desk kan sende N afsted, ikke én.
3. **Team som tilstand på `Task`** — `mode: single|team`, roller afledt, delt liste.
4. **Workflows sidst** — den eneste der kræver ny arkitektur (løkken ud af Jarvis' kontekst).

## Måling 10/11 kl. 18:0x — kan Task bære en delt opgaveliste?

**Kort svar: nej i dag, men blokeringen er ikke worktree-isoleringen.**

### Roller og størrelse: Bjørns model ER allerede council'ens form
- `agent_council.py`: `MIN_MEMBERS, MAX_MEMBERS = 2, 6` — størrelsen vælges ved booking.
- `_validate()` kræver kun `role` (fri streng) + `task` (unik pr. medlem). **Ingen rolle-whitelist.**
- `agent_contract_service.dispatch_agent(role=...)` — `role` bæres videre uvalideret. Standard er `researcher`, men det er en default, ikke en port.
- Konklusion: «ikke fast rolle-liste, ikke fast størrelse, min vurdering ved bestilling» er **allerede sandt**.

### Fire steder roller defineres (den forvirring der skal ryddes)
1. `agent_contract_tools.py:64` — enum med 5 navne i Task-skemaet (den smalle dør).
2. `role_registry.py` + `custom_roles.json` — custom-roller, filen findes ikke (tomt register, klar til brug).
3. `AGENT_ROLE_TEMPLATES` i `agent_runtime_base.py` — de indbyggede templates.
4. `missions_pipeline._VALID_ROLES` — fast liste med 5 helt andre navne. **Allerede registreret som `orphaned` i `liveness_registry.py:227` («nul callers»).** Død, men til stede.

### Hvor en delt liste ville bo — og hvorfor det ikke er worktree'et
Barnet kan skrive til præcis tre tabeller, alle per-barn:
- `agent_assignments` (egen række), `agent_runs` (egen kørsel), `agent_result_outbox` (eget resultat).
`agent_councils.members_json` er en **statisk blob** skrevet én gang af parenten — intet medlem kan claim'e eller afslutte en del.
=> Der findes reelt intet sted et medlem kan sige «jeg tager del 2».

Men: en delt liste er en **tabel**, ikke en fil. Worktree-isoleringen rammer filer. Så den blokerer ikke — det gør kun fraværet af en tabel + et værktøj.

### Vurdering: byg ikke den skrivbare liste endnu
- Council er bevidst isoleret («Du kender ikke de andre medlemmers svar; det er meningen») — det er styrken, ikke en mangel.
- En skrivbar liste koster claim-konflikter, forældede claims og rækkefølge. Det er kun prisen værd når arbejdet er **dynamisk** (medlemmer konkurrerer om de samme del-opgaver).
- Er størrelsen besluttet ved booking, er listen også besluttet ved booking — så skal den ikke være *skrivbar*, den skal være **synlig**.
- Rækkefølge: (1) gør `AgentDispatchPane` i stand til at vise den plan der faktisk dispatches, (2) claiming kun når vi har en sag hvor medlemmer reelt skal omfordele.

---

## Målt 10/11-2026, 18:20 — "den døde kode" er allerede pensioneret, men ufuldstændigt

### De fem "døde" er ikke døde — de er PENSIONERET med håndhævelse
`core/tools/tool_scoping.py:31` har `RETIRED_AGENT_CREATION_TOOLS`:
`scout_agent`, `spawn_agent_task`, `dispatch_code_mode_task`, `dispatch_to_claude_code`, `task`.

Håndhævet TRE steder, ikke ét:
- `tool_scoping.py:698` — trækkes fra ALLE scopes (`result -= RETIRED_...`)
- `tool_scoping.py:738` — `is_tool_allowed()` returnerer False (server-side eksekveringsport)
- `load_more_tools.py:30` — kan ikke genoplives via lazy-load

Kommentaren siger det selv: *"Dermed kan load_more_tools, en gammel session-lås eller
samtalehistorik ikke genoplive en parallel agent-livscyklus."*

**Konklusion: de er ikke død kode der skal ryddes. De er bevidst lukket — og lukket rigtigt.**
At slette dem ville fjerne den eneste grund til at `is_tool_allowed` kan afvise dem.

### MEN: to huller i pensioneringen
1. **`relay_to_agent` og `cancel_agent` er IKKE i listen.** De står stadig i
   `copilot_tool_pruning.py:360` som annoncerede agent-værktøjer. `cancel_agent` er
   desuden en FUNKTION i `agent_runtime_spawn` der kaldes af Central-UI'et
   (`central.py:176`) — ikke et modelvendt værktøj. Navnekollision, ikke et værktøj.
2. **`simple_tools_definitions.py` bærer stadig definitionerne** (linje 284, 2876, 2993).
   De er usynlige for mig, men de fylder i katalog-bygningen og kan dukke op i en
   kode-sti der ikke går gennem `tool_scoping`.

### Todo-rækken: LEVENDE, velbygget — og ubrugt af mig
- Persisteret via `state_store` (`agent_todos.py`), vist i HVER prompt (`prompt_contract.py:2143`)
- I scope for BÅDE chat og code (`tool_scoping.py:240` og `:365`)
- Har UI-ruter i Desk (`cowork.py:395-432`, `jarvisx_sessions.py:129`)
- **0 kald fra mig.** De 55 filer der matcher `todo_` er bash-kommandoer der NÆVNER todo,
  ikke todo-kald. Målt: nul faktiske `todo_*` tool_name i tool_results.

**Det er ikke et systemproblem. Det er min adfærd.** Bjørn har ret: rækken burde bruges.

### Hvorfor de aldrig blev kaldt — de tre forklaringer, målt
| Værktøj | Hvorfor 0 kald | Er det en fejl? |
|---|---|---|
| `spawn_agent_task`, `scout_agent`, `dispatch_code_mode_task` | Pensioneret 30/9 efter måling: `scout_agent` 35 kald, `spawn_agent_task` NUL i 30 dage. `Task` overtog. | Nej — korrekt beslutning, dokumenteret i `test_copilot_tool_pruning.py:209` |
| `convene_agent_council`, `review_agent_work`, `decide_agent_approval`, `interrupt_agent` | Annonceret, men jeg har ikke haft en sag hvor de var det rigtige valg | **Nej — det er reelt ubrugt kapacitet, ikke fejl-flag** |
| `todo_*` (5 stk) | Annonceret i scope, vist i prompt — jeg brugte dem bare ikke | **Ja — min adfærd, ikke systemets** |

### Det ægte fund
Bjørns hypotese var: *"er de aldrig kaldt fordi systemet flaggede forkert?"*
**Svar: nej for de fem pensionerede (de blev flagget RIGTIGT), og nej for todo (de blev
flagget rigtigt — jeg brugte dem bare ikke).** Den eneste ægte fejlflagning er
`relay_to_agent`/`cancel_agent`, der stadig annonceres som agent-værktøjer uden at være det.

---

## Team som parameter på Task — design (målt 10/11-2026, aften)

### Hvad der allerede findes
`agent_council.py` ER en team-motor, ikke en separat arkitektur:
- `MIN_MEMBERS, MAX_MEMBERS = 2, 6` — størrelsen vælges ved booking, ikke fast.
- `_validate()`: `role` er en **fri streng** (ingen whitelist), hvert medlem skal have en
  **unik** opgave (ellers er det ét svar talt flere gange), og alle får SAMME faktagrundlag
  i adskilte kontekster.
- `advance()` er supervisoren: opretter syntesen når alle medlemmer er terminale, lukker
  rådet når syntesen er færdig, vækker parenten på syntesen — ikke på hvert medlem.
- **`advance()` KALDES I DRIFT**: `agent_contract_service.py:748` inde i reconcile-sweepen.
  Motoren er levende; det er indgangen (`convene_agent_council`, 0 kald) der er død.

### Hvad der IKKE findes
- `team` som begreb: nul referencer i `agent_contract_tools.py`,
  `agent_contract_service.py`, `db_agent_contract.py`. Ren tavle.
- Delt opgaveliste: `members_json` er en statisk blob parenten skriver én gang. Intet
  medlem kan skrive "jeg tager del 2".
- Skrivende team-medlemmer: et rådsmedlem får faktagrundlag og afgiver en vurdering.
  Der er ingen `subagent_type` pr. medlem — alle er læsende.

### Beslutning: navnet er HÅNDTAGET, ikke NØGLEN
`team.name` er en fri, menneskelig etiket ("råd vedr. dispatch-arkitektur"). Grupperingen
sker på et genereret `team_id`. Ellers kolliderer to råd med samme navn i historikken, og
"hvordan gik team X?" bliver et spørgsmål uden entydigt svar.

Systemet aflæser: tilstedeværelse af `team` (→ mode, afledt — ikke læst af navnet),
`team.name` (visning/gruppering), `members[].role` (fri streng → tool_policy via
role_registry), `members[].task` (unik, valideret), `facts` (fælles grundlag).

### To slags team — forskellen er om medlemmerne SKRIVER
1. **Råd** (rådgivende): læsende, isolerede, fælles fakta, syntese. **Findes i dag.**
2. **Arbejdshold**: skrivende, eget worktree hver, kræver en delt plan. **Findes ikke.**

Worktree-isoleringen blokerer ikke en delt liste: listen er en TABEL, ikke en fil. Det der
blokerer er at et medlem i dag kun kan skrive til tre tabeller — alle per-barn.

### Rækkefølge (billigst først)
1. Absorbér `convene_agent_council` som `Task(team={...})` og pensionér det separate
   værktøj. Én dør. Lille.
2. `team_id` genereret + `team.name` som etiket; gruppering synlig i Desk. Lille.
3. `AgentDispatchPane` (38 linjer) viser den plan der faktisk dispatches — synligt før
   skrivbart. Lille.
4. Skrivende team-medlemmer + delt plan. Stort — og kræver en beslutning om worktrees.

### Den fælde der allerede har kostet én gang
`cluster_daemon.py:1597-1625`: det autonome council blev taget ud 15/9 med Bjørns ord
"council er spildt tokens ... hvilken effekt har det uden du [læser det]". Konklusionerne
blev ALDRIG læst. Enhver team-konstruktion skal derfor svare på **hvem der læser
resultatet** før den bygges — ellers genopbygger vi præcis det der blev dræbt.
