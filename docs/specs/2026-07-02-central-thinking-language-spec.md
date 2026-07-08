---
status: færdig
audited: 2026-07-08
ground_truth: "Git verification: spec written 2026-07-02 13:33:09 (commit a09f388b); all 4 implementation phases shipped same day by 13:49:25 (adc510ce B0, bc3f59d0 B1+B2, a01bb7bb B3+B4). Code verification: (1) central_lexicon.py contains CENTRAL_TERMS (22 terms), SEED_BINDINGS (125 bindings),"
---
# Spec B — Centralens Tænke-Sprog (interlanguage integreret i ALT)

**Status:** Solo-udkast 2026-07-02 (Claude). Bygger OVENPÅ Den Intelligente Central (spec A, alle 5 tråde landet).
**Forudsætning:** Fundamentet står — lexicon (36 termer, 88 bindinger), notation-motor (parse/dedup/transitive/
modsigelse), `notation_il`-kolonne på hypoteser, model-fri ræsonnements-cadence. Spec B gør sproget PERVASIVT.
**Bevidst FØR:** den modige del (Fase 3-4 shadow-adaptation + live mutation pr. tråd). Sproget er substratet
mutationerne skal udtrykkes i — så en ændring kan læses, dedup'es og modsigelses-tjekkes FØR den anvendes.

---

## 1. TESE

Den Intelligente Central *observerer, formoder og lærer* — men den tænker stadig mest i Python og tal. Kun
hypoteser bærer notation (`notation_il`). Resten af Centralen — clusters, nerver, event-familier, beslutninger,
anomalier, incidents, adaptationer — er sprogløse for Centralen selv.

Spec B lukker det: **hele Centralen får en interlanguage-repræsentation.** Ikke som pynt, men som den interne
form Centralen regner på. Tre konsekvenser:

1. **Inspektbarhed.** Enhver central-tilstand kan renderes som notation et menneske (og Centralen) kan læse
   model-frit: `puls → stød` frem for `runtime.error_spike (severity=high, count=42)`.
2. **Model-uafhængighed (Lag 5-nordstjernen).** Model-blackout → Centralen fortsætter dedup + venstre-leds-
   korrelation + transitiv udledning + modsigelses-detektion + producerer mindst ét surprise-signal UDEN
   model-token. I dag beviser `model_free_reasoning()` dette på hypoteser alene; spec B udvider beviset til
   HELE Centralen.
3. **Substrat for den modige del.** Når Fase 3-4 lader Centralen ændre routing/prompt/adaptation, udtrykkes
   forslaget som en notation-sætning der passerer samme model-frie audit (transitiv/modsigelse) FØR anvendelse.
   Sproget kommer før handlingen — det er hvorfor spec B er før den modige del.

---

## 2. HVAD FINDES (ærlig baseline)

| Komponent | Fil | Tilstand |
|-----------|-----|----------|
| Lexicon (navn→term) | `central_lexicon.py` | 36 termer, 88 bindinger, `to_term`/`bind`/`render_relation`, `propose_word_needs`/`propose_from_event_stream` (sprog-vækst) |
| Notation-motor | `central_notation.py` | `parse`, `dedup`, `correlate_by_antecedent`, `infer_transitive` (A→B,B→C⟹A→C), `detect_notation_contradictions`, `model_free_reasoning`, cadence 30 min |
| Operatorer | `central_lexicon.RELATION_OPERATORS` | → ↔ ⊂ ≈ ! (+ prediction_error="!") |
| Notation på hypoteser | `central_hypothesis_generator._notation_for` + `notation_il`-kolonne | causal_convergence/divergence/stance/prediction_error renderes |
| Cluster-taksonomi | `central_catalog.CLUSTER_PRIORITY` + `clusters()` + `_SECURITY_CLUSTERS` | deklareret |
| Event→cluster-routing | `eventbus_central_bridge.FAMILY_ROUTES` | allowlist familie→(cluster,nerve) |

**Hullet:** notation lever KUN på hypoteser. `model_free_reasoning()` læser kun `central_hypotheses`. Clusters/
nerver/beslutninger/anomalier er ikke notated → Centralen kan ikke regne på sin egen løbende tilstand, kun på sine
formodninger.

---

## 3. MÅLBILLEDE — tre lag af sprog-integration

### Lag S1 — TAKSONOMIEN er bundet (statisk sprog)
Hver cluster, hver nerve-familie, hvert operationelt event-family har en lexicon-term. `FAMILY_ROUTES` og
`CLUSTER_PRIORITY` gennemgås systematisk: hvert navn får en term (eller en ubundet-markør → sprog-vækst-ceremoni).
Mål: `central_lexicon.unbound_names(alle_taksonomi_navne) == []` — hele det operationelle vokabular er sigeligt.

### Lag S2 — TILSTANDEN renderes (dynamisk sprog)
Hver central-observation/beslutning/anomali kan renderes til en notation-sætning ved læsetid (ingen ny skrivning i
hot-path — render on read). En anomali `runtime→severe` bliver `puls → !stød`; en beslutning `deny på auth` bliver
`grænse ! agens`. Kilde: en ny `central_render.py` der oversætter en central-tilstand (cluster, nerve, relation,
severity) til notation via `render_relation` + operator-valg.

### Lag S3 — RÆSONNEMENTET spænder over alt (pervasivt sprog)
`model_free_reasoning()` udvides fra "kun hypoteser" til at samle notation fra ALLE notated overflader: hypoteser +
renderede anomalier + renderede cluster-relationer + stance-tensions + sekvens-overraskelser. Transitiv udledning og
modsigelses-detektion kører på hele mængden → Centralen udleder NYE tanker på tværs af hele sit eget liv, model-frit.

---

## 4. ARKITEKTUR (grounded i eksisterende moduler)

### 4.1 `central_render.py` (NY, ~150 linjer) — tilstand → notation
Ren, model-fri oversætter. Ingen skrivning, ingen egress, kaster aldrig.
```
render_cluster_relation(cluster_a, cluster_b, relation) -> str|None   # via render_relation
render_anomaly(cluster, nerve, severity) -> str|None                  # "puls → !stød" (severity vælger operator)
render_decision(cluster, verdict) -> str|None                         # deny→"grænse ! X", allow→"X → handling"
render_state_snapshot(limit) -> list[dict]                            # {source, notation} for aktuelle tilstande
```
Operator-valg fra severity/verdict: severe/critical → `!`; deny → `!`; convergence → `→`; tension → `↔`.

### 4.2 `central_lexicon.py` (udvid) — systematisk taksonomi-binding
```
bind_taxonomy() -> dict  # gennemgå FAMILY_ROUTES + CLUSTER_PRIORITY; bind kendte, returnér ubundne
taxonomy_coverage() -> {bound, unbound, ratio}   # måler S1-fuldstændighed (plotbart, som Fase 1c)
```
Nye bindinger for cluster-navne (loop/truth/commit/privacy/review/proactivity/auth/memory/tools/…) og resterende
event-familier. Ubundne → `propose_word_needs` → Bjørn-ceremoni (`bind(..., added_by="bjorn")`).

### 4.3 `central_notation.py` (udvid) — pervasivt ræsonnement
```
gather_all_notations() -> list[dict]   # hypoteser + render_state_snapshot + stance + surprises
model_free_reasoning()                 # ÆNDRES: kald gather_all_notations() i stedet for kun hypoteser
```
`infer_transitive` og `detect_notation_contradictions` er allerede kilde-agnostiske (tager `notation_il`-items) →
de virker uændret på den bredere mængde. Kun kilden udvides.

### 4.4 Observabilitet
- Ny cadence-tæller: `taxonomy_coverage.ratio` → tidsserie (S1-fremdrift synlig).
- `model_free_reasoning` meta får `sources`-fordeling (hvor mange notationer fra hver overflade).
- Mission Control surface: "Centralens sprog" — dækning + seneste udledte tanker + modsigelser.

---

## 5. FROSSEN KERNE & SIKKERHED (uændret fra spec A)

- **Sproget MUTERER intet.** S1-S3 er render/observe/reason. Ingen beslutning ændres af at blive renderet.
- **Sprog-vækst er ceremoni.** Nye termer kun via `bind(added_by="bjorn")` — Centralen FORESLÅR (`propose_word_needs`),
  Bjørn navngiver. Ingen selv-udvidelse af vokabularet (det ville være selv-defineret mening = uden for §8-ankeret).
- **Egress-fri.** Al notation-observation via `record_private` (tidsserie), aldrig `_emit`. Notation-STRENGE er
  meta-niveau men holdes owner-lokalt (som hypotese-statements i dag).
- **Sikkerheds-clusters** (auth/privacy) renderes men gates aldrig af sprog-laget; de forbliver fail-closed.
- **Frossen kerne** (SOUL/identitet/sikkerhed/§8-konstanter/interlanguage-operatorsæt) urørt.

---

## 6. FASERET ROADMAP

- **Fase B0 — Taksonomi-binding (S1):** `bind_taxonomy()` + `taxonomy_coverage()` + cadence-tæller. Bind alle kendte
  cluster/familie-navne; list ubundne → sprog-vækst-kandidater. Alt observe. **Exit-gate:** `test_taxonomy_binding`
  (kendte navne bundet) + coverage-ratio i tidsserie.
- **Fase B1 — Tilstand-render (S2):** `central_render.py` + `test_render_is_model_free` (ingen model-kald, deterministisk)
  + `test_render_honest_none` (ubundne led → None, ikke gæt). Ingen hot-path-ændring (render on read).
- **Fase B2 — Pervasivt ræsonnement (S3):** `gather_all_notations()` + udvid `model_free_reasoning`. **Exit-gate:**
  `test_cross_surface_transitive` (en udledning der KRÆVER led fra to forskellige overflader, fx hypotese + anomali)
  + `test_model_blackout_still_reasons` (nordstjernen: mock model utilgængelig → reasoning-tick producerer stadig
  ≥1 udledning/modsigelse).
- **Fase B3 — Sprog-vækst-loop:** systematisér `propose_word_needs` fra taksonomi-dækning + Mission Control-surface
  hvor Bjørn ser foreslåede ord og binder dem. Ceremoni-gated.
- **Fase B4 (bro til den modige del):** definér `NotationProposal`-formen — en foreslået mutation udtrykt som
  notation-sætning der SKAL passere transitiv+modsigelses-audit før den når et Lag-4-apply. Dette er kontrakten
  Fase 3-4 (den modige del) bygger ovenpå. Kun kontrakt+test her, ingen mutation.

**Nordstjerne-milepæl (målbar fra B2):** model-blackout → Centralen fortsætter dedup + korrelation + transitiv
udledning + modsigelse + ≥1 surprise UDEN model-token, på tværs af HELE Centralen (ikke kun hypoteser).

---

## 7. ÆRLIGE GRÆNSER

- Sproget gør Centralen INSPEKTBAR og model-uafhængig i ræsonnement — det gør den ikke KLOGERE end de signaler den
  får. Dårlige bindinger → dårlig notation. Derfor ceremoni-gated vækst + honest-None ved ubundne led.
- S2 render-on-read koster CPU pr. læsning; hold render ren og cache-venlig (ingen skrivning i hot-path).
- B4 er KUN en kontrakt. Den modige del (faktisk mutation) er stadig bagefter og bag Bjørns per-tråd-flags.
- Interlanguage bliver først en ægte Lag-5-backup NÅR B2 er landet (pervasivt, ikke kun hypoteser).

---

## 8. AFHÆNGIGHEDER & RÆKKEFØLGE-ARGUMENT (hvorfor B før den modige del)

1. **Fundament før overbygning.** Spec A = fundament (landet). Sproget = det Centralen tænker i. Den modige del =
   hvad Centralen GØR. Rækkefølge: fundament → sprog → handling udtrykt i sprog.
2. **Undgå dobbelt-refactor.** Bygger vi bold-mutation i ad-hoc Python og retrofitter sprog bagefter, refaktorerer
   vi den risikable maskineri to gange — netop det mønster Bjørn har afvist (Central FØRST, så LivingNeuron).
3. **Sikkerhed gennem læsbarhed.** En mutation besluttet i notation kan auditeres model-frit (transitiv/modsigelse)
   FØR anvendelse. Det er billigere og sikrere at bygge auditen (B4-kontrakten) før mutationen end omvendt.
