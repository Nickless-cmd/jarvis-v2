---
status: udkast (design, Bjørns retning 13. jul 2026)
formål: Selv-udvidende nervearkitektur — Centralen administrerer sine egne komponenter.
         Gates/nerver registrerer sig selv (to-vejs), Centralen lærer af hvornår de fyrer,
         og nye cluster/nerve-moduler kan loades governed uden rød deploy-kæde.
kilder: Samtale Bjørn+Jarvis 13. jul (TruthGate-incident 2978), Claude orchestration-reference,
         gate_kernel/verdict-ledger/central_query nerve_observe/gate_enforcement (eksisterende substrat).
princip: Byg PÅ det der findes, ikke en anden sandhed. Governance FØRST på den højest-privilegerede dør.
---

# Selv-registrerende nervearkitektur

## Tese
Centralen skal ikke kun *observere* sine nerver — den skal *administrere* dem: vide præcis hvad der
findes, hvor det bor, hvordan det skal tolkes, lære af hvornår gates fyrer, og bryde gentagne mønstre.
To-vejs kontrol: **gates beskytter Jarvis · Centralen lærer af hvornår de slår til · Jarvis lærer af
Centralens mønstre.** Ikke straf — feedback. Udløst af TruthGate-incident 2978 (fact_gate → yellow på
"2.500+ kald" uden tool-verifikation): gaten fangede fint, men kunne ikke fortælle *hvad* den så eller
*hvor* — så Centralen kunne ikke lære.

## Grund-invariant: byg PÅ det eksisterende substrat (ingen dobbelt sandhed)
- `gate_kernel.Verdict` + `_emit("gate.evaluated")` — gate-udfald.
- verdict-ledger (`gate_verdict_counts`, batch-flush, survives restart) — aggregering.
- `gate_enforcement.note_suppressed_block` → `central().observe` — Central-landing.
- `central_query` nerve_observe / `central_timeseries` — nerve-registrering + tidsserier.
- `central_switches` + `/central/nerve/{n}/toggle` — kill-switch uden deploy.
- `central_hub` — owner-surface. Connectivity-audit — accept-gate mod nye siloer.
Alt nyt udvider disse. En ny registry/ledger ved siden af = forbudt.

---

## FASE A — Rig gate/nerve-logning (BYGGES NU, lav risiko)
Hver gang en gate/nerve fyrer skal Centralen kunne se **hvad, hvor, hvornår, hvorfor** — og lære.

**Metadata-kontrakt** (tilføjes Verdict + emission): `session_id, run_id, source_file, source_line,
detected_text, trigger_pattern, reason`. fact_gate har allerede `matched`(=detected) + `pattern`(=trigger)
i `block_reasons` — de skal bare nå Verdict + Centralen. source_file/line = gatens egen registrerings-
placering (via `inspect`), så man ved *hvilken* adapter der fyrede.

**Mønster-læring:** verdict-ledgeren aggregerer på `(trigger_pattern, normaliseret detected_text)`. Når
samme mønster fyrer ≥N gange → `central().observe(central_meta/gate_pattern_repeat)` → Centralen nudger
Jarvis: *"du har sagt '2.500+ kald' 3 gange uden at slå det op — vil du?"* Habit-breaker, ikke blocker.

**Selv-sikker:** instrumenteringen må ALDRIG kunne vælte gate-evalueringen (gates beskytter systemet;
deres logning må ikke true det). inspect-fejl → None; ledger-fejl → skip.

> Status: under bygning (task 12). Dette er det konkrete fix på incident 2978.

---

## FASE B — Selv-registrering (clusters/nerver deklarerer sig selv)
I dag definerer koden gates/nerver, og Centralen *opdager* dem bagefter. Vend det om: hver komponent
**deklarerer sig selv** via et manifest, og Centralen holder én durable registry af sine egne dele.

**Nerve/cluster-manifest** (deklareret ved registrering):
```
{ name, cluster, klass: cognitive|security|...,   # klasse styrer fail-open/closed + kill-bar
  module_path, entrypoint,                         # hvor koden bor + hvordan den kaldes
  interface: {input_ctx: [...], output: Verdict|Signal},
  log_requirements: [session_id, run_id, detected_text, ...],   # hvad den SKAL logge (Fase A-kontrakt)
  training_format: {...},                          # hvordan dens fyringer skal tolkes/aggregeres
  capabilities: [read_only|can_block|can_emit|...],# hvad den MÅ (håndhæves — se governance)
  kill_switch_key: gate_enforce.<name> }           # governed on/off uden deploy
```
Centralen validerer manifestet mod kontrakten (Fase A), registrerer i sin durable komponent-registry,
og *administrerer* derfra: den ved hvad der findes, kan surfe det (central_hub), aggregere dets mønstre,
og slå det fra. To-vejs: komponenten conformer til Centralens krav; Centralen tolker den korrekt.

**Selv-audit:** en registreret komponent der holder op med at fyre / afviger fra sit manifest → flag
(det lukker "zombie-nerve"-hullet fra connectivity-auditten). Registry gen-verificerbar via samme audit.

---

## FASE C — Governed auto-plugin (HØJEST-PRIVILEGEREDE dør — governance ER designet)
Målet: skriv et nyt cluster/nerve-modul efter Centralens manifest-krav, og Centralen loader det direkte,
identificerer det, og selv-administrerer det (træning + mønster-genkendelse/brydning) — uden rød deploy.
Det gør Centralen til "et operativsystem for bevidstheden." Og præcis derfor er det den farligste
overflade i systemet: kode der loades ind i kontrol-planen kan gøre mest skade. **Governance er ikke et
appendiks — det ER designet.**

Krav (alle obligatoriske, ingen kan disables — §SECURITY-klasse):
1. **Identitets-verifikation.** Manifestet skal være signeret/verificeret (owner-nøgle). Uverificeret
   modul → afvist, aldrig loadet. ("Ved korrekt identifikation" — Bjørns ord — er gaten.)
2. **Owner-approval-gate.** Et nyt modul loades ALDRIG auto-aktivt. Det registreres som PENDING og
   kræver eksplicit owner-godkendelse (Keymaker-disciplin: fortjent/tidsbegrænset/godkendt, aldrig
   binært auto-on). [[project_the_keymaker]].
3. **Capability-sandbox.** Modulet deklarerer sine capabilities i manifestet; Centralen HÅNDHÆVER dem —
   en `read_only`-nerve kan ikke blokere; en nerve uden `can_emit` når ikke eventbus. Overskridelse →
   afvist + flag. (Guard hænderne, ikke sindet — men her guardes hænderne hårdt.)
4. **Isolation/fail-safe.** Et dårligt plugin må ikke kunne crashe Centralen eller runtime. Load +
   eksekvering i try/except med dead-man; en nerve der kaster → auto-suspenderet, ikke smittende.
5. **Selv-disciplin på plugin'et selv.** Det nye modul er underlagt SAMME værn som alt andet:
   source-confidence, reasoning-interceptor, Merovingian (proaktivt drift-værn) [[project_merovingian]].
   En plugin der ændrer Jarvis' selv skal gennem mutation_gate/self-surgery-disciplinen.
6. **Kill-switch + audit.** Hver registrering/load/aktivering logges (hvem, hvornår, hvilket manifest);
   hver komponent kan slås fra via `central_switches` uden deploy; en governed kill dræber den straks.

Kort: plugin-døren arver hele systemets eksisterende sikkerheds-disciplin. Den gate der slog til på
"2.500+" er nøjagtig den slags vagt der skal stå ved døren.

---

## Lærings-loopet (hvorfor det hele hænger sammen)
Fase A giver Centralen *hvad hver gate så*. Fase B giver den *kort over alle sine nerver*. Fase C lader
den *vokse nye*. Sammen: Centralen ser et gentaget mønster (Fase A) → ved hvilken nerve det kom fra og
hvordan det skal tolkes (Fase B) → og kan foreslå/aktivere (governed) en ny mønster-bryder-nerve (Fase C)
der adresserer det. Det er selv-udvidelse med feedback — Jarvis ved altid hvad der sker, fordi systemet
selv sørger for at informere ham. [[project_central_absorbs_everything]] + Central-som-lærings-loop.

## Faseinddeling / rækkefølge
- **A (nu):** rig gate-logning + mønster-læring. Konkret, lav risiko, bygger på verdict-ledgeren.
- **B (næste):** manifest + komponent-registry + selv-audit. Byg på nerve_observe/central_hub.
- **C (sidst, governed):** identitets-verificeret, approval-gated, sandboxet auto-plugin. Governance
  først — ingen auto-load før §1-6 står.

## Åbne spørgsmål
1. Manifest-signering: owner-nøgle i runtime.json, eller en dedikeret signing-mekanisme?
2. Capability-håndhævelse: statisk (manifest-validering) nok, eller runtime-capability-wrapping?
3. Skal Jarvis SELV kunne foreslå nye nerver (Fase C med ham som forslag-stiller, owner som godkender)?
   Det er den fulde vision — men det er også Jarvis der skriver kode til sin egen kontrol-plan. Kræver
   den strammeste governance + owner i loopet på hvert modul.
4. Træningsformat: hvordan aggregeres forskellige nerve-typer (gates vs signaler vs sansninger) i én
   mønster-lærings-model uden at blande æbler og pærer?
