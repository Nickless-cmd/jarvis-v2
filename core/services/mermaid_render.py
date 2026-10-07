"""Mermaid → SVG, server-side. Så diagrammer også når mobilen.

## Hvorfor serveren og ikke klienten

Desk tegner ` ```mermaid ` selv (`MermaidBlock.tsx`, lazy `import('mermaid')`).
Mobilen har ingen mermaid-renderer: nul referencer i `apps/mobile/src`, og
`mermaid` står ikke i dens `package.json`. Markdown-reglerne i
`MessageBubble.tsx` sender enhver fence til `CodeBlock` — også `mermaid` — så
telefonen viser rå kildekode (målt 7/10-2026, Bjørn: «Det virker kun i desk,
ikk på mobilen»).

Prompten i `output_discipline.py` siger til modellen at en mermaid-blok
*RENDERES som et diagram i jarvis-desk*. Det er sandt i desk og falsk på
mobilen — derfor blev mermaid brugt i god tro.

## Hvorfor en browser og ikke jsdom

Målt 7/10-2026: mermaid kan IKKE rende i ren node. Den kræver `document`,
`CSSStyleSheet` og — afgørende — en layout-motor til `getBBox()`. jsdom har
ingen layout, så hver shim avler den næste fejl:

  1. `document is not defined`          → jsdom
  2. `CSSStyleSheet is not defined`     → shim
  3. `getBBox is not a function`        → shim
  4. viewBox = 36.448 px                → shim'en målte `<style>`-teksten
  5. `Could not find a suitable point`  → nul-bokse giver ubrugelig geometri
  6. viewBox = 26 px                    → stadig forkert

Fem shims dybt og stadig forkert. Med Playwrights chromium-binær rendrer det
korrekt i første forsøg (12.408 tegn SVG). Vejen er altså en browser.

## Prisen, ærligt

Chromium-binæren ligger allerede i `~/.cache/ms-playwright/chromium-1208`
(Google Chrome for Testing 145). Men `playwright`-pakken er IKKE installeret,
og hvert kald starter en browser — ~1-2 sekunder. Det er en tung afhængighed
for et diagram, og den hører ikke i den varme sti.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

#: Chromium-binæren. Playwrights cache, ikke en systeminstallation — der
#: findes ingen browser i /usr/bin på denne maskine (målt 7/10-2026).
CHROME_STIER = (
    Path.home() / '.cache/ms-playwright/chromium-1208/chrome-linux64/chrome',
    Path.home() / '.cache/ms-playwright/chromium_headless_shell-1208/chrome-linux/headless_shell',
)

#: Mermaid ligger i desk's node_modules (76 MB). Vi genbruger den frem for at
#: installere en kopi til serveren.
MERMAID_STIER = (
    Path('/media/projects/jarvis-v2/apps/jarvis-desk/node_modules/mermaid/dist/mermaid.min.js'),
)

#: Samme grænse som desk bruger (`MermaidBlock.tsx`): `strict` saniterer
#: labels og klik-handlere i mermaid's output, så en fjendtlig diagram-titel
#: ikke bliver en script-vektor.
SIKKERHEDSNIVEAU = 'strict'

#: Et diagram er en visning. Samme ånd som widget-grænsen.
MAX_KILDE_BYTES = 20_000
TEGN_GRAENSE_S = 30


class MermaidFejl(RuntimeError):
    """Kunne ikke rende diagrammet — med en årsag der kan handles på."""


def find_chrome() -> Path | None:
    """Første kørende chromium-binær, eller None."""
    for sti in CHROME_STIER:
        if sti.exists() and sti.is_file():
            return sti
    return None


def find_mermaid() -> Path | None:
    for sti in MERMAID_STIER:
        if sti.exists() and sti.is_file():
            return sti
    return None


def tilgaengelig() -> tuple[bool, str]:
    """Kan serveren rende mermaid lige nu? (ja/nej, grund)."""
    if find_chrome() is None:
        return False, 'ingen chromium-binær fundet (se CHROME_STIER)'
    if find_mermaid() is None:
        return False, 'mermaid.js ikke fundet (se MERMAID_STIER)'
    return True, 'klar'


def _side(kilde: str, mermaid_js: str) -> str:
    """HTML-siden der rendrer diagrammet og lægger SVG'en i titlen.

    Titlen er transporten: `--dump-dom` giver hele DOM'en, og SVG'en kan
    indeholde vilkårlige citationstegn. At pakke den i JSON i titlen er
    entydigt, hvor et regex over DOM'en ikke er.
    """
    return f"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<script>{mermaid_js}</script>
<script>
const KILDE = {json.dumps(kilde)};
mermaid.initialize({{startOnLoad:false, theme:'dark', securityLevel:{json.dumps(SIKKERHEDSNIVEAU)}}});
mermaid.render('jarvis-diagram', KILDE).then(
  r => {{ document.title = JSON.stringify({{ok:true, svg:r.svg}}); }}
).catch(
  e => {{ document.title = JSON.stringify({{ok:false, fejl:String(e && e.message || e)}}); }}
);
</script></body></html>"""


def render(kilde: str, *, timeout: int = TEGN_GRAENSE_S) -> str:
    """Mermaid-kilde → SVG. Rejser `MermaidFejl` hvis det ikke kan lade sig gøre."""
    raa = (kilde or '').strip()
    if not raa:
        raise MermaidFejl('tom mermaid-kilde — der er intet diagram at tegne')
    n = len(raa.encode('utf-8'))
    if n > MAX_KILDE_BYTES:
        raise MermaidFejl(f'mermaid-kilden er {n} bytes (højst {MAX_KILDE_BYTES})')

    chrome = find_chrome()
    if chrome is None:
        raise MermaidFejl('ingen chromium-binær fundet — kan ikke rende mermaid')
    mermaid_js = find_mermaid()
    if mermaid_js is None:
        raise MermaidFejl('mermaid.js ikke fundet — kan ikke rende mermaid')

    with tempfile.TemporaryDirectory(prefix='jarvis-mermaid-') as tmp:
        side = Path(tmp) / 'diagram.html'
        side.write_text(_side(raa, mermaid_js.read_text(encoding='utf-8')), encoding='utf-8')
        try:
            svar = subprocess.run(
                [
                    str(chrome),
                    '--headless',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--virtual-time-budget=8000',
                    '--dump-dom',
                    side.as_uri(),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise MermaidFejl(f'chromium svarede ikke inden {timeout} s') from e

    dom = svar.stdout or ''
    if not dom:
        raise MermaidFejl(f'chromium gav intet output (exit {svar.returncode})')

    # Titlen bærer resultatet som JSON.
    start = dom.find('<title>')
    slut = dom.find('</title>', start)
    if start < 0 or slut < 0:
        raise MermaidFejl('kunne ikke læse resultatet ud af chromium-outputtet')

    raa_titel = dom[start + len('<title>'):slut]
    # Chromium HTML-escaper titlen; JSON'en skal pakkes ud igen.
    for soeg, erstat in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>')):
        raa_titel = raa_titel.replace(soeg, erstat)

    try:
        data = json.loads(raa_titel)
    except json.JSONDecodeError as e:
        raise MermaidFejl(f'kunne ikke tolke chromium-svaret: {raa_titel[:200]!r}') from e

    if not data.get('ok'):
        raise MermaidFejl(f'mermaid afviste diagrammet: {data.get("fejl", "ukendt fejl")}')

    svg = data.get('svg') or ''
    if '<svg' not in svg:
        raise MermaidFejl('mermaid svarede uden SVG-indhold')
    return svg
