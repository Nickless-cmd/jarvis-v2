# Kontekst-komprimering: én sti, med de garantier specen kræver

**Mål:** Én komprimator i repoet, uden løkker, med en opsummering der bygger
videre på den forrige, en ægte timeout, et maskinlæsbart spor for hvilken vej
der blev taget, og tool-historik der bevarer sine fejl over en genindlæsning.

**Grundlag:** Bjørns spec 18/9-2026 + kortlægning efterprøvet mod koden og
CT105's database samme aften. Tallene nedenfor er målt, ikke antaget.

## Efterprøvet — hvad der faktisk står

| Påstand | Status | Belæg |
|---|---|---|
| `compaction_runtime.py` er død kode | **sand** | nul kaldere; capability_matrix:67 🔴 |
| Den er en komprimator der kan kobles ind | **falsk** | ren token-aritmetik: `summarize()` bruger aldrig `summary_text`, `prune_tool_results` ændrer kun et tal. Den har intet indhold at komprimere |
| Kaldet har en hård timeout på 45 s | **falsk** | `with ThreadPoolExecutor` → `shutdown(wait=True)` ved exit. Isoleret forsøg: timeout 1 s, blokeret 4,0 s |
| Fallback'en kan aldrig give en tom markør | **sand for den kørende sti**, **falsk for de fire andre kaldere** | de gemmer `[Kontekst komprimeret — detaljer ikke tilgængelige]` |
| Vejen er maskinlæsbar | **falsk** | kun en log-warning og tekst i markøren |
| Token-tælleren læser `input_tokens` fra seneste assistant-besked | **falsk** | den er et estimat over det RENDEREDE transcript (`estimate_messages_tokens`). En snip ses derfor automatisk — problemet specen beskriver findes ikke her |
| `cache_deleted_input_tokens` | **findes ikke** | det er Anthropics API-felt. DeepSeek rapporterer `prompt_cache_hit/miss_tokens`, som ligger i `costs` |
| Overflow-retry kan løbe i ring | **der er ingen overflow-retry** | `HTTP_400_OVERFLOW` er ikke-retrybar (stream_failure_kind:62-67) |
| Et tool_result uden match droppes stille | **sand** | foldToolResults.ts:15 `continue` |
| Fejlede kald står alene | **sand live, FALSK efter genindlæsning** | se fejl B |

## To fejl specen ikke kender

**A. Hver komprimering glemmer alt før de seneste 500 rækker.**
`compact_session_history` læser `recent_chat_session_messages(limit=500)` uden
markører og giver ALDRIG den forrige markør med som input (ground truth er
git-fakta). Den nye markør erstatter den gamle. Sessioner på CT105: 8.344
rækker/29 markører, 3.848/18, 3.601/13. Ved hver komprimering forsvinder alt
ældre end ~500 rækker (mest tool-rækker) ud af hans kontekst. Femte udgave af
`limit`-vindue-fælden.

**B. Hver fejl gemmes som en succes.**
`visible_turn_accumulator.py:121-126` hardkoder `status: "done"`,
`is_error: False` for hvert resultat. Målt: 4.885 af 4.885 gemte resultater er
«done». Live får desk den rigtige status fra strømmen, så fejl står alene; efter
genindlæsning er de succeser og foldes ind i gruppen.

## Opgaver, i rækkefølge

1. **Tool-status er sand efter genindlæsning** (Krav 4, fejl B).
   `ToolResult.status`; `_to_followup_results` bærer runde-resultatets status;
   én delt regel `er_fejlstatus()` for strøm og akkumulator. Desk:
   uparret resultat vises som sin egen fejl-blok, et kald uden resultat vises
   ikke som lykkedes.
2. **Ægte timeout + maskinlæsbart spor + ingen indholdsløse markører** (Krav 3).
   `shutdown(wait=False)`. `CompactResult.path` ∈ {`llm`, `mekanisk`} gemt i en
   kolonne på markøren. Alle kaldere af `compact_session_history` går gennem den
   strukturerede summariser.
3. **Opsummeringen bygger videre på den forrige** (fejl A).
   Kun beskeder EFTER forrige markør læses; forrige markør gives med som
   «tidligere resumé».
4. **Én komprimator, med fremdrifts-værn** (Krav 1).
   Før/efter-tokens på hver komprimering. Uden fremdrift låses sessionen i det
   delte lager indtil der er kommet nye beskeder — ingen ny komprimering på samme
   overflade. `compaction_runtime.py` og den døde krop i `auto_compact.py`
   slettes; testene der pinner reglerne flyttes til den kørende sti.
   capability_matrix genereres.
5. **Cache-bevidst microcompact** (Krav 2) — afventer Bjørns valg, se nedenfor.

Krav 5 (signal i delt lager med TTL, markøren uden opdatering) er leveret i
`abb5790b6` og tjekkes kun af mod acceptkriterierne.

## Åbent: Krav 2

Specens snip-begrundelse (tælleren overser snip) gælder ikke her, og
`cache_deleted_input_tokens` findes ikke hos DeepSeek. Den ærlige ækvivalent:
microcompact udløses i dag af 60 minutters stilhed som gæt på «cachen er kold».
Den kan i stedet læse den MÅLTE cache-miss-andel fra `costs` for sessionens
seneste synlige kald. Snip som selvstændigt lag ville overlappe
`select_for_compaction`.
