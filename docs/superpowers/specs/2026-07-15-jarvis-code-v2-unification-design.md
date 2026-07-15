# Én Jarvis overalt — jarvis-code ↔ v2 forening (design)

**Dato:** 2026-07-15
**Status:** Design godkendt af Bjørn ("ja vi prøver med den"), afventer eksekvering.
**Grundlag:** [v2-responsibility-surface-map.md](2026-07-15-v2-responsibility-surface-map.md) (6 kortlægninger af v2's ansvarsflade).

---

## 1. Mål (én sætning)

Samme Jarvis — samme hjerne, samme hukommelse, samme sessioner — overalt (desk chat+code, web, mobil,
jarvis-code), hvor den **eneste** forskel mellem overflader er *hvor hænderne (værktøjerne) kører*.

## 2. Kerne-arkitektur: delt session + server-hjerne + klient-hænder

Bjørns to pile:
- `desk ──sessioner──▶ jarvis-code` — jarvis-code arver v2's delte server-sessioner.
- `jarvis-code ──tool-boks──▶ desk` — desk arver jarvis-codes klient-side tool-eksekvering.

**Én driver:** v2-turn-loopet (`visible_runs._stream_visible_run`) er den eneste eksekutor. Det bygger
prompten, kører det agentiske loop, kører hukommelse/kognition/gates/cost — **intet af hjernen tabes.**
jarvis-codes gamle selv-byggede prompt (`agent_loop._full_context`) og klient-drevne loop **pensioneres.**

**Hænderne deler sig — ikke loopet.** Loopet er ÉN ubrudt kæde (Jarvis blander en lokal `bash` og en
`search_memory` i samme ræsonnement). Kun tool-EKSEKVERING ruter efter lokation:

```
   ÉN loop (v2 driver)
        ├─ execution:"client"  → den forbundne klients maskine (bash/read/write/edit)
        ├─ execution:"runtime" → Jarvis' container (runtime_bash, aliaset)
        └─ execution:"server"  → serveren/hjernen (search_memory, operator_, …)
```

**Endpoints:**
- `/chat/stream/v2` = DRIVEREN (uændret rolle, udvidet med klient-tool-delegering: emitterer `tool_use`
  for `execution:"client"`-tools og pauser til resultatet lander).
- **Hænder-kanalen** = et NYT run-scopet endpoint `POST /chat/runs/{run_id}/tool-result` (co-lokeret med
  det eksisterende `/chat/runs/{run_id}/steer`), hvor klienten poster resultatet af en delegeret tool.
  Dette er "hænder-rollen" agent-endpointet havde — nu flyttet til run-stien hvor loopet lever.
- `/v1/agent/step` (agent_step) = pensioneres som selvstændig loop-driver (Fase 4). Dets prompt-bygning
  (`_full_context`) og klient-drevne loop fjernes; jarvis-code bliver en ren v2-klient.
- `/v1/tools/execute` (findes) = beholdes for den omvendte retning (klient→server tool-forward), indtil
  den nye delegering gør den overflødig for driver-stien.

---

## 3. Tool-lokations-modellen (førsteklasses lag)

Fundamentet findes allerede i [jc_tool_catalog.py](../../../core/tools/jc_tool_catalog.py):
`COLLIDING_TOOLS = ("bash","read_file","write_file","edit_file")` er de fire der findes BÅDE klient-side
og på Jarvis' container; container-versionen aliaseres `runtime_`. Kollisionen ER pointen: `bash` = din
maskine, `runtime_bash` = hans.

**Ændring:** gør lokation EKSPLICIT i kataloget i stedet for implicit navne-medlemskab:

- Hvert tool får `execution: "client" | "runtime" | "server"`.
- `runtime_`-præfikset bliver *præsentations*-formen af `execution:"runtime"` (ikke sandheden selv).
- Serverens loop-router slår `execution` op og ruter `tool_use` til rette sted.
- Kataloget (`build_jc_catalog`) forbliver single source of truth og serveres til ALLE overflader.

**Governance uændret på serveren:** owner-gate på `load_more_tools`, den hårde brain-write-gate
(`check_brain_write_allowed`), og user/workspace-scopet eksekvering. En member på desk får aldrig
`runtime_bash`.

---

## 4. Turn-flow (Option 1, ende til ende)

1. Klient (jarvis-code/desk) POSTer bruger-tur til `/chat/stream/v2` med delt `session_id` + en
   **capability-deklaration**: "jeg kan eksekvere `execution:client`-tools på host X".
2. Serveren persisterer user-beskeden (uændret — kritisk for aktiv-chat-gaten + dedup), assemblerer den
   fulde prompt (den rigtige Jarvis), starter det agentiske loop.
3. Model beslutter et tool:
   - `execution:"server"`/`"runtime"` → serveren eksekverer selv (in-container / brain), som i dag.
   - `execution:"client"` → serveren emitterer `tool_use` over v2-SSE og **pauser loopet på det tool**.
4. Klienten eksekverer lokalt (bash/read/write/edit på sin host) og POSTer `tool_result` tilbage til
   hænder-kanalen for det `run_id`.
5. Serveren genoptager loopet med resultatet, kører gates/kognition/cost som normalt.
6. Ved tur-slut fyrer HELE side-effekt-regnskabet (cost, episodes, memory-postprocess, self-model,
   trackers, verdict-ledger) — fordi turen kørte gennem `visible_runs`. Intet tabt.

**Konsekvens:** `search_memory` virker igen (recall kører server-side i korrekt `user_context`);
delte sessioner er automatiske; klient-tool-hastigheden (ingen sandbox-round-trip på filer/bash) bevares.

---

## 5. Hårde constraints (fra kortlægningen) — og hvordan de håndteres

1. **Ét globalt aktiv-run-slot** (`visible_runs.active_run`, ikke per session): Klient-hænder ændrer
   IKKE dette — loopet kører stadig server-side som ét run. Single-flight/attach forbliver som i dag.
   (Modsat Option 2, hvor et klient-loop ville konkurrere om slottet — endnu en grund til Option 1.)
2. **Aktiv-chat-gate læser user-rækken:** klienten POSTer stadig user-turen til v2 (trin 1), så rækken
   skrives → heartbeat/inderliv undertrykkes korrekt. Ingen regression.
3. **compact_marker-kontrakt:** serveren ejer al session-læsning/skrivning (klienten driver ikke loopet)
   → markers, growing-window, tool-result-store håndteres server-side som i dag. Klienten rører dem aldrig.
4. **jarvisx todos/staged_edits/checkpoints:** fordi turen kører server-side, populeres disse af den
   normale sti → desk code mode ser jarvis-codes arbejde i samme session. (Klient-tool-resultater
   persisteres via serverens tool-result-persistering, trin 5.)
5. **Single-process (`--workers 1`):** uændret — al deling via DB + runtime_state + de eksisterende
   in-memory follow-buffere (`run_follow`, `run_event_log`). Klient-hænder tilføjer kun et
   tool_result-POST, ingen ny delt-tilstand.
6. **`current_user_id()`-kontekst:** serveren kører turen i korrekt user-kontekst → recall/workspace
   scoper rigtigt. Klienten sender sit user_id ved POST (som i dag via owner-JWT/bridge-uid).

---

## 6. Hvad ændres, pr. komponent

**Server (`visible_runs` / chat_stream_v2 / jc_tool_catalog / simple_tools):**
- Tilføj `execution`-felt til tool-kataloget; udled `runtime_`-alias fra det.
- Ny **klient-tool-delegering** i turn-loopet: når et `execution:"client"`-tool kaldes, emit `tool_use`,
  pause, afvent `tool_result` fra hænder-kanalen, genoptag. Genbrug approval/keepalive-maskineriet.
- Hænder-kanal-endpoint: `POST /chat/runs/{run_id}/tool-result` (klient→server, modsat af tool_use).
- Klient-capability-deklaration i request (hvilke `execution:client`-tools hosten kan køre).

**jarvis-code (klient):**
- Drop `agent_step`-loopet + `_full_context`-prompt-bygning. Bliv en v2-klient: POST til
  `/chat/stream/v2`, render v2-SSE (samme protokol som desk).
- Behold de 8 lokale tool-eksekutorer (`TOOL_EXECUTORS`: bash/read/write/edit/glob/grep/…) — kald dem nu
  som svar på server-emitteret `tool_use`, ikke i eget loop; POST resultat til hænder-kanalen.
- Behold delt session (server-ejet) — `/session`-kommandoer læser/attacher server-sessioner.

**desk (klient):**
- Code mode: begynd at eksekvere `execution:"client"`-tools på desks host (i dag server-side) → forening
  med jarvis-code. Kræver at Electron-siden kan køre lokale tools (den er en lokal app).
- Chat mode/web/mobil: ingen klient-host → kun `execution:"server"/"runtime"` tilgængelige (som i dag).

---

## 7. Faser (speed er en SEPARAT fase — forurener ikke foreningen)

- **Fase 0 — Tool-lokations-lag:** eksplicit `execution`-felt i kataloget + router-opslag. Ingen
  adfærdsændring endnu (server eksekverer stadig alt). Ren refaktor + tests.
- **Fase 1 — Klient-tool-delegering (server):** `tool_use`-emit + pause/resume + `tool-result`-endpoint.
  Bag flag. Testet med en syntetisk klient.
- **Fase 2 — jarvis-code bliver v2-klient:** drop eget loop/prompt; render v2-SSE; kør lokale tools på
  delegering. Delte sessioner virker. `/session`-attach.
- **Fase 3 — desk code mode klient-hænder:** desk eksekverer lokale tools på egen host via samme kanal.
- **Fase 4 — Pensionér agent_step som driver:** fjern `_full_context`-stien når jarvis-code er migreret.
- **Fase 5 (SEPARAT) — Speed:** angrib server-assembly-latency: udnyt den eksisterende sentinel-split
  (prewarm holder stabilt hoved varmt), async-cache de tunge futures, mål mod ~7-8s med hel Jarvis.

Hver fase er flag-gated, bagudkompatibel, og efterlader systemet kørende.

## 8. Test-strategi

- Tool-lokations-router: unit-tests pr. `execution`-klasse; alias round-trip (`bash`↔`runtime_bash`).
- Delegering: syntetisk klient der besvarer `tool_use` med `tool_result`; verificér loop-genoptag +
  at side-effekt-regnskabet (cost/memory/gates) fyrer uændret.
- Regression: aktiv-chat-gate (user-række skrevet), compact-kontrakt urørt, jarvisx-state populeret.
- E2e: jarvis-code kører en fler-tur code-opgave mod en delt session; verificér den er synlig+konsistent
  i desk, at `search_memory` virker, og at delte sessioner ikke bryder cachen.

## 9. Risici / åbne punkter

- **Latency-forventning:** Option 1 betaler server-assembly på model-kaldet indtil Fase 5. Bjørn accepterede
  ("hastighed slås vi med efter"). Skal kommunikeres tydeligt i UI (det er hel Jarvis, ikke den lette).
- **Desk-host tool-eksekvering:** Fase 3 kræver Electron-side lokal eksekvering — verificér sandkasse/
  sikkerhed matcher jarvis-codes OS-sandbox.
- **Klient-tool-timeout/afbrud:** hvad sker der hvis klienten dør midt i en delegeret tool? Genbrug
  approval-gatens timeout/auto-deny-mønster.
- **Capability-mismatch:** en klient der lover `execution:client` men ikke kan køre en specifik tool →
  fald tilbage til server-eksekvering eller fejl pænt.

## 10. Ikke i scope (YAGNI)

- Multi-worker skalering (systemet er `--workers 1`; deling via DB gælder hvis det ændres — ikke nu).
- Ny council/agent-arkitektur (separat spor).
- Speed-optimering ud over Fase 5's assembly-angreb.
