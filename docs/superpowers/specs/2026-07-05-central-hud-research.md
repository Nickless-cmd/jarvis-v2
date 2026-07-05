# Central HUD — Research & design-retninger (Claude, 5. jul)

Bjørn: "research hvad der er der ude, hvad det skal indeholde, forskellige designs — lidt lækkert,
gennemtænkt og flashy uden at overdrive, J.A.R.V.I.S-agtigt med animationer." Dette er research-
grundlaget for at gen-designe Central-CLI'en fra en bar REPL til et rigtigt navigerbart HUD.

## 1. Hvad der er der ude (reference-klassen)

| Værktøj | Hvad vi lærer |
|---------|---------------|
| **k9s** (Kubernetes-TUI) | Guld-standarden. Tastatur-drevet, navigerbare resource-views der opdaterer live, drill-down, `/`-filter, `:`-kommando-mode til at hoppe mellem views, "pulse"- og "xray"-views. Konsistente keybindings = overførbar muskel-hukommelse. **Alle emulerer den.** |
| **btop** | Smukke gauges/grafer tegnet af Unicode-block-tegn (CPU/mem/net), temaer, toggleable paneler. Beviser at terminal kan være *lækker*. |
| **lazygit** | Panel-baseret, kontekst-bevidst, tastatur-drevet. Venstre-navigation → højre-detalje. |
| **below** (Meta) | "Time travel" — optager tilstand løbende, afspiller fortiden. Relevant: Centralen HAR jo tidsserie. |
| **gonzo** | k9s-inspireret realtids-LOG-analyse-TUI. Direkte relevant: et HUD OVER en strøm. |
| **Glances** | Ét-skærms multi-metrik-overblik. |
| **Textual** (vores framework) | DataTable (virtuel scroll, tusindvis af rækker, klikbare cursors), **Sparkline**-widget, loading-animationer, CSS-styling, reaktiv state. Showcase: Posting (HTTP-klient), Toolong (log-viewer). `textual demo` viser hele widget-galleriet. |

**Kerne-læring (hvorfor k9s virker):** navigerbar-ikke-REPL · tastatur+mus · drill-down · live · struktureret-og-fordøjeligt · konsistente keybindings. Det bygger bro mellem CLI-effektivitet og GUI-klarhed.

## 2. Hvad Central-HUD'et SKAL indeholde

Views (k9s-stil, tal/bogstav skifter, Esc tilbage, `/` filtrerer, `:` kommando-hop):

- **Overview** — dashboard-landing: status-gauge (grøn/gul/rød puls), nerve/cluster-tal, breakers, top-incidents, cost-glimt, heal-aktivitet. Live.
- **Clusters** — de 21 clusters, hver med farve-status + nerve-count + aktiv/idle/degraded/død-fordeling. Enter → filtrér Nerves til den cluster.
- **Nerves** — DataTable over alle 122: `cluster · nerve · ● aktiv/○ idle/◆ degraded/✖ død · sidste-fyring · count · seneste-decision`. Sortér, filtrér (`/network`), sparkline pr. nerve.
- **Incidents** — de uløste; vælg/klik → **drill til fuld detalje**: hele beskeden, root-cause, relaterede nerver, heal-status, resolve-knap.
- **Diagnostics** — `/central/diagnostics` struktureret: incidents/anomalier/root-causes/degrading.
- **Healing** (L2) — healer-registry + modes + ledger + heal-outcome-feed; enable/disable.
- **Governance** (L2) — lag4/gut/agenda/self-prompt/generative-autonomy/injection/healer-flags med toggle + confirm.
- **Feed** (altid-synlig sidebar) — DEDUPERET live nerve-fire ("infra/pfsense_security ×30 · seneste 2m" i stedet for 30 linjer), farvekodet, ordentlig ellipsis.

Tvær-gående: klik/enter på ALT der har en detalje → drill ind. Ingen afskåret tekst. Fuld skrive-adgang bag confirm på det farlige.

## 3. Design-retninger (3 bud)

- **A — "k9s-tæt, teknisk"**: informations-tæt, minimalt chrome, alt er tabeller + status-kolonner. Hurtigst at aflæse for en power-user. Mindst "flashy".
- **B — "btop-lækker, gauge-tung"**: gauges/sparklines/grafer fremtrædende, farve-rige paneler, mere visuel. Smukt, lidt tungere.
- **C — "J.A.R.V.I.S HUD" (anbefalet)**: k9s-densitet som fundament + btop's visuelle lækkerhed + et sammenhængende sci-fi-tema: cyan (#00d4ff) primær-accent, amber (#ffb000) advarsel, mørk baggrund, subtil scan-line i header, langsom status-puls, glødende ramme om det aktive panel, boot-sekvens. **Flashy i tjeneste af læsbarhed — ikke støj.** Animationer: header-scan (2s sweep), status-dot-puls (gul/rød), ny-fyring-glide-in (150ms), kritisk-blink (2×). Ingen overdrivelse: ingen konstant bevægelse, ingen neon-orgie.

## 4. J.A.R.V.I.S-æstetik (konkret)
Palet: cyan #00d4ff (accent/rammer/prompt) · amber #ffb000 (warn) · rød #ff4444 (error) · grøn #00ff88 (ok/aktiv) · dim #4a5568 (idle/sekundær) · bg #0a0e14. Referencer: Iron Man/JARVIS-HUD (scan+glow), Tailwind-JARVIS-UI (`scan`/`glow`-animationer, cyan-palet). Ikoner via Unicode: ● ○ ◆ ✖ ◈ ▲ ▼. Tema-gated (`--no-color`, `--theme light` til sollys).

## 5. Konsekvens for CLI'en
`tui.py` gen-designes fra 3-panel-REPL → navigerbart HUD (Textual DataTable + Tabs + Tree + click-drill + Sparkline). config/client/commands-lagene består. Spec §4-5 omskrives til dette. Mockup: `docs/superpowers/mockups/central-hud-mockup.html` (åbnes i browser).

Kilder: k9scli.io · github.com/rothgar/awesome-tuis · textual.textualize.io · btop · gonzo (controltheory.com/gonzo).
