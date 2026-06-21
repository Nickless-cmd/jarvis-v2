# Spec: Unified Gate Architecture (GateKernel + 7 cluster-gates)

**Status:** Design · **Dato:** 2026-06-21 · **Forfatter:** Claude (på Bjørns observation)
**Grundlag:** `docs/notes/2026-06-21-gate-audit.md` (26 ægte gates → 7 clusters, verificeret komplet)

## 1. Mål

Erstat ~26 spredte beslutnings-gates (4 lag, hver sin fil/logging/event/timeout) med
**7 cluster-gates + 1 GateKernel**. Ikke for at fjerne sikkerhed — men fordi
ustabiliteten kommer fra gatenes *interaktioner*, ikke fra deres antal. Vi skærer
fejlfladen fra ~26² interaktioner til 7 isolerede gates bag én kerne.

**Tre gevinster:** (1) isoleret fejlhåndtering → én gate kan ikke hænge/cascade hele
runnet; (2) ét struktureret event pr. tur → fejl bliver SYNLIGE i stedet for tavse;
(3) konsolideret logik → færre dubletter der er uenige.

## 2. GateKernel (den centrale brik — bygges FØRST)

Én orchestrator alle gates registrerer sig hos.

```
register(name, phase, fn, *, timeout_ms, flag_key)
```

- **Faser:** `pre_llm` · `pre_tool` · `post_output` · `async` (background, aldrig i hot-path).
- **Isoleret eksekvering:** hver gate køres med eget timeout + try/except. Timeout/exception
  → `Verdict(decision=SKIP, reason="gate-error/timeout")` — fail-open, ALDRIG cascade.
- **Verdict-model:**
  ```
  Verdict(gate, decision: GREEN|YELLOW|RED|SKIP, reason: str,
          evidence: dict|None, latency_ms: int, action: "allow|strip|block|warn|none")
  ```
- **Præcedens:** RED i `pre_tool` (AuthGate) = hård blok. RED i `post_output` (TruthGate)
  = strip/flag teksten. YELLOW = advar+log. GREEN = videre. Eksplicit, ét sted.
- **Ét event pr. tur:** `gate.evaluated` med ALLE verdicts (gate, decision, reason, latency,
  flag-state). Mission Control + debug læser KUN dette ene event → central overvågning.
- **Inter-gate-kommunikation:** en gate læser en andens verdict via `kernel.verdict(name)`
  — ikke ad-hoc cross-imports.
- **Kill-switch pr. gate:** `flag_key` → tænd/sluk en hvilken som helst gate i runtime
  (debug "hvilken gate fejler?" = sluk én ad gangen).

## 3. De 7 cluster-gates (kontrakter)

| Gate | Fase | Checker | Absorberer | Verdict-effekt |
|---|---|---|---|---|
| **TruthGate** | post_output | Påstand uden tool-evidens → flag/strip ved EMIT (mekanisme-skift, ikke prompt-formaning) + kommunikations-sikkerhed | self_deception, fact_gate, apophenia, hallucination, diagnosis, verification, claim_scanner, communication_guard | strip/flag |
| **AuthGate** | pre_tool | Rolle/scope/override/sudo/identity/abuse/mutations-sikkerhed | tool_scoping, role-gate, tool_intent(+approval), sudo-verdicts, classify_command, veto, identity_guard, security_guard, abuse_monitor, read_before_write, memory_safeguard, delete/memory_write_policy, skill_gate | hård blok |
| **LoopGate** | per-runde | Skal loopet stoppe / tvinge tekst / lukkes | run_closure, tool-only-guard, capability-cap, good_enough, agentic_checkpoints, presentation-invariant | terminér/fortsæt |
| **CommitGate** | post_output/async | Holdt Jarvis sine beslutninger/løfter | decision_gate, decision_adherence, decision_review | warn/log |
| **PrivacyGate** | pre_data/pre_share | Cross-user privatliv + deling | cross_user_share_guard, share_guard_store | hård blok |
| **ReviewGate** | async (UDE af hot-path) | Selv-review — afbryder ALDRIG turen | self_review_unified + trackers, self_monitor, narrative | none (kun log) |
| **ProactivityGate** | pre_llm | Signal/støj + initiativ-tryk | signal_noise, pressure_threshold, proactive_question, r2_5_blocking | gate proaktivitet |

**Vigtigt mekanisme-skift (kun TruthGate):** de 8 anti-konfabulations-gates var
prompt-formaninger FØR svaret — og Jarvis konfabulerede alligevel. TruthGate skifter til
et **evidens-tjek EFTER**: en faktuel påstand der ikke kan pege på tool-evidens i runnet
flagges/strippes ved emit. Ét sted, output-tid, evidens-baseret. De øvrige 6 er ægte
logik-sammenlægninger (de virker, de er bare for mange).

## 4. Migrations-rækkefølge (bag flag, shadow-målt)

**Fase A — GateKernel + wrap eksisterende gates UÆNDRET.** Byg kernen, registrér de 26
gates som de er (samme logik), men nu kørt isoleret + observerbart. Dette ALENE dræber
cascade-fejlene (den faktiske ustabilitet) og giver den centrale debug-flade — UDEN at
ændre nogen gates adfærd. Højeste værdi, lavest risiko. Mål: nul tomme svar / hængte runs.

**Fase B — TruthGate (8→1, mekanisme-skift).** Shadow side-by-side: kør gammelt + nyt
parallelt, mål konfabulations-rate + stabilitet før flip.

**Fase C-G — én cluster ad gangen:** Loop → Proactivity → Commit → Review → Privacy.
**AuthGate sidst** (sikkerheds-kritisk — rør den når alt andet er stabilt).

## 5. Surface-sporet (UDSKUDT — efter gates lander)

~25 `build_*_surface` (signal- + affekt-surfaces) konsolideres til ét **AwarenessContext**-
lag med on/off pr. kategori. Separat spor — påbegyndes IKKE før gate-migrationen er landet
og stabil. Noteret her så det ikke glemmes.

## 6. Succes-kriterier

- Nul cascade-hængte runs (én gates fejl isoleres).
- Ét `gate.evaluated`-event pr. tur som eneste debug-kilde.
- Konfabulations-rate ↓ efter TruthGate-mekanisme-skift (shadow-målt).
- Prompt-cache-hit ↑ (færre dynamiske surfaces — surface-sporet).
- Hver gate kan tændes/slukkes individuelt i runtime.
