# Eksternt review — V2 Remote-paritet (spec + fase 1-plan)

Reviewer: Claude (Opus), 2026-09-02
Anmodet af: Bjørn. Næste led i kæden: Codex, derefter Jarvis' endelige review.
Anmeldte dokumenter:
- `docs/superpowers/specs/2026-09-02-jarvis-mobile-companion-v2-remote-design.md`
- `docs/superpowers/plans/2026-09-02-jarvis-mobile-companion-v2-remote-phase1.md`

## Hvordan jeg har reviewet

Jeg har efterprøvet **hver server-påstand** mod koden og databasen frem for at
vurdere designet på papiret. Det er værd at sige først: **alt det Jarvis
påstod, holder.**

| Påstand | Resultat |
|---|---|
| `/mc/approvals` capper ved 5 (`mission_control_common.py:588`) | ✅ korrekt |
| `push_dispatcher` har kun 3 kinds, ingen `approval_requested` | ✅ korrekt |
| `recent_capability_approval_requests(limit=…)` findes | ✅ korrekt |
| `_owner_of_run(run_id)` findes (fallback-modtager) | ✅ korrekt |
| `_persist_capability_approval_request` linje 2177, stempler `scheduled_for_user_id` | ✅ korrekt, linjetal præcist |
| `sudo_approval_window_allows_request` findes | ✅ findes (men se F6) |
| Capability-approvals har ingen timeout | ✅ korrekt for **den** tabel (se F1) |
| Approve/execute-endpoints findes | ✅ korrekt |
| App-filer (`relativeDate.ts`, `tokens.ts`, `push.ts`, `ApprovalCard.tsx`) | ✅ findes på branchen |

Det er usædvanligt god research. Fejlene nedenfor handler næsten alle om
**rækkevidde** — hvor langt en verificeret påstand må generaliseres — ikke om
metode.

---

## F1 — KRITISK: der er TO godkendelsessystemer, og speccen modellerer kun det ene

**Fund.** Runtime har to uafhængige approval-systemer:

| | `capability_approval_requests` | `tool_intent_approval_requests` |
|---|---|---|
| Udløb | **ingen** | **`_APPROVAL_TTL = 15 min`** |
| Model | asynkron, fingerprint-beskyttet | vindue der lukker |
| Verb | approve → execute (to trin) | approve/deny |

Speccens beslutning 2 siger: *«Ingen auto-timeout på godkendelser. Serveren har
ingen timeout-mekanisme, og behøver ingen.»* Det er **sandt for
capability-approvals og forkert for tool-intent-approvals.**

**Hvorfor det er kritisk, ikke akademisk.** Det kort Bjørn faktisk sad med i
dag — og bad om hjælp til at godkende — var et *tool-intent*-kort. Serveren
svarede:

    POST /mc/tool-intent/approve → HTTP 409
    "Tool intent approval is not pending; current state is expired."

Appen, som den er specificeret, ville altså **ikke** have løst det problem han
oplevede. Værre: `tool_intent_approval_requests` indeholder i dag rækker fra
juli og august der stadig står som `approval_state='pending'`, fordi udløb
aldrig skrives tilbage. En kø der læser `status` ville vise seks uger gamle,
døde kort som ventende.

**Rettelse.**
1. Skriv eksplicit i speccen hvilket system fase 1 dækker, og hvad det andet
   koster at udelade.
2. Hvis tool-intent kommer med: kortet **skal** vise resterende tid og
   deaktiveres ved udløb. Filtrér på `expires_at`, **aldrig** på
   `approval_state`.
3. Uanset valg: en oprydning der markerer udløbne rækker som `expired` hører
   hjemme i fase 1, ellers arver appen en kø fuld af spøgelser.

**Hvorfor — lektien.** Når et begreb har to implementeringer i samme kodebase,
er det klassiske fejltrin at verificere den ene og formulere konklusionen
generelt. «Verificeret i koden» skal navngive *hvilken* kode. En hurtig test:
kan du skrive tabelnavnet ved siden af påstanden? Kan du ikke, har du ikke
verificeret den endnu.

---

## F2 — KRITISK: `/mc/runs` har præcis samme 5-cap som `/mc/approvals` — og planen retter kun den ene

**Fund.** Samme fil, 13 linjer fra hinanden:

    mission_control_common.py:575   "persisted_recent_runs": recent_visible_runs(limit=5),
    mission_control_common.py:588   "recent_approval_requests": recent_capability_approval_requests(limit=5),

Og ruten skærer kun ned, aldrig op — nøjagtig det mønster Jarvis selv
beskrev for approvals:

    mission_control_runs_ops.py:95  recent_runs = list(surface.get("persisted_recent_runs") or [])[: max(limit, 1)]

`GET /mc/runs?limit=50` returnerer altså **højst 5 runs**.

**Konsekvens.** Accept-kriterie 1 («Arbejde-tab viser A/B/C-runs samlet, aktive
+ afsluttet-i-dag, grupperet») kan ikke opfyldes. Tasks-listen — kernen i hele
Arbejde-rummet — viser maksimalt fem elementer uanset hvad appen beder om.
Værst: den fejler *tavst*, med en plausibel liste.

**Rettelse.** Udvid Task 2 til at rette begge overflader, eller lav den om til
«fjern 5-cap-mønsteret i `_visible_run_surface` og
`_capability_invocation_surface`». Tilføj et accept-kriterie: `?limit=20` med
20 seedede runs returnerer 20.

**Hvorfor — lektien.** Da du fandt fejlen, fandt du i virkeligheden et
**mønster**: «overfladen hardcoder et loft, ruten kan kun skære ned». Når en
fejl har en form, så søg efter formen — ikke efter forekomsten. Ét `grep -n
"limit=5"` i den fil ville have fanget begge.

---

## F3 — KRITISK: C-runs findes ikke i `/mc/runs`. A/B/C-modellen er en hensigt, ikke en server-kendsgerning

**Fund.** Speccen siger: *«Alle tre eksponeres som runs af mission-control
(`/mc/runs`).»* Data siger noget andet. Run-id-præfikser i `visible_runs`,
seneste 7 døgn:

    autonomous-   525
    visible-      133
    (ingen agent-/C-runs overhovedet)

Agent-arbejde bor i en **selvstændig tabel**, `agent_runs` (155 rækker,
seneste 23. juli), og eksponeres kun **pr. agent** via
`/mc/agents/{agent_id}/runs` — som i øvrigt også har `limit=5`.

**Konsekvens.** Tasks-listen kan ikke vise C fra ét kald. Den ville skulle
opremse agenter og fan-oute. Og C har været dødt siden 23. juli, så fase 1
ville bygge en kolonne til noget der ikke findes.

**Rettelse.** Vælg ét:
- **(a) Ærlig fase 1:** Tasks viser A + B. Skriv det i speccen og i
  accept-kriteriet. C tilføjes i fase 2 sammen med Review (som alligevel er
  C-orienteret).
- **(b) Server først:** byg en samlende `/mc/work`-overflade der forener
  `visible_runs` + `agent_runs` til én liste med et ægte `source`-felt. Så er
  A/B/C-løftet sandt, og appen forbliver simpel.

Jeg anbefaler **(a)** til fase 1 og **(b)** som fase 2's server-opgave.

**Hvorfor — lektien.** En påstand om *modellen* skal efterprøves mod *data*,
ikke kun mod koden der kunne producere dem. Én SQL-forespørgsel over
run-id-præfikser afgjorde det på tredive sekunder. Kode viser hvad der er
muligt; data viser hvad der faktisk sker.

---

## F4 — KRITISK: leverance-kriteriet kan ikke opfyldes af fase 1's opgaver

**Fund.** Målet er formuleret som: *«Bjørn kan lukke appen → få en notifikation
→ åbne → godkende fra Arbejde-tabben → **og run'et fortsætter**.»*

Men `POST …/approve` gør præcis én ting — den stempler `approved_at`:

    approve_capability_approval_request(request_id, approved_at=…)

Der findes **intet** der auto-eksekverer efter godkendelse. Selve arbejdet sker
først når nogen kalder det separate `…/execute`-endpoint, eller når Jarvis
tilfældigvis kalder capability'en igen og fingerprintet matcher.

Fase 1's opgaver kalder kun `/approve`. Så efter Bjørns tryk sker der —
observerbart — ingenting. Task 9 trin 3 røber det selv: den nøjes med at
verificere at «run-status afspejler approved», hvilket er noget svagere end
målsætningen.

**Rettelse.** Vælg ét, og skriv det ind begge steder:
- **(a) Gør løftet sandt:** «Godkend» kalder `/approve` og derefter
  `/execute`. Ét tryk, to kald. Bemærk konsekvensen: eksekveringsfejl lander nu
  på telefonen og skal have en fejltilstand i kortet.
- **(b) Gør løftet ærligt:** omformulér til «godkendelsen registreres, og
  forslaget udføres næste gang Jarvis kalder capability'en» — og vis den linje
  i UI'et (det er dit eget åbne spørgsmål 4, som du havde ret i at stille).

**Hvorfor — lektien.** Dette er den vigtigste fejltype i hele reviewet: et
**leverance-kriterie hvis verber ikke findes i opgavelisten.** Prøv altid at
gå baglæns fra sætningen — for hvert verbum («fortsætter»), peg på den opgave
og det endpoint der udfører det. Kan du ikke pege, er kriteriet en hensigt,
ikke en definition af færdig. Du var *tæt* på selv at fange den: dit åbne
spørgsmål 4 rammer nøjagtig mekanikken, men behandler den som et spørgsmål om
UI-tekst frem for som et hul i definitionen af færdig.

---

## F5 — VÆSENTLIG: `source`-feltet, som B/C-adskillelsen hviler på, findes ikke

**Fund.** Speccen: *«Forskellen er kun synlig i kilden (`source`-felt).»*
`visible_runs` har disse kolonner:

    id · run_id · lane · provider · model · status · started_at · finished_at
    text_preview · error · capability_id · user_id · workspace_name

Der er intet `source`. Dertil: autonome runs skriver `provider="?"` og
`model="jarvis"` (198 kørsler på tre døgn) og **ingen cost-rækker** — så
WorkTaskCard'ets «maskine/source-tag» ville vise pladsholder-skrald for hele
B-kategorien.

**Rettelse.** Udled kilden af run-id-præfikset (`visible-` = A, `autonomous-`
= B) som en midlertidig, dokumenteret aflæsning — og tilføj et rigtigt
`source`-felt når `/mc/work` bygges (F3b). Nævn i planen at B-kort ikke kan
vise model/maskine før den telemetri er rettet.

**Hvorfor — lektien.** Når et design siger «vi læser bare felt X», så kør
`PRAGMA table_info` på tabellen. Et feltnavn i en spec er en påstand på lige
fod med alle andre.

---

## F6 — VÆSENTLIG: B1 låner en mekanisme fra det forkerte system

**Fund.** B1 begrunder «Godkend altid» med
`sudo_approval_window_allows_request`. Den funktion bor i
`core/services/tool_intent_approval_runtime.py` — altså i **tool-intent**-
systemet — mens kortene i køen er **capability**-approvals. Vinduet gælder
ikke for dem. Og `_SUDO_APPROVAL_WINDOW_TTL` er **5 minutter**, hvilket er et
meget kortlivet «altid».

**Rettelse.** Enten drop «Godkend altid» helt i fase 1 (og tegn den som
deaktiveret med en ærlig forklaring), eller specificér en rigtig præfiks-regel
for capability-approvals som server-arbejde. Undgå mellemtilstanden hvor
knappen findes og gør noget andet end den siger.

**Hvorfor — lektien.** Samme rod som F1. Inden du bruger en mekanisme som
begrundelse: hvilket modul bor den i, og gælder den for det objekt du har i
hånden? Et funktionsnavn der lyder rigtigt er ikke det samme som et
anvendelsesområde der passer.

---

## F7 — VÆSENTLIG: branchen er 1690 commits bagud, og rebase er blokeret

**Fund.** Planen deler arbejdet: server på `main`, app på
`codex/jarvis-mobile-companion-v1`.

    main har 1690 commits branchen ikke har
    branchen har 120 commits main ikke har

Og `CLAUDE.md` slår fast at **rebase er blokeret** af attributions-hooks
(replay bevarer forældede Actor-trailere). Integration kan altså kun ske som
merge — af 1690 commits' drift, hvoraf en del rører netop de runtime-veje
appen skal kalde.

Planen nævner det ikke med ét ord. Det er efter min vurdering fase 1's største
tidsrisiko, større end nogen af opgaverne.

**Rettelse.** Tilføj **Task 0: bring branchen ajour med main** (merge, ikke
rebase), kør appens tests, og løs konflikter *før* Task 3 begynder at flytte
tokens. Ellers laver du en stor visuel migration oven på et fundament der
skal flyttes bagefter.

**Hvorfor — lektien.** En plan der spænder over to brancher skal navngive
integrationstrinnet. Divergens er en omkostning der vokser lydløst, og den
opdages typisk på det værst tænkelige tidspunkt — når alt andet er færdigt.

---

## Mindre punkter

- **Spec linje 38** siger «plus en limit-fix på `/mc/approvals`» — bliver til
  to fixes hvis F2 følges. Ret formuleringen så plan og spec stemmer.
- **Spec-beslutning 3 vs plan-B4** modsiger hinanden om cancel. Du har selv
  set det (åbent spørgsmål 6) — det er godt. Men lad det ikke stå: **ret
  speccen**, så to dokumenter ikke siger hver sit. Se svar nedenfor.
- **Shift-tallene (~44%, ~81%, …)** er markeret som sekundær kilde. Godt gjort.
  Overvej at flytte hele bruger-research-afsnittet til et bilag — det begrunder
  designet, men det er ikke noget en implementerende agent skal læse for at
  bygge.
- **Accept-kriterie 5** («UI matcher R1–R8, side-for-side») er ikke
  maskinelt verificerbart og vil enten blive sprunget over eller blokere.
  Gør det til en manuel tjekliste med ét punkt pr. skærm, adskilt fra de
  automatiserbare kriterier.

---

## Svar på dine seks åbne spørgsmål

1. **B1 sudo-only?** Hverken-eller — se F6. Mekanismen du støtter dig til
   gælder ikke for de kort køen viser. Drop knappen i fase 1, eller byg
   præfiks-reglen rigtigt server-side.
2. **B2 lokal dismissal?** Acceptabelt for fase 1 — men skriv i UI'et at
   kortet vender tilbage næste gang appen åbnes, ellers føles det som en fejl.
   Server-side `denied` hører sammen med F1's oprydning; overvej at slå dem
   sammen til én opgave.
3. **ChatScreen-header?** Fjern ChatScreens egen header og lad TopBar eje
   toppen. En wrapper der lader to komponenter forhandle om samme areal er
   den slags der giver «hoppen» ved tilstandsskift — præcis det speccens
   mikro-interaktions-afsnit lover at undgå.
4. **Forklarende linje om deferred approve?** Ja — men det er større end
   UI-tekst. Se F4: det er dit leverance-kriterie der ikke holder.
5. **Token-migrationens rækkevidde?** Migrér alt på én gang, som du foreslår.
   To parallelle paletter er værre end én stor ændring, og de omdøbte nøgler
   giver dig typefejl som tjekliste — det er en god idé. Men gør det **efter**
   Task 0 (F7), ikke før.
6. **Cancel i fase 1?** Din læsning er rigtig: B4 vinder. Speccens beslutning 3
   svarer på *om det er tilladt*, ikke *hvornår det bygges*. Ret speccen til at
   sige «B/C kan afbrydes fra mobilen — fase 2», så dokumenterne ikke skændes.

---

## Samlet vurdering

Speccen er den bedste jeg har set fra Jarvis: research med navngivne kilder,
en selv-review der fandt en ægte serverfejl, og åbne spørgsmål der peger på de
rigtige steder. Disciplinen med «verificeret i kode» er den rigtige vane.

De fire kritiske fund har alle samme rod: **en verificeret kendsgerning blev
generaliseret ét skridt for langt.** Ét approval-system blev til «systemet»,
ét cap blev til «cappet», én tabel blev til «run-modellen», ét endpoint blev
til «run'et fortsætter». Det er ikke sjusk — det er den fejl man laver når man
er grundig nok til at tjekke, men ikke endnu har vanen med at spørge *«hvor
langt rækker det jeg lige har set?»*

Anbefaling: **ikke klar til implementering endnu.** F1–F4 skal lukkes først;
de ændrer scope, ikke bare ordlyd. Med dem rettet er det en solid plan.
