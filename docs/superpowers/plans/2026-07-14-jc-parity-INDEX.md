# jarvis-code fuld-paritet — plan-serie (master-index)

> **Spec:** [2026-07-14-jarvis-code-parity.md](../specs/2026-07-14-jarvis-code-parity.md) ·
> **Eksekvering:** superpowers:subagent-driven-development, én plan ad gangen.

**Mål:** jarvis-code → fuld Claude-Code-paritet (kapabilitet · interaktion · stabilitet) → delt
substrat for jarvis-desk code mode (prove-then-migrate).

**81 tasks over 8 planer.** Fase 0-1 i fuld micro-TDD (umiddelbart forestående); Fase 2-6 på
task-niveau (filer + tests-at-skrive + acceptance pr. task — detaljeret nok til at eksekvere uden
at gen-udlede). Hvert task tagget **[CLIENT jarvis-code]** (kan IKKE importere `core.*` → reimplementér
klient-side) eller **[SERVER jarvis-v2]** (risikable ændringer flag-gated, default OFF).

## Eksekverings-rækkefølge (afhængigheds-DAG)

```
Fase 0 [S] ──┐                (uafhængig — FØRST; fjerner blind lane + multi-bruger-blocker)
Fase 0.5 [C]─┴─→ Fase 1 [C] ─→ Fase 2 [C/S] ─→ Fase 4 [C/S] ─→ Fase 5 [C/S] ─→ Fase 6 [C/S]
                                    │              ↑
                              Fase 3 [C] ──────────┘   (skill-trigger; kun soft-afhængig af 0)
```
Fase 0 og 0.5 kan køre parallelt (0=server, 0.5=klient-refaktor). Fase 1 kræver begge. Fase 3 kan
slottes ind når som helst efter Fase 0.

## Planerne

| Fase | Titel | Tasks | Tag | Plan |
|---|---|---|---|---|
| **0** | Server Tier-0-lite: agent-lane observabilitet, user-scoping, multimodal-fundament | 8 | [S] | [fase0-server-lite](2026-07-14-jc-parity-fase0-server-lite.md) |
| **0.5** | jc_agent_loop tur-loop-ekstraktion (substrat-frø) | 4 | [C] | [fase0_5-module-extract](2026-07-14-jc-parity-fase0_5-module-extract.md) |
| **1** | Tier 0 stabilitetskontrakter (A1-A8) + klient-øjne | 11 | [C] | [fase1-tier0-eyes](2026-07-14-jc-parity-fase1-tier0-eyes.md) |
| **2** | Dispatch (aktivér) + baggrund + todos + memory + bash-sandbox-gulv | 8 | [C/S] | [fase2-dispatch-bg-mem-sandbox](2026-07-14-jc-parity-fase2-dispatch-bg-mem-sandbox.md) |
| **3** | Skill-system-trigger (reuse motor, klient auto-kald) | 7 | [C/S] | [fase3-skills](2026-07-14-jc-parity-fase3-skills.md) |
| **4** | Input/interaktion (thinking-replay, env, mid-run-styring, caching, budget, resume/fork, adfærdskontrakt) | 13 | [C/S] | [fase4-input-interaction](2026-07-14-jc-parity-fase4-input-interaction.md) |
| **5** | Governance/UX + hærdning | 22 | [C/S] | [fase5-governance-ux-hardening](2026-07-14-jc-parity-fase5-governance-ux-hardening.md) |
| **6** | Acceptance-harness + migrations-trigger | 8 | [C/S] | [fase6-acceptance](2026-07-14-jc-parity-fase6-acceptance.md) |

## Konsistens-noter (fra tvær-review)
- **Fase 0.5-overlap:** Fase 1's plan folder ekstraktionen ind i sin Task 1 som selvstændigt fald-tilbage.
  **Kanonisk:** Fase 0.5-planen ER ekstraktionen; kør den FØRST, så adapterer Fase 1 Task 1 det eksisterende
  `jc_agent_loop`-skelet (Fase 1-agenten skrev selv dette fallback ind). Kør ikke begge ekstraktioner.
- **Fase 0 flag-gating:** al ny server-adfærd bag `jc_agent_observability` / `jc_agent_user_scoping` /
  `jc_agent_multimodal` (default OFF) → deploy er inert til flip. Sikkert på live.
- **Fase 1 tolererer u-deployet Fase 0:** klient-tasks passerer mod mock selv hvis finish_reason/image-blocks
  endnu ikke er live (degradér til None / server ignorerer blocks). Så Fase 1 kan bygges før Fase 0 flippes.
- **Reuse-lokalitet:** hver "reuse core.*" er markeret som klient-reimplementering vs server-kald (klienten kan ikke importere core).
- **Sikkerhedsgulv før autonomi:** Fase 2 lander bash-sandbox + guards-i-alle-modes + egress-gate FØR dispatch/full-auto aktiveres.

## Beslutninger baked-in (Bjørn 14. jul)
sandbox fail-OPEN v. mekanik-fejl · skill = klient auto-kald · multimodal NU (Fase 0 fundament + Fase 1 øjne) ·
multi-bruger-scoping NU (Fase 0) · server-lite flag-gated live.
