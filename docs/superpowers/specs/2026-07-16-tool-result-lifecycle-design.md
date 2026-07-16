# Tool-Result Lifecycle (visible-lane) — Design Spec

**Dato:** 2026-07-16
**Status:** Godkendt af Bjørn (design), afventer spec-review før plan
**Lane:** Kun visible (`/chat/stream/v2`). Agent-lane (`/v1/agent/step`) urørt.

---

## 1. Problem

Visible-samtaler måler median **187k input-tokens** (max 315k), hvoraf **68–83% er
tool-resultater**. Én prod-session: 1969 beskeder, 1770 tool-results = 191k tok, mens
selve samtale-teksten kun var 40k.

Rod-årsag (målt, ikke teoretiseret):

1. **Volumen, ikke størrelse.** Hvert tool-result er allerede lille (gns 432 tegn, max
   697) — `tool_result_history_max_chars=1500` fyrer aldrig. Problemet er de ~1770 styk.
2. **Ventilen er slået fra af det store vindue.** Baggrunds-compactoren hæver sin tærskel
   til `fraktion × model_context_window`. Med Jarvis' **1M-vindue** løftes 130k-tærsklen til
   **~700k** → compaction fyrer i praksis aldrig på visible → intet nulstiller vinduet →
   tool-results hober sig op.

Bjørns intention: micro-compaction **undervejs** i et run + **efter** run + **pruning** af
gammelt, "så han har hvad han skal bruge og er i gang med" — uden at dræbe cachen eller
skære i selve samtalen (1M-vinduet er til samtale-tekst, ikke tool-dumps).

## 2. Kerne-invariant (cache-garantien)

> Hver tier-grænse er et **persisteret integer message-id** der kun rykker i **diskrete
> batches med hysterese** — aldrig gen-beregnet pr. tur fra "sidste N". Mellem ryk renderes
> hver historisk besked **byte-identisk** → DeepSeek prefix-cachen holder. Hvert ryk = ét
> lokalt cache-reset, amortiseret.

Dette er den **eksakte modgift** til fejlen fra 2026-06-09 (fjernet 2026-06-30,
`transcript_sections.py:248-258`): dengang fik "seneste 20" tool-results expand=True/4000
tegn, ældre 1200. Et result der gled fra "seneste 20" → "ældre" (fordi samtalen voksede én
tur) gen-renderedes → samme historik-bytes ændrede sig hver tur → cache-prefixet brækkede
(~28% hit vs ~90% loft). **Recency-relativ rendering er forbudt.** Kun stabile,
persisterede id-ankre der rykker i spring.

Samme disciplin bruges allerede af `compact_marker` (rykker diskret, nulstiller vinduet én
gang). Vi genbruger mønstret.

## 3. Anker-fakta (verificeret i kode)

- `chat_messages` har et monotont integer-`id` (PK) — det `id > since_id` som
  growing-window'et (`chat_session_messages_since_last_compact`) allerede bruger. Stabilt
  anker.
- Der er **intet `run_id`** på beskeder. Et "run" udledes: spændet mellem to bruger-beskeder
  (alle assistant+tool-beskeder imellem). "Sidste N runs" = "siden N'te-sidste
  bruger-besked" → også et stabilt id.
- Tool-results ligger på disk som JSON (`tool_result_store.save_tool_result`), transcript'en
  bærer kun `[tool_result:<id>]`-reference. Stub-rendering = render mindre af den reference
  vi allerede har. Fuldt output altid rehydratbart via `read_tool_result`.

## 4. Tre tiers

| Tier | Betingelse | Rendering | Ændring vs i dag |
|------|-----------|-----------|------------------|
| **HOT** (fuld) | Nuværende turs tool-results | Fuldt output (followup-exchanges) | Uændret |
| **WARM** (summary) | `id ≥ cold_floor`, ikke nuværende tur | Fast summary-budget (dagens `expand=False`, cap 1500) | Uændret rendering |
| **COLD** (stub) | `id < cold_floor` | Én linje: `[tool_result:id — <tool>: ~N linjer, brug read_tool_result]` | **Ny** |

Token-gevinsten kommer fra COLD: ~15 tegn i stedet for ~430. Med 80% af 1770 results i cold
≈ ~150k tok sparet, uden permanent tab (fuldt på disk, rehydratbart).

## 5. `cold_floor`-pointeren (pruning)

- **Lagring:** persisteret pr. session. Genbrug markør-mekanikken — en let række (ny rolle
  `tool_cold_floor` i `chat_messages`, eller en kolonne på `chat_sessions`; besluttes i
  planen efter mindste-indgreb-princip). Værdien er et message-`id`.
- **Advance-trigger** (evalueres ved run-slut + defensivt ved prompt-build):
  Beregn warm-sættets omfang (alt med `id ≥` nuværende `cold_floor`, ekskl. nuværende tur):
  - `runs_i_warm` = antal bruger-besked-grænser i warm-sættet
  - `tokens_i_warm` = sum af warm tool-result-summary-tokens
  - Trigger hvis `runs_i_warm > N × (1+M)` **eller** `tokens_i_warm > T × (1+M)`
    (M = hysterese-margin, default 0.25 → thrasher ikke).
- **Advance-handling:** sæt `cold_floor` frem til det id der efterlader **præcis** sidste N
  runs OG under T tokens warm (den mest aggressive af de to grænser vinder). Rykker kun
  fremad, aldrig tilbage. Log linje: `[tool-lifecycle] cold_floor {gammel}→{ny}, warm: {runs}
  runs / {tok} tok`.
- **Defaults (tunbare):** `tool_warm_run_window=8`, `tool_warm_token_ceiling=40000`,
  hysterese `tool_warm_hysteresis=0.25`.

## 6. "Undervejs" — within-run micro-compaction

- I ét langt run akkumulerer nuværende tur mange fulde HOT-results. Cap dem med et
  **run-lokalt token-budget** (`tool_run_hot_budget`, default 30000).
- Overskrides budgettet → ældste-i-runnet batch-demoteres HOT→WARM (summary) ved **trin**,
  ankret på **tool-call-index inden for runnet** (fx demotér i blokke à 10), ikke pr. kald og
  ikke tidsbaseret. Så cut-off'en inde i det ekspanderende run rykker i spring → prefixet er
  stabilt mellem spring.
- Rationale: et 200-kalds-run skal ikke selv blive 300k, men "undervejs"-skrump må ikke
  glide hvert kald (samme cache-fælde i det små).

## 7. "Efter" — post-run

- Ved run-slut forlader runnets results "nuværende tur" → bliver WARM automatisk (eksisterende
  adfærd).
- Run-slut er det naturlige diskrete epoke-event: evaluér `cold_floor`-advance **én gang**
  her (sektion 5). Prompt-build-evalueringen er kun et defensivt sikkerhedsnet.

## 8. Moduler / hvor koden bor

| Fil | Ændring |
|-----|---------|
| `core/context/tool_result_lifecycle.py` (**ny**) | Pointer-lagring, advance-beregning (hybrid+hysterese), run-grænse-udledning, within-run-budget-logik. Holder transcript-filen lean. |
| `core/services/tool_result_store.py` | `render_tool_result_for_prompt(..., stub=False)` — ny stub-gren (én linje m. tool-navn + linje-estimat + reference). |
| `core/services/prompt_sections/transcript_sections.py` | I den eksisterende render-løkke (~L259-279): 3. gren — hvis `id < cold_floor` og flag on → stub-render. Ellers uændret warm. |
| `core/services/visible_runs.py` | Ved run-slut: kald `tool_result_lifecycle.evaluate_and_advance(session_id)`. |
| Settings (`RuntimeSettings`) | Nye felter (sektion 9). |

## 9. Flag + settings + rollback

- `tool_result_lifecycle_enabled` — **default OFF**. Off → dagens opførsel eksakt (ingen
  stub-gren, ingen advance, ingen within-run-skrump).
- Rollback: flag OFF → advance stopper, alt renderes warm igen → ét cache-reset tilbage til
  fuld warm, derefter stabilt. `cold_floor`-værdien bevares (ikke slettet) så re-enable er
  billigt.
- Settings-felter: `tool_result_lifecycle_enabled` (bool), `tool_warm_run_window` (int, 8),
  `tool_warm_token_ceiling` (int, 40000), `tool_warm_hysteresis` (float, 0.25),
  `tool_run_hot_budget` (int, 30000).

## 10. Tests

1. **Byte-stabilitet (kritisk):** byg visible-prompt 2× hen over en simuleret ny tur med
   flag ON og `cold_floor` der IKKE rykker → assertér identiske historik-bytes. Dette er
   præcis regressionen fra juni.
2. **Advance:** warm-sæt over grænse → `cold_floor` springer frem → beskeder under floor
   render som stub, over floor som warm.
3. **Hysterese:** warm lige over N men under N×1.25 → ingen advance (ingen thrash).
4. **Rehydrering:** `read_tool_result` på et cold-id returnerer stadig fuldt output fra disk.
5. **Within-run:** N fulde results, run-hot-budget overskredet → ældste demoteres i batch,
   cut-off ankret på tool-index (trin), ikke pr-kald.
6. **Flag-off golden:** flag OFF → output byte-identisk med nuværende kode-sti.
7. **Run-count-udledning:** "sidste N runs" beregnet korrekt fra bruger-besked-grænser.

## 11. Hvad vi IKKE rører

- Fuld-historik-compaction (`compact_session_history`, `compact_marker`).
- 1M-samtale-vinduet / `context_compact_threshold_tokens`.
- Agent-lane.
- Selve samtale-teksten — kun tool-result-volumen styres.

## 12. Succeskriterier

- Visible tool-tunge sessioner: input-tokens falder markant (mål: warm tool-tokens ≤ ~T=40k
  uanset session-længde) uden at cache-hit% falder under ~90% loftet.
- `read_tool_result` rehydrerer ethvert cold-resultat.
- Flag OFF = bit-identisk med i dag (golden test grøn).
- Ingen recency-relativ rendering nogen steder (kode-review-gate).

## 13. Åbne tuning-knapper (Bjørn kalibrerer)

- `N=8` runs warm — hvor mange opgaver i fuld/summary-detalje.
- `T=40k` warm-tokens — token-loft på arbejds-sættet.
- (within-run 30k og hysterese 0.25 er mekanik-defaults, kan justeres efter observation.)

## Relateret memory

`project_tool_result_history_bloat`, `reference_visible_prompt_cache_buster_fixed`,
`project_cache_prefix_optimization`, `reference_model_context_windows`.
