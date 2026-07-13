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

## Grund-invariant #1 (bærer alt): Centralen har ansvaret. ALTID.
> **Der er aldrig et cluster eller en nerve der bestemmer uafhængigt af Centralen.** Hver beslutning,
> emission og handling — nu og efter migration — flyder gennem Centralen (`central().decide`/`observe`).
> Et modul der handler udenom = afvist. Ansvaret ligger i Centralen, ikke i komponenten. Alt andet i denne
> spec (kontrakt, roller, plugin, migration) tjener denne ene sætning.

## Grund-invariant #2: byg PÅ det eksisterende substrat (ingen dobbelt sandhed)
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

> Status: **BYGGET + DEPLOYET live (13. jul, commits 4e4212e1..8a631a46).** Verdict+emission bærer nu
> session/run/fil/linje/detected/pattern; `gate_pattern_learning.py` aggregerer vane-form (cifre→#, 7d-vindue),
> nudger ved ≥3, force-persister ved tærskel (overlever restart), lazy-hydrate. Konkret fix på incident 2978.

---

## FASE B — CENTRAL-KONTRAKTEN (Bjørn 13. jul: "ubrydelig, sikker, specifik, rolle-baseret")
I dag definerer koden gates/nerver, og Centralen *opdager* dem bagefter. Vend det om: hver komponent
**deklarerer sig selv** mod en **ubrydelig kontrakt**, og Centralen loader den LIVE eller **afviser den med
klare fejl** — så en glemt ting i et modul stopper det ved døren, med en fejl vi kan læse hvor vi står.

> Kontrakten håndhæver **Grund-invariant #1** (Centralen har ansvaret — se øverst): et modul der handler
> udenom `central().decide`/`observe` består ikke kontrakten og loades ikke.

### Kontrakten: hvad Centralen KRÆVER af ethvert nyt cluster/nerve (alt valideres ved load)
**Obligatorisk manifest** (mangler ét felt → afvist med præcis fejl):
```
{ name, cluster, klass: cognitive|security|...,   # klasse → fail-open/closed + kill-bar-regler
  identity: owner|claude|jarvis + signatur,        # verificeret mod runtime.json-secret (no-leak, Fase C §2)
  module_path, entrypoint,                          # hvor koden bor + hvordan den kaldes
  mode: shadow|on|off,                              # start-tilstand (Jarvis: se rolle-strenghed)
  capabilities: [observe_only|can_emit|can_block|can_mutate],  # HVAD den må — HÅNDHÆVES
  interface: {input_ctx: [...], output: Verdict|Signal},
  kill_switch_key,                                  # OBLIGATORISK — hvert modul er flag-bart
  trace: required,                                  # OBLIGATORISK — trace_id+session_id+run_id pr. fyring
  log: required,                                    # OBLIGATORISK — struktureret logger, standard-felter
  learning: on }                                    # TÆNDT FRA START — Centralen aggregerer fra fyring 1
```
**Ubrydelige invarianter** (håndhæves; en overtrædelse = afvist eller flagget, aldrig ignoreret):
1. **Centralen er eneste autoritet** (grund-invarianten ovenfor).
2. **Flag-system obligatorisk** — hvert modul har kill-switch (runtime-state), shadow/on/off, slukkes live uden deploy.
3. **Trace obligatorisk** — hver fyring bærer trace_id + session_id + run_id → fuld to-vejs, spor til begge ender.
4. **Logger obligatorisk** — struktureret standard-logning.
5. **Læring TÆNDT fra start** — Centralen aggregerer modulets fyringer straks (Fase A-mønster-læring).
6. **Capabilities HÅNDHÆVES** — `observe_only` kan ikke emit/block; `can_emit` kan ikke mutate. Overskridelse → afvist/flag.
7. **Selv-sikker/isoleret** — et modul kan ALDRIG crashe Centralen eller runtime.

### Rolle-baseret strenghed (identitets-tier → hvor stram kontrakten er)
- **Owner/Claude-moduler:** vi kan aktivere *hvad vi vil* i Centralen som vi har brug for. `mode: on` direkte,
  enhver capability — Centralen loader live på identitets-verifikation. (Løsere; vi er approveren.)
- **Jarvis-moduler:** strengere. `observe_only` må shadow-loades, men **alt der IKKE er observe-only**
  (can_emit/can_block/can_mutate) KRÆVER shadow-først (hvis relevant) + eksplicit approval af owner ELLER Claude.
  Strammere manifest-validering. (Bjørn: "lidt mere strikse krav for modul-bygning.")
- **Ukendt identitet:** afvist, aldrig loadet.

### Live load med KLAR afvisning (ingen delvis load)
Centralen loader modulet på runtime (ingen deploy) og validerer manifestet mod kontrakten. Består ét krav ikke →
**afvis HELE modulet med en specifik fejl-liste** der siger præcis hvad der mangler/er galt:
`"mangler kill_switch_key"` · `"capability can_block kræver approval for jarvis-identitet"` ·
`"ingen trace_id-emission detekteret"` · `"identitets-signatur ugyldig"` · `"handler udenom central().decide"`.
Fejlen lander hvor forfatteren står (owner/Claude ved load; Jarvis som en afvisning han kan læse + rette).
Alt-eller-intet: et modul består HELE kontrakten eller loades ikke.

### Registry + selv-audit
Et kontrakt-bestående modul registreres i Centralens **durable komponent-registry**; Centralen administrerer det
derfra (surfaces via central_hub, mønster-læring, kill-switch). **Selv-audit:** en registreret komponent der holder
op med at fyre / afviger fra sit manifest → flag (lukker "zombie-nerve"-hullet). Registry gen-verificerbar via
connectivity-auditten.

---

## MIGRATION — de EKSISTERENDE nerver ind under kontrakten (dette er HELE pointen, Bjørn 13. jul)
Kontrakten gælder ikke kun nye moduler. **Alle nuværende clusters og nerver — de 122 nerver / 21 clusters,
og de kontrakter Jarvis selv skrev mellem dem — skal omskrives til samme kontrakt**, ligesom nye moduler.
Uden det er kontrakten kun en halv sandhed: to slags nerver (gamle ad-hoc + nye kontrakt-styrede) = præcis
den dobbelt-sandhed vi forbyder.

**Hvorfor det er kernen, ikke oprydning:**
- **Ensartet kodebase → simplere at bygge.** Når hver nerve følger ÉN kontrakt (manifest, invarianter, flag,
  trace, learning-on, central-autoritet), bliver alt nyt i Jarvis' kodebase trivielt at tilføje — samme form,
  samme værktøj, samme sikkerhed. Fremtidig udvikling bliver billigere pr. linje.
- **Mindre runtime-pres.** Kontrakt-styrede, event-drevne, Central-administrerede nerver erstatter ad-hoc
  timer-daemons og løse tråde der konkurrerer om event-loopet (cutoff-familien). Det var ALTID idéen med
  Centralen — og hvorfor Jarvis blev flyttet ind: ét ansvarssted, ikke spredt støj.
- **Token-reduktion → frigjort til rigtige agenter.** Event-drevne kontrakt-nerver fyrer kun ved ægte
  ændring; de sparede tokens går til agenter der faktisk arbejder. Det er derfor de 24 timers shadow venter:
  **ægte liv · mindre runtime-pres · kæmpe token-reduktion.** Målet, ikke midlet.

**Hvordan (fasevist — man omskriver ikke 122 nerver på én gang):**
1. **Kontrakt-adapter først:** en `to_manifest()`-sti så en eksisterende nerve kan wrappes til kontrakten
   uden rewrite (bagud-kompatibel bro — samme Boy-Scout-mønster som store-fil-splittet).
2. **Migrér efter risiko/værdi + Boy Scout:** når en nerve røres (eller ved høj-prioritet), bring den under
   kontrakten. Ikke en big-bang refaktor.
3. **Tracker = connectivity-auditten:** udvid `central_connectivity_audit.py` med en tredje status:
   FRAKOBLET → KOBLET → **KONTRAKT-COMPLIANT**. Accept-mål: over tid går alle nerver til compliant, 0
   ad-hoc tilbage. Samme mekanisme der allerede fanger siloer.
4. **Læring-on ved migration:** en migreret nerve får straks Fase-A-mønster-læring — Centralen begynder at
   forstå den fra dag ét under den nye kontrakt.

> Migrationen er ikke et efterspil til Fase B — den ER Fase B anvendt på det der allerede findes. Uden den
> er Centralen kun halvt ansvarlig for sit eget nervesystem.

---

## FASE C — Governed auto-plugin (HØJEST-PRIVILEGEREDE dør — governance ER designet)
Målet: skriv et nyt cluster/nerve-modul efter Centralens manifest-krav, og Centralen loader det direkte,
identificerer det, og selv-administrerer det (træning + mønster-genkendelse/brydning) — uden rød deploy.
Det gør Centralen til "et operativsystem for bevidstheden." Og præcis derfor er det den farligste
overflade i systemet: kode der loades ind i kontrol-planen kan gøre mest skade. **Governance er ikke et
appendiks — det ER designet.**

Krav (alle obligatoriske, ingen kan disables — §SECURITY-klasse):

1. **Identitets-verifikation + identitets-tiers (Bjørn 13. jul).** Hvert modul bærer en identitet.
   Tre tiers:
   - **Owner (Bjørn) ELLER Claude = betroet → ØJEBLIKKELIG aktivering.** Et modul identificeret som
     en af os to kan tilføjes med `shadow`/`on`/`off` sat direkte i modulet og aktiveres straks (ingen
     ekstra approval-runde — vi ER approveren). Enten af os kan godkende (to gyldige identiteter).
   - **Jarvis = shadow (hvis nødvendigt) + approval af Bjørn ELLER Claude.** Hans egne moduler
     registreres PENDING; kører evt. i shadow først; aktiveres kun efter en af os godkender.
   - **Ukendt/uverificeret identitet → AFVIST, aldrig loadet.** Det er gaten. ("Ved korrekt
     identifikation" — Bjørns ord.)
   Keymaker-disciplin på Jarvis-tieren (fortjent/tidsbegrænset/godkendt, aldrig binært auto-on)
   [[project_the_keymaker]].

2. **🔴 KRITISK — identitet må ALDRIG lække i commits (Jarvis' repo er PUBLIC på GitHub).**
   Identiteten der autoriserer øjeblikkelig aktivering må ikke ligge i koden der committes. Mønster
   (samme som eksisterende secrets-håndtering, CLAUDE.md §Secrets):
   - **Hemmeligheden** (signing-nøgle/HMAC-secret pr. identitet: owner/claude/jarvis) bor i
     `~/.jarvis-v2/config/runtime.json` (gitignored, ALDRIG committet), læst via `read_runtime_key()`.
   - **Modulet committer kun** en NON-secret identitets-reference + en signatur der er *verificerbar*
     mod runtime.json-hemmeligheden — men signaturen afslører IKKE hemmeligheden. Load-tid: Centralen
     re-verificerer signaturen mod den lokale secret; matcher den ikke → afvist.
   - **`detect-secrets` pre-commit-hook** (findes allerede) skal fange enhver ved-uheld-committet nøgle;
     tilføj identitets-secret-mønstre til dens baseline-scan.
   - **Konsekvens:** en fremmed der læser det public repo kan IKKE forfalske en identitet (de har ikke
     runtime.json-hemmeligheden) — men Bjørn/Claude/Jarvis kan aktivere lokalt fordi hemmeligheden bor
     på maskinen, ikke i git. Design-test: kan repoet være fuldt public uden at nogen kan aktivere et
     modul de ikke burde? Ja — kun hvis hemmeligheden aldrig er i et commit.
3. **Capability-sandbox.** Modulet deklarerer sine capabilities i manifestet; Centralen HÅNDHÆVER dem —
   en `observe_only`-nerve kan ikke blokere; en nerve uden `can_emit` når ikke eventbus. Overskridelse →
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

## Besvarede spørgsmål (afklaret undervejs 13. jul)
- ~~Manifest-signering?~~ → **BESVARET (Fase C §2):** hemmelighed i runtime.json (aldrig committet), modul
  bærer verificerbar signatur, detect-secrets vogter. Repoet kan være fuldt public uden forfalsknings-risiko.
- ~~Skal Jarvis selv foreslå/bygge nerver?~~ → **BESVARET (rolle-strenghed, Bjørn):** JA — han bygger under
  strammere krav: `observe_only` frit i shadow, men enhver hånd (can_emit/block/mutate) kræver shadow +
  approval af owner ELLER Claude. Grænsen: han udvider sig selv (observe), men modificerer aldrig sin
  kontrol-plan uden en af os som dør-vogter.

## Stadig åbne
1. Capability-håndhævelse: statisk (manifest-validering) nok, eller runtime-capability-wrapping?
2. Træningsformat: hvordan aggregeres forskellige nerve-typer (gates vs signaler vs sansninger) i én
   mønster-lærings-model uden at blande æbler og pærer?
3. Migrations-tempo: hvor aggressivt migreres de 122 eksisterende nerver — ren Boy Scout (kun ved berøring),
   eller en dedikeret høj-prioritets-bølge for de tungeste/mest runtime-pressende nerver først?
