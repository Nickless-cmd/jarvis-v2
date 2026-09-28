---
status: delvist
audited: 2026-09-28
ground_truth: 4 punkter lukket 28/9-2026 efter kode-verifikation; 3 står reelt åbent
---
# Spec-Gap Backlog

Genereret 2026-06-14 efter audit af alle 61 specs i `docs/superpowers/specs/` mod
kodebasen (7 parallelle Explore-agenter). ~50 specs er fuldt live; hullerne herunder.

> **Opdateret 28/9-2026.** Fire punkter stod markeret som åbne huller, men er bygget
> siden — verificeret i koden, ikke i commit-beskeder. Backloggen var 2,5 måned gammel
> og bar derfor forældede huller. Se «Lukket 28.9» nedenfor.
>
> Frontmatter sagde `status: færdig` fra 8. juli. Det var forkert — tre punkter stod
> stadig åbne. Rettet til `delvist`.

Status-legende: 🔴 ægte hul (kode mangler) · 🟡 hurtig win (kode findes, mangler wire)
· 🟠 større men afgrænset · ⚪ bevidst parkeret · 🔍 skal verificeres

---

## ✅ LUKKET 28.9.2026 — verificeret i kode

- **Promise-ledger (var #5)** — `core/services/promise_ledger.py` findes **og er wired**:
  `record_promise` kaldes fra `core/services/visible_runs_memory.py:268`, og
  `pending_promises` bruges i `core/services/prompt_contract.py:4215`.
  Backloggen sagde «ikke bygget».
- **db-split (var #9)** — `core/runtime/db.py` er **1.234 linjer**, ikke ~33.700.
  Domæne-splittet er gennemført; punktet er ikke længere et hul.
- **Interlanguage fase 3-4 (var #10)** — `interlanguage_llm_judge.py` og
  `interlanguage_analyze.py` findes begge i `core/services/`. Backloggen sagde «mangler».
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

## 🔴 Ægte huller — kode mangler (STADIG ÅBNE pr. 28.9.2026)

**1. Code-mode git-diff** *(jarvis-desk)* — `CodePanel.tsx` importerer `CodeBlock`, ikke
`DiffView`. Skriver Jarvis en fil, viser panelet filens indhold — ikke hvad der ændrede
sig. `DiffView.tsx` findes og virker (bruges i `rich/ToolCard.tsx` til tool-resultater),
så komponenten er der; det er wire'en i CodePanel der mangler.
*(Mobil-appen har det: `apps/mobile/src/lib/toolDiff.ts` + `components/DiffArk.tsx`.)*

**2. Context-ring backend-event** *(jarvis-desk)* — preview-panelet er bygget, men
streamen emitterer intet `system_event kind="context"` med live token/compaction-tal.
SSE-streamen bor nu i `apps/api/jarvis_api/routes/chat_stream_v2.py` (den gamle
`visible_runs_sse_v2.py` findes ikke længere). Ringen viser localStorage-fallback.

**3. Decisions-as-Signals** — `fired_decisions_section()` findes i
`core/services/decision_signals.py:251`, men kaldes ikke. `prompt_contract.py:1876-1877`
bruger stadig den gamle `enforcement_section()`. Én-linjes skift.

---

## 🟠 Større, men afgrænset

*(db-split og interlanguage flyttet til «Lukket 28.9». Ingen tilbage her.)*

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

- **2026-09-28:** 4 punkter lukket efter kode-verifikation; frontmatter rettet fra
  `færdig` til `delvist` (den var forkert — 3 punkter stod åbent). Nummereringen omlagt:
  de lukkede er ude af hul-listen, så de åbne står som 1-3.
- **2026-06-14:** genereret.
