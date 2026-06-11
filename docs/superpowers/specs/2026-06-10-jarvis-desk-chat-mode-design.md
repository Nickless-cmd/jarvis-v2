# jarvis-desk — Chat mode visual design

> ⚠ **Visuelt design er locked; FEATURE-PLACERING er superseded.** Det visuelle
> (palette, layout, bobler, composer, typografi) gælder uændret. MEN tabellen
> "Hvad der ER med" nedenfor placerer Channels/Mind/Dashboard i Cowork/Settings
> — det er **forældet**. Autoritativ feature-placering:
> `2026-06-11-jarvis-desk-feature-coverage.md` (Channels/Mind/Dashboard/Trading/
> Dispatches → Mission Control, ikke jarvis-desk). Brug coverage-kataloget for
> hvad der bygges; brug dette dokument for hvordan Chat ser ud.

**Status:** visuelt design approved (Bjørn 2026-06-10); feature-placering
superseded af 2026-06-11 coverage-katalog
**Mockup:** `2026-06-10-jarvis-desk-chat-mode-mockup-v3.html`
**Parent project:** ny app sideløbende med JarvisX, taler `/chat/stream/v2`

## Design-DNA

Codex' ro + Claude Desktop's mode-mønster + JarvisX' features (skjult/pakket).

## Locked decisions

### Layout
- **Sidebar 260px venstre** med (top→bund):
  1. App-navn: `● jarvis-desk` (lille grøn dot + bold)
  2. **Pill-segment slider**: `Chat | Cowork | Code` (Claude Desktop mønster, ovalt formet)
  3. `+ Ny samtale` knap
  4. Session-liste grupperet `i dag` / `i går` / `tidligere`
  5. Foot: bruger-avatar + navn + indstillinger-cog
- **Main: 40px head + flex transcript + composer + 26px statusbar**

### Chat
- **Asymmetrisk**: Bjørn højre (blå-grå boble, max 75%), Jarvis venstre (avatar + tekst, ingen boble, max 92%)
- **Avatar Jarvis**: 28px cirkel med tynd ring (neutral grå, ikke grøn)
- **Under HVER besked**: tid (`5 min siden`) + 3 ikon-actions
  - User: kopiér / rediger / send-igen
  - Jarvis: kopiér / læs op / send-igen
  - **Opacity 0 som default, fader ind ved hover** — roligt i hverdagen

### Composer (Codex-stil, ikke JarvisX-stil)
- En boks med rounded corners, fokus-state med subtle border-skift
- **Venstre**: én `+ Tilføj kontekst` knap (lucide plus i border-button)
  - Klik → menu med: vedhæft fil / skærmbillede / `@` fil-reference / URL
  - Valgte items dukker op som **chips OVER input-feltet** med ×-knap til at fjerne
- **Højre**:
  - Model-pill: `● deepseek-flash ▾` (grøn dot = active)
  - Thinking-pill: `think ▾`
  - **Cirkulær send-knap**: hvid baggrund, sort lucide `arrow-up`, 30px diameter
    - Hover: subtle lift + shadow

### Palette (locked)
```
--bg-0:   #0d1117   /* yderste */
--bg-1:   #131922   /* primær flade */
--bg-2:   #1a212d   /* card / composer */
--bg-3:   #232b39   /* hover / active item */
--bg-4:   #2c3543   /* active mode-segment */
--line:   #1f2733   /* næsten usynlige skel */
--fg-1:   #e8eaed   /* brødtekst */
--fg-2:   #a8b0bd   /* sekundær */
--fg-3:   #6b7480   /* tertiær / pladsholder */
--accent: #6ee7a8   /* KUN status-dots & app-name dot */
--user-bubble: #1f2837
--code-bg: #0a0e14
```

**Accent-regel:** den grønne `--accent` bruges KUN som små dots (app-name, model pill, statusbar). Aldrig som flade på knapper.

### Typografi
- **Brødtekst Jarvis**: 15.5px / 1.6 line-height
- **Bjørn boble**: 15px / 1.5
- **Sidebar items**: 13.5px / 1.35
- **Statusbar**: 11px monospace
- **Sidebar labels (i dag / i går)**: 11px uppercase, 0.06em letter-spacing
- **Mode-segments**: 12.5px medium weight

### Statusbar (bund)
- Venstre: `● primary · deepseek-v4-flash`  `cache 34.5%`  `$0.024`
- Højre: tid
- Monospace, fg-3 (dæmpet)

## Hvad der ER med (alle JarvisX' features bevaret):

| Feature | Hvor |
|---------|------|
| Sessions med søg | Sidebar |
| Vedhæft / screenshot / @ fil-ref | Composer `+ Tilføj kontekst` menu |
| Model-vælger | Composer højre pill |
| Thinking-mode | Composer højre pill |
| Trust-mode / approval-mode | Sidebar-foot ⚙ → settings |
| Tool calls inline | Klikbare cards i Jarvis' tekst |
| Approval-cards | Indlejret i Jarvis besked (samme stil som tool-block) |
| Cost meter | Statusbar |
| Cache hit % | Statusbar |
| Multi-user (Bjørn/Mikkel) | Sidebar-foot bruger-info |
| Discord / Voicemail / Channels | I egen mode (Cowork eller egen overflade) |
| StagedEdits / PinnedStrip | Cowork mode |
| Mind / Dashboard | Settings eller egen surface, ikke i Chat |
| Run overlay / Working steps | Inline i Jarvis besked (samme som tool-block) |

## Hvad er IKKE med (bevidst skjult fra Chat-mode):

- Hele JarvisX' top-bar-batteri af ikoner
- Dashboard, Claude Jobs, Mind, Channels som tabs
- Token-meter altid synligt
- Multi-line composer bar med 10 indstillinger samtidigt

## Next steps

1. **Cowork mode mockup** — verificér konsistens (samme slider, samme spacing, men anden indhold)
2. **Code mode mockup** — verificér konsistens
3. **Scaffold `apps/jarvis-desk/`** — Electron + Vite + React + TypeScript skelet
4. **Implementér Chat mode** mod `/chat/stream/v2` (allerede deployed)
5. **Iterér** — første hands-on test
