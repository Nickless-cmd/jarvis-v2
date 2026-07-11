# Central Cockpit Redesign — Fase 1: Motoren & Rammen

**Status:** Design godkendt (Bjørn, 2026-07-11). Fase 1 af 4.

**Mål (Fase 1):** Byg en async, aldrig-frysende, markør-stabil, fokus-drevet ramme
for Central-CLI'en (Bjørns operator-HUD/failsafe), bevist på tre kerne-views
(Overview, Incidents, Nerves) med ægte fuld-skærms drill-down.

**Ikke-mål (Fase 1):** De øvrige 11 faner, live SSE-feed, og de fulde failsafe-actions
(kun resolve-hook stubbes) — de kommer i Fase 2–4.

---

## Baggrund: hvorfor (audit-grundet)

Central-CLI'en (`apps/central_cli/central_cli/`) er i dag et **synkront polling-dashboard**.
En 3-agents-audit (2026-07-11) fastslog fire rod-problemer:

1. **Alt er synkront på UI-tråden.** `client.py` bruger en blokerende `httpx.Client`;
   `hud.py:refresh_data()` (3 s interval) og `hud_populate.py` laver alle fetches i
   tegne-løkken. Mind-fanen: 6 sekventielle kald hvert 3. s (`hud_populate.py:941,
   1023, 1056, 1080, 1103, 1119`). Clusters: `/central/realtime` 3× pr. refresh
   (`datasource.py:29, 113, 115, 167`). Incidents: 3 kald pr. markør-flyt
   (`datasource.py:346, 373, 408`). → UI fryser; faner føles "manglende"/"tunge".
2. **Refresh nulstiller tabellen.** `_reset_columns()` kører `table.clear(columns=True)`
   (`hud_populate.py:56-59`) uden at gemme/gendanne `cursor_row` → markøren hopper til
   top hvert 3. s.
3. **Taster er ikke wired.** `r` (resolve) og `t` (toggle) står i hjælpeteksten
   (`hud_populate.py:189`, `hud.py:483`) men er ikke i `BINDINGS`. Et altid-fokuseret
   kommando-input (`hud.py:291`) sluger enkelt-tastetryk.
4. **Trunkering + intet drill-down.** Faste kolonnebredder + `[:N]`-klip overalt; et
   48-tegns sidepanel (`hud.py:146`) er hårdt loft. Paneler er ikke scrollbare (Mind kan
   ikke køres ned). Backenden tilbyder 5–10× mere: fulde incident-beskeder (500+ tegn),
   root-cause-signaturer (300–500), per-nerve beslutnings-spor (`/central/nerve/{navn}`
   → 30 obs. med `decision`+`reason`+`payload`), per-proces timeseries — alt ubrugt.

Konklusion: fundamentet (backend-data, view-indhold) findes; **interaktions- og
data-kernen skal bygges forfra** som et instrument, ikke et dashboard.

## Roadmap (kontekst — hver fase = egen spec+plan)

| Fase | Indhold |
|------|---------|
| **1 (denne)** | Async data-motor + fokus-drevet ramme + drill-Screen-stak, bevist på Overview/Incidents/Nerves. |
| 2 | Fulde drill-down-detaljer (incident/nerve/anomali/run) + debug-spring (incident→nerve→run→fil:linje). |
| 3 | Failsafe-actions: resolve (enkelt/bulk), sikkerheds-kontakter (gates/nerver/kill), run/agent-kontrol, approvals, healers — governed + bekræftelse. |
| 4 | Port de øvrige 11 faner på rammen (u-trunkeret + drill) + live SSE-feed. |

## Byggestrategi: inkrementel på stedet (Approach A)

Ny motor/ramme bygges i `apps/central_cli/central_cli/` ved siden af de eksisterende
`hud*.py`. Et flag (`CENTRAL_COCKPIT_V2`, env eller `--v2`) vælger hvilken skal der
starter. De gamle filer forbliver kørbare under hele overgangen → Bjørn står aldrig uden
et vindue. Når Fase 4 er færdig, fjernes de gamle filer.

---

## Arkitektur — tre lag

```
 workers (async, baggrund) ──► HudState (last-good cache) ──► frame/views (tegner diff)
                                    ▲                                │
                                    └────────── actions (optimistisk + reconcile) ◄──┘
```

### Lag 1 — Data-motor (`engine/`)

**`engine/state.py` — `HudState`.** En enkelt in-memory cache. Pr. surface-navn
(fx `"realtime"`, `"nerves"`, `"nerve_detail:<navn>"`) holdes en `SurfaceEntry`:

```python
@dataclass
class SurfaceEntry:
    data: object | None = None      # sidste gode payload (None = aldrig hentet)
    fetched_at: float = 0.0         # monotonic timestamp
    error: str | None = None        # sidste fejl (None = ok)
    loading: bool = False           # en worker kører netop nu

class HudState:
    def get(self, surface: str) -> SurfaceEntry: ...
    def set_ok(self, surface: str, data: object) -> None: ...   # rydder error, sætter fetched_at
    def set_error(self, surface: str, error: str) -> None: ...  # BEVARER sidste gode data
    def is_stale(self, surface: str, max_age_s: float) -> bool: ...
```

Invariant: `set_error` **overskriver aldrig** `data` — UI viser altid sidste gode værdi
+ en diskret stale/fejl-markør. Ingen tom skærm ved backend-hikke.

**`engine/workers.py`.** Async fetch-funktioner (én pr. surface) + en kadence-tabel
`{surface: interval_s}`. Kørt via Textuals `@work(exclusive=True, group=surface)` så et
langsomt kald ikke stabler. Bruger den eksisterende `client.py`, men wrappet så kaldet
sker i en tråd (`asyncio.to_thread`) — httpx.Client forbliver synkron, men UI-tråden
blokeres aldrig. Hver worker: `state.set loading → fetch → set_ok/set_error`.

**`engine/client.py`.** Genbrug eksisterende httpx-klient uændret (remote-først + jc-token).

### Lag 2 — Rammen (`frame/`)

**`frame/app.py` — `CockpitApp(App)`.** Skallen: layout (header/tabs/body/footer),
tab-liste, global refresh-tick (`set_interval`) der **kun** kalder `view.rerender(state)`
(aldrig netværk), tast-dispatch, og styring af drill-Screen-stakken. Starter workers i
`on_mount` via `run_worker`.

**`frame/table_view.py` — `CursorStableTable`.** En `DataTable`-subklasse med
`update_rows(rows: list[Row], key_fn)` der **diff'er pr. row-key** i stedet for
`clear()`:
- byg `{key: RowData}` for nye rækker
- fjern rækker hvis key forsvandt (`remove_row`)
- opdatér ændrede celler (`update_cell`)
- tilføj nye keys (`add_row(..., key=key)`)
- bevar `cursor_coordinate` (clamp til nyt row-antal hvis nødvendigt)

Dette er den præcise fix for markør-hop. Enhedstestbar isoleret.

**`frame/detail_screen.py` — `DetailScreen(Screen)`.** Base for drill-down. Fuld bredde,
`VerticalScroll`-body, brødkrumme øverst (`Central ▸ Incidents ▸ INC-2761`), `escape`
popper. Subklasser (i views/) fylder body. Screen-stakken giver gratis scroll, egne
bindings og navigations-historik — fundament for debug-spring i Fase 2.

**`frame/palette.py` — kommando-palette.** `:` åbner en modal `Input`; genbruger den
eksisterende `commands.resolve_command`-dispatch. Erstatter den altid-fokuserede
input-boks, så enkelt-taster er frie til actions.

**Tast-model.** `BINDINGS` på App: piletaster → fokuseret tabel (native); `tab`/`shift+tab`
skifter fane; `enter` → `action_drill()` (push detalje-Screen for valgt række); `escape`
→ pop; `:` → palette; `f1..f9` → direkte fane. Enkelt-tast-actions (`r`, `t`, `x`)
registreres men no-op'er i Fase 1 (fuldt wired i Fase 3). Ingen skjult fokus-tyveri.

**Actions (mønster, stubbed i Fase 1).** `action_*` → optimistisk mutation i `HudState`
→ `run_worker` der kalder backend → reconcilér (eller rul tilbage + vis fejl i footer).

### Lag 3 — View-adaptere (`views/`)

Hver fane = en lille modul: en `build_rows(entry) -> list[Row]` (for tabeller) eller
`render(entry) -> Renderable` (for paneler), plus evt. en `DetailScreen`-subklasse.
Ingen fetch-logik i views — de læser kun `HudState`.

- **`views/overview.py`** — paneler fra `realtime`+`costs_daily`+`affect`+`tone`; scrollbar.
- **`views/incidents.py`** — `CursorStableTable` (key = incident-id) + `IncidentDetailScreen`
  (fuld besked, root-cause, korrelation, relaterede, healer-status; kilde `/central/diagnostics`
  + `/central/realtime`). `r` reserveret til resolve (Fase 3).
- **`views/nerves.py`** — `CursorStableTable` (key = nerve-navn) + `NerveDetailScreen`
  (30 obs. med decision+reason+payload; kilde `/central/nerve/{navn}`).

---

## Data-flow

1. `on_mount` → workers starter; hver skriver sin surface til `HudState` på sin kadence.
2. Refresh-tick (fx 1 s) → aktiv view'ets `rerender(state)` → `CursorStableTable.update_rows`
   diff'er → markør/scroll bevaret. Stale/fejl vises som markør, ikke tom skærm.
3. Enter → `action_drill()` → view'ets `DetailScreen` pushes; dens data er en egen surface
   (`nerve_detail:<navn>`) hentet af en on-demand worker; Esc popper.
4. (Fase 3) Action → optimistisk `HudState`-mutation → backend-worker → reconcile.

## Fejlhåndtering

- Worker-fejl → `state.set_error` (sidste gode data bevaret) → diskret markør i UI.
- Drill-Screen uden data endnu → "henter…" spinner, aldrig blokerende.
- Al render er defensiv: en enkelt views exception må aldrig vælte skallen (fanges i
  refresh-tick, logges til footer).

## Modul-opdeling (splitter god-filer)

Nuværende: `hud_populate.py` 1237 linjer (>1200 split-grænse), `datasource.py` 797,
`hud.py` 503, `hud_actions.py` 365. Ny struktur holder hver fil < ~300 linjer:

```
apps/central_cli/central_cli/
  engine/   state.py · workers.py · client.py(genbrug)
  frame/    app.py · table_view.py · detail_screen.py · palette.py
  views/    overview.py · incidents.py · nerves.py
  theme.py (genbrug hud_theme)
```

De gamle `hud.py`/`hud_populate.py`/`hud_actions.py`/`datasource.py` bevares urørt bag
flaget indtil Fase 4.

## Test

**Unit:**
- `HudState`: `set_error` bevarer `data`; `is_stale`; loading-flag.
- `CursorStableTable.update_rows`: markør bevaret når rækker (a) opdateres, (b) én fjernes
  over markøren, (c) én tilføjes, (d) rækkefølge ændres. **Dette er kerne-regressionen.**
- workers: mocket client → `set_ok`/`set_error` korrekt.

**Visuelt/integration (headless, `app.run_test()` pilot):**
- Naviger `↓↓`, udløs et refresh-tick med ændret data, assert `cursor_coordinate` uændret.
- `enter` → assert `IncidentDetailScreen`/`NerveDetailScreen` på stakken; `escape` → assert
  popped.
- `save_screenshot()` SVG → `rsvg-convert` PNG → billedet læses og bekræftes at tegne
  (obligatorisk: ingen "virker"-påstand uden at have set det rendere — jf.
  feedback_verify_visual_before_done).

## Verifikation (accept)

- Fanen fryser aldrig under load (Mind-agtig 6-surface-belastning simuleret → UI responsivt).
- Markør + scroll står stille gennem ≥3 refresh-cyklusser mens data ændrer sig.
- Alle paneler kan scrolles til bunds.
- Enter åbner en fuld, scrollbar detalje-Screen med u-trunkeret indhold; Esc tilbage.
- Ingen fil > 300 linjer i den nye kode; ingen fetch i view-laget; ingen dobbelt-sandhed
  (views læser kun `HudState`).
