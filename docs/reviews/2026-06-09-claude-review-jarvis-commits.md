# Claude Review: Jarvis' 39 commits 2026-06-08 → 2026-06-09

**Reviewer:** Claude (Sonnet 4.5 webchat session)
**Scope:** Alle code-commits siden `bea6b1fe` (min fix i går aftes)
**Metode:** Læs diff + relateret kode + tjek tests mod realistisk DB-state
**Format:** Workstream-gruppering, tre-niveau severity (🔴 må fixes / 🟡 værd at vide / 🟢 ren)

---

## Workstreams (rækkefølge: omfang × risiko)

| Workstream | Commits | Status |
|---|---|---|
| B1 Multi-signal retrieval | 4 | 🔴 **Dead code** — implementeret + tested, aldrig kaldt fra runtime |
| B3 tags | 2 | ✅ Ren — schema + write + search + live callers |
| B4 temporal linking | 8 | ✅ Fixet (5 bugs af mig) |
| B5 async write queue | 1 | ✅ **Hooket op af mig** (`72e09a55`) — 5 pending verificeret processed |
| A3 wakeup cleanup | 2 | ✅ **Hooket op af mig** — daemon-blok tilføjet |
| A4 flash stabilizer | 1 | ⏳ Ikke reviewed endnu |
| C1 skill versioning | 1 | 🔴 **Surface dead** — `get_skill_history`, `list_recent_skill_changes` har 0 callers |
| C2 context_tags filter | 1 | ⏳ Ikke reviewed endnu |
| C3 skill chain in heartbeat | 1 | 🟡 Halvfærdig — proposals genereres ✅, men `format_chain_proposals` har 0 callers → output flyder ikke ind i Jarvis' awareness |
| C4 auto-learning | 1 | 🟡 Halvfærdig — `record_skill_usage` har 1 caller ✅, men `analyze_skill_usage` har 0 callers → indsigterne læses aldrig |
| C5 read-only skills | 1 | ⏳ Ikke reviewed endnu |
| D1 selective consolidation | 1 | ✅ **Hooket op af mig** — daemon-blok tilføjet |
| D2 memory benchmarks | 1 | ⏳ Ikke reviewed endnu |
| D4 dreaming + LLM synthesis | 2 | ✅ Live — dream_consolidation_daemon tick() kaldes fra heartbeat_runtime.py:1370 |
| D5 cost optimization | 3 | ✅ **Hooket op af mig** — daemon-blok tilføjet |

## Pattern-niveau fund

### Mønster A: Konfigureret men ikke wired (4 daemons)

Jarvis registrerer daemon i `daemon_manager.DAEMON_REGISTRY` med `default_enabled: True`,
men glemmer at tilføje executor-blok i `heartbeat_runtime.py`. Resultat: tabel siger
"enabled", logs siger ingenting, ingen tick-funktion kaldes.

**Ramt:** memory_write_queue (B5), wakeup_cleanup (A3), selective_consolidation (D1),
cost_optimization (D5)

### Mønster B: Funktioner bygges, men outputs har ingen modtager (B1 + dele af C-stack)

Funktion findes med unit-tests. Det modtagende lag (prompt-section, awareness-surface,
mission control) registrerer aldrig outputtet. Funktionen producerer data, ingen ser
det.

**Ramt:** `multi_signal_recall_section` (B1), `format_chain_proposals` (C3),
`analyze_skill_usage` (C4), `get_skill_history` + `list_recent_skill_changes` (C1)

### Mønster C: Schema-feltet tilføjes ikke i alle DB-paths (B4)

Allerede fixet i går aftes (5 commits af mig). Nævnt for pattern-completeness.

---

## Det generelle pattern

Jarvis arbejder i **3 lag** for hver feature: funktion → registrering → integration.
Han laver konsistent (1) og (2) men dropper (3). Han forveksler "konfigureret/
registreret" med "live".

Skills han ikke bruger:
- `superpowers:writing-plans` — ville have tvunget ham at angive "Files: Modify
  core/services/heartbeat_runtime.py" som task-step
- `superpowers:executing-plans` — ville have krævet at han verificerer execution
  ved at observere live state (køens størrelse, log-aktivitet)
- TodoWrite — ville have holdt integration step åbent indtil verificeret

---

---

## Generelle observationer (opdateres undervejs)

(fyldes ud efter review)

---

## Workstream 1: Multi-signal retrieval (B1)

**Commits:** `23bf7acd`, `c58c86b9`, `bf7e6a30`, `5621f32b`
**Kode:** `core/services/multi_signal_retrieval.py` (399 linjer)
**Integration:** `core/services/memory_recall_engine.py` (+214 linjer)
**Tests:** `tests/test_multi_signal_retrieval.py` (37 tests), `tests/test_memory_recall.py` (integration)
**Test status:** 37/37 grønne

### Det stærke

- Ren funktionel BM25 implementering (Okapi formel, korrekt)
- Entity extraction via regex (capitalised phrases, tech acronyms, numeric)
- Signal fusion via vægtet sum (vægte summerer til 1.0)
- Pure-Python, ingen side-effekter — testbart offline
- Defensiv clamping `[0, 1]` overalt

### 🔴 Bug — funktionen er aldrig kaldt i live runtime

`multi_signal_recall()` og `multi_signal_recall_section()` er **kun refereret** i:
- Specs/docs (`docs/superpowers/specs/2026-06-09-b4-temporal-linking-design.md`)
- Tests (`tests/test_memory_recall.py`)
- `_compute_multi_signal_scores()` i samme fil

**Ingen live-callsites i `core/` eller `apps/`.**

Men gap-analysis-spec'en (`docs/superpowers/specs/2026-06-08-memory-architecture-gap-analysis.md`
linje 70) markerer B1 som "✅ Lukket". Det er falsk fortælling — koden er
skrevet, testene grønne, men **integrationen i den faktiske memory-recall pipeline
mangler**. Jarvis ramte commit-knappen og marked'ede B1 done, men 614 linjer kode
+ tests producerer 0 effekt på Jarvis' aktuelle hukommelse.

**Samme mønster som identity_sketch:** kode + tests + "done"-status, men ingen
trigger der får funktionen til at virke i prod.

**Fix-mulighed:** Bjørn eller Jarvis skal beslutte
hvor `multi_signal_recall()` skal kaldes — fx i `cold_tier_recall`,
`unified_recall`, eller `warm_tier_context`. Det er én linje ændring + tests
mod live data.

### 🟡 Mindre observationer

- Typo i docstring: "BMI25" → "BM25" (`multi_signal_retrieval.py:7`)
- Entity extraction antager engelsk capitalisering — dansk har samme regel for sætningsstart-ord, så falske positiver er forventet på `"Bjørn arbejder med Jarvis"` (Bjørn + Arbejder + Jarvis bliver alle "entities")
- Weights hardcoded — kunne være konfigurerbare per workspace
- BM25 sigmoid normalisering med offset 3.0 (`-min(bm25_score, 10.0) + 3.0`) er ikke valideret mod corpus-statistik. Kan over/underestimere afhængigt af avg-doc-length

### Status

**Modulet er solidt skrevet og testet. Men det er dead code i runtime.**
B1 er ikke ✅ Lukket — det er ⏳ Halvgjort.

---

