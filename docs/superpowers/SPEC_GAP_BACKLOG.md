---
status: færdig
audited: 2026-09-28
ground_truth: ingen åbne huller — alle 7 punkter lukket efter kode-verifikation 28/9-2026; 4 punkter under «skal verificeres» er stadig uafklarede
---
# Spec-Gap Backlog

Genereret 2026-06-14 efter audit af alle 61 specs i `docs/superpowers/specs/` mod
kodebasen (7 parallelle Explore-agenter). ~50 specs er fuldt live; hullerne herunder.

> **Opdateret 28/9-2026 (anden runde).** Alle tre huller der stadig stod åbne, er nu
> lukket — men kun ét af dem krævede kode. De to andre var **allerede bygget** med en
> anden løsning end backloggen beskrev; beskrivelsen var forældet, ikke hullet ægte.
> Det er den samme fejlklasse som frontmatter bar: en tekst der påstod en tilstand
> uden at nogen verificerede den mod koden.
>
> **Læren:** en backlog er kun sand den dag den skrives. Verificér punktet i koden
> før du bygger — to af tre «huller» her var arbejde nogen allerede havde gjort.

Status-legende: 🔴 ægte hul (kode mangler) · 🟡 hurtig win (kode findes, mangler wire)
· 🟠 større men afgrænset · ⚪ bevidst parkeret · 🔍 skal verificeres

---

## ✅ LUKKET 28.9.2026 — kode skrevet

- **Code-mode git-diff** *(jarvis-desk)* — `CodePanel.tsx` viser nu ændringerne: en
  «Vis ændringer»-knap i edit-mode skifter mellem tekstfeltet og `DiffView`
  (`oldText=content`, `newText=draft`). Bygget 28/9; test i `CodePanel.test.tsx`
  (8/8 grønne). `DiffView` blev genbrugt, ikke genopfundet.

## ✅ LUKKET 28.9.2026 — var allerede bygget (backloggen tog fejl)

- **Context-ring backend-event** — backloggen sagde «ringen viser localStorage-fallback».
  Det er ikke sandt længere: `ChatView.tsx` poller `getContextInfo` og får det
  backend-autoritative transcript-estimat siden sidste compaction (`setContextTokens(r.tokens)`).
  Kommentaren i kilden siger det direkte: den gamle per-tur stream-usage «hoppede ulogisk»
  og blev erstattet 23/6-2026 af et **poll** frem for et SSE-event. Den *arkitektur*
  backloggen beskrev, findes ikke mere.
- **Decisions-as-Signals** — backloggen sagde `fired_decisions_section()` «kaldes ikke».
  Sandt, men irrelevant: den er en **ubrugt alternativ-formatter**. Den aktive vej er
  `evaluate_decision_triggers()`, som kaldes i det agentiske loop
  (`core/services/visible_runs.py:4347`), lægges i rundens kontekst via `_a_parts`, og
  emitteres som `decision_signal`-SSE-event. Signalet fyrer og når modellen.
- **Promise-ledger (var #5)** — `core/services/promise_ledger.py` findes **og er wired**:
  `record_promise` kaldes fra `core/services/visible_runs_memory.py:268`, og
  `pending_promises` bruges i `core/services/prompt_contract.py:4215`.
- **db-split (var #9)** — `core/runtime/db.py` er **1.234 linjer**, ikke ~33.700.
  Domæne-splittet er gennemført; punktet er ikke længere et hul.
- **Interlanguage fase 3-4 (var #10)** — `interlanguage_llm_judge.py` og
  `interlanguage_analyze.py` findes begge i `core/services/`.
- **User-temperature Site 4 (var #7)** — `get_response_style_modifiers` kaldes nu fra
  `core/services/prompt_sections/private_layer_sections.py:63`.

## ✅ LUKKET 15. juni (uændret)

- **Codex follow-up-adapter** — bygget + live-verificeret (commit 71c1fede). gpt-5.4-mini
  fuldfører nu tool-ture. Se [[project_codex_toolcall_empty_bug]].
- **Diagnosis-gate fase 1** — bygget (advisory, commit fe26fece). Logger uverificerede
  diagnostiske konklusioner; eskalerer til blocking efter data.
- **read_model_config aktiv-model** (ba292444) + **SIKKERHEDS-fixes** (search-scoping,
  override-data-guard, chronicle/scheduled-scope) — se [[project_db_table_scope_audit]].
- **Generalized-learning capture-wiring (item 8)** — plan A (direkte capture m. dedup):
  `capture_conclusion(..., dedup_key=...)` → reasoning_store. Live (0a850449).
- **User Management** (hele spec'en) + app-self-control tool-scope-fix + footer-fix —
  se [[project_user_management]] / [[project_desk_toolchips_appcontrol]].

---

## 🔴 Ægte huller — kode mangler

**Ingen.** Alle punkter der stod her pr. 28/9 er lukket.

## 🟠 Større, men afgrænset

*(db-split og interlanguage flyttet til «Lukket». Ingen tilbage her.)*

## ⚪ Bevidst parkeret (ikke huller)

- Counterfactuals fase 2 (gated `counterfactual_engine_phase2_llm_enabled=False`)
- Lying-engine Layer 3 (Ground Truth Registry)
- Associative-memory `memory_associations` DB-tabel (in-memory fallback virker)
- Multi-user Group 7 (oprydning + E2E-test)
- Code-mode deferred: multi-fil-diff-review, git-graf/branch-UI, inline-editor
- Terminal v2: interaktiv TTY via node-pty (feasibility lavet, deferred)
- Boy Scout-split af `cheap_provider_runtime.py` (codex-provider udskilles)

## 🔍 Skal verificeres (agenter var usikre)

- Code-mode hand-off-knap (`dispatch_to_claude_code`) — backend findes, UI-knap?
- Cowork ShareGuard/AgentDispatch-wiring
- Foundation R2 hang-watchdog → HungPrompt-sti
- Edge-case-tests: reconcile-race, approval-timeout, 401-midt-i-session

---

## Ændringslog for denne fil

- **2026-09-28 (runde 2):** de tre sidste huller lukket. Ét krævede kode (Code-mode
  git-diff — bygget); to var allerede bygget med en anden løsning (context-ring poller,
  decisions-signaler wired i loopet). Ingen åbne huller tilbage.
- **2026-09-28 (runde 1):** 4 punkter lukket efter kode-verifikation; frontmatter rettet fra
  `færdig` til `delvist` (den var forkert — 3 punkter stod åbent).
- **2026-06-14:** genereret.
