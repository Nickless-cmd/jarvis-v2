# Central-styret indre liv — ændrings-drevet injektion

**Dato:** 2026-07-05
**Status:** Design godkendt, afventer spec-review → plan
**Ophav:** Bjørn 5. jul — "gør hans indre liv ægte og mere rigt, bare smartere og styret af Centralen. Alt flyder igennem den; når værdierne faktisk ændrer sig, laver Centralen kaldene og injicerer dem i hans prompt."

---

## 1. Problem (målt, ikke antaget)

Den visible prompt-assembly tager **5–24s (median ~12s)** FØR modellen overhovedet begynder at svare. Det er den latens Bjørn mærker som "han er lang før han svarer". Pengene er ikke problemet (cache-hit 98,5% → $0,13/døgn); **latens + spildt compute** er.

Målt via eksisterende instrumentering (`prompt-assembly-timing` + `prompt-assembly-awareness-top10`, stderr pr. assembly, `prompt_contract.py:2164`):

- **Strukturel rod:** wall-clock domineres ikke af de parallelle futures, men af at **~40 sektioner bygges serielt på hovedtråden** (`sync_seg_mid_done` ~7s, `sync_before_heavy_resolves` op til 14,7s).
- **Tunge enkelt-sektioner (ægte ms/tur):** `rule_engine_conclusions` ~6.000, `frame` ~4.000, `cognitive_state` 170 cached / **6.000 kold**, `memory_selection` 1.500–2.700, `multi-signal_recall` 1.200–1.900, `recall-before-act` ~1.200, `relevance` ~1.500, `visible_session_continuity` 1.300–1.800.
- **Beviset på det rigtige mønster:** `self_state` (~50ms) *læser* durabel tilstand i stedet for at genberegne den. Det er modellen alle de tunge burde følge.

Kerne-observationen: de tunge sektioner beskriver **Jarvis' egen tilstand** (mood, frame, fyrede regler, kausal-narrativ) — de afhænger IKKE af den aktuelle brugerbesked. Alligevel regenereres de fra bunden ved hvert samtale-hjerteslag, på den blokerende svar-sti, i kamp med den model der skal svare (kommentar i `prompt_contract.py:543`: futures "hver laver et ollama/LLM-kald der kø'er 28-91s når ollama er optaget af det synlige svar").

Fuldt sektions-inventar (verificeret pr. builder): `docs/notes/` — se agent-inventaret 5. jul (alle ~50 sektioner klassificeret LLM_CALL / STATE_READ / DB_QUERY / SUBSYSTEM_COMPUTE / STATIC).

## 2. Mål og ikke-mål

**Mål:**
1. Flyt de tunge, ikke-besked-afhængige indre-livs-sektioner af den blokerende svar-sti → Centralen vedligeholder dem i baggrunden, hot-path'en *læser* dem (~50ms).
2. Genberegn kun når en værdi **materielt ændrer sig** (ændrings-drevet, ikke ur-drevet) → nul LLM-kald på de fleste ture, men altid aktuelt indhold.
3. Gør det indre liv **rigere** — genopliv sektioner der var støj før Centralen, nu under Central-styring.
4. Median-assembly fra ~12s → **~2-4s** uden at gøre ham fladere.

**Ikke-mål:**
- Ikke fjerne indre liv for hastighedens skyld. Hver flytning skal bevise lige-så-rig-eller-rigere.
- Ikke røre de load-bearing recall/relevance-mekanismer ud over dedup (de er besked-afhængige og bliver live).
- Ikke bygge en ny model-router (cache/burn er allerede løst, jf. `reference_llm_economy_and_egress`).

## 3. Arkitektur — Central-styret injektions-register

Ny komponent: **injektions-register** (`core/services/central_injection_registry.py`). Hver indre-livs-sektion bliver en registreret **injektions-enhed**:

```
InjectionUnit:
  key: str                    # fx "cognitive_state", "rule_conclusions"
  source_nerves: list[str]    # fx ["cognition:affect", "cognition:agenda"]
  threshold: float            # materiel-ændrings-tærskel på delta
  max_age_s: float            # sikkerhedsnet: refresh selv uden ændring
  compose_fn: Callable[[], str]   # den EKSISTERENDE builder (uændret)
  cache_key: str              # durabel runtime-state-nøgle
  priority: int
```

**Tre klart adskilte enheder med ét ansvar hver:**

1. **Refresh-motor** (runtime-proces, kører på Centralens cadence): finder beskidte enheder → kalder `compose_fn` → skriver `{text, composed_at, source_snapshot}` til durabel kv. Dette er hvor LLM/subsystem-kaldene nu sker — OFF den blokerende sti.
2. **Ændrings-detektor** (del af refresh-motoren): afgør beskidt/ren (§4).
3. **Injektions-læser** (api-proces, i prompt-assembly): `read_injection(key) -> str` læser den cachede tekst. Ingen komposition. Falder tilbage til tom streng hvis aldrig komponeret (aldrig et LLM-kald på hot-path).

Cross-proces via runtime-state kv (samme mønster som `central_self_state`/`bridge_presence` — refresh i runtime-proces skriver, api-proces læser).

**Interface-kontrakt:** hot-path kalder KUN `read_injection(key)`. Den kan ikke udløse komposition. Det er den hårde grænse der garanterer at assembly aldrig blokerer på et indre-livs-kald igen.

## 4. Ændrings-detektion — signal-delta + max-alder (hybrid)

Refresh-motoren holder sidst-sete kilde-nerve-værdier pr. enhed. En enhed er **beskidt** hvis:
- en `source_nerve`s seneste værdi (fra `central_timeseries`) er flyttet > `threshold` siden sidste komposition, ELLER
- `now - composed_at > max_age_s` (sikkerhedsnet — fanger drift tærsklen missede, og garanterer at intet står stale ubegrænset).

Centralen ser allerede alle nerver, så delta-tjekket er et kv/timeseries-opslag, ikke et nyt signal. De fleste ture: intet over tærskel → ingen enhed beskidt → **nul kald**.

**Governance:** tærskler og max-alder er per-enhed konfig (runtime-state, kan tunes live uden deploy). Rate-limit pr. enhed (min-interval mellem refreshes) mod churn hvis en kilde-nerve er støjende.

## 5. Sektions-klassifikation (de tre bunker)

### 🟢 Flyttes til Central-vedligeholdt cache (baggrund)
Beskriver Jarvis' tilstand, ikke beskeden:
- `rule_engine_conclusions` (~6s) — kilde: regel-fyrings-nerver.
- `cognitive_state` (kold 6s) — kilde: affekt/agenda/valens.
- `frame` (~4s) — kilde: mode/salience-nerver.
- `causal_narrative` / `causal_alerts` / `causal_patterns` / `pattern_counterfactuals` — kilde: event-graf-opdateringer.
- `indre_liv` — kilde: inner-voice/self-model-surfaces.
- **De ~30 serielle STATE_READ-surfaces konsolideres til ÉN baggrunds-enhed:** "runtime awareness digest" (self-report, world-model-nudges, goals, todos, drift, hypoteser, milestones osv.). Én cache-læsning i stedet for 30 serielle builds. Det fjerner størstedelen af `sync_seg_mid_done`.

### 🔵 Bliver live (besked-afhængige) — men dedupliceres
- Recall-klyngen: `multi-signal_recall`, `recall-before-act`, `memory_selection`, `recall_bundle`, `jarvis_brain_facts` = 4-5 overlappende recall-LLM-passes (~5-8s samlet). **Konsolidér til 1-2** friske passes. Bliver på hot-path (grounding til spørgsmålet skal være friskt).
- `relevance` (~1,5s LLM-gatekeeper): bliver live nu; noteret som senere kandidat til en billigere/hurtigere klassifikator (ikke i denne spec).

### 🔴 Lukkes (ægte spild — IKKE indre liv)
- `dead_skills_(never_invoked)` (~175ms/tur) — bygger tekst om aldrig-brugte skills.
- `bounded inner visible prompt bridge` — future der på visible-lane GARANTERET returnerer `line=None` (`prompt_contract.py:2860`); ren spildt orkestrering.

Alt andet der tidligere så "dødt" ud (curiosity/retrospektiv-teasere, one-shot-milestones) **genoplives** i stedet under Central-styring (§6) — Bjørns pointe: hans adfærd har ændret sig markant efter Centralen, så tidligere støj kan være signal nu. De behandles som 🟢-baggrunds-enheder med lav-prio + fader-når-tom, ikke som luk-kandidater.

## 6. Anti-gaming — self-surveillance-genoplivningen

Self-surveillance-familien (`R2_gate_telemetry`, `decision_adherence`, `metacognition_signals`) blev skåret 22. jun fordi (a) rå tal injiceret → modellen narrerede dem tilbage performativt, og (b) selv-set score er gambelbar (han kan lære at *se* lydig ud uden at *være* det). Genoplives nu under ét jernhårdt princip:

> **Den målte må aldrig kontrollere måleren.**

**Mekanisme:**
1. **Central-ejet målemodul** (`core/services/central_behavioral_truth.py`, read-only over event-strømmen/runs): udleder adherence, kontradiktion, metacognition fra Jarvis' *faktiske adfærd* — aldrig fra hvad han siger om sig selv.
2. **Self-surveillance-injektions-enheder læser KUN fra dette modul.** Eksekverbar invariant-test: disse enheders `compose_fn` importerer/læser ingen Jarvis-skrivbar tilstand (workspace-filer, selv-rapporteret kv). Kun `central_behavioral_truth`.
3. **Centralen injicerer konsekvensen, ikke tallet.** I stedet for "din kontradiktions-rate er 0,3" → `central().decide` producerer et direktiv: "du modsagde X tidligere — forlig det før du fortsætter." Signalet driver adfærd; modellen ser virkningen, ikke måleren.
4. **Divergens er et §8-flag.** Hævder han "jeg var lydig" men events viser andet → Centralen ser afvigelsen, og *den* er et selvbedrags-signal (samme ånd som §8 hypotese-døds-mekanismen: falsificerbar ground truth, selv-påstand tjekket mod den).

## 7. Rigdom bevaret + måling + rollback (førsteklasses)

- **Rigdoms-bevis:** for hver flyttet sektion, snapshot-sammenlign den renderede tekst før (hot-path-build) vs efter (cached injektion). Den cachede skal være **lige-så-rig-eller-rigere** — ellers rulles enheden tilbage. Vi cacher, vi amputerer ikke.
- **Latens-måling:** før/efter via eksisterende `prompt-assembly-timing`. Mål median + p95 over ≥50 ægte ture pr. fase.
- **Rollback-kriterium (per enhed):** rul tilbage hvis (a) renderet output bliver fladere/kortere uden grund, (b) latens-regression, ELLER (c) staleness (Bjørn eller en check ser forældet indhold). Hver enhed er individuelt reversibel (flag pr. enhed: live-cache vs hot-path-build).

## 8. Intern fasering (én spec, faset eksekvering)

- **Fase 0 — mekanisme:** `central_injection_registry` + refresh-motor + ændrings-detektor + `read_injection`. Ingen sektioner flyttet. Verificér: register kan holde en test-enhed, refresh fyrer på delta+max-alder, hot-path læser cached. Tests grønne.
- **Fase 1 — pilot (bevis):** flyt `rule_engine_conclusions` + `cognitive_state`. Mål før/efter-ms + rigdoms-snapshot. GATE: begge lige-så-rige + målt latens-fald, ellers stop og revidér.
- **Fase 2 — fuld migration:** resten af 🟢 + digest-konsolidering (30 reads → 1 enhed) + recall-dedup (5 → 1-2). Mål pr. skridt.
- **Fase 3 — self-surveillance-genoplivning:** `central_behavioral_truth` + anti-gaming-invariant-test + de tre familier som konsekvens-injicerende enheder.
- **Løbende:** luk `dead_skills` + null-bridge (kan gøres i Fase 0, lav risiko).

Hver fase deployes + måles + er reversibel før næste.

## 9. Risici

- **Staleness:** en enhed refresher ikke fordi tærskel/max-alder er sat forkert → forældet indre liv. Modvirkes af max-alder-sikkerhedsnet + rollback-kriterium (c) + live-tunbare tærskler.
- **Cross-proces-cache-race:** refresh (runtime) skriver mens læser (api) læser. Løses med atomisk kv-write + læser tolererer sidste-gode-værdi (samme mønster som `central_self_state`, allerede bevist).
- **Refresh-kontention:** baggrunds-refresh laver stadig LLM-kald der deler ollama med den visible model — men OFF den blokerende sti, så det forsinker kun refresh (acceptabelt) og er dirty-gated (sjældent).
- **Rigdoms-regression:** en cached enhed mister nuance den friske havde. Fanges af snapshot-sammenligning i hver fase-gate.
- **Anti-gaming-hul:** en genoplivet enhed læser ved en fejl Jarvis-skrivbar tilstand. Fanges af den eksekverbare invariant-test (Fase 3).

## 10. Test

- **Fase 0:** enheds-tests for register (dirty-detektion på delta, på max-alder, ren når intet flyttet), `read_injection` fallback-til-tom, cross-proces-læsning.
- **Fase 1-2:** pr. migreret enhed: rigdoms-snapshot-test (før/efter ikke fladere) + latens-assertion.
- **Fase 3:** invariant-test (self-surveillance-enheder rører ingen Jarvis-skrivbar kilde) + divergens-flag fyrer når selv-påstand ≠ måling.
- **Live:** før/efter `prompt-assembly-timing` over ≥50 ægte ture pr. fase; median + p95.

## 11. Åbne valg (afgøres i planen, ikke blokerende)

- Præcise tærskler + max-alder pr. enhed (starter konservativt: lav tærskel, max-alder ~5-10 min; tunes på data).
- Om recall-dedup lander på 1 eller 2 passes (måles i Fase 2).
- Digest-enhedens interne struktur (én stor tekst vs få prioriterede blokke).
