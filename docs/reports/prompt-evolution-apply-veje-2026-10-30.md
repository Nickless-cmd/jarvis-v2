# Prompt-evolution: alle apply-veje kortlagt

Målt 30/10-2026. Leverance for side-opgave `side-ca5035373b`. **Ingen kodeændringer** —
dette er kortlægningen der skulle ligge FØR nogen byggede en ny apply-mekanisme.

## Konklusion først

Der findes **to** veje, og de lever vidt forskellige liv:

| Vej | Status | Autoritativ? |
|---|---|---|
| `development_ritual` → `## Udvikling` i SOUL.md | **Lever** — kaldt fra heartbeat, skriver faktisk | **JA** |
| `runtime_self_authored_prompt_proposals` → `applied` | **Står fast** — rejse-funktionen har nul kaldere | Nej |

De 66 forslag er **ikke** et bevis på en defekt. 64 af dem blev bevidst afvist
28/10-2026 med en skriftlig begrundelse. De sidste 2 står fast af en anden grund.

## Vej 1 — development_ritual (AUTORITATIV)

`core/services/development_ritual.py`, kaldt fra
`heartbeat_runtime_influence.py:1130` → `run_development_ritual()`.

Mekanisme, fire trin:
1. `propose()` samler materiale ugentligt (`_MIN_INTERVAL_DAYS = 7`) og lægger ét
   afsnit i den proaktive kø som forslag med **24 timers veto**
   (`_VETO_HOURS = 24`). Tavshed er et ja; et nej er ét ord.
2. `apply_if_due()` skriver linjen når veto-vinduet er udløbet.
3. Skrivningen går gennem `core.memory.memory_md_writer.upsert_section(path,
   "Udvikling", line, mode="append")` — **kun** `## Udvikling`-sektionen.
4. Resten af SOUL.md er låst af `gate_mutation`.

Betingelser, alle opfyldelige:
- `gather_material()` skal finde mindst ét `memory_promotion`-kandidat fra
  `end_of_run_memory_consolidation` med ≥12 tegn. Tom liste = intet forslag
  (korrekt udfald, ikke en fejl).
- Ét forslag ad gangen (`already-pending` blokerer et nyt).
- 7 dages kadence.

**Bevis for at den virker:** SOUL.md's `## Udvikling` har 7 linjer siden
11/9-2026, senest 24/10. Det er den eneste vej der faktisk har skrevet til
SOUL.md siden 15. maj.

Gate: `core/services/gate_mutation.py`. `SOUL.md` står i både
`PROTECTED_IDENTITY_FILES` og `TIER_3_AUTHORIZED_FILES` — den må muteres, men
kun med audit-spor via `identity_mutation_log.record_mutation`. `HEARTBEAT.md`,
`AFFECTIVE_STATE.md`, `STANDING_ORDERS.md`, `INNER_VOICE.md`,
`DREAM_LANGUAGE.md` og `SELF_CRITIQUE.md` er `EVOLVABLE_FILES` (autonom mutation
uden menneske).

## Vej 2 — de 66 forslag (STÅR FAST)

Skrives af `track_runtime_self_authored_prompt_proposals_for_visible_turn()`,
kaldt ubetinget fra `visible_runs_cognitive.py:293` hver visible turn. Det er
**tracking**, ikke en apply-vej: den udleder forslag fra
`dream_influence`-signaler og gemmer dem med status `fresh`.

Den byggede forbindelse findes: `propose_prompt_evolution_apply()` i
`core/services/autonomy_proposal_queue.py:793`. Dens docstring siger det selv:

> «Dette er den manglende forbindelse: forslaget lever i
> `runtime_self_authored_prompt_proposals`, men godkendelses-vejen lever i
> `autonomy_proposals`. Uden denne funktion kan et forslag aldrig naa fra
> «fresh» til «applied».»

**Målt: `propose_prompt_evolution_apply` har NUL kaldere.** Grep over hele
repoet giver kun definitionen på linje 793. Det er samme fejlform som
guard-emitteren 29/10: en funktion der ser monteret ud, bygget til at lukke
forbindelsen, og aldrig kaldt.

Eksekverings-leddet findes og er registreret:
`register_proposal_executor("prompt-evolution", _execute_prompt_evolution_proposal)`.
Det fyrer kun når et menneske godkender en `autonomy_proposals`-række — og der
bliver aldrig oprettet en.

## Hvor stopper et forslag præcis?

Ikke ét sted, men to forskellige steder — og kun det ene er en fejl:

**De 64 stoppede korrekt.** Status `superseded` 28/10-2026, med begrundelse
skrevet ind i `status_reason`:
- 60 rækker: «skabelon-grenen interpolerer parametre ind i en saetning der taler
  om sig selv ('with consolidate around prompt-shape'). Ikke en indsaettelig
  instruktion. 60 raekker = 3 unikke fragments, 56 identiske. Bevares som bevis.»
- 4 rækker: «baerer ingen 'Candidate fragment'-hale — der er intet at anvende.
  Merget 1000+ gange uden afgoerelse: fastlaast loop i produceren.»

Det er en **bevidst kvalitetsgate der virkede**. `candidate_fragment` er tom for
alle 64. Selv hvis rejse-funktionen var blevet kaldt, ville den have svaret
`"proposal carries no candidate_fragment — nothing to apply"`.

**De 2 fresh står fast uden grund.** Målt:
- `focus-nudge:no-active-runtime-loop` — oprettet 28/10, `frag_len=205`, altså en
  ægte indsættelig instruktion.
- `world-caution-nudge:world-thread` — oprettet 15/5, `frag_len=0`, med noten
  «den ENESTE af 65 der baerer en aegte indsaettelig instruktion … Halen er
  parameter-sovs og skal klippes foer brug.»

Den første har noget at indsætte og ingen vej til at rejse det. Den anden mangler
fragmentet (kendt og noteret 28/10).

## Svar på de fire spørgsmål

1. **Alle skriveveje til identitets-/prompt-filer:** (a) `development_ritual` →
   SOUL.md `## Udvikling`; (b) `autonomy_proposal_queue._execute_prompt_evolution_proposal`
   → `HEARTBEAT.md`-familien via menneskelig godkendelse; (c) `candidate_workflow`
   → SOUL.md/IDENTITY.md `## Proposed Canonical Self Shifts` ved eksplicit
   bruger-godkendelse; (d) `workspace_capabilities` (`MEMORY.md`/`USER.md`);
   (e) `workspace_bootstrap` (opretter filer, skriver ikke indhold i dem).
2. **Betingelser:** (a) opfyldelig og opfyldt — virker i drift. (b) opfyldelig
   som mekanisme, men **aldrig udløst**: ingen opretter forslaget. (c) kræver
   eksplicit bruger-godkendelse; opfyldelig. (d)+(e) ikke identitets-mutation.
3. **Autoritativ:** `development_ritual`. Den er den eneste med en kaldt
   skrivevej og et audit-spor. De 66 forslag er en **observationskanal**, ikke en
   mutationskanal — og bør beskrives sådan.
4. **Bevidst grænse eller glemt led?** Begge: kvalitetsgaten der afviste 64 er
   bevidst og korrekt. Men `propose_prompt_evolution_apply` er et **glemt led** —
   bygget til formålet, dokumenteret som forbindelsen, nul kaldere.

## Hvad der IKKE er bygget (og ikke skal bygges uden beslutning)

En kallende vej fra `fresh` → `propose_prompt_evolution_apply`. Den er et
produktvalg, ikke en bug-fix: skal Jarvis selv rejse prompt-forslag til Bjørns
godkendelse, eller skal den kanal være lukket? Spørgsmålet er ikke teknisk.

Hvis den skal åbnes, er den mindste ærlige form: kald
`propose_prompt_evolution_apply(proposal_id)` for forslag der (1) har
`candidate_fragment`, (2) er ældre end en kvalitets-periode, og (3) ikke
allerede er rejst. Ikke en ny mekanisme — den eksisterende, kaldt.
