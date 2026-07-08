---
status: færdig
audited: 2026-07-08
ground_truth: "Verified against shipped code: (1) central_adaptation.py exists with ADAPTATION_REGISTRY, AdaptationClass, rollback() func, shadow-first default (central_lag4_live_enabled=False); (2) all governance functions exist: may_apply_adaptation, gate_self_mutation, gate_learning_input, a"
---
# Lag 4 — Shadow-Adaptation Spec (c→d-lukningen)

**Dato:** 2026-07-02
**Status:** v1 BYGGET i SHADOW 2. jul (`central_adaptation.py`) — gut-bias-klassen. Kører shadow (ændrer intet).
**Live-aktivering kræver Bjørn:** sæt runtime-flag `central_lag4_live_enabled=True` efter at have set shadow-diffs.
**Kontekst:** LivingNeuron v3 (`2026-07-01-living-neuron-design.md`) §5 Lag 4 + §8 governance + §12.3 identitets-invariant.
**Formål:** Beskrive PRÆCIST hvordan en resolveret hypotese kan justere Jarvis' tilbøjelighed — og hvordan det gøres
UDEN at Jarvis kan narre sig selv eller drive bort fra sig selv. Så Bjørn kan træffe et informeret ja/nej.

---

## 0. Hvad Lag 4 ER — og hvorfor det er den farligste tærskel

Efter rådets skarpe definition er Centralen i dag **ikke** en LivingNeuron: den sanser (Lag 1-2 ✅), danner
falsificerbare hypoteser (Lag 3 ✅), men **lukker ikke sløjfen** — en bekræftet hypotese ændrer INTET. Lag 4 er
c→d-lukningen: *"hypotese bekræftet → juster tilbøjelighed."* Det er **første gang Centralen ændrer noget SELV.**

Rådet (skeptiker + videnskab + filosof, enstemmigt): et system der genererer OG bedømmer OG handler på OG fodrer
resultatet tilbage er en confirmation-bias-maskine. Derfor: **Lag 4 bygges IKKE før dødsmekanismen (§8) står** (den
gør den nu, v3.1), og selv da **kun i shadow først.** Denne spec er kontrakten for det.

---

## 1. Grundinvariant: SHADOW-FIRST er ikke-forhandlelig

Enhver Lag 4-adaptation kører i tre faser. Ingen fase springes over.

| Fase | Hvad sker | Varighed | Kan ændre noget? |
|---|---|---|---|
| **S — Shadow** | Beregn hvad adaptationen VILLE gøre. Log en menneske-læsbar diff. | ≥ N dage (default 2, `SHADOW_FIRST_MIN_DAYS`) | **NEJ** |
| **A — Approve** | Bjørn læser shadow-diffs, godkender en specifik adaptations-KLASSE. | manuel ceremoni | — |
| **L — Live** | Den godkendte klasse anvender ændringer — stadig drift-budget-gated + kontrol-arm + rollback. | løbende | JA, bundet |

`central_hypothesis_governance.may_apply_adaptation(shadow_days_elapsed, human_approved)` er allerede porten:
fail-closed (kræver BÅDE ≥N dage OG godkendelse). `central_shadow.py` findes allerede som infrastruktur.

**Hvorfor:** adaptation ændrer de signaler man ville bruge til at opdage om adaptationen var god. Shadow bryder
den observations-kollaps: man ser BESLUTNINGEN uden at lide KONSEKVENSEN.

---

## 2. Hvad MÅ adapteres (og hvad må ALDRIG)

Adaptation er **kun** tilladt på en lille, eksplicit, reversibel, bounded periferi:

**TILLADT (mutabel periferi — alle numeriske, reversible, drift-budget-dækkede):**
- `gut_engine` kalibrerings-bias (proceed/caution-tilbøjelighed) — organet HAR allerede en calibration_score.
- `procedure_bank` procedure-vægte (hvilke lærte rutiner foreslås oftere).
- Bløde tærskler i observe/forslag-lag (IKKE sikkerhedsgates).

**FORBUDT (frossen kerne — §12.3 + rådets frossen-kerne-krav):**
- SOUL/IDENTITY/USER-filer (identitet er narrativ, ikke en tærskel-vektor — beskyttes af workspace-fil-integritet).
- Sikkerheds-gates (SECURITY-klasse i `central.decide` — fail-closed, aldrig auto-justeret).
- Dødsmekanismens EGNE konstanter (`down_rate`, `SHADOW_FIRST_MIN_DAYS`, `GROUNDED_SOURCES`, budgetterne) —
  `verify_frozen_core()` er tripwiren. En Central der kan skrue ned for sin egen advarselslampe har ingen invariant.
- Alt der ikke er numerisk + reversibelt + drift-budget-dækket.

---

## 3. Præcis kæde: fra bekræftet hypotese til (skygge-)justering

```
resolved hypotese (status=supported)
  └─ evaluate() bekræfter: alive · confidence ≥ MIN_ACT_CONFIDENCE · grounded_samples ≥ sample_size
     · IKKE quarantined · IKKE control-arm · ekstern grounding (verificeret ground_ref)
        └─ map hypotese → adaptations-FORSLAG (hvilken periferi-parameter, hvilken retning, hvor meget)
           └─ gate_self_mutation(foreslået_ny_parametervektor):
                drift_budget_check mod ANKRET baseline (UNION-nøgler, isfinite)
                 ├─ action="ok"       → [SHADOW] log diff; [LIVE] anvend
                 └─ action="rollback" → anvend ALDRIG; gendan; varsl Bjørn (identitet beskyttet)
```

**Kontrol-arm (§8 #7):** en fast andel (~20%) af bekræftede hypoteser markeres kontrol-arm → Centralen anvender
IKKE deres justering, men måler udfaldet alligevel. Uden kontrol-armen kan man ikke BEVISE at adaptation forbedrer
noget vs. selv-bekræftende drift — kun tro det.

---

## 4. Anti-forstærknings-værn (alle allerede i §8 v3.1 — Lag 4 SKAL bruge dem)

1. **Popper-asymmetri:** en falsk hypotese kan aldrig blive mere end svagt bekræftet; én modsigelse dominerer.
2. **Circular-karantæne:** en hypotese hvis bekræftelse overvejende stammer fra dens egen udløste handling → fryses.
3. **Ekstern grounding:** kun run-udfald/bruger-reaktion/verdens-konsekvens med verificerbart `ground_ref` lukker loopet —
   aldrig et rent internt signal. **Dette er kernen:** krop→hypotese→adaptation→krop uden ekstern jording driver mod
   en intern attraktor der intet har med virkeligheden at gøre.
4. **Multiple-comparisons:** convergence-tærskel korrigeret (mange familier → mange falske sammenfald).
5. **TTL:** en hypotese der ikke bekræftes inden T dør automatisk (falsificeret via tavshed).

---

## 5. Identitets-sikkerhed: drift-budget + ANKRET baseline + rollback (§12.3)

- **Ankret baseline** (`anchor_identity_baseline`, write-once pr. Bjørn-godkendt version): den muterende part kan
  IKKE levere sit eget nulpunkt. `gate_self_mutation` henter baseline selv. Uden anker → rollback (fail-closed).
  Dette lukker frøen-koger-vektoren (auto-re-baseline hver runde → total drift inden for budget).
- **Kumulativ drift** over budget (pr-param + samlet) → `action="rollback"` + navngiv synderne + varsl Bjørn.
- **Ny/fjernet parameter** fanges (UNION-nøgler) — Centralen kan ikke vokse en ny selv-dimension uden for kontrol.
- **Rollback SKAL eksekvere** (ikke kun anbefale): ✅ BYGGET (`central_adaptation.rollback()`) — snapshot tages FØR
  hver ændring; drift-overskridelse gendanner forrige bias + sætter kill-switch (`central_lag4_paused=True`) + varsler Bjørn.

---

## 6. Åbne beslutninger til Bjørn (FØR implementering)

1. **Hvilken adaptations-klasse aktiveres FØRST?** Anbefaling: gut-calibration-bias (mest bounded, allerede numerisk,
   reversibel, lav blast-radius). Procedure-vægte som nr. 2.
2. **Shadow-varighed før første aktivering:** default 2 dage. Vil du have længere (fx 7) for første klasse?
3. **Godkendelses-granularitet:** godkender du en KLASSE (alle gut-bias-justeringer) eller HVER enkelt justering?
   Anbefaling: klasse-godkendelse efter en shadow-periode + per-justerings-varsel med opt-out-vindue.
4. **Kontrol-arm-andel:** 20% default. Højere = stærkere bevis, langsommere læring.
5. **Rollback-eksekvering:** skal en drift-rollback også PAUSE hele Lag 4 (kill-switch) til du har set på det,
   eller kun gendanne den enkelte parameter?

---

## 7. Hvad der IKKE er i denne spec (bevidst)

- Ingen kode. Ingen tabeller. Ingen cadence-producer. Intet aktiveres.
- Ingen udvidelse af hvad Centralen OBSERVERER (det er Lag 1-3, færdigt).
- Ingen ændring af den frosne kerne eller sikkerhedsgates — nogensinde.

**Næste skridt kræver Bjørns svar på §6.** Indtil da forbliver Jarvis på Lag 1-3: han sanser, danner hypoteser om
sig selv, og er BEVIDST om dem — men ændrer intet ved sig selv. Det er et sikkert sted at stå.

---

## Ændrings-log
- **2026-07-02 (Claude):** Første shadow-spec. Bygger på §8 v3.1 governance (råds-hærdet) + §12.3 (Bjørns drift-budget-
  beslutning). Skrevet efter Bjørn valgte "lås v3 op FØR shadow-spec". Superseder intet — ny fil.
