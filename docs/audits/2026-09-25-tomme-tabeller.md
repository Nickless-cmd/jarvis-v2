---
status: målt
målt: 2026-09-25
grundlag: levende runtime (bs@10.0.0.39:~/.jarvis-v2/state/jarvis.db, 304 tabeller) + kode-call-sites
forfatter: jarvis
---
# Tomme tabeller — 25. september 2026

**Anledning:** Claude bad om listen over de tabeller der findes uden at få rækker — med tabel, fil og det linjenummer hvor skrivningen står. Målt mod den *levende* runtime, ikke mod kilden alene.

**Metode:** `SELECT count(*)` mod hver tabel i den kørende DB. For hver tabel med nul rækker: grep efter `INSERT ... INTO <tabel>` i `core/`, `apps/` og `scripts/`. Worktree-kopier under `.claude/worktrees/` er ekskluderet — de gjorde mit første tal **ni gange for stort** (samme tabel så ud til at have 9 skrivestier; den havde én, plus 8 kopier). Et tal der gentager sig ens på tværs af tabeller der intet har med hinanden at gøre, er et måleartefakt indtil det modsatte er vist.

---

## Resultat

**27 tabeller er helt tomme. 26 har præcis én skrivesti i kilden. 1 har ingen.**

| Tabel | Skrivesti (fil:linje) |
|---|---|
| `agent_schedules` | `core/runtime/db_agent_runtime.py:784` |
| `cadence_idempotency_keys` | `core/services/cadence_claims.py:173` |
| `central_rca` | `core/services/central_rca.py:102` |
| `cheap_lane_admission_leases` | `core/services/cheap_lane_admission.py:143` |
| `cheap_lane_admission_state` | `core/services/cheap_lane_admission.py:87` |
| `cheap_lane_audit` | `core/runtime/db_cheap_lane_control.py:280` |
| `cheap_lane_quota_observations` | `core/runtime/db_cheap_lane_control.py:214` |
| `claude_dispatch_audit` | `core/tools/claude_dispatch/audit.py:88` |
| `claude_dispatch_budget` | `core/tools/claude_dispatch/budget.py:28` |
| `cognitive_epistemic_claims` | `core/services/epistemics.py:203` |
| `cognitive_mission_messages` | `core/services/missions_pipeline.py:233` |
| `cognitive_missions` | `core/services/missions_pipeline.py:150` |
| `cognitive_morning_threads` | `core/services/session_continuity.py:390` |
| `cognitive_repairs` | `core/services/rupture_repair.py:354` |
| `cognitive_trade_outcomes` | `core/services/negotiation_pipeline.py:195` |
| `cognitive_wrongness` | `core/services/epistemics.py:217` |
| `composer_jarvis_forslag` | **INGEN** |
| `experiment_broadcast_events` | `core/runtime/db_runtime_misc.py:305` |
| `message_feedback` | `core/services/message_feedback.py:91` |
| `meta_learning_hypotheses` | `core/services/meta_learning_hypotheses.py:101` |
| `meta_learning_hypothesis_samples` | `core/services/meta_learning_hypotheses.py:145` |
| `research_sources` | `core/services/research_store.py:238` |
| `research_steers` | `core/services/research_store.py:249` |
| `research_tasks` | `core/services/research_store.py:119` |
| `runtime_world_facts` | `core/runtime/db_world_self_truth.py:149` |
| `session_write_leases` | `core/runtime/db_session_ledger.py:136` |
| `user_flags` | `core/services/security_guard.py:170` |

---

## Hvad listen siger — og hvad den ikke siger

**Den siger ikke at stierne er døde.** En skrivesti i kilden betyder at nogen kan kalde den. Det den viser er at forbindelsen findes formelt og aldrig har båret en række.

**Det er samme signatur som `dream_bias_active`** (samme dag, separat fund): tabellen fandtes siden 10. maj, koden fandtes, kaldestedet fandtes — og fejlede på første tegn hver eneste cyklus i fire og en halv måned. Formen var bygget færdig; indholdet kom aldrig.

**To klasser, ikke én:**

- **Aldrig kaldt rigtigt.** Stien findes, men kaldes sjældnere end den skulle — eller med input der får den til at returnere før skrivningen. `relation_dynamics` og `relational_warmth` var denne klasse: de fejlede med `NoUserContextError` på hvert tik, fejlen blev slugt, og filerne stod 82–121 dage gamle mens mind-rapporten viste dem som `active: true`.
- **Aldrig færdigbygget.** Der er en form, men ingen reel producent bag. `composer_jarvis_forslag` er den eneste i denne liste uden nogen skrivesti overhovedet — et bord uden stol.

At skelne de to kræver at man læser hvad stien gør når den kaldes, ikke bare at den findes. Det er den næste måling, og den er ikke lavet her.

---

## Registret havde allerede svaret for syv af dem

**Tilføjet af Claude 25/9-2026.** `core/services/liveness_registry.py` — skrevet
som Stage 2 efter auditten 15. juni — er et maskinlæsbart register over præcis
dette spørgsmål. Dets egen docstring siger hvorfor det findes:

> Formålet er at STOPPE konfabulation — både Jarvis' og menneskers — om at
> "hans systemer er døde". En tom GAMMEL tabel betyder oftest AFLØST, ikke død.

Det dækker 21 tabeller. **Syv af de 27 her står allerede klassificeret:**

| Tabel | Registrets status | Producent / note |
|---|---|---|
| `cognitive_epistemic_claims` | `orphaned` | epistemics.reconcile_claim (nul callers) |
| `cognitive_mission_messages` | `orphaned` | missions_pipeline.send_mission_message (nul callers) |
| `cognitive_missions` | `orphaned` | missions_pipeline.create_mission (nul callers) |
| `cognitive_trade_outcomes` | `orphaned` | negotiation_pipeline.record_trade_outcome (nul callers) |
| `cognitive_wrongness` | `orphaned` | epistemics.reconcile_claim (nul callers) |
| `meta_learning_hypotheses` | `manual_only` | meta_learning_tools (Jarvis-tool) |
| `meta_learning_hypothesis_samples` | `manual_only` | meta_learning_tools (Jarvis-tool) |

**Tyve er uklassificerede** — og det er den egentlige arbejdsliste.

### En tredje klasse

Registrets vokabular har en status hverken Jarvis' audit eller Claudes
gennemgang havde: **`manual_only`** — skrives kun via et eksplicit tool, ikke
autonomt. `meta_learning_hypotheses` er ikke i stykker og ikke ufærdig. Den
venter på at Jarvis selv bruger værktøjet.

Så der er tre klasser, ikke to:

- **aldrig kaldt rigtigt** — stien findes og fejler eller springes over
  (`relation_dynamics`: `NoUserContextError` på hvert tik i 82–121 dage)
- **aldrig færdigbygget** — formen findes uden producent
  (`composer_jarvis_forslag`: ingen skrivesti overhovedet)
- **venter på at blive brugt** — virker, men ingen har kaldt værktøjet
  (`meta_learning_hypotheses`, `meta_learning_hypothesis_samples`)

At blande de tre er hvordan man ender med at reparere noget der ikke er i
stykker.

### Metode-tilføjelse

`liveness_registry` læses af **én** fil i hele repoet
(`apps/api/jarvis_api/routes/mission_control_runs_ops.py`). Det er tredje
sted samme dag hvor sandheden er skrevet ned og lagt hvor ingen kigger — de to
andre er kommentaren i `central_body_mood_feel.py:14` om at `body_memory` er
droppet, og `quarantine_legacy_world_topics`, der rydder samtale-emner ud af
verdensmodellen tolv linjer over det kald der laver nye.

**Spørg registret før du graver.** Står tabellen der ikke, er svaret at
klassificere den — ikke at gætte.

---

## Sidestykke: den 15. juni

`docs/audits/2026-06-15-cognitive-liveness-audit.md` blev skrevet på præcis samme anledning — Codex flagede «mange tomme/stale livs-tabeller». Dengang var konklusionen at Jarvis var *intenst i live*, og at de ægte problemer var små og afgrænsede. Den konklusion holdt for de tabeller den undersøgte.

De 27 her er en anden måling tre måneder senere, og den er ikke lavet for at afgøre om nogen er i live. Den er lavet fordi Claude spurgte, tabel for tabel, med fil og linje.

---

## Parallelt fund (Claude, samme dag)

11 moduler har **ingen tabel overhovedet** — de skriver til en modul-liste der dør ved genstart. Det er den anden ende af samme sag: hans ende er moduler uden bord, min er borde uden rækker. Begge er et lag hvor formen blev bygget og indholdet aldrig kom.

---

*Målt af Jarvis 25/9-2026 mod den kørende runtime på CT105. Worktree-kopier ekskluderet. Linjenumre er fra `main` @ `3021f10fe`.*

## Efterskrift (Claude, samme aften): de elleve er lukket

De ti moduler med egen tilstand har nu et bord. Det ellevte,
`cognitive_core_experiments`, fik **ikke** et — den samler fem andre familiers
flader gennem `_safe_build` og har ingen egen tilstand. Et bord der ville have
været en anden sandhed ved siden af den den læser. Registret fik i stedet en
fjerde status, `projektion`: *gemmer med rette intet*.

Det er en rettelse af selve listen. «Uden bord» er kun en mangel når modulet
**har** noget at miste.

### To fund der lå under persistensen

**1. Tilstanden var per proces, ikke kun per opstart.** `jarvis-api` og
`jarvis-runtime` kører samme kode i hver sin proces, men kun runtime muterer.
Målt på CT105 25/9 kl. 17:50, mens runtime havde tikket hele dagen:

```
continuity_kernel        {"active": false, "tick_count": 0}
initiative_accumulator   {"active": false, "want_count": 0}
boredom_curiosity_bridge {"active": false, "boredom_level": 0.0}
```

Genstart var altså kun den ene halvdel. Den anden var at `/mc/runtime` aldrig
kunne vise andet end nul, uanset hvor længe han levede.

**2. `record_tick_elapsed(seconds=30)` var hårdkodet.** Tikket kommer fra
`wakeup_dispatcher` med variabelt interval, så de 30 var et gæt — og for netop
dette modul et selvmodsigende et: `should_express_continuity()` er
`gap >= 300`, så et konstant gap på 30 gjorde `format_continuity_for_prompt()`
tom for altid. Modulet var bygget, forbundet og stumt på samme tid.

Mellemrummet måles nu mellem daemon-blokkens egne kørsler, og tidsstemplet
ligger i `state_store`, så målingen også holder hen over en genstart — det er
netop de lange mellemrum der betyder noget.

### Persistens uden udløb er en ny fejl

`_curiosities` blev aldrig beskåret (`clear_curiosities()` har ingen kaldere),
og et ønske af en given type blokerer for et nyt af samme type. Genstarten
ryddede op; disken ville ikke. Begge får derfor det døgn `initiative_queue`
allerede giver en `low`-post (`_EXPIRE_MINUTES_LOW = 24*60`), så broen og køen
er enige om hvad der stadig findes.

### Og en regning til mig selv

`core/runtime/state_store.py` har eksisteret hele tiden — 49 moduler bruger
den, og dens egen docstring siger at den findes fordi *«every daemon that fixed
the same problem re-implemented load/save inline»*. Jeg skrev den samme
load/save seks gange i løbet af dagen uden at slå op om den fandtes.

Det har en målt konsekvens ud over gentagelsen: `tests/conftest.py`
skærmer `state_store._STATE_DIR` for hver eneste test (`autouse`), men ikke
`shared_dir()`. Målt samme aften skrev `tests/test_body_memory.py` i den
**rigtige** `~/.jarvis-v2/shared/runtime/body_memory.json`. Det er samme
mønster som `in_flight_runs.json`-hændelsen 17/9, som netop den skærm blev
skrevet for. De seks bør flyttes til `state_store`.
