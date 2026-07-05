# Central HUD — 1:1 mockup-nedbrydning (element for element)

Kilde-sandhed: `docs/superpowers/mockups/central-hud-mockup.html`. Hvert element
herunder SKAL matches præcist i `apps/central_cli/central_cli/hud.py`. Ingen "næsten".

## Palet (mockup :root — brug præcist disse)
- bg #0a0e14 · panel #0d1420 · **line #16324a** (paneladskillere) · cyan #00d4ff
- amber #ffb000 · red #ff4a4a · green #00ff88 · blue #4488ff · dim #4a5568
- fg #c7d3e0 · **fgdim #7b8a9c** (sekundær tekst — VIGTIG, jeg brugte forkert dim før)

## Struktur (top→bund), fast ramme 1180×720, border 1px cyan + radius + glød
1. **head** (40px, border-bottom line)
2. **tabs** (32px, border-bottom line, bg #080c12)
3. **body** (flex): `main` (venstre, flex, border-right) + `side` (højre, 420px fast)
4. **cmd** (30px, border-top line, bg #080c12)

### 1. HEAD
- scan-sweep animation (cyan-gradient, 4s) — approximér m. subtil bevægelse
- `◈ CENTRAL` (cyan bold, letter-spacing 1) + `· J.A.R.V.I.S CLI v1.0` (fgdim)
- status: **pulserende** dot (amber) + `GUL` (amber bold)
- `nerver 122 · clusters 21 · incidents 12(rød) · breakers 0` (label fgdim, tal fg bold)
- spacer (skub resten højre)
- `cost i dag $0.13` (label fgdim, tal fg bold) ← DATA: /mc/costs
- grøn dot + `CONNECTED · 12ms` (latens)
- `14:32:05` (ur)

### 2. TABS
- hver: `[k]N` (dim, 11px) + label. Aktiv = cyan + **border-bottom 2px cyan**.
- Healing(6) + Governance(7) = **l2** (dæmpet #3a4658) — men stadig klikbare/virker.

### 3a. MAIN venstre (Nerves-view)
- **pane-h** (26px, cyan uppercase, letter-spacing, border-bottom, .glow=inset cyan):
  `NERVES — 122 i alt · filter: / · sortér: state`
- **tabel**: kolonner m. FASTE bredder:
  - cluster 150 (fgdim) · nerve 210 (fg) · state 120 · sidste 96 (fgdim) ·
    count 60 (fgdim, **højre**) · aktivitet flex (dim spark, letter-spacing -1)
  - header-row: fgdim, border-bottom, 11px
  - **valgt row**: cyan-tint bg + **inset 2px cyan venstre-kant** + selglow-puls
  - state: `● aktiv`(grøn) `○ idle`(dim) `◆ degraded`(amber) `✖ død · error`(rød)
- **feed** (148px, border-top, INDE i venstre kolonne under tabellen):
  - pane-h: `live feed — deduperet`
  - linje: farvet dot + `cluster/nerve`(farvet) + `· decision — reason` +
    badge `×30 · seneste 2m` (fgdim). Nyeste = fresh slide-in.

### 3b. SIDE højre (420px — Incident-detalje, FULD HØJDE)
- **pane-h**: `INCIDENT-DETALJE — network/health`
- **d-tag** bordered badge: `● ERROR · network` (rød kant+tekst, radius) ← severity+cluster
- **d-title**: kort titel (fg) ← afledt af nerve/besked
- besked (fgdim) ← incident.message
- **root cause** (d-k uppercase fgdim label) + værdi ← diagnostics.root_causes[match].signature
- **relaterede nerver** + chips (bordered, line-kant) ← samme-cluster andre aktive incidents
- **heal-status** (grøn) ← healer-ledger/AUTO-HEALED-markør i signature
- **correlation** (fgdim) ← `#{sig-hash} · {count} forekomster / {first..last}`
- knapper: `↵ fuld diagnostik` (cyan kant) + `r resolve` (amber kant)

### 4. CMD
- `central>` (cyan) + **blinkende caret** (cyan blok)
- højre keys (dim, 11px, tal/tast fgdim bold):
  `1-7 views · ↑↓ naviger · ↵ drill · / filter · : kommando · r resolve · ? hjælp`

## Datasource-interface (bygges FØR presentation)
```python
# incident (dict fra realtime) → beriget detalje, ALT fra ægte data:
def incident_detail(client, incident: dict) -> dict:
    # join realtime-incident ↔ diagnostics.root_causes (cluster,nerve) ↔ healers
    return {
      "severity","cluster","nerve","kind","message",       # fra incident
      "title": str,                                          # afledt kort titel
      "root_cause": str | None,                              # root_causes[match].signature
      "related": list[str],                                  # ["cluster/nerve",...] samme cluster, andre incidents
      "heal_status": str | None,                             # AUTO-HEALED-markør / ledger
      "correlation": {"sig": str,"count": int,"first": str,"last": str} | None,
    }

def cost_today(client) -> float | None:   # /mc/costs → dagens beløb (None hvis utilgængelig)
```

## Verifikation (obligatorisk, intet "færdig" uden)
Render HUD headless mod live-container → SVG → PNG → sammenlign element-for-element
mod mockup-PNG. Adversarisk agent-review pr. region (head/tabs/table/feed/detail/cmd)
→ gap-liste → luk → gentag til 0 gab.
