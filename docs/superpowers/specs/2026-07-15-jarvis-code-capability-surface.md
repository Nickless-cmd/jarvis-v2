# jarvis-code capability surface — parity-mål for desk code mode

**Dato:** 2026-07-15
**Formål:** Udtømmende inventar af ALT jarvis-code kan som klient, så desk code mode kan nå 1:1 —
**Jarvis må ikke kunne mærke forskel på desk code mode og jarvis-code** (Bjørns north star).
Bygget fra 6 read-only kortlægninger af `/home/bs/jarvis-code/src/`.

Klassifikation for foreningen: **(a)** rider server→klient-delegerings-skinnen · **(b)** klient-infrastruktur
desk SKAL replikere/dele · **(c)** server-side.

---

## 0. Den fundamentale opdagelse (rammer alt)

jarvis-code har **to lanes allerede**, og de er asymmetriske:
- **Klient-lane** (`/v1/agent/step`): klienten driver `jc_agent_loop`. **ALT det rige nedenfor lever her.**
- **Server-lane** (`/chat/stream/v2` — desk-lanen): tynd SSE-renderer, tools kører i containeren, `ctx="full"`,
  **intet af nedenstående kører.** Default er klient; persisteret `server` **tvinges ned til klient**.

`jc_agent_loop.py` er **bevidst UI-frit og forbudt at importere `core.*`** — dokumenteret som "det rene
substrat desk (code mode) og enhver anden klient kan konsumere direkte." **Det var designet som det delte loop.**

Det rejser kerne-arkitektur-valget (se §12): reimplementér hele substratet server-side (Option 1), eller lad
begge overflader **dele `jc_agent_loop`** (server = hjerne via endpoints). Beviset peger nu mod det sidste.

---

## 1. Agent-loop (jc_agent_loop.py) — det delte substrat
Robusthedskontrakt **A1–A7**: user-persist-først, terminal-klassifikation (tom = aldrig terminal, trunkeret =
aldrig terminal), degeneration-detektor (≥80× gentag, diversitet <0.18), empty-recovery (præcis 1 [RESEND] →
[SYNTHESIS]), [CONTINUE]-trunkering-akkumulering, kontekst-fit (round-atomisk eviction, 600k tegn), reasoning-
pairing-invariant (reasoning kun m. overlevende tool_result), force-synthesis. **max_rounds=60**. Self-correction
(3-strikes pr. objektiv). Rate-limit-halt (ingen blind retry). Stream→non-stream failover pr. step.
→ **(c) hvis server driver / delt substrat hvis klient driver.** Kernen i beslutningen.

## 2. Tools — klient-eksekveret (rider skinnen, (a))
bash, read_file, write_file, edit_file, multi_edit, glob, grep, web_fetch/scrape/search, bash_output,
kill_shell, todo_write, task, exit_plan_mode, operator_channel[_status]. Plus runtime_-aliaser (container),
forwarded companions/dispatch/council (server, (c)), MCP-tools ((a) når surfacet).

## 3. Tool-infrastruktur — klient-side ((b), desk skal replikere/dele)
- **Fuzzy multi-strategi-edit** (exact→whitespace→indent→difflib ≥0.85). Desk har nok kun exact = mærkbar forskel.
- **cap_and_spill + secret-redaktion** (24k-loft, spill til fil, sk-/gh_/AKIA-scrub).
- **Dry-run diff-preview** ved approval. **Kompakt farvet +N/−M-render** (Unicode `−` U+2212).
- **Multimodal** (billeder base64 + clipboard-paste). **Web-tools + FetchCache** (DuckDuckGo, 300s dedup).
- **Baggrunds-shells** (run_in_background, bash_output, kill_shell) + **delta-drevet re-invoke** (afslut ikke
  turen mens en shell producerer). Telemetri, undo-stack, auto-test.

## 4. Security-floor — klient-side ((b))
bwrap-sandbox (fail-open + `_sandbox_degraded`-markør), net-namespace-isolation (READ_ONLY/RESTRICTED = tom
net-ns), SSRF-guard (169.254.169.254 + RFC1918 + loopback, per-hop redirect-revalidering), egress-klassifikation,
dangerous-command + secret-path-guards (ALLE modes, også bypass), ANSI-sanitize, untrusted-fencing (invariant 15),
to-akse-permissions (SandboxProfile × approval-mode). Kan IKKE importere `core.*` → alt fra bunden.

## 5. Dispatch ((a)+(b))
Klient-lokal `task`-subagent: eget nested loop, egen besked-liste, **8 runder / 120k tokens / 180s wallclock**,
strictest-mode-arv, untrusted-fencing af resultat. Per-tur-loft **8 subagenter**. Forwarded spawn_agent_task +
convene_council (server, (c), men klienten renderer agent/council-entries). Ingen worktree-isolation (aspirationel).

## 6. Skills
Motor server-side (skill_engine.py). `skill_gate` = forwarded tool ((a)). Klient-glue ((b)): **first-turn
auto-kald (fire-once) + `[SKILL:]`-prepend + CC→Jarvis-tool-legend**. Det er glue'et der får skills til at *føles
proaktive* — uden det surfacer skills kun når modellen selv kalder.

## 7. Hooks — 100% klient-side ((b))
9 events (SessionStart/End, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact, SubagentStop,
Notification). Config `.jarvis-code/hooks.json` (repo→global). Matcher-grammatik (`*`, `A|B`, `Tool(glob)`,
`Tool(/regex/)`). command+http hooks, exit-2=block, stdout-JSON=inject, fail-open/closed. Nul server-backing.

## 8. MCP — klient-side ((b)) MEN halvt bygget
stdio+http JSON-RPC, trust (allowlist + TOFU-pin, fail-closed drift). **Kritisk: ikke wired ind i default-UI'et
(repl_ptk), tool-defs sendes ALDRIG til modellen** → reelt inert i dag. Mangler initialize-handshake, reconnect-
kald, OAuth, hot-reload, SSE-consume. **Desk skal bygge den TILSIGTEDE flow, ikke kopiere den brudte wiring.**

## 9. Session / hukommelse / compaction
Lokal JSONL (uuid, (c) → server-ejet). Project-memory-injektion (JARVIS/CLAUDE/AGENTS.md, nearest-wins, 4k,
secret-redakteret, (b)). **Compaction: udløses af besked-ANTAL (>50), IKKE den viste %; %'en er char/3-fake;
resumé er naiv 200-tegns-trunkering; INGEN pause/fortsæt-UX (lydløst synkront swap).** checkpoint/rollback
(git stash create, (b)). todos (TodoStore, (a)+(b)). plans (plan_store, (c)).
→ **Foreningen gør Bjørns "ægte %/pause/bevar/fortsæt" VIRKELIG** via v2's server-side ægte-token-compaction +
en SSE-lifecycle begge klienter renderer.

## 10. REPL / commands / render ((a) UX + (b) semantik)
**~25 slash-commands** (den FAKTISKE ptk-liste, IKKE de stale docs): /quit /exit /help /context /loop /mode /plan
/permissions /files /native /paste-image /undo /rollback /budget /clear /session /version /banner /cost /model
/compact /tools /mcp /hooks /quota. **Render-stil skal matche EKSAKT:** palet (hex), banner-boks, tool-hoved
`[chev label · summary · +A −D  status]`, braille-spinner `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`, glyffer `✓✗⧖⊘?⚠`, diff-farver
(grøn 8cff98 / rød ff7b7b / dim 2f6f4a), cost `${:.4f}` / tokens `Nk`, scrollback (user højre-mint / assistant
markdown), separator `─── ◦ ───`. Steering-kø (skriv midt-tur → leveres ved runde-boundary), Esc kooperativ steer,
Ctrl-C dobbelt-tap idle-exit, approval-kort, completions (slash + @-mentions), footer/HUD.
Notifikationer (bell/ntfy/desk-push; completion ≥30s, attention altid).

## 11. Config / permissions / models / flags / API ((b)+(c))
Config-præcedens (CLI→env→repo→global→default), auth (0600, repo-strip), **api_url-divergens at pinne**
(`api.srvlab.dk` vs `jarvis.srvlab.dk:8010`). To permissions-systemer (to-akse + ældre per-tool always/ask/never).
Klient-model-registry (bør catalog-drevet). ~20 flags (klient-hænder-flags SKAL matche: os_sandbox, ssrf_guard,
ansi_sanitize, untrusted_fencing, fuzzy_edit). Error-taxonomi + retry-backoff (5× 2/4/8/16/32s).
**API-kontrakt = kernen der ændres:** `/v1/agent/step` (klient-driver) vs `/chat/stream/v2` (server-driver/desk).

---

## 12. Kerne-beslutningen kortlægningen tvinger frem

**Option A — Server driver loopet (min oprindelige Option 1):** v2 reimplementerer HELE §1-substratet
(A1–A7, recovery, budget, self-correction, degeneration) + koordinerer al klient-infra (§3-8) cross-proces.
Stor port, høj divergens-risiko (desk føles anderledes på hver edge-case).

**Option B — Delt substrat (klient driver, server = hjerne via endpoints):** begge overflader kører SAMME
`jc_agent_loop` (allerede bygget til det). §3-8 lever klient-side og **deles som samme kode** (nul divergens).
Serveren leverer hjernen dér hvor loopet ALLEREDE kalder den: **hvert step er allerede et server-kald** → serveren
assemblerer fuld prompt + kører per-step-gates (TruthGate/claim_scanner/reasoning_interceptor) + returnerer;
ved tur-slut poster klienten turen → serveren fyrer de ~85 trackers/memory/cost. Sessioner server-ejet.

**Nøgle-indsigt:** "server ejer hjernen" kræver IKKE "server ejer loopet" — fordi model-kaldet allerede er et
server-round-trip. Så Option B giver HELE hjernen UDEN at flytte loopet, og desk = jarvis-code fordi de kører
samme substrat mod samme hjerne. Det er den reneste vej til "ingen forskel".

**Konsekvens:** Option B gør Fase 1's server→klient-delegering (byggede, branch, ikke merged) overflødig —
klienten eksekverer allerede tools lokalt. Fase 0 (tool-lokation) er nyttig i begge.

---

## Kilder
6 read-only kortlægninger (tools/sikkerhed, loop/dispatch, skills/hooks/MCP, session/memory/compaction,
REPL/commands, config/API), 2026-07-15. Fil:linje i agent-transkripterne.
