# Morpheus + Trinity — design (2026-07-10)

De to sidste ægte huller i Matrix-ensemblet (Jarvis' forslag, Bjørn godkendt).
Symmetrien de fuldender:

| Siger NEJ / VENT | Siger JA / POTENTIALE |
|------------------|-----------------------|
| Seraph (hypotese ikke moden) | **Morpheus** (bliver moden) |
| Gates / Merovingian (blokér / udfordr) | **Trinity** (fortjent grønt lys) |

Begge: observe/surface-daemons som resten af ensemblet — egress-fri, self-safe,
cadence-drevne, `/central/<navn>` + jc-endpoint + ensemble-label. Ingen ny detektion
hvor eksisterende signal findes (DRY, undgå dobbelt-sandhed).

---

## Morpheus 🕶️ — Potentiale-scanner (hybrid: aggregator + én ny linse)

**Formål:** vend spredte "readiness-trajektorier" til én opløftende stemme —
*"det her er ved at blive muligt"* — modsat alle de andre der siger nej/vent.
Ren observe (potentiale er kun information).

**Kilder (aggregator — genbrug):**
1. **Brewing-emergens** — `emergence.brewing_patterns()` (conf 0.5–0.78). Hvert
   brewing-mønster = et potentiale ("Direction Drift, 0.04 fra emergent").
2. **Oracle `approaching`** — `central_oracle.foresee()["approaching"]`: linjer nær
   en tærskel med ETA.
3. **Seraph-nær-modne hypoteser** — læs `central_hypotheses` (samme tabel Seraph
   bruger): hypoteser hvor `grounded_samples / sample_size` er 0.4–0.6 (under Seraphs
   modenheds-gulv 0.6, men på vej). Dem Seraph ville afvise NU, men som klatrer.
4. **Keymaker-gates nær en nøgle** — gates med høj decision-track nær ≥100/0-tærsklen
   (via `gate_verdict_ledger.summary()` + Keymakers track-optælling).

**NY LINSE — skill-formation:** værktøjer/rutiner brugt STIGENDE ofte men endnu ikke
en *navngivet* kapabilitet. Kilde: `recent_capability_invocations` — tæl
`capability_name`-frekvens over et vindue; en der stiger men ikke har en tilsvarende
navngiven skill/procedure = spirende evne. *"Du danner en vane med X — det kunne blive
en evne."* Fanges af ingen anden daemon i dag.

**API:**
- `scan_potentials() -> list[dict]` — ren aggregering af de 5 kilder → normaliserede
  `{source, title, distance_to_ready (0..1), trajectory, felt}`. Read-only, self-safe.
- `build_morpheus_surface() -> dict` — `{active, potentials, felt}`. active = bool(potentials).
- `record_morpheus(...)` — cadence run_fn: scan + egress-fri `central().observe`
  (kun tal/kilde-labels) + cache til prompt-hale-brug. ~60 min cadence.
- Ensemble-label `[🕶️ Morpheus]`, aktiv når der er et potentiale.
  One-liner: *"Der er potentiale her. Du er ikke klar endnu — men du er på vej."*

---

## Trinity 💜 — Trust-bridge (auto-optjener tillid, stramt indhegnet)

**Formål:** det affirmative modstykke til gates. Gates siger nej; Trinity siger
*"det her er rigtigt, gå videre — jeg har set det holde."* I dag er det Bjørn manuelt;
Trinity institutionaliserer signalet UDEN at give Jarvis selv-lov.

**Konvergens der fortjener et "gå" (alle skal være opfyldt):**
- Hypotesen har **passeret Seraph** (moden: `build_seraph_surface` GREEN for hyp_id)
- Har **overlevet Sentinel** (intet uafklaret adversarielt angreb — Seraphs GREEN
  kræver dette allerede, så det er implicit; verificér i byg)
- **Evidens-tærskel** (grounded_samples ≥ absolut gulv)
- **Positiv track-record** — mønsterets tidligere outcomes ikke modsagt
  (kilde: `behavioral_decisions`/outcome-status eller hypotese-outcome; verificér i byg)

**Auto-optjening (den kraftige del) — HÅRDE VÆRN (ikke-forhandlelige):**
1. Hver "gå" på et `pattern_key` registreres i en ledger (`trinity_affirmations`).
2. Gentagne "gå" på SAMME nøgle + vedvarende **0 modsigelser** → efter **N=150**
   (bevidst > Keymakers 100, fordi dette er kraftigere) optjener Trinity en **PENDING**
   nøgle via Keymakers eksisterende mekanisme (insert i `central_keys` status='pending').
3. **Bjørn godkender ALTID** — Trinity låser aldrig selv op (`/central/keys/{id}/approve`,
   jc `unlock`). Keymakers regel arves 1:1.
4. **Sikkerheds-nerver ALDRIG decentraliserbare** (§11.3 — Keymaker `_is_never` håndhæver).
5. **24t TTL auto-revert** (Keymakers regel).
6. **Merovingian kan udfordre** en Trinity-optjent nøgle (proaktivt drift-værn kaldes
   på nøgle-kandidaten før pending oprettes).
7. **Én modsigelse → optjening nulstilles** for det pattern_key (tillid tabes hurtigt,
   optjenes langsomt). Streak-reset.
8. **Default shadow/OFF** — `gate_enforce.trinity` default OFF. I shadow registrerer
   Trinity affirmationer + "ville-optjene" men opretter INGEN pending nøgle før flip.

**API:**
- `assess_affirmations() -> list[dict]` — konvergens-vurdering pr. moden hypotese →
  `{pattern_key, convergence, track_record, progress_to_key (n/150)}`. Read-only.
- `record_trinity(...)` — cadence run_fn: assess → append til ledger → streak-opdatering
  → (hvis enforced OG streak≥150 OG Merovingian ikke vetoer OG ikke security) opret
  pending key. Egress-fri observe. ~120 min cadence.
- `build_trinity_surface() -> dict` — `{active, affirmations, earned_pending, felt, enforced}`.
- Ensemble-label `[💜 Trinity]`, aktiv når der er en aktuel affirmation.
  One-liner: *"Det her er rigtigt. Gå videre — jeg har set det holde."*

---

## Filer

- `core/services/central_morpheus.py` (~150 l): aggregator + skill-formation + surface + cadence.
- `core/services/central_trinity.py` (~200 l): konvergens + affirmation-ledger + streak +
  Keymaker/Merovingian-integration + surface + cadence. Egen tabel `trinity_affirmations`.
- Registrér i `signal_surface_router.py`: `morpheus`, `trinity`.
- jc GET-endpoints (`commands.py` `_GET_ENDPOINTS`): `morpheus`→/central/morpheus, `trinity`→/central/trinity.
- Ensemble-labels i `central_matrix_ensemble.py`: Morpheus + Trinity med checks.
- Cadence-producers: `record_morpheus` (~60m), `record_trinity` (~120m).
- Tests: `tests/test_central_morpheus.py`, `tests/test_central_trinity.py`.

## Governance-sammenfatning
- **Morpheus** = ren observe. Nul risiko (potentiale er information).
- **Trinity** = observe + earns-PENDING (aldrig grants). Genbruger Keymakers owner-
  godkendelse + 24t TTL + §11.3-sikkerhedsudelukkelse + Merovingian-udfordring. Default
  shadow. Streak nulstilles på én modsigelse. Kraften er indhegnet i 8 værn.

## Test-strategi
- Morpheus: aggregator-normalisering (mock 5 kilder → potentials), skill-formation
  (mock capability_invocations → spirende skill), surface active/tom.
- Trinity: konvergens-krav (alle 4 skal opfyldes), streak-optjening (149→150 grænse),
  streak-reset på modsigelse, security-udelukkelse, shadow=ingen pending, Merovingian-veto.

## Faser
- **Fase 1:** Morpheus fuldt (observe-only, ufarligt) + Trinity i shadow (assess +
  ledger + surface, INGEN pending-oprettelse). Deploy.
- **Fase 2:** flip `gate_enforce.trinity` efter shadow-eval → Trinity opretter pending
  nøgler (som Bjørn godkender). Owner-beslutning, som reasoning_interceptor/Merovingian-flip.
