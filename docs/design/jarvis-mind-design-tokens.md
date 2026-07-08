---
status: færdig
audited: 2026-07-08
ground_truth: "Verified against live codebase:
1. Mockup file exists (docs/design/jarvis-mind-terminal-mockup.html, 9.0K, Jun 23 17:54)
2. All 15 color hex codes actively used in apps/jarvis-desk/src/styles/app.css (verified grep on: #0a0e16, #1ad9c4, #eaf6f4, #c7d4e0, #f5c451, #f5a14a, #3ee08a"
---
# Jarvis Mind — design-tokens (KANONISK REFERENCE)

Bjørn godkendte dette design 1:1 (2026-06-23): "stil og farver er meget bedre end det nuværende,
nemmere at læse og mere levende." Erstatter den nuværende flade ens-farvede MC hvor alt smelter
sammen. Mørk JARVIS/MCU-HUD med cyan-glød. **Dette er sandheden vi bygger Jarvis Mind imod.**
Live-mockup gemt i `jarvis-mind-terminal-mockup.html`.

## Farver (eksakte hex — mørkt tema, hardcoded scene, ikke theme-responsivt)

| Rolle | Hex |
|---|---|
| Skærm-baggrund | `#0a0e16` |
| Panel-baggrund (dybere) | `#0d1622` · `#13202b` |
| Panel-kant | `#163040` |
| **Accent (JARVIS-cyan)** | `#1ad9c4` |
| Lys tekst (overskrift) | `#eaf6f4` |
| Primær tekst | `#c7d4e0` · `#a9c6d4` |
| Dæmpet tekst | `#6b8295` · `#566b7d` · `#3a5160` |
| OK / grøn | `#3ee08a` (glød `#1ad9c455`) |
| Advarsel / gul | `#f5c451` |
| Tør / orange | `#f5a14a` |
| Sikkerhed / lilla 🔒 | `#b98ff0` |
| Fejl / rød | `#ff5d5d` |
| Knap-kant | `#1f3a4a` (hover `#1ad9c4`) |

**Cluster-node-fyld [bg, kant, tekst]:** grøn `[#0c2218,#1f5a3e,#4fe0a0]` · gul `[#241b08,#5a4416,#f5c451]`
· sikkerhed `[#1a0f24,#4a2d6b,#b98ff0]` · idle `[#10151c,#283645,#6b8295]`.
**Sind-celle aktiv:** `#125043` + `box-shadow 0 0 4px #1ad9c455`; inaktiv `#13202b`.

## Typografi
Monospace overalt (`var(--font-mono)`). Overskrifter med `letter-spacing: 2-3px`, små caps-labels
10px `letter-spacing 2px` dæmpet. Brødtekst 11-12px. Store tal 18-22px lys.

## Layout (top→bund)
1. **Header:** blinkende cyan-prik + `C E N T R A L` (spaced) + OWNER-badge · ur + "systemet lever".
2. **Reaktorkerne** (venstre, pulserende cyan-ring m. nerve-tal) + **metric-grid** 4×2 (clusters/processer/
   flag/sind-felter/providers/tørre-lanes/breakers/puls).
3. **Cluster-konstellation:** 20 noder i grid, farvet efter status, klikbar.
4. **To-kolonne:** levende nerve-feed (SSE, ruller) · providers + flag-panel.
5. **Betjenings-bar:** tænd/sluk nerve · resolve flag · kør scan · provider-styring · model-skift · daemon-kontrol.
6. **Live terminal:** command-line ind i Centralen (skriv+test kommandoer).
7. **Sind-grid:** 70 felter som åndende cellevæv.

## Animationer
- `corePulse` 2.6s — reaktor-glød ind/ud.
- `blink` 1.6s — live-prikker + sind-celler (varieret delay).
- `scan` 6s — sweeping linje top→bund.
- `fade` 0.3s — nye feed-rækker glider ind.

## Adaptivt princip
HUD'en omarrangerer efter tilstand: alt nominelt → Sind/kognition fylder mest. Flag/anomali/tør
provider → de kritiske paneler flyder OP og fylder mere. Viser det vigtige uden man leder.

## Kontrast-mål (Bjørn: alt smeltede sammen før)
Klare farve-kodede tilstande (grøn/gul/orange/lilla/rød på mørk), tydelige panel-kanter, store lyse
tal mod dæmpede labels. ALDRIG ens flad farve på alt.
