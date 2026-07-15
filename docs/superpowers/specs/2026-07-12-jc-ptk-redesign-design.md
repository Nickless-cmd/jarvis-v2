# jarvis-code — Claude Code-model redesign (prompt_toolkit) — Design

**Dato:** 2026-07-12
**Status:** IMPLEMENTERET (15. jul 2026) — repl_ptk.py canonical, render.py testet; tui.py/repl.py bevaret som --legacy/--simple. Godkendt design (Bjørn: "kør") → writing-plans → subagent-byg
**Mål:** Gør jarvis-code til den ægte Claude Code-oplevelse: simpelt, **native terminal**
(kopier/scroll/transparens/højreklik virker af sig selv), kraftfuldt, brugervenligt —
ved at skifte render-laget fra Textual (fuldskærm/alternate-buffer) til prompt_toolkit
(print-til-scrollback + live bund-region). AL logik genbruges; kun visningen skiftes.

---

## 1. Kerne-indsigt (hvorfor skiftet)

Textual kører **fuldskærm (alternate screen buffer)** → appen tager terminalen over →
kopier/scrollback/transparens/højreklik driller (kræver Shift-tricks, terminal-profil-
hacks). Claude Code (Ink) renderer til den **normale buffer**: færdige beskeder printes
til scrollback (bliver en del af terminalens historik → native kopier/scroll/transparens),
og kun input+footer er en live region nederst.

prompt_toolkit er Pythons Ink-ækvivalent. Verificeret (12. jul): non-fullscreen
`Application` bevarer scrollback ovenover; `Frame(TextArea)` giver kantet composer-boks;
to-kolonne-banner er triviel print. prompt_toolkit 3.0.52 installeret i `ai`-env.

## 2. Arkitektur

**Render-model:** prompt_toolkit `Application(full_screen=False)`:
- **Bund-region (live, styret af app'en):** composer-boks (Frame'd input) + footer-toolbar
  + en live status-linje under processing (liveness).
- **Ovenover (scrollback, native terminal):** færdige beskeder emittes via
  `run_in_terminal()`/print → ryger i terminalens historik. Native kopier/scroll/transparens.

**Filstruktur (client repo `/home/bs/jarvis-code`):**
- Genbruges UÆNDRET: `src/api.py`, `src/tools.py` (lokale tools + diff + undo), `src/session.py`,
  `src/config.py`, `src/flags.py`, `src/hooks.py`, `src/commands.py`, `src/models.py`.
- Ny: `src/repl_ptk.py` — prompt_toolkit-app'en (banner, composer, footer, render, loop-driver).
- Ny: `src/render.py` — rene render-funktioner (banner, tool-linje, diff, cost, message) der
  returnerer prompt_toolkit `FormattedText`/ANSI — testbare uden en kørende app.
- Bevares: `src/tui.py` (Textual) tilgængelig via `--legacy` indtil den nye er bevist.
- `src/main.py`: default = `repl_ptk`; `--legacy` = Textual; `--simple` = eksisterende linjær repl.

**Loop-genbrug:** client-owned loop-logikken (agent_step/agent_step_stream, 3-vejs-router,
diff/undo/cost/plan, katalog, full-context) flyttes fra `tui.py` til en render-agnostisk
driver (delt), så både ptk og legacy kalder samme logik. Render-kald bliver callbacks
(on_assistant_delta, on_tool_line, on_diff, on_cost, on_approval) som ptk-laget implementerer.

## 3. Komponent-designs

### 3.1 Banner (to-kolonne, kant-til-kant)
Printet én gang ved start (scrollback). Venstre = greeting+info, højre = kommandoer:
```
✦ jarvis-code v0.5.0                                    KOMMANDOER
Welcome back, Bjørn!                                    /help    /context   /plan
deepseek-v4-flash · full · $0.00 i dag                  /files   /undo      /native
~/jarvis-code                                           /loop    /mode      /quit
```
- Venstre-kolonne: logo-linje · welcome · model+lane+dagens-cost · cwd (~-forkortet).
- Højre-kolonne: kommando-liste (2-3 kolonner).
- Bredde-bevidst: smal terminal → condensed (én linje: `jarvis-code v0.5.0 · full · ~/jarvis-code`).

### 3.2 Composer (kantet boks nederst, kant-til-kant)
```
────────────────────────────────────────────────────────────────────
 ❯ skriv til Jarvis…
────────────────────────────────────────────────────────────────────
 ◉ ctx:full · 🔓 auto-edit · ◷ 2.1s · 5,100↑ 180↓ tok · $0.003        build v0.5.0
```
- `Frame`'d multiline `TextArea` (top+bund-linje hele bredden, ingen side-luft, tekstfelt imellem).
- Under boksen: footer-toolbar (én linje): context-indikator · permissions · liveness/cost
  (venstre) · build-version (højre). Disclaimer kan rulle i footer eller egen dæmpet linje.
- Enter sender · Shift+Enter ny linje · multiline understøttet.

### 3.3 Beskeder (scrollback, kompakt — Claude Code-stil)
- **Bruger:** `❯ <tekst>` (dæmpet prefix).
- **Assistent:** streames token-for-token til scrollback; markdown-let (fed/kode/lister) ved slut.
- **Thinking:** rolig `· tænker …` live-linje under processing (ikke rå reasoning-tokens).
- **Tool-call = ÉN metadata-linje:** `[edit_file: src/parser.py] +32/-0` / `[bash: pytest] exit 0`.
- **Diff:** inline `+`/`-` linjer (grøn/rød), ingen `---/+++/@@`-headers, ingen border.
- **Tool-output:** dæmpet, indrykket, klippet (12 linjer × 160 bredde), ingen border.
- **Cost pr. tur:** flettet i footer-liveness (◷ tid · in↑/out↓ tok · $) — ikke separat linje.

### 3.4 Liveness (live status under processing)
Live-linje i bund-regionen mens en tur kører: braille-spinner · tid · ~tokens · (cost når kendt).
Idle: dæmpet ur-ikon + sidste-tur-tal. Opdateres via prompt_toolkit-invalidate/refresh-timer.

### 3.5 Approval (inline, ikke modal)
Når et lokalt skrivende/farligt tool kræver godkendelse: en inline-linje i bund-regionen
`⚙ Godkend edit_file: src/foo.py?  ❯ Ja  Nej   (↑↓ · Enter · y/n)`. Worker-tråden venter på
valget (event). Ingen fuldskærms-modal.

### 3.6 Fil-tree / filer
`/files` (eller Tab) → en let fil-picker: prompt_toolkit `completer`/`fuzzy` over projekt-filer,
eller en simpel scrollende liste + preview. Valgt sti indsættes i composeren. (Lettere end
Textual-modalen; native.)

## 4. Feature-paritet (alt fra Textual skal med)
- [x] Tiered context: none · identity · **full** (full-context client loop, server-memory + lokal exec)
- [x] Mode PERSISTERES (config-merge) → overlever `--continue`
- [x] Kurateret katalog + `runtime_`-præfiks (bash=lokal, runtime_bash=container) + load_more
- [x] Companions (memory/mood) + forwarded exec + HARD brain-gate (server)
- [x] Diff-visning · Undo (Ctrl+Z) · Cost-transparens · Auto-test · Plan-mode (/plan)
- [x] Stop-stream (Ctrl+C) · afslut (Ctrl+Q//quit)
- [x] Connection-indikator (● online · Nms) — i banner eller footer højre
- [x] Slash-kommandoer (/help /context /plan /native /loop /mode /files /undo /session /version …)
- [x] Native kopier/scroll/transparens/højreklik (gratis via scrollback-modellen)

## 5. Non-goals
- Ingen ændring af server/runtime (agent-step, catalog, execute er allerede på plads).
- Ingen fjernelse af Textual endnu (bevares som `--legacy` indtil ptk er bevist i drift).
- Ingen ny dep udover prompt_toolkit (allerede installeret).

## 6. Test-tilgang
- `src/render.py` rene funktioner → unit-testes (banner to-kolonne, tool-linje-format,
  diff-farvning, cost-formatering) uden en kørende app.
- Loop-driver testes med mocks (som de eksisterende router/loop-tests).
- Visuel verifikation: kør på Bjørns skærm + screenshot (native buffer → rigtig terminal).
- Legacy Textual-suite (185 tests) skal fortsat være grøn (uændret logik-lag).

## 7. Åbne detaljer (afklares i plan/byg)
- Præcis prompt_toolkit-mekanik for "print-over-live-region" under streaming
  (`run_in_terminal` vs `patch_stdout` vs app-styret output-buffer) — vælges tidligt i byg.
- Om liveness-refresh bruger en app-timer (invalidate) eller en baggrundstråd.
- Banner condensed-tærskel (kolonne-bredde).
