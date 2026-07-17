# Context / Compaction / Harness parity — research + design

**Formål:** forstå hvordan en velfungerende coding-agent-harness (Claude Code / Claude Agent
SDK) håndterer kontekst, compaction, trunkering og agentic-loop — så jarvis-code kan opnå
paritet og især fikse "Jarvis nulstiller og glemmer alt mellem compacts".

**Kilder:** (1) officielle docs (Claude Code + Agent SDK + Anthropic engineering) — agent-
research, afsnit indsættes. (2) mit første-hånds-syn (nedenfor, ADVARSEL: introspektion ≠
dokumenteret sandhed — verificér mod docs). (3) jarvis-code harness-audit — indsættes.

---

## DEL 2 — Første-hånds-syn (Claude Code, mig) — *verificér mod docs*

> Dette er hvordan jeg oplever at operere. Bjørns pointe er korrekt: mit indre syn er ikke
> altid den dokumenterede virkelighed. Behandl hvert TAL her som "sandsynligt, bekræft i DEL 1".

### A. Compaction — hvad der SKER, og hvorfor jeg IKKE glemmer alt

Det centrale princip, og præcis dér jarvis-code fejler: **et compact er en OPSUMMERING der
ERSTATTER den gamle del af samtalen med en tekst-summary — men jeg forbliver i SAMME session.**
Jeg får en sammenfatning af det tidligere forløb ind i konteksten og **fortsætter derfra**. Jeg
"vågner" ikke som en blank tavle; jeg får et resumé + de seneste beskeder og kører videre.

Konkret oplevet flow:
1. Konteksten fyldes op mod vinduets grænse.
2. Et compact udløses (automatisk nær fuldt vindue, eller manuelt via `/compact`).
3. Den TIDLIGE del af samtalen komprimeres til en **struktureret summary** (hvad blev lavet,
   beslutninger, filer rørt, åbne tråde, næste skridt).
4. Den summary + de **seneste** rå beskeder bevares; resten kasseres fra den aktive kontekst.
5. Jeg fortsætter — med summary'en som "hukommelse" af det tidligere.

**Hvad der bevares efter compact (min oplevelse):**
- En prosa-summary af det tidligere forløb (mål, beslutninger, hvad der er gjort/verificeret,
  åbne opgaver, "optional next step").
- De seneste beskeder rå (det umiddelbare arbejds-vindue).
- Nok task-state til at fortsætte uden at spørge "hvad lavede vi?".
Det er DERFOR samtalen fortsætter. Hvis jarvis-code i stedet **dropper historikken uden at
gen-injicere en summary**, forklarer det præcis "nulstiller totalt og glemmer alt".

### B. "microcompact" / delvis compaction (min fornemmelse — bekræft)
Ud over det store compact fornemmer jeg en lettere, løbende beskæring: **gamle værktøjs-
resultater** kan skrumpe/erstattes med korte stubs mens samtale-teksten bevares — så et enkelt
kæmpe fil-dump ikke æder hele vinduet resten af sessionen. (Dette matcher det vi netop byggede
i desk: tool-result-lifecycle + within-run aging. Verificér om CC har et separat "microcompact".)

### C. Kontekst-% (`ctx`)
Min forståelse: **tokens brugt ÷ modellens kontekst-vindue**, vist som en procent, med et
reserveret **headroom/buffer** så auto-compact kan nå at fyre FØR reelt overløb (man compacter
ved fx ~"nær fuldt", ikke ved 100%). Den vigtige nuance for jarvis-code: procenten skal regnes
mod det FAKTISKE vindue for den aktuelle model, og der skal være en buffer, ellers rammer man
hård overflow-fejl i stedet for et blødt compact.

### D. Fil-læsning / trunkering
- Jeg læser en fil i **stykker**, ikke nødvendigvis hele filen på én gang — der er en default-
  grænse (jeg oplever noget i retning af ~et par tusinde linjer pr. læsning), og for store
  filer læser jeg et vindue (offset+limit) ad gangen.
- **Værktøjs-output trunkeres**: meget lange kommando-/tool-outputs afkortes med en grænse, og
  jeg kan hente mere målrettet hvis nødvendigt. Pointen Bjørn ramte: **jeg klarer mig fint med
  trunkerede svar** — jeg behøver ikke hele filen i hovedet; jeg henter det relevante vindue.
  Det bør jarvis-code også: send ikke fulde fil-dumps ubetinget ind i konteksten.

### E. Agentic loop — runder og kald
- Jeg kører **mange værktøjs-kald i træk** inden for én bruger-tur (en agentic loop), indtil
  opgaven er løst eller en grænse nås.
- **Parallelle kald i én runde:** uafhængige værktøjs-kald kan fyres i ÉN tur (batch), afhængige
  skal serialiseres. Det er en reel effektivitets-løftestang.
- Der er en øvre grænse på antal runder pr. tur (så en loop ikke kører uendeligt). Det præcise
  tal: bekræft i docs.

### F. Hvad jarvis-code sandsynligvis mangler (hypotese, audit bekræfter)
1. **Compaction der opsummerer + fortsætter** (ikke drop-alt) — den store bug.
2. **Tool-result-trunkering** på agent-lanen (vi har det på desk nu; agent-lanen skal spejle det).
3. **Præcis ctx%** mod faktisk vindue + buffer der udløser blødt compact før overflow.
4. **Fil-læsning i vinduer** (offset/limit) frem for hele filer.
5. Fornuftige **loop-grænser** (runder/tur, kald/runde, parallelisme).

---

## DEL 1 — Officiel docs-research

### 1A. Agent SDK + Anthropic engineering (verificeret mod officielle docs)

**TRE forskellige compaction-mekanismer (må IKKE forveksles):**
| # | Mekanisme | Trigger (default) | Hvad den gør |
|---|---|---|---|
| a | **SDK client-side compaction** (Claude Code-stil) | "nær vindues-grænsen" (intet dokumenteret tal) | opsummerer ældre historik, beholder seneste + nøglebeslutninger, emitter `compact_boundary` |
| b | **Server-side compaction API** `compact_20260112` (header `compact-2026-01-12`) | `input_tokens` **150.000** (min **50.000**) | genererer `<summary>`-blok, dropper alt FØR blokken, fortsætter |
| c | **tool_runner `compaction_control`** | `context_token_threshold` **100.000** | injicerer summary-prompt som user-turn, rydder historik, fortsætter |

**KERNE-PRINCIP (præcis dét jarvis-code fejler) — verbatim fra Anthropic:**
> *"Compaction is … summarizing its contents, and reinitiating a new context window **with the summary**."*
> *"Compaction **replaces older messages with a summary**, so specific instructions from early in the conversation may not be preserved."*

Man BLIVER i sessionen — summary'en bærer **state, next steps, learnings** videre. Default
summary-prompt (server-side) siger eksplicit: *"provide continuity so you can continue to make
progress … Write down … the state, next steps, learnings … wrap … in `<summary></summary>`."*

**Hvad et compact BEVARER** (SDK CLAUDE.md-eksempel): nuværende opgave-mål + accept-kriterier ·
fil-stier læst/ændret · test-resultater + fejl · beslutninger + begrundelse. **Beholder / taber:**
beholder ID'er/status/outcome/mønstre; taber rå fil-tekst, fulde drafts, intermediate tool-results.

**Tool-results / TRUNKERING (de tal du ville have):**
- **Claude Code capper tool-svar til 25.000 tokens by default.** ← eksakt.
- **Context editing** (`clear_tool_uses_20250919`, header `context-management-2025-06-27`): trigger
  **100.000** input-tokens, **keep 3** seneste tool-use-par, rydder ældste først → placeholder.
  (= "microcompact af tool-results" — server-side, klienten beholder fuld historik.)
- **Memory `view`** trunkerer fil-visning >**16.000 tegn**; `view_range: [start, end]` (`-1`=til slut);
  fil >999.999 linjer = fejl. ← kanonisk "læs et vindue af filen"-mønster.
- Toolkit: *"pagination, range selection, filtering, and/or truncation med fornuftige defaults."*
  Styr agenten mod "mange små målrettede søgninger frem for én bred."

**Agentic loop:**
- `max_turns` = **ingen grænse** by default (tæller KUN tool-use-runder). Ramt → `error_max_turns`.
- `max_budget_usd` = ingen grænse (anbefalet default i prod). `tool_runner max_iterations` fx 10.
- **Parallelisme:** read-only tools (Read/Glob/Grep) kører SAMTIDIGT; state-ændrende (Edit/Write/
  Bash) serielt. En tur = ét round-trip; loop slutter når Claude svarer uden tool-kald.
- Effort-niveauer: low/medium/high/xhigh/max (per-tur reasoning-budget).

**Kontekst-budget:** kontekst nulstilles ALDRIG mellem turns — alt akkumulerer (system+tools+
historik+tool-in/out). Loft ~**200k**; compaction fyrer v. 150k, context-editing v. 100k → headroom
så der er plads at arbejde. **Prompt-cache:** stabilt prefix caches; rydning invaliderer cache fra
ryddepunktet (brug `clear_at_least` så invalideringen er umagen værd); behold thinking-blokke =
bevar cache. `count_tokens` med `context_management` viser før/efter så man kan budgettere.

**Design-stak (langlivede agenter):** *"compaction to manage conversation length, note-taking to
preserve critical state, and sub-agents to handle complex subtasks."* Sub-agenter: eget friskt
vindue, returnerer kun **1.000-2.000-token summary** til parent. **Memory-tool** (`memory_20250818`,
GA) = note-substratet; auto-instruktion: *"ASSUME INTERRUPTION: context window might be reset at
any moment, so you risk losing any progress not recorded in your memory directory."*

**Kilder:** code.claude.com/docs/en/agent-sdk/{overview,agent-loop,sessions} ·
platform.claude.com/docs/en/build-with-claude/{compaction,context-editing} ·
platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool ·
platform.claude.com/cookbook/tool-use-automatic-context-compaction ·
anthropic.com/engineering/{effective-context-engineering-for-ai-agents,writing-tools-for-agents,
building-effective-agents,effective-harnesses-for-long-running-agents}
*Uverificeret: %-besparelses-tal (29/39/84%) kom kun fra web-summary, ikke primær-kilde.*

### 1B. Claude Code officielle docs (code.claude.com) — eksakte tal

**Auto-compact ORDEN (den vigtigste paritets-detalje) — verbatim:**
> *"It **clears older tool outputs first, then summarizes the conversation if needed.** Your
> requests and key code snippets are preserved; detailed instructions from early in the
> conversation may be lost."*

To-trins: (1) ryd gamle tool-outputs, (2) opsummér samtalen. Præcis det lag-mønster vi bør bygge.

**Tærskler (env-vars, code.claude.com/docs/en/env-vars):**
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` = kapacitet i tokens brugt til auto-compact-beregning; default
  = modellens vindue (**200K standard / 1M extended**). Sonnet 5 har egen default.
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` = **procent (1-100) af vinduet hvor compact udløses**; lavere =
  tidligere. Kan KUN sænke tærsklen. (Default-%-værdien er IKKE publiceret = ægte gap.)
- Sonnet 5: auto-compacter v. ~**967K**. Opus 4.8 lokal session: ved modellens grænse (ikke
  proaktivt by default). Ingen enkelt "compact v. 92%"-konstant for alle modeller.

**`/context`-indikatoren:** live breakdown pr. kategori. Status-line `used_percentage` = **tokens ÷
modellens fulde vindue** (kan afkobles fra compact-tærsklen når AUTO_COMPACT_WINDOW er sat).

**Hvad der OVERLEVER et compact (autoritativ tabel):**
| Element | Efter compact |
|---|---|
| System-prompt / output-style | uændret (ikke del af historik) |
| Projekt-CLAUDE.md + MEMORY.md | **gen-injiceres fra disk** |
| Invokerede skill-bodies | gen-injiceres, cap **5.000 tok/skill, 25.000 total**, ældste droppes |
| `paths:`-scopede regler / nested CLAUDE.md | tabt indtil en matchende fil læses igen |

Summary'en beholder: **dine requests+intent, nøglekoncepter, filer+vigtige snippets, fejl+hvordan
de blev rettet, ventende opgaver, nuværende arbejde.** Rå tool-outputs + intermediate reasoning
er væk. I simulationen: komprimeret til **~12%** af pre-compact-størrelse. Samme session fortsætter.

**Tool-output TRUNKERING (eksakte tal, code.claude.com/docs/en/tools-reference + /mcp):**
- **Read:** token-baseret (IKKE fast 2000-linjer). Whole-file-read over grænsen → første "page" +
  `PARTIAL view`-notits med hvordan man læser mere via `offset`/`limit`. (Præcist token-tal ikke publ.)
- **Bash:** output **30.000 tegn default**; over → fuld output gemmes til fil + kort preview. Hæves
  via `BASH_MAX_OUTPUT_LENGTH` op til **hårdt loft 150.000 tegn**. Timeout 120s default.
- **MCP:** advarsel >**10.000 tokens** (fast), max **25.000 tokens** (`MAX_MCP_OUTPUT_TOKENS`).
- **Grep:** default `files_with_matches` (kun stier). **Glob:** cap **100 filer**.
- **Tool-svar generelt (fra writing-tools):** Claude Code capper tool-svar til **25.000 tokens**.

**Agentic-loop:** intet publiceret hårdt cap (turns/iterations/parallelle kald). Anti-loop-værn:
`"Autocompact is thrashing: the context refilled to the limit..."` → stopper efter "a few attempts"
(antal ikke publ.). Recovery: læs i mindre stykker / `/compact` fokuseret / subagent / `/clear`.

**Kontekst-vinduer + regnskab (platform.claude.com):** 1M for Opus 4.6-4.8/Sonnet 5/Fable 5/Sonnet
4.6 (1M = default, intet header); **200K alle andre**. ALT tæller (system+beskeder+tool-defs+
output+thinking). Context-awareness-budget injiceres på nyere modeller: `<budget>200000</budget>`
og efter hvert tool-kald `<system_warning>Token usage: 35000/200000; 165000 remaining</system_warning>`
— modellen kender sit eget headroom. **Overflow:** input over vinduet → 400 "prompt is too long";
på 4.5+ → `stop_reason: model_context_window_exceeded`. Auto-memory-load cap: **første 200 linjer
ELLER 25KB af MEMORY.md**.

**Adjacent:** `/clear` (frisk session) vs `/compact` (opsummér+fortsæt). `/rewind` = partiel
compaction fra/til et checkpoint. Sub-agent-isolation: eget friskt vindue, returnerer kun
**1.000-2.000-token summary** til parent (primær løftestang mod store fil-læsninger i hoved-vinduet).
API-primitiver et 3.-parts-harness kan kalde direkte: server-compaction (`compact_20260112`, 150K),
context-editing (`clear_tool_uses_20250919`, 100K/keep-3), memory-tool.

**GAPS (gæt ikke):** default auto-compact-%, eksakt Read-token-cap, thrashing-forsøgs-antal, loop-
grænser — alle udokumenterede.

## DEL 3 — jarvis-code harness-audit (file:line)

Live-klient = `repl_ptk.py` (client-owned loop; server `/v1/agent/step` er **stateless** — kun
per-step-eksekvering, ingen historik/compaction). Al samtale-hukommelse + compaction er **client-side**.

**ROD-ÅRSAG til "glemmer alt ved compact" — to sammenfaldende fejl:**
1. **`jc_memory.py:200`** — compaction'ens "summary" er en **mekanisk første-200-tegn-trunkering-join**,
   IKKE en rigtig summary. `content = str(m.get("content") or "")[:200]`. Ingen LLM-kald, ingen
   semantisk kondensering. Den gen-injicerer dog *en* streng + beholder sidste 10 beskeder (~5 turns),
   så det er ikke en bogstavelig nulstilling — men indholdet er ubrugeligt.
2. **`repl_ptk.py:1559-1560`** — cross-turn-historik (`self.messages`) holder **KUN final user-tekst +
   final assistant-tekst** (2 rækker/tur). **Tool_use/tool_result persisteres ALDRIG** mellem turns.
   Så selv FØR compaction har modellen ingen erindring om filer den læste/ændrede i tidligere turns.

→ Kombineret: efter compact ser modellen 200-tegns-stubs + sidste ~5 turns med **nul tool-arbejde-
kontekst** → opfører sig som om alt ældre er væk. **Præcis symptomet.** Bidragende: `fit_rounds_atomic`
(`jc_agent_loop.py:934-952,1135-1139`) hard-dropper ældste runder v. 600k wire-tegn **tavst**.

**Det der ALLEREDE er fint (rør ikke):**
| Element | jarvis-code | vs CC | Dom |
|---|---|---|---|
| Tool-result-cap | 24.000 tegn + spill-til-fil + redaction (`jc_tool_result.py:13`) | CC: 25k tokens | ✅ ~paritet |
| Max runder/tur | 60 (`jc_agent_loop.py:1084`) + forced synthesis v. udmattelse | CC: intet hårdt cap | ✅ fornuftig |
| Subagent-dispatch | max_rounds=8 (`jc_dispatch.py:74`) | CC: 1-2k-tok summary | ✅ ok |
| Compact-tærskel | 80% (`jc_memory.py:29`) | CC: %-af-vindue env-var | ✅ ok |

**Det der er I STYKKER:** (3) `_context_estimate` (`repl_ptk.py:528-553`) tæller kun `self.messages`
(ekskluderer in-turn tool-bytes der DOMINERER den reelle kontekst) → **under-rapporterer**; footer viser
en tier-**navn** ("full"/"identity"/"none"), IKKE en %. Den rigtige `pct` findes kun i den transiente
compact-besked. (4) tavst hard-drop uden summary/notits.

## DEL 4 — Paritets-design for jarvis-code (flag-gatet, TDD)

Prioriteret efter impact. Filer: primært `src/jc_memory.py`, `src/repl_ptk.py`, `src/session.py`,
`src/jc_agent_loop.py`, `src/config.py`.

**FIX 1 (bugen) — rigtig summariserende compaction, ikke 200-tegns-join.**
Erstat `jc_memory.build_session_summary` (`:168-210`) med et **LLM-kald** der producerer en løbende
summary i CC's ånd — bevar: *requests+intent, filer læst/ændret + vigtige snippets, beslutninger+
begrundelse, fejl+hvordan rettet, ventende opgaver, nuværende arbejde* (wrap i `<summary>`). Gen-injicér
+ fortsæt i samme session. Cheap-lane-model (ollama/gratis) til summariseringen — ikke betalt deepseek.

**FIX 2 — persistér det arbejdende transcript (tool-results), ikke kun final-tekster.**
Uden dette har FIX 1 intet ægte at summarisere. `session.py` har allerede `load_session_raw` (:81);
udvid `save_message`/`load_session` (:35,60) + `repl_ptk.py:1559-1560` til at bevare tool_use/tool_result-
beskeder cross-turn (med den eksisterende 24k-cap/stub så de ikke sprænger). To-trins som CC:
**(a) skrump gamle tool-results til stubs FØRST** (vi byggede præcis dette på desk: cold_floor/aging —
portér mønstret), **(b) LLM-summarisér samtalen hvis stadig over tærskel.**

**FIX 3 — præcis, synlig ctx%.**
Driv trigger + footer fra serverens reelle `prompt_tokens` (`jc_memory.context_pct` findes, :32-43;
`agent_step`-usage returnerer det) i stedet for char/3-heuristikken der ignorerer tool-bytes. Vis et
**tal** i footer (`_ctx_label`/`_footer_text`, :485-486/566-567), ikke tier-navn. Det er dét der gør at
`ctx:xx%` "faktisk virker".

**FIX 4 — intet tavst hard-drop.**
`fit_rounds_atomic`/`_fit` (`:934-952,1135-1139`) skal summarisere + notificere v. eviction, ikke kaste
`_dropped` væk lydløst.

**BEHOLD:** 60 runder, 24k tool-cap+spill, 80%-tærskel, subagent-isolation. **Tilføj til `config.py`
DEFAULTS** (:42): `compact_pct`, `max_tool_rounds`, `budget_chars` (i dag kun tunbare hvis håndtilføjet).

**Sekundære CC-idéer værd at overveje (fra DEL 1):** to-trins "clear tool-outputs først, så summarisér";
`CLAUDE.md`-agtig "compact instructions"-sektion der re-injiceres; anti-thrashing-værn (stop hvis
konteksten gen-fyldes flere gange i træk); memory-fil som "ASSUME INTERRUPTION"-substrat der overlever
compaction (Jarvis har allerede MEMORY.md — bind den til at gen-injiceres efter compact som CC gør).
