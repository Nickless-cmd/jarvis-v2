# Spec-Gap Backlog

Genereret 2026-06-14 efter audit af alle 61 specs i `docs/superpowers/specs/` mod
kodebasen (7 parallelle Explore-agenter). ~50 specs er fuldt live; hullerne herunder.

Status-legende: 🔴 ægte hul (kode mangler) · 🟡 hurtig win (kode findes, mangler wire)
· 🟠 større men afgrænset · ⚪ bevidst parkeret · 🔍 skal verificeres

---

## ✅ LUKKET 15. juni
- **Codex follow-up-adapter** — bygget + live-verificeret (commit 71c1fede). gpt-5.4-mini
  fuldfører nu tool-ture. Se [[project_codex_toolcall_empty_bug]].
- **Diagnosis-gate fase 1** — bygget (advisory, commit fe26fece). Logger uverificerede
  diagnostiske konklusioner; eskalerer til blocking efter data.
- **read_model_config aktiv-model** (ba292444) + **SIKKERHEDS-fixes** (search-scoping,
  override-data-guard, chronicle/scheduled-scope) — se [[project_db_table_scope_audit]].

## 🔴 Ægte huller — kode mangler

2. **Code-mode git-diff** *(v1-krav, jarvis-desk)* — `CodePanel` har ingen diff-rendering.
   Spec 2026-06-12-jarvis-desk-code-mode kræver "write/edit viser en diff i panelet" (v1).
   Var "Task 10 / openDiff"-TODO der aldrig blev lavet. Byg: detektér write/edit-tool_use-
   blokke → byg diff-artifact → vis i ArtifactPanel med diff-komponent.

3. **Context-ring backend-event** *(jarvis-desk)* — preview-panelet er bygget, men v2-stream
   emitterer ikke `system_event kind="context"` med live token/compaction-tal. Ringen viser
   localStorage-fallback. Backend: emit context-event i visible_runs_sse_v2.

5. **Promise-ledger** *(14. jun, fase 2 af diagnosis-gate)* — ledger + verifier (tjek git/fil
   for "det er gjort"-løfter). Ikke bygget. Bygger ovenpå diagnosis-gate (nu live).

## 🟡 Hurtige wins — kode findes, mangler ét wire

6. **Decisions-as-Signals** — `fired_decisions_section()` findes men kaldes ikke;
   `prompt_contract.py:1156-1157` bruger stadig gamle `enforcement_section()`. Én-linjes skift.

7. **User-temperature Site 4** — `get_response_style_modifiers()` findes men injiceres ikke i
   visible-run-prompten.

## ✅ LUKKET 15. juni (runde 2)
- **Generalized-learning capture-wiring (item 8)** — plan A (direkte capture m. dedup):
  deep_analyze/reasoning_classify/self_evaluation/counterfactual kalder nu
  `capture_conclusion(..., dedup_key=...)` → reasoning_store. learning_policy fungerede
  allerede via orchestratoren (cognitive_state-familie). Latent-bug fixet: `reasoning`
  event-familie var afvist af eventbus (publish kastede altid). Live (0a850449).
- **User Management** (hele spec'en) + app-self-control tool-scope-fix + footer-fix —
  se [[project_user_management]] / [[project_desk_toolchips_appcontrol]].

## 🟠 Større, men afgrænset

9. **db-split** — `core/runtime/db.py` er stadig ~33.700 linjer (kun fase 0 udskilt). Fase 1-N
   domæne-splits (runtime_self, private, dream, chronicle…) mangler.

10. **Interlanguage-validation fase 3-4** — data indsamlet (1000+ udtryk), men
    `interlanguage_llm_judge.py` + `interlanguage_analyze.py` mangler → ingen analyse-rapport.

## ⚪ Bevidst parkeret (ikke huller)

- Counterfactuals fase 2 (gated `counterfactual_engine_phase2_llm_enabled=False`)
- Lying-engine Layer 3 (Ground Truth Registry)
- Associative-memory `memory_associations` DB-tabel (in-memory fallback virker)
- Multi-user Group 7 (oprydning + E2E-test)
- Code-mode deferred: multi-fil-diff-review, git-graf/branch-UI, inline-editor
- Terminal v2: interaktiv TTY via node-pty (feasibility lavet, deferred)
- Boy Scout-split af `cheap_provider_runtime.py` (2897 linjer — codex-provider udskilles)

## 🔍 Skal verificeres (agenter var usikre)

- Code-mode hand-off-knap (`dispatch_to_claude_code`) — backend findes, UI-knap?
- Cowork ShareGuard/AgentDispatch-wiring
- Foundation R2 hang-watchdog → HungPrompt-sti
- Edge-case-tests: reconcile-race, approval-timeout, 401-midt-i-session
