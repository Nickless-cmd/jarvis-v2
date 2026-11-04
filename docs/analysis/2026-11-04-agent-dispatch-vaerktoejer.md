# Agent-dispatch: opgaver agenten ikke kan udstyres til (side-7e1d28d53b)

**Dato:** 2026-11-04 · **Besluttet af:** Bjørn (valgte forslag c) · **Skrevet af:** Opus

## Problemet, målt

Fire executor-kørsler 4/11-2026 (`run-e33171f602274a72`, `run-c377491fe1cc449b`,
`run-2a533ecf96974dfb`, `run-0cfb22847ff24e88`) fik en prompt der begyndte med
«Kald værktøjet `restart_self` …». Executorens sæt er fast: `wt_bash`,
`wt_write_file`, `agent_note`. Alle fire blev accepteret, kørte, brændte tokens og
svarede at værktøjet ikke fandtes. Dispatch-vejen så ud som om den virkede.

Det er ikke en glemt mekanisme. `agent_task_facade.py` siger det selv: *prompt-tekst
afgør aldrig stier, værktøjer, budget, mål eller bivirkningsklasse*, og
`agent_contract_service.py` tillader kun `wt_*` til en Task-executor.

## De tre spørgsmål

**(a) Kan en agent få tildelt et eksplicit værktøjssubset via mandatet? — Nej.**
Mandatets `allowed_tools` udledes af runtime og faste profiler. Lader vi kalderen
nævne værktøjer, bliver prompten (eller en model der skriver den) den der afgør
autoritet, og det er netop den grænse facaden er bygget til at holde.

**(b) Må en kold agent få `restart_self`? — Nej.** Værktøjet dræber processer, og en
kold agent har ingen af den forælders sammenhæng der ved om en genstart er
sikker lige nu (aktive synlige runs, igangværende deploy). Genstart hører til en
tur med en menneskelig modpart, ikke til en delegeret.

**(c) Skal dispatch afvise en opgave den ikke kan udstyre agenten til? — Ja.**
Det er den billigste løsning og den eneste der ikke flytter en grænse: ingen
tildeles noget, en urealistisk opgave stoppes før den koster tokens, og afsenderen
får en fejl der siger hvad der mangler og hvad agenten faktisk har.

## Hvad der er bygget

`core/services/agent_task_requirements.py::ufuldstaendige_vaerktoejer` genkender et
**kald-krav** i prompten: et kaldeverbum (`kald`, `kør`, `brug`, `udfør`, `call`,
`invoke`, `use`, `run`, `execute`), evt. «værktøjet/tool/funktionen», så et
`backtick-navn`. Navnet skal stå i runtime-registeret (`_TOOL_HANDLERS`) og mangle i
agentens sæt. `agent_task_facade.derive` rejser så `INVALID_SCOPE` **før** en
assignment oprettes.

## Bevidste afgrænsninger

- **Kun afvisning, aldrig tildeling.** Et krav vagten ikke genkender slipper
  igennem som før; den gør ikke systemet dårligere, kun bedre i de tilfælde den ser.
- **Omtale er ikke krav.** «Ret funktionen `read_file` i file_tools.py» og «skriv en
  test for `restart_self`» afvises ikke — en executor der arbejder PÅ værktøjskode er
  hovedanvendelsen. Derfor kræves et kaldeverbum lige foran navnet.
- **Negation er ikke krav.** «Du skal ikke kalde `restart_self`» og «do not call» afvises ikke.
- **Uden backticks genkendes ingenting.** «Kald restart_self» uden backticks
  afvises ikke. Et bart ord matcher for ofte almindelig tekst; tabet er at et
  sådant krav stadig fejler efter en kørsel, som i dag. Alle fire målte prompts
  havde backticks.
- **Registeret kan ikke læses → afvis intet.** Vagten er additiv og skal ikke kunne
  gøre dispatch ubrugelig. Fejlen logges.
- **`kendte` er registeret, ikke en liste i koden.** Et nyt værktøj er dækket fra
  dag ét; en omdøbning kan ikke efterlade en forældet liste.

## Acceptkriterier

| | |
|---|---|
| (a) en dispatch der kræver et værktøj agenten ikke har afvises | `test_de_fire_rigtige_dispatches_afvises`, `test_facaden_afviser_en_ufuldstaendig_executor` |
| (b) en dispatch der kræver et værktøj agenten HAR virker uændret | `test_et_vaerktoej_agenten_har_er_ikke_ufuldstaendigt`, `test_facaden_lader_en_opgave_uden_krav_passere`, de 53 eksisterende facade-/kontrakttests |
| (c) beslutningen er skrevet ned med begrundelse | dette dokument |
| (d) måling | se «Måling» |

## Måling

(d) er målt 4/11-2026 direkte i den deployede, read-only database over de
seneste 30 dage. Hver af de 82 `agent_assignments` blev joined med sit mandat,
og den nu deployede kald-kravsdetektor blev kørt mod `goal` og mandatets
`allowed_tools_json`:

- **5 af 82 dispatches (6,1 %)** krævede et kendt runtime-værktøj agenten ikke
  havde.
- 4 krævede `restart_self`; 1 krævede `suggest_next_task`.
- De fire `restart_self`-opgaver nåede alle en rigtig agentkørsel. De fire
  run-ID'er er dem der står øverst i dokumentet; outputtet siger eksplicit at
  værktøjet ikke fandtes.

Det er en lille, men reel driftsklasse — omtrent hver tyvende dispatch i det
målte vindue — og ikke kun den ene genstartssekvens der udløste rettelsen.
Målingen er retrospektiv: afvisninger sker før en assignment oprettes, så en
fremtidig driftsmåling af selve `INVALID_SCOPE`-afvisningerne kræver en separat
afvisningstæller eller tool-call-telemetri; `agent_assignments` kan ikke tælle
noget der netop blev afvist før oprettelsen.
