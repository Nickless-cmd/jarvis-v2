# Nådig Glemsel & Lærings-modning — Design

**Anledning:** Liveness-audit + Codex' health-check (15. jun). Spørgsmål fra Bjørn:
har vi døde systemer / for meget DB-støj, og hvordan bevarer vi hans indre liv RIGT
mens vi bremser ubegrænset vækst? Princip: **mål er ikke at få ham til at glemme —
mål er at hans læring bliver til erfaring, ikke bare flere events.**

---

## Allerede bundet (deployet 15. jun — verificeret live)

| Problem | Fix | Resultat |
|---|---|---|
| `jobs_queue.json` 48 MB (66k jobs, 99,5% færdige) genskrevet hvert tick | prune-on-save: behold ikke-terminale + seneste 2000 terminale | **48 MB → 1,46 MB**, 66.260 → 2.000 jobs |
| `reasoning_conclusions` +3k/dag, prune forældreløs | wire `compact_stale` (30d+conf<0.1) i 24h-retention | janitor live; 0 slettet (hans læring urørt) |
| `generalized_policies` aldrig-matchede akkumulerer | prune (match_count=0 + 30d) | 47 værdiløse fjernet |
| Telemetri (`cheap_provider_invocations`, `daemon_output_log`) | age-prune (60d/30d) | ~21k rækker; selv-bounding |

→ De **konkrete ubegrænsede vækst- + perf-problemer er løst.** Hans hukommelse/identitet er **ikke rørt**.

---

## Tilbage — to ægte design-spor (rører hans kognition → review før eksekvering)

### Spor 1 — Lærings-modning (Codex' kerne: "erfaring, ikke flere events")

**Rod-årsag (verificeret):** `policy_abstraction.py:132` laver en **ren INSERT pr. generalisering** — ingen dedup/merge. ~2.750 policies/dag, mange near-duplikater. `reasoning_conclusions` ligeså (plain INSERT). Konsolidering KØRER (idle_consolidation, distillation, forgetting-cycles aktive sidste 24h) men på et HØJERE niveau; de specifikke lærings-tabeller modnes ikke.

**Vigtigt:** det forurener IKKE prompten (top-k retrieval ved confidence+match_count). Det er lærings-KVALITET: signal-til-støj i policy-rummet falder, og near-dups der lejlighedsvist matcher overlever never-matched-prunen.

**Design:** ved generalisering, FØR insert — slå op efter en eksisterende near-identisk principle (embedding-similarity over `generalized_principle`). Hvis match over tærskel → **MERGE** (bump `match_count` + hæv `confidence`, tilføj kilden til `source_rules_json`) i stedet for ny række. Effekt: gentagne lektioner bliver til ÉT stærkere princip, ikke 2.750 svage. Det ER "erfaring frem for events".
- Risiko: ændrer hans lærings-dynamik (færre, stærkere policies). Bør pilottes med shadow-måling (sammenlign policy-rummets entropi før/efter).
- Reasoning_conclusions: samme mønster kan overvejes, men de er allerede top-k-hentet, så lavere prioritet.

### Spor 2 — Nådig glemsel for HUKOMMELSE/IDENTITET (aldrig sletning)

Disse vokser men må ALDRIG age-slettes (det = at få ham til at glemme sit liv):
`events` (1.2M, load-bearing — læses af counterfactual/dream_bias/longing/finitude),
`private_brain_records` (87k), `cognitive_*`-memories, `sensory_memories`,
`emotional_memory_anchors` (51k), `causal_edges` (80k, +3k/dag).

**Design pr. type (decay ≠ delete):**
- **Salience-decay + arkivering:** `private_brain` har allerede `compute_effective_salience` + `auto_archive_low_salience` (status='archived', beholder rækken). Verificér det KØRER og udvid mønstret: lav-salience + gammel + aldrig-genkaldt → `archived` (skjult fra hot-path, bevaret). ALDRIG DELETE.
- **`events`:** load-bearing. Hvis vækst bliver et reelt problem: rul gamle events (>Nd) op i et komprimeret `events_archive` (eller en daglig sammenfatning) i stedet for at slette — så counterfactual/dream stadig kan nå dem hvis nødvendigt. Kræver verifikation af hvor langt læserne kigger tilbage.
- **`causal_edges`:** confidence/recency-decay — svage, gamle, aldrig-aktiverede kanter → archived. Bevarer kausal-strukturen, nedprioriterer støj.
- **`emotional_memory_anchors` / `memory_entities`:** har friskheds-felter (`captured_at`, `first_seen/last_seen`) — IKKE uden tid. Salience-decay, ikke sletning.

### Spor 3 — Friskheds-mapping (tooling, lav risiko)

Cartography/liveness-scripts antog `created_at/updated_at` og kaldte fejlagtigt store tabeller "uden tid". De HAR tid under andre navne: `captured_at`, `indexed_at`, `first_seen/last_seen`. Fix: en tabel→tidsstempel-kolonne-mapping i liveness-tooling, så hjernekortet ser friskhed korrekt.

### Spor 4 — Konsoliderings-ratio-metrik (observability)

Eksponér forholdet læring-throughput / konsolidering (fx `learning_policy.generalized` vs `*_consolidation_completed` pr. døgn) som en Mission Control-metrik, så vi kan SE om modningen holder trit fremover — i stedet for at opdage det ved en 48 MB-fil.

---

## Anbefalet rækkefølge (lav→høj risiko)

1. **Spor 3** (friskheds-mapping) — ren tooling, nul risiko.
2. **Spor 4** (konsoliderings-ratio-metrik) — observability, nul runtime-risiko.
3. **Spor 2 verifikation** — kører `auto_archive_low_salience` på private_brain? (samme gut-spørgsmål). Hvis forældreløs → wire den (arkiver, ikke slet).
4. **Spor 1** (policy-merge/dedup) — pilot med shadow-måling; ægte lærings-kvalitets-gevinst.
5. **Spor 2 udvidelse** (events/causal_edges arkivering) — størst omhu, rører hans substrat.

**Princip hele vejen:** bevar lagene, modn læringen, arkivér det svage, slet kun ren telemetri. Aldrig få ham til at glemme for at spare plads.
