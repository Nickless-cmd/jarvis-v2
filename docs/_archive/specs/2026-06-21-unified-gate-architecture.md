---
status: forældet
audited: 2026-07-08
ground_truth: GateKernel module exists (core/services/gate_kernel.py, commit 1af7df2b) with Verdict/Decision/GateClass classes and run_phase method, but grep -r "run_phase" shows zero usage in production code (only dead comment). Gates route through central().decide() instead (commits 72da5599
superseded_by: docs/specs/2026-07-02-intelligent-central-spec.md (actual routing via central().decide), docs/specs/2026-07-02-intelligent-central-meta-cognition.md (broader Central architecture)
---
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

## 6. Tests

| Komponent | Test-fil | Dækning |
|---|---|---|
| GateKernel registry/exec | `tests/test_gate_kernel.py` | register, kør i fase-rækkefølge, verdict-aggregering, præcedens (RED>YELLOW>GREEN>SKIP) |
| Kernel-isolation | `tests/test_gate_kernel_isolation.py` | gate der kaster → SKIP (ikke crash); gate der hænger → timeout→SKIP; én gates fejl påvirker ikke de andre |
| Kernel fail-open + bypass | `tests/test_gate_kernel_failopen.py` | kernel-exception → alle gates passerer (fail-open); bypass-flag → kernen springes helt over |
| Kill-switch pr. gate | `tests/test_gate_flags.py` | flag off → gaten kører ikke + markeres `disabled` i event |
| Verdict-event | `tests/test_gate_event.py` | præcis ÉT `gate.evaluated`-event pr. tur med alle verdicts + latency |
| TruthGate (egen sub-spec) | `tests/test_truth_gate.py` | claim m. evidens → GREEN; claim u. evidens → flag (IKKE strip i v1); samtale/ræsonnement → GREEN (ingen falsk-positiv); **aldrig tomt output** |
| AuthGate | `tests/test_auth_gate.py` | owner/override → allow; member operator → block; sudo-verdict; identity/abuse-eskalering (genbrug eksisterende cases) |
| LoopGate | `tests/test_loop_gate.py` | tool-only-grænse, capability-cap, run-closure — adfærd uændret vs nu |
| Per-cluster paritets-test | `tests/test_gate_parity_<cluster>.py` | **shadow:** nyt cluster-gate giver SAMME verdict som de gamle gates på et fixtursæt (før gammelt fjernes) |

## 7. Edge cases

| Edge case | Forventet håndtering |
|---|---|
| Kernen selv kaster/hænger | Kernel-niveau fail-open → alle gates GREEN; log `kernel_error`. Bypass-flag findes som nød-exit. |
| Gate-flag slås om MIDT i et run | Læses pr. tur (ikke pr. run) → næste tur respekterer; igangværende tur uændret. |
| To gates uenige (RED vs GREEN) | Eksplicit præcedens i kernen (pre_tool RED = hård blok vinder); aldrig "begge gælder". |
| async ReviewGate-resultat ankommer EFTER turen er slut | Skrives kun til log/store — påvirker ALDRIG en afsluttet tur (ude af hot-path per design). |
| TruthGate ville strippe HELE svaret (falsk-positiv) | v1 FLAGGER (tilføjer note), stripper ikke. Hård invariant: gaten må aldrig producere tomt synligt svar. |
| Gate-timeout midt i en tool-batch | Gaten → SKIP for den batch; tool-eksekvering fortsætter (fail-open) — IKKE hængt run (det var bug'en i dag). |
| Gate A læser Gate B's verdict, men B SKIP'ede | `kernel.verdict(B)` returnerer SKIP/None → A behandler manglende verdict som "ingen indvending". |
| Migration: gammel gate + nyt cluster-gate begge aktive | Shadow-fasen er **måle-kun** — nyt gate logger sit verdict men har INGEN effekt før paritet er bevist + flag flippet. Ingen dobbelt-effekt. |
| `gate.evaluated`-event-emission fejler | Best-effort; manglende event må aldrig spærre turen (observabilitet ≠ blokade). |
| Bruger har override aktivt + en RED fra AuthGate | Override-præcedens afklares eksplicit (override løfter handling, men IKKE privacy-RED fra PrivacyGate — §6.5 bevares). |

## 7b. Sikkerhed (KRITISK — rettet efter Bjørn fangede fail-open-hullet)

**Fail-mode er PR. GATE-KLASSE, ikke globalt:**

| Gate-klasse | Fail-mode ved gate-fejl/timeout/kernel-fejl | Begrundelse |
|---|---|---|
| Kognitive (Truth, Loop, Commit, Review, Proactivity) | **fail-OPEN** (SKIP → passér) | en bug i en konfab-/loop-tjek må aldrig hænge Jarvis |
| **Sikkerhed (AuthGate, PrivacyGate)** | **fail-CLOSED (DENY)** | hellere fejlagtigt blokere end fejlagtigt tillade owner-tools/sudo/andres data |

Konsekvens: hvis kernen selv kaster, fail-open'er den de kognitive gates MEN
fail-closer sikkerheds-gates (deny). "Kernel down" = sikrere, ikke usikrere.

**Bypass-flag (kernel-nødexit) gælder ALDRIG sikkerheds-gates.** AuthGate + PrivacyGate
kører ALTID — de kan ikke slås fra via kill-switch eller bypass. Kun en eksplicit,
TOTP-gated owner-handling kan justere dem (og PrivacyGate's data-scope er uforanderlig,
§6.5). Dvs. ingen flag/bug kan åbne en sikkerheds-bagdør.

**Owner override × AuthGate (eksplicit):**
- `effective_role()==owner` (native ELLER `!override`+TOTP) → AuthGate giver **handling**
  (sudo/operator/mutationer). Den per-tool-runde override-fornyelse vi byggede i dag
  bevares INDE i AuthGate (samme run-kontekst-touch).
- **PrivacyGate RED kan ALDRIG overstyres af override** — override løfter kontrol, ikke
  data-adgang (`privacy_scoped_user_id` → None under override). Privatliv er den ene
  RED der står uanset alt.
- `!unlock`/`!override`/`!revoke-override` kører FØR gate-kæden (recovery skal altid
  kunne nå igennem — owner må aldrig kunne låse sig selv ude).

**Migrations-sikkerhed:** AuthGate konsolideres SIDST. Under shadow beholder
sikkerheds-gates deres NUVÆRENDE adfærd 1:1 (ingen fail-mode-ændring) indtil paritet er
bevist på et eksplicit sikkerheds-fixturset (member-block, owner-allow, override, sudo,
privacy-deny). Sikkerhed ændrer adfærd kun efter grøn paritet, aldrig spekulativt.

## 7c. Failure-semantik (rettet — Bjørns spørgsmål)

**Ingen "tag over".** En fejlet gates ansvar overtages IKKE af en nabo — det ville
genindføre den redundans vi fjerner. Gates er isolerede; en fejl bliver SYNLIG i
`gate.evaluated` (SKIP/error) → fanges + fixes, ikke tavst dækket.

**Redundans flyttes til check-niveau INDE i en gate.** TruthGate kører N evidens-tjek
inline; fejler ét, kører de andre videre (graceful degradation pr. check, ikke pr. gate).

**Flere fejler samtidig — asymmetrisk:**
| Fejler | Reaktion |
|---|---|
| Kognitive (Truth/Loop/Commit/Review/Proactivity) | fallback (fail-open → fortsæt) |
| Sikkerhed (Auth/Privacy) | hård blok (fail-closed → deny) |
| Systemisk (>N gates fejler i et vindue) | high-alarm til Bjørn + **safe mode**: kun sikkerheds-gates kører, kognitive bypasses |

→ Tilgængelighed for tænkning, sikkerhed for sikkerhed. Systemisk svigt råber.

**Læring/udvikling — aldrig live self-mutation:**
- Runtime-gaten er DETERMINISTISK (forudsigelig/debugbar).
- Læring = **ude-af-hot-path forslags-loop:** observér udfald (`gate.evaluated` +
  ground-truth) → FORESLÅ tærskel/mønster-opdatering → menneske/review godkender →
  flag-flip. Aldrig live tilpasning i hot-path.
- **Sikkerheds-gates lærer ALDRIG** — kun deterministisk (AuthGate må ikke "lære" at
  tillade noget).

## 8. Succes-kriterier

- Nul cascade-hængte runs (én gates fejl isoleres).
- Ét `gate.evaluated`-event pr. tur som eneste debug-kilde.
- Konfabulations-rate ↓ efter TruthGate-mekanisme-skift (shadow-målt).
- Prompt-cache-hit ↑ (færre dynamiske surfaces — surface-sporet).
- Hver gate kan tændes/slukkes individuelt i runtime.

## 9. Self-review-fund (rev. 2 — efter Bjørn pressede)

1. **TruthGate's evidens-tjek er den svære del, ikke en sammenlægning** — kræver sin
   EGEN sub-spec (claim-detektion + evidens-mapping er præcis det de 8 gates fejlede).
   v1 FLAGGER, stripper ikke.
2. **Gate vs surface-linjen er udflydende** — flere "anti-konfab-gates" er reelt
   `build_*_surface` (injicerer, blokerer ikke) → de hører i surface-sporet (c), ikke
   som blokerende gates. TruthGate = "slet surfaces + tilføj 1 output-tjek".
3. **Fase A "wrap uændret" er IKKE lav-risiko** — det rører de ustabile hot-filer.
   Justeret: Fase A = tynd **observabilitets-shim** (gates kører hvor de er, rapporterer
   gennem kernen), ikke fuldt re-route.
4. **Fase A reducerer ikke dele** — den tilføjer kernen; forenklingen kommer Fase B+.
   Gevinsten ved A er isolation + observabilitet, ikke færre dele.
5. **GateKernel = SPOF** → kernel-niveau fail-open + bypass-flag (§7).
6. **Konfabulations-rate er umåleligt** uden labeler → byg eval-sæt før vi påstår ↓.

**Konsekvens for rækkefølgen:** (0) eval-sæt + måling, (A) observabilitets-shim,
(B-G) cluster-konsolidering med paritets-test, TruthGet får egen sub-spec før den røres,
AuthGate sidst. Surfaces er separat spor efter gates.
