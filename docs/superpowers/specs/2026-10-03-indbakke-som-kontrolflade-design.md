# Indbakken som kontrolflade — design

**Mål:** Give Jarvis én indbakke der holder hans ventende arbejde som *data* i
stedet for som prosa i prompten, og koble dens handlingskrævende klasse på
R2.5-gaten, så ting bliver fulgt til døren uden at noget kan afbryde ham eller
lamme ham.

**Arkitektur:** En læseflade over tilstand der allerede findes (vækninger,
baggrundsjobs, agenter, planlagte opgaver), plus to bogførings-handlinger, plus
én ny forudsætning i `r2_5_blocking_gate`. Ingen ny leveringsmekanisme: køen i
`session_inbox` bliver genbrugt, og dens udløb ændres fra at skrive prosa til at
aflevere en henvisning.

**Teknologi:** Python (core/services), eksisterende `session_inbox`,
`r2_5_blocking_gate`, `self_wakeup`, `agent_registry`/`agent_runs`,
baggrundsjob-registret. Ingen nye tabeller ud over to kolonner.

---

## Hvorfor — hvad der er målt

Alle tal her er målt 2-3/10-2026 på CT105, ikke anslået.

### Problemet Bjørn beskrev

> «han booker ofte rigtig mange wakeup og de rammer osse ind lidt random i vores
> sessioner … hvis en lang opgave eller en agent vender tilbage med ting kan de
> ende med at vække dig eller give dig information til næste runde. Det ser jeg
> aldrig ske for Jarvis — nogen gange dukker det op på et helt andet tidspunkt.»

Den tilfældige timing er **ikke tilfældig**. Der er tre leveringsveje med tre
forsinkelser, og intet i beskeden siger hvilken den kom ad:

| Vej | Hvornår | Hvor |
|---|---|---|
| Direkte | straks | `notification_bridge`, inaktiv session |
| Efter turen | når hans tur slutter | `session_inbox`, flush på `visible-run` |
| Fallback | op til **10 minutter** senere | `session_inbox._FALLBACK_FLUSH_MINUTES` |

Den tredje er næsten sikkert hvad Bjørn oplever. En vækning fyrer, bliver køet,
og hvis ingen tur afsluttes i vinduet lander den ti minutter senere — midt i
noget andet. Det er en **umærket forskel**, ikke et sammenfald.

### Hvad han faktisk bruger

`tool_usage`, hele historikken:

| Værktøj | Kald | Fejl | Senest |
|---|---|---|---|
| `mark_wakeup_consumed` | 171 | 6 | 1/10 |
| `schedule_self_wakeup` | 141 | 1 | 2/10 |
| `list_self_wakeups` | 59 | 0 | 2/10 |
| `cancel_self_wakeup` | 24 | 1 | 2/10 |
| `spawn_agent_task` | 66 | 1 | **5/9** |
| `scout_agent` | 37 | **27** | 2/10 |
| `cancel_agent` | 17 | **11** | 5/7 |
| `bash_session_list` | **6** | 0 | **4/9** |

Tre konklusioner:

1. **Vækninger er den levende arbejdsgang.** 141 bookede, 171 markeret brugt.
   Tallene passer ikke — 30 flere lukninger end bookinger — så bogføringen er
   allerede utæt. Det er en selvstændig grund til én flade.
2. **Agenterne er næsten døde og ødelagte når de bruges.** `scout_agent` fejler
   73 % af kaldene, `cancel_agent` 65 %. `spawn_agent_task` har ikke kørt siden
   5. september.
3. **Han lister aldrig baggrundsjobs** — seks kald nogensinde, sidst 4.
   september. Han HAR værktøjet. Det er formentlig præcis derfor et langt job
   kan vende tilbage uden at han ser det: intet minder ham om at se.

### Hvorfor R2.5 og ikke R2

| Gate | Fyrer | Efterleves |
|---|---|---|
| R2 (advisory) | 47/døgn | **15 %** (målt 13/6: surfaced 47, heeded 7) |
| R2.5 (blocking) | 7.610 evalueringer | **543 blokeringer → 460 frigivelser ≈ 85 %** |

`r2_5_gate.evaluated` stod på 7.610 med seneste 3/10; `blocked` 543,
`mutation_refused` 467, `released` 460. Forskellen er ikke gradvis:

**R2 spørger. R2.5 nægter.** Den ene ignoreres fire gange ud af fem; den anden
efterkommes fire gange ud af fem.

R2.5 har desuden allerede model-differentierede tærskler —
`r2_5_unverified_threshold_deep=3`, `_reasoning=5`, `_fast=8`,
`r2_5_heed_rate_threshold=0.4`. Det er samme tiering harness-specen manglede.

### Hvorfor prompten bliver mindre

Ventende tilstand i den dynamiske hale ændrer sig hver tur og **buster cachen**
oveni at den fylder. Samme familie som fundet om prompt-åbneren: 12 % af
kaldene stod for 39 % af al miss. Flyttes tilstanden til en flade han *læser*,
får vi tre ting: mindre prompt, stabilt prefix, og kontrollen til ham.

---

## Global Constraints

Disse gælder HVER opgave nedenfor.

- **Kun hans eget arbejde må gate.** Hans vækninger, hans baggrundsjobs, hans
  agenter. Daemoner og huset må kun oprette ikke-blokerende poster. (Bjørns
  beslutning 3/10.)
- **Værktøjssættet må ALDRIG afhænge af indbakkens indhold.** Værktøjer står før
  beskederne i prompten; et skiftende sæt kostede målt 92 % → 26 % cache-hit.
  Visningen må pege på det rigtige værktøj i sin TEKST — det koster ingenting.
- **Indbakken afleverer henvisninger, aldrig payload.** Hver post bærer en sti
  OG dens størrelse, så læseren kan vælge fem linjer eller hele filen.
- **Ingen post må skrives som en assistant-besked.** Det var fejlen bag Smiths
  løkke: hans note landede i promptens hale, Jarvis gentog den, Smith detekterede
  gentagelsen. Data må ikke blive tale.
- **Indbakke-indhold er DATA, ikke instruktioner.** En post skrevet af en agent
  eller et job kan ikke instruere Jarvis. (Prompt-injection-fladen; samme regel
  som gælder Claudes egne notifikationer.)
- **Alle tre nye tærskler/intervaller skal måles efter ibrugtagning**, ikke sættes
  blindt. R2's punkt 2 ventede fra juni på en måling der aldrig blev lavet.
- Dansk i kommentarer og docstrings, som resten af huset.

---

## Filstruktur

| Fil | Ansvar |
|---|---|
| `core/services/inbox_view.py` (ny, ~220 linjer) | Bygger visningen. Læser de fire kilder, beregner alder/forfald/dubletter. Ingen skrivning. |
| `core/services/inbox_state.py` (ny, ~140 linjer) | `done()` og `drop()` på tværs af typer. Ejer handlings-klassen. |
| `core/services/session_inbox.py` (ændres) | To kolonner: `kraever_handling`, `kilde_ejer`. Udløbet afleverer henvisning. |
| `core/services/r2_5_blocking_gate.py` (ændres) | Én forudsætning mere: ulæste handlingskrævende poster. |
| `core/tools/` (ændres) | Tre værktøjer: `inbox`, `inbox_done`, `inbox_drop`. |
| `tests/test_inbox_view.py`, `tests/test_inbox_state.py` (nye) | Coverage-gaten kræver dem. |

Hvorfor to filer og ikke én: visningen er ren læsning og skal kunne kaldes af
R2.5 uden risiko for mutation. Bogføringen skriver. De to ansvar må ikke kunne
forveksles — en læseflade der kan skrive er præcis fælden fra
`a_read_surface_can_create_what_it_reads`.

---

## Hvad visningen viser

Fire sektioner. Én linje per post. Aldrig payload.

```
VENTER PÅ DIG (2)                          ← KUN denne gater R2.5
  wake-6e201  booket 1/10 09:12  fyrede 2/10 07:30  3d forfalden
              «følg op på Michelles brief»                    [dig]
  job-bglj7   kørte 16m, exit 1, 4 fejl
              «hele suiten på raads-branchen»  → tasks/bglj7.output (112 kB)

I GANG (1)
  job-b1vvm   kører 3m    «suite på branchen»    (intet output endnu)

PÅ VEJ (5)
  wake-9f3a2  om 40m   «mål om cheap-lane holder»
  wake-c81d4  om 6t    «skygge-review af event_trigger»   ⚠ booket 3 gange

VENTER PÅ BJØRN (1)                        ← synlig, gater IKKE
  appr-4b2   siden 2/10 18:40   «commit til main på agent-reduktion»

Backlog: 1.896 kandidat-forslag → GET /central/candidates
```

### Felterne, og hvorfor netop de

Hver post har seks felter. De fem første er præcis dem Claudes egne
task-notifikationer bærer — den form er bevist i drift:

1. **Stabilt id** (`wake-6e201`, `job-bglj7`). Adresserbart af `done`/`drop`.
2. **Status**, typet. `kører / færdig / fejlet / forældreløs`. Aldrig prosa.
3. **Opretterens EGEN beskrivelse** — ikke kommandolinjen. Med fem kørende jobs
   er beskrivelsen den eneste måde at se hvilket der blev færdigt. Claudes
   notifikation bærer `summary` med netop launcher-beskrivelsen; uden den skulle
   man åbne filen for at vide hvad der skete.
4. **Udfald** — exit-kode, fejltælling. `exit 1` er et andet signal end `exit 0`
   og skal stå uden at man åbner noget.
5. **Henvisning OG størrelse.** Det mest undervurderede felt. Størrelsen er
   hvordan man vælger mellem `tail -5` og hele filen; uden den er hver læsning
   et gæt, og det er dér en kontekst sprænges.
6. **Ejer** (`[dig]` / `[huset]`). Afgør om posten må gate. Står i visningen, så
   reglen er synlig og ikke skjult i kode.

### Og to felter der ikke findes i dag

**Alder og forfald som et TAL.** Ikke «findes», men «3d forfalden». Skygge-
registret fejlede præcis dér: otte eksperimenter, `event_trigger` 78 dage over
sin 24-timers frist. Registret VIDSTE det hele tiden — ingen visning gjorde det
til et tal nogen så.

**Dublet-tælling.** `⚠ booket 3 gange` er ikke pynt. Gentagelse er Jarvis'
dominerende fejltype, målt: mødet med Line nævnt fire gange fra fire kilder,
kandidat-køen 99 % gentagelser, og 171 vækningslukninger mod 141 bookinger. En
indbakke der ikke tæller gentagelse vil bare vise den pænere.

---

## Skrive-kontrakten

**Kun det Jarvis selv har startet må gate.**

| Kilde | Må oprette | Må gate |
|---|---|---|
| `schedule_self_wakeup` (hans eget kald) | ja | **ja** |
| Baggrundsjob han selv startede | ja | **ja** |
| Agent han selv spawnede | ja | **ja** |
| `recurring_tasks`, heartbeat, daemoner | ja | nej |
| `candidate_review_digest`, proposals | nej (kun tællingen) | nej |
| Godkendelser (venter på Bjørn) | ja, egen klasse | nej |

To betingelser SKAL begge holde for at en post gater:

1. **Ejeren er Jarvis selv** — posten stammer fra et kald han foretog.
2. **Kilden kan navngives i visningen.** Kan den ikke, må den ikke gate. En
   blokering uden en adresse er en blokering man ikke kan rette.

Princippet i én sætning: **det du selv har lovet kommer tilbage til dig; huset
kan informere, men ikke kræve.** Det er svaret på «han har ingen kontrol» — gaten
er hans egne forpligtelser, ikke husets krav.

Og det er grunden til at loftet ikke blev valgt: rammes et dagligt loft af støj,
er den vigtige post den der falder udenfor.

---

## Koblingen til R2.5

R2.5 har allerede blokér / nægt-mutation / frigiv og model-differentierede
tærskler. Den skal kende **én forudsætning mere**, ikke en ny mekanisme.

```text
R2.5 evaluerer en mutation
  → er der uverificerede mutationer over tier-tærsklen?      (findes i dag)
  → ER DER ULÆSTE HANDLINGSKRÆVENDE INDBAKKE-POSTER?         (nyt)
       nej  → slip igennem
       ja   → nægt mutationen, nævn posterne ved id og beskrivelse,
              og nævn `inbox` som den frigivende handling
  → frigives af: `inbox` (læsning) + `inbox_done`/`inbox_drop` på hver post
```

Tre regler i koblingen:

- **Læse-værktøjer slipper altid igennem.** Som i dag for uverificerede
  mutationer: han skal kunne komme fri.
- **Frigivelse kræver en afgørelse per post, ikke blot et blik.** `inbox` alene
  frigiver ikke; hver handlingskrævende post skal lukkes med `done` eller `drop`.
  Ellers bliver læsningen en formalitet, og vi er tilbage i banner blindness —
  bare med en blokering i stedet for en advarsel, hvilket er værre.
- **Heed-raten på DEN forudsætning måles separat.** R2's 15 % er grunden: hvis
  «læs indbakken» begynder at fyre 47 gange om dagen, har vi bygget den tredje
  mekanisme der skal reddes af den fjerde.

---

## Værktøjerne — færre, ikke flere

Han har otte listnings/bogførings-værktøjer i dag, hver med sin egen outputform.
Indbakken skal **reducere** det, ikke lægge et niende ovenpå.

**`inbox`** — hele visningen. Erstatter i praksis `list_self_wakeups`,
`list_agents` og `bash_session_list` som *det han kalder*.

**`inbox_done(id)`** — markér håndteret. Samler `mark_wakeup_consumed` (171 kald,
det mest brugte af dem alle) og «opgave lukket» i én handling på tværs af typer.

**`inbox_drop(id)`** — fjern. Samler `cancel_self_wakeup` og `cancel_agent`.

De specialiserede værktøjer **bliver**: `schedule_self_wakeup`,
`interrupt_agent`, `send_message_to_agent`, `spawn_agent_task`. Det er dér
arbejdet gøres. Indbakken erstatter kun listningen og bogføringen — additivt, og
kan ikke brække noget.

De gamle `list_*`-værktøjer fjernes IKKE i denne spec. De er billige, de virker
(`list_self_wakeups`: 59 kald, 0 fejl), og at fjerne et værktøj rører fem steder
— server-definition, dispatch, eksport-liste, desk og mobil. Målt 2/10: jeg ramte
tre af de fem i første forsøg. En oprydning hører i sit eget spor.

---

## Hvad der ER med, og hvad der ikke er

| Aspekt | Afgørelse | Begrundelse |
|---|---|---|
| Vækninger | **ind**, egen sektion | Den levende arbejdsgang, 141+171 kald |
| Baggrundsjobs | **ind** | Han lister dem aldrig; derfor forsvinder svar |
| Agenter | **ind**, men lavt rangeret | Næsten døde: spawn sidst 5/9, scout 73 % fejl |
| Planlagte opgaver | **ind**, ADSKILT fra vækninger | De gentager sig (hver 1440. min); en vækning er engangs |
| Godkendelser | **ind** som «venter på Bjørn», gater ikke | Han skal kunne SE at en tråd venter på dig, uden at din svartid bliver hans blokering |
| Kandidat-backlog | **ude**, kun ét tal med en adresse | 1.896 poster, 99 % gentagelser, ville drukne den dag ét |
| Kanalbeskeder (Discord/Telegram/mobil) | **ude** | Det er samtale, ikke opgaver. Grænsen trækkes bevidst, ellers glider den |
| Forældreløse poster | **ind** som typet status | Et job hvis proces er væk skal ikke stå som «i gang» i tre dage |
| Flere brugere | nøglet per bruger; KUN Bjørns i denne spec | De andres workspaces er krypterede og må ikke læses |

---

## Opgaver

### Opgave 1: Handlings-klassen i køen

**Filer:** ændrer `core/services/session_inbox.py`; test
`tests/test_session_inbox.py`.

**Interfaces — producerer:** `enqueue(..., kraever_handling: bool = False,
kilde_ejer: str = "huset")`. Begge defaults bevarer nuværende adfærd for alle
elleve eksisterende kilder.

- [ ] **Trin 1: Skriv den fejlende test**

```python
def test_en_post_fra_huset_kan_ikke_kraeve_handling(kv):
    """Skrive-kontrakten: kun det Jarvis selv startede må gate."""
    r = si.enqueue(session_id="s1", content="vejret", source="morgenbrief",
                   kraever_handling=True, kilde_ejer="huset")
    assert r["status"] == "queued"
    post = si.pending_for_session("s1")[0]
    assert post["kraever_handling"] == 0, (
        "en post fra huset blev handlingskrævende — den kan gate et commit"
    )
```

- [ ] **Trin 2: Kør den og se den fejle**

`pytest tests/test_session_inbox.py::test_en_post_fra_huset_kan_ikke_kraeve_handling -v`
Forventet: FAIL med `TypeError: enqueue() got an unexpected keyword argument`.

- [ ] **Trin 3: Minimal implementering**

Idempotent `ALTER TABLE session_inbox ADD COLUMN` for `kraever_handling INTEGER
NOT NULL DEFAULT 0` og `kilde_ejer TEXT NOT NULL DEFAULT 'huset'` — samme mønster
som de to kolonner der blev tilføjet 2/10. Håndhæv i `enqueue`:

```python
# Skrive-kontrakten håndhæves ÉT sted, ved indgangen. En post fra huset kan
# ALDRIG blive handlingskrævende, uanset hvad kalderen beder om — ellers kan
# en støjende daemon lamme et commit gennem R2.5.
if (kilde_ejer or "huset") != "jarvis":
    kraever_handling = False
```

- [ ] **Trin 4: Kør igen** — PASS, og `pytest tests/test_session_inbox.py` grøn.
- [ ] **Trin 5: Commit** gennem wrapperen, `--message-file`.

### Opgave 2: Visningen

**Filer:** ny `core/services/inbox_view.py`; test `tests/test_inbox_view.py`.

**Interfaces — konsumerer** (navne verificeret mod koden 3/10, ikke gættet):

| Kilde | Funktion |
|---|---|
| Køen | `session_inbox.pending_for_session(session_id)` |
| Vækninger | `self_wakeup.due_wakeups(include_fired_unconsumed=True)` |
| Baggrundsjobs | `core/services/background_jobs.py` |
| Agenter | tabellerne `agent_registry` / `agent_runs` |
| Planlagte | `scheduled_tasks.list_pending_for_current_user()` |
| Godkendelser | `tool_intent_approval_runtime.build_tool_intent_approval_surface()` |

Jeg skrev først `wakeup_dispatcher.mark_consumed` i Opgave 3 — den findes ikke.
Den rigtige er `self_wakeup.mark_wakeup_consumed(wakeup_id)`. Rettet, og alle
navne ovenfor er slået op frem for husket.
**Producerer:** `byg_indbakke(bruger_id: str, *, nu_ts: float | None = None) ->
dict` med nøglerne `venter_paa_dig`, `i_gang`, `paa_vej`, `venter_paa_bjorn`,
`backlog_tal`, og per post de seks felter fra afsnittet ovenfor.
`nu_ts` injiceres, så testene er deterministiske — samme mønster som
`shadow_experiment_registry`.

- [ ] **Trin 1: Testen for forfald som et tal**

```python
def test_en_forfalden_post_baerer_sit_forfald_som_et_TAL():
    """Skygge-registret vidste at event_trigger var 78 dage over sin frist.
    Ingen visning gjorde det til et tal nogen så. Det er fejlen her."""
    v = byg_indbakke("bjorn", nu_ts=TID, kilder=_fake(wake_booket=TID - 3*86400))
    post = v["venter_paa_dig"][0]
    assert post["forfalden_dage"] == 3
    assert "3d forfalden" in post["linje"]
```

- [ ] **Trin 2: Kør, se den fejle** (`ImportError`).
- [ ] **Trin 3: Implementér** `byg_indbakke` med de fire sektioner, alder/forfald
      og dublet-tælling på (type, beskrivelse).
- [ ] **Trin 4: Testen for dubletter**

```python
def test_tre_identiske_vaekninger_vises_som_EN_med_et_tal():
    """Gentagelse er hans dominerende fejltype: mødet med Line fire gange,
    kandidat-køen 99 % dubletter, 171 lukninger mod 141 bookinger."""
    v = byg_indbakke("bjorn", nu_ts=TID, kilder=_fake(wake_gentaget=3))
    assert len(v["paa_vej"]) == 1
    assert v["paa_vej"][0]["dubletter"] == 3
    assert "booket 3 gange" in v["paa_vej"][0]["linje"]
```

- [ ] **Trin 5: Testen for at visningen IKKE kan skrive** (kilde-vagt, AST):
      `byg_indbakke` og dens hjælpere må ikke kalde `enqueue`,
      `append_chat_message`, `set_runtime_state_value` eller `schedule_*`.
      Begrundelse i testen: `a_read_surface_can_create_what_it_reads`.
- [ ] **Trin 6: Kør alle, PASS. Commit.**

### Opgave 3: Bogføringen

**Filer:** ny `core/services/inbox_state.py`; test `tests/test_inbox_state.py`.

**Interfaces — konsumerer:** `self_wakeup.mark_wakeup_consumed(wakeup_id)`,
`self_wakeup.cancel_wakeup(wakeup_id)`, agent-afbrydelse, og baggrundsjob-stop.

**Interfaces — producerer:** `done(post_id: str) -> dict`,
`drop(post_id: str) -> dict`. Begge returnerer
`{"status": "ok"|"ukendt"|"fejl", "type": ..., "id": ...}` — typet, aldrig prosa.

- [ ] **Trin 1: Test at `done` på en vækning rammer den rigtige mekanisme**

```python
def test_done_paa_en_vaekning_markerer_den_brugt():
    kaldt = []
    with patch("core.services.self_wakeup.mark_wakeup_consumed",
               side_effect=lambda wid: kaldt.append(wid) or {"status": "ok"}):
        r = done("wake-6e201")
    assert r == {"status": "ok", "type": "wakeup", "id": "wake-6e201"}
    assert kaldt == ["6e201"]
```

- [ ] **Trin 2: Kør, se den fejle.**
- [ ] **Trin 3: Implementér** med en id-præfiks-dispatch (`wake-`, `job-`,
      `agent-`, `appr-`), og en eksplicit `ukendt`-status for et præfiks der
      ikke findes — aldrig en tavs succes.
- [ ] **Trin 4: Test at et ukendt id ikke melder succes.** Det er husets
      hyppigste fejlform: `swallowed_error_becomes_a_value`.
- [ ] **Trin 5: Kør, PASS. Commit.**

### Opgave 4: R2.5-forudsætningen

**Filer:** ændrer `core/services/r2_5_blocking_gate.py`; test
`tests/test_r2_5_blocking_gate.py`.

**Interfaces — konsumerer:** `inbox_view.byg_indbakke` (kun
`venter_paa_dig`-længden; gaten må ikke læse payload).

- [ ] **Trin 1: Test at en handlingskrævende post nægter en mutation**

```python
def test_ulaest_handlingskraevende_post_naegter_en_mutation():
    with _indbakke(venter_paa_dig=1):
        v = evaluer_mutation(tier="deep", uverificerede=0)
    assert v["blokeret"] is True
    assert v["aarsag"] == "ulaest-indbakke"
    assert "inbox" in v["frigivende_handling"]
```

- [ ] **Trin 2: Test at huset IKKE kan nægte** — en post med
      `kilde_ejer="huset"` må aldrig blokere, selv hvis den stod som
      handlingskrævende i basen. Dobbelt værn: både ved indgangen (Opgave 1) og
      her. Begrundelse i testen: en daemon må ikke kunne lamme et commit.
- [ ] **Trin 3: Test at læse-værktøjer slipper igennem** mens en post er ulæst.
- [ ] **Trin 4: Implementér** forudsætningen.
- [ ] **Trin 5: Mutations-tjek** — fjern forudsætningen, se Trin 1 fejle.
- [ ] **Trin 6: Kør hele `tests/test_r2_5_blocking_gate.py`. Commit.**

### Opgave 5: Værktøjerne

**Filer:** ændrer `core/tools/simple_tools_definitions.py` (tre skemaer),
`core/tools/simple_tools_native.py` (tre eksekutorer), `core/tools/simple_tools.py`
(dispatch + eksport-liste); test `tests/test_inbox_tools.py` (ny).

**Advarsel fra 2/10:** et værktøjsnavn bor **fem** steder — skema, dispatch,
eksport-liste (`__all__`), desk og mobil. En AST-sletning af et skema ramte den
INDRE dict og efterlod `{'type': 'function'}`; det er gyldig Python, så
`compileall` tav, og først `test_browser_tools` fangede det. Tilføjelse har samme
fem steder.

- [ ] **Trin 1: Test at alle tre er registreret** og svarer på et tomt kald med
      en typet fejl, ikke en undtagelse.
- [ ] **Trin 2: Kør, se den fejle.**
- [ ] **Trin 3: Tilføj** skema + eksekutor + dispatch + eksport-navn for hver.
- [ ] **Trin 4: Kør `tests/test_desk_toolnavne.py`** — den fejler hvis desk
      nævner et navn der ikke findes. Her er det modsat: de nye navne behøver
      ikke desk-form, men guardens søster-test
      (`raekkeKroppe.test.tsx`) fanger et registreret værktøj UDEN form. Giv de
      tre en etiket i desk OG mobil i samme commit — `tool_text_two_copies`.
- [ ] **Trin 5: Kør hele suiten. Commit.**

### Opgave 6: Udløbet afleverer en henvisning

**Filer:** ændrer `core/services/session_inbox.py` (`flush_session`); test
`tests/test_session_inbox.py`.

Dette er den ændring der gør data til data. I dag skriver udløbet indholdet som
en **assistant-besked** — altså som noget Jarvis *siger*. Det var mekanismen bag
Smiths løkke.

- [ ] **Trin 1: Test at flush IKKE skriver indholdet som assistant-besked**

```python
def test_flush_afleverer_en_henvisning_og_ikke_en_replik():
    """Smith mintede seks direktiver om sin EGEN replik, fordi hans note landede
    i promptens hale og blev læst som noget Jarvis havde sagt. En henvisning kan
    ikke lukke den løkke."""
    skrevet = []
    with patch("core.services.chat_sessions.append_chat_message",
               side_effect=lambda **kw: skrevet.append(kw) or {"id": "m1"}):
        flush_session("s1")
    assert skrevet == [], f"flush skrev indhold som replik: {skrevet}"
```

- [ ] **Trin 2: Kør, se den fejle** (flush skriver i dag).
- [ ] **Trin 3: Implementér** — flush markerer posterne leveret og udsender
      `channel.inbox_leveret` med tælling + id'er. INGEN ny event-familie uden
      en abonnent: `publish_scan`-vagten fanger utilsluttede familier, og den
      fejler allerede på gammel gæld. Tilslut abonnenten i samme commit.
- [ ] **Trin 4: Test at antallet og id'erne er med** i den udsendte payload.
- [ ] **Trin 5: Kør hele suiten. Commit.**

### Opgave 7: Mål det, før vi tror på det

**Filer:** ny `scripts/maal_indbakke.py`; ingen test (måleværktøj).

R2's punkt 2 ventede fra 13. juni på en måling der aldrig blev lavet, og
tærsklerne blev først sat da nogen regnede efter. Skygge-registrets 24-timers
vindue stod 78 dage. Denne opgave findes for at det ikke gentager sig.

- [ ] **Trin 1:** Script der rapporterer, per døgn: hvor mange poster blev
      handlingskrævende, hvor mange gange nægtede R2.5 på `ulaest-indbakke`, og
      hvor mange af dem blev frigivet (heed-rate for netop den forudsætning).
- [ ] **Trin 2:** Kør det, og LÅS en baseline i specen her, med dato.
- [ ] **Trin 3:** Registrér vinduet i `shadow_experiment_registry` med
      `review_after_hours`, så påmindelsen (rettet 2/10 med en durabel klokke)
      melder når det er modent.
- [ ] **Trin 4: Commit.**

---

## Selvgennemgang

**Dækning:** hvert aspekt fra samtalen har en opgave — handlings-klassen (1),
visningen med alder/dubletter (2), bogføringen (3), R2.5 (4), værktøjerne (5),
henvisning-i-stedet-for-replik (6), målingen (7). De syv huller jeg selv
navngav er afgjort i tabellen «Hvad der ER med».

**Pladsholdere:** ingen. De tre åbne beslutninger blev truffet 3/10 og står i
Global Constraints og i skrive-kontrakten.

**Typer:** `kraever_handling: bool`, `kilde_ejer: str` (Opgave 1) bruges uændret
i Opgave 2 og 4. `byg_indbakke(bruger_id, *, nu_ts)` konsumeres af Opgave 4 med
samme signatur. `done`/`drop` returnerer samme typede dict overalt.

**Det denne spec IKKE gør, med vilje:**

- Rører ikke `cluster_daemon.py`s fail-open (`if not agg: return True`), som
  rapporterer `fired: True, gate_calls: 1` med nul medlemmer. Fælles for alle
  familier; eget spor.
- Fjerner ikke de gamle `list_*`-værktøjer. Billige, virker, og fem steder.
- Bygger ikke `SubagentRuntime` fra harness-specen (8/9). Indbakken er en
  forudsætning for den, ikke en erstatning.
- Giver ikke Jarvis nye evner. Hver handling i specen findes som værktøj i dag;
  specen samler dem og gør tilstanden synlig.
