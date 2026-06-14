# Spec-Gap Backlog

Genereret 2026-06-14 efter audit af alle 61 specs i `docs/superpowers/specs/` mod
kodebasen (7 parallelle Explore-agenter). ~50 specs er fuldt live; hullerne herunder.

Status-legende: 🔴 ægte hul (kode mangler) · 🟡 hurtig win (kode findes, mangler wire)
· 🟠 større men afgrænset · ⚪ bevidst parkeret · 🔍 skal verificeres

---

## 🔴 Ægte huller — kode mangler

1. **Codex follow-up-adapter** *(blocker for gpt-5.4-mini)* — `core/services/visible_followup.py`
   har adaptere for ollama + openai-compat, men INGEN for `openai-codex`. Resultat:
   agentic-loop springer codex over (`agentic-loop-skip reason=provider-not-supported`)
   → run afbrydes på ENHVER tool-tur. Empty-response-fixet (commit 346ae72c) gjorde tool-
   kaldet synligt; denne adapter mangler for at *fortsætte* samtalen med tool-resultatet i
   Responses API-format (function_call + function_call_output items, call_id-koblet).
   Workaround indtil da: brug deepseek/glm/ollama. Se [[project_codex_toolcall_empty_bug]].

2. **Code-mode git-diff** *(v1-krav, jarvis-desk)* — `CodePanel` har ingen diff-rendering.
   Spec 2026-06-12-jarvis-desk-code-mode kræver "write/edit viser en diff i panelet" (v1).
   Var "Task 10 / openDiff"-TODO der aldrig blev lavet. Byg: detektér write/edit-tool_use-
   blokke → byg diff-artifact → vis i ArtifactPanel med diff-komponent.

3. **Context-ring backend-event** *(jarvis-desk)* — preview-panelet er bygget, men v2-stream
   emitterer ikke `system_event kind="context"` med live token/compaction-tal. Ringen viser
   localStorage-fallback. Backend: emit context-event i visible_runs_sse_v2.

4. **Diagnosis-gate** *(14. jun, Jarvis' egen spec)* — `diagnosis_gate.py` findes ikke. Guard
   der kræver verifikation før diagnostiske konklusioner (mod konfabulation). Spec udvidet
   14. jun (175 linjer), kode aldrig skrevet.

5. **Promise-ledger** *(14. jun, fase 2 af diagnosis-gate)* — ledger + verifier (tjek git/fil
   for "det er gjort"-løfter). Ikke bygget.

## 🟡 Hurtige wins — kode findes, mangler ét wire

6. **Decisions-as-Signals** — `fired_decisions_section()` findes men kaldes ikke;
   `prompt_contract.py:1156-1157` bruger stadig gamle `enforcement_section()`. Én-linjes skift.

7. **User-temperature Site 4** — `get_response_style_modifiers()` findes men injiceres ikke i
   visible-run-prompten.

## 🟠 Større, men afgrænset

8. **Generalized-learning capture-hooks** — 5 kilde-systemer publicerer ikke capture-events
   (deep_analyze_tool, reasoning_classify, agent_self_evaluation, counterfactual_self_simulation,
   learning_policy_engine) → læringen får intet input.

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
