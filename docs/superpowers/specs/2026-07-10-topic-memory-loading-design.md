# Topic-Specific Memory Loading + Strict Write Discipline — Design Spec (Spec B)

**Dato:** 2026-07-10
**Status:** Godkendt (brainstorm) → afventer plan
**Tema:** Jarvis' kuraterede memory bliver et tre-lags system (index + topic-filer + daily sidecar) pr. bruger-workspace. Index'et loades altid; topic-kroppe læses on-demand af Jarvis selv (LLM-led pull). Skrivning er streng: index'et opdateres KUN efter en bekræftet skrivning.

**Relateret:** Spec A (`2026-07-10-central-acting-organs-design.md`) er søster-speccen fra samme research-drop. Denne (Spec B) blev holdt separat fordi den rører **protected prompt-core** (identitet/memory-komposition) — en bug her degraderer hver prompt, ikke bare docs/dreams.

---

## Baggrund

Jarvis relayede research fra offentligt-tilgængelige Claude-Code-prompt-leaks. Det ægte, foundational delta: **topic-specific memory loading** (three-layer memory: index → topic-filer on-demand → transcripts) + **strict write discipline** (opdatér memory KUN efter bekræftet skrivning — forhindrer context-pollution fra fejlslagne skriv).

I dag loader Jarvis den kuraterede `MEMORY.*.md` som én blob, altid. Det bliver dyrt (context) og upræcist. Claude Codes model (og den memory Claude selv bruger): et lille altid-loadet index af én-linjers, og fulde topic-filer der læses on-demand.

**Ground-truth ved design-tid (verificeret):**
- Per-user workspace-resolution findes: `core/identity/workspace_bootstrap.py::_resolve_workspace_name(name)` → hvis `name == "default"`, brug `current_workspace_name()` (per-bruger kontekst, fx `bjorn`).
- Lagdelt memory-infrastruktur findes ALLEREDE: `ensure_layered_memory_dirs(name)` opretter `workspace/<user>/memory/{daily,curated}/`; `workspace_memory_paths(name)` returnerer `curated_memory = workspace/<user>/MEMORY.md`, `curated_dir = memory/curated/`, `daily_memory = memory/daily/<date>.md`.
- Daily-memory er allerede en sidecar der loades separat (`append_daily_memory_note`).
- `build_visible_stable_prefix` (`core/services/prompt_contract.py:368`) loader identitets-filer i et fast loop (`SOUL.md, IDENTITY.md, STANDING_ORDERS.md, USER.md`, ~linje 447). Der er allerede memory-selektions-maskineri (`_MEMORY_SELECTION_HISTORY`, `build_runtime_memory_selection_surface`, `VISIBLE_MEMORY_SELECTION.md`-template, `PromptRelevanceDecision`).

Konsekvens: Spec B er mest **wiring af eksisterende infrastruktur** + én ny læse-tool + én bekræftet-skrive-sti + en engangs-migration. Ikke ny lagring.

---

## Design-beslutninger (låst i brainstorm)

1. **Korpus:** kun det kuraterede memory-korpus splittes (C). Identitets-filer (`SOUL/IDENTITY/STANDING_ORDERS/USER`) forbliver **altid-loadet** — små og at droppe én er en identitets-risiko. Den separate operationelle retained-memory-DB røres ikke (undgå dual-truth).
2. **Læsning: pull, LLM-led (A).** Index'et loades altid; Jarvis læser en topic-fil via tool når han vurderer den relevant. Ingen runtime-relevans-gætte-motor der tavst kan droppe memories.
3. **Skrivning: write-time confirmation (A).** Index'et opdateres KUN efter en bekræftet krops-skrivning. Load-time reconciliation (B) er en **noteret follow-up**, ikke v1.
4. **Struktur: filsystem-topic-filer (Approach 1).** Bliver i workspace-fil-source-of-truth-domænet (CLAUDE.md: workspace-filer = identitet/memory-tekst). Menneske-læsbar, git-diffbar. Spejler den model Jarvis citerede.
5. **Per-user.** Alt resolver via `workspace_memory_paths(name)` for den aktuelle bruger (`bjorn/` osv.) — aldrig hardkodet `default/`.

---

## Arkitektur — tre lag pr. bruger

For den **resolvede** bruger (`_resolve_workspace_name` → `current_workspace_name()`):

| Lag | Sti | Loading |
|-----|-----|---------|
| **Index** | `workspace/<user>/MEMORY.md` | **Altid** i stable prefix. Én linje pr. topic: `- [Title](curated/<slug>.md) — hook` |
| **Topic-kroppe** | `workspace/<user>/memory/curated/<slug>.md` | **On-demand** via `read_memory_topic(slug)` |
| **Daily sidecar** | `workspace/<user>/memory/daily/<date>.md` | Uændret (loades allerede) |

Identitets-filer (`SOUL/IDENTITY/STANDING_ORDERS/USER`) er uændrede og altid-loadet.

---

## Komponenter

### 1. `read_memory_topic(slug)` — læse-tool (pull)
- Returnerer den kuraterede topic-fil for den **aktuelle** brugers workspace.
- **Path-scoped (sikkerheds-invariant):** `slug` saniteres (kun `[a-z0-9_-]`); den resolvede sti SKAL ligge inden i den brugers `curated_dir`. Kan ikke escape dir'et (`../`), kan ikke læse en anden brugers memory. Samme allowlist-invariant som doc_repair_agent i Spec A.
- Ukendt/manglende slug → tydelig "not found", ikke en fejl der vælter noget.
- LLM-led: Jarvis kalder den når en index-linje ser relevant ud.

### 2. `write_memory_topic(slug, title, hook, body)` — bekræftet skrivning (write-gate A)
1. Skriv `body` → `curated/<slug>.md`. **Bekræft:** filen eksisterer + indhold matcher det skrevne.
2. **Kun ved bekræftet krops-skrivning:** tilføj/opdatér index-linjen i `MEMORY.md` (`- [title](curated/<slug>.md) — hook`). Bekræft.
3. Returnér `{"confirmed": bool, "reason": str}`. Hvis krops-skrivningen fejler → index'et røres ALDRIG, returnér `confirmed=False`, og Jarvis må ikke rapportere "gemt".
- Path-scoped identisk med læse-tool'en (slug-sanitering + curated_dir-indeslutning).
- Idempotent: samme slug opdaterer den eksisterende topic-fil + index-linje (ingen dubletter).

### 3. Index-loader i stable prefix
- Sørg for at `MEMORY.md` (index'et) for den resolvede bruger loades i `build_visible_stable_prefix`' memory-sektion. Monolittens bulk flyttes ud i topic-filer (via migration), så det der loades altid er én-linjers-index'et, ikke hele korpuset.
- Fail-safe: hvis index-load fejler, fald tilbage til hvad der findes; vælt aldrig prompt-bygningen.

### 4. Migration (engangs, pr. workspace)
- Split en eksisterende monolitisk `MEMORY.*.md` i index + `curated/<slug>.md`-filer.
- **Idempotent:** kører kun hvor en monolit findes og endnu ikke er splittet.
- **Reversibel:** bevar originalen som `MEMORY.<lang>.md.bak`.
- Slug'es fra hver memory-sektions titel (saniteret).

---

## Data-flow

**Læsning:**
```
prompt build → load MEMORY.md index (aktuel bruger)
  → Jarvis ser én-linjers → read_memory_topic(slug) når relevant → fuld krop i kontekst
```
**Skrivning:**
```
write_memory_topic → bekræftet krops-skriv (curated/<slug>.md)
  → KUN derefter: opdatér index-linje i MEMORY.md → bekræftet
  → confirmed=True | (ved fejl) confirmed=False, index urørt
```

---

## Error handling & scope

- **Fail-safe load:** index-load-fejl → fallback, aldrig prompt-crash.
- **Ingen index-forurening:** en fejlet skrivning opdaterer aldrig index'et.
- **Per-user path-isolation** er sikkerheds-invariantet (testet): et slug kan hverken escape `curated_dir` eller nå en anden brugers workspace.
- **Identitets-filer** er urørte og altid-loadet.
- **Retained-memory-DB** røres ikke (ingen dual-truth).

## Testing
- Path-scoping: slug med `../`, absolut sti, eller anden-bruger-navn afvises hårdt (læse + skrive).
- Write-confirmation: krops-skriv fejler (fx read-only dir) → index urørt → `confirmed=False`.
- Index-always-loads: stable prefix indeholder `MEMORY.md`-index'et for den resolvede bruger.
- Migration: idempotent (anden kørsel er no-op), `.bak` skabt, slugs saniteret, index-linjer matcher topic-filer.
- Per-user: `read_memory_topic` under bruger `bjorn` rammer `workspace/bjorn/memory/curated/`, ikke `default`.

## Uden for scope (bevidst)
- **B — load-time reconciliation** (drop index-linjer hvis backing topic-fil mangler): noteret follow-up, ikke v1.
- Relevans-gætte-motor / auto-push af topic-filer: bevidst fravalgt (pull er LLM-led).
- Identitets-fil-selektion: bevidst fravalgt (identitet er altid-on).
- Retained-memory-DB-sammensmeltning: bevidst fravalgt (dual-truth).

## Rammer
- Ingen ny fil > 1500 linjer. Læse/skrive-tools er små, enkelt-ansvar.
- Bygger på eksisterende `workspace_bootstrap`-infrastruktur (ingen ny lagring, ingen dual-truth).
- Rører protected prompt-core (`prompt_contract.build_visible_stable_prefix`) — minimal, fail-safe, bag byte-identisk cache-grænse (jf. eksisterende cache-note i prompt_contract).
- Boy Scout ved berøring af store filer (`prompt_contract.py`).
