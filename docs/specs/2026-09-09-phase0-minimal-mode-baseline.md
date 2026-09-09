# Phase 0 — minimal-mode-basislinjen

Dato: 2026-09-09 · Hører til [DeepSeek Harness Lessons for Jarvis-v2](2026-09-08-deepseek-harness-lessons-for-jarvis.md) §12

Spec'ens §12: DeepSeeks `minimal`-preset er bevidst nøgent — fast prompt, ingen
runtime-kontekst, ingen kompaktion, præcis to værktøjer. Det er den flade
DeepSeek selv benchmarker på, fordi produktions-tal afhænger lige så meget af
stilladset som af modellen.

Fase 0 kræver det samme hos os: *«record model-only success/failure on the same
fixtures, so later phases can measure what the harness adds rather than assuming
it»*.

Køreren: `scripts/minimal_mode_baseline.py`. Den låner intet fra runtimen —
ingen prompt-samling, ingen Central, ingen hukommelse, ingen identitet. Fast
system-prompt, to værktøjer (`bash`, `str_replace_editor`), maskin-tjekbar
facit.

## Resultatet: 18 af 18

`deepseek-v4-flash:cloud`, 2026-09-09:

| opgave | resultat | runder | værktøjskald | tid |
|---|---|---|---|---|
| fil-skriv | 3/3 | 2–3 | 1–2 | 1,1–1,9 s |
| find-linje | 3/3 | 3 | 2 | 1,6–1,9 s |
| ret-fejl (syntaksfejl i script) | 3/3 | 4–8 | 3–7 | 2,5–10,0 s |
| tælle filer | 3/3 | 3 | 2 | 1,6–1,9 s |
| sammenhold flere filer | 3/3 | 5–7 | 4–6 | 4,3–10,8 s |
| flertrin (skriv script, kør det, gem svar) | 3/3 | 4–6 | 3–5 | 2,8–5,6 s |

## Hvad basislinjen faktisk siger

**På opgaver af denne størrelse tilfører stilladset intet målbart.** Den nøgne
model med to værktøjer løste hver eneste, også dem der kræver at læse flere
filer, sammenholde dem og handle på resultatet — netop dér hvor kontekst-samling
og hukommelse i teorien skulle hjælpe.

Det er ikke en dom over Jarvis. Det er en afgrænsning: **stilladsets værdi ligger
ikke i opgaver der kan afsluttes i seks værktøjskald.** Den ligger et andet sted
— lang horisont, tværgående hukommelse, identitet, kontinuitet på tværs af
kanaler — og dét skal måles med andre fixtures end disse.

## Loftet er ikke fundet — og det er problemet

18 af 18 betyder at prøven ikke kan skelne. En benchmark hvor alt består, måler
ingenting. Præcis samme fælde er allerede noteret én gang i dette projekt:
*«KALIBRERING UDESTÅR: alle 3 modeller scorer 100 efter værktøjs-fixene»*.

Basislinjen er derfor **etableret, men ikke kalibreret**. Før den kan bruges til
at måle hvad senere faser tilføjer, skal opgavesættet gøres hårdt nok til at
noget fejler. Kandidater:

- opgaver der kræver flere end 10 runder (rammer `max_tool_calls`-trykket §11
  handler om)
- opgaver med tvetydig formulering, hvor stilladset skal bære en afklaring
- opgaver der strækker sig over mere kontekst end ét vindue
- opgaver hvor et tidligere svar skal huskes — dér HAR stilladset noget at give

## Den ubehagelige sidebemærkning: latens

Nøgen model, hele opgaver løst: **1,1–10,8 sekunder.**

Til sammenligning er den målte median-latens for en synlig tur i produktion
**77 sekunder**, med 20 af 21 målinger over 30 sekunder. Det er ikke en
sammenligning af ens ting — produktionsture er større og bærer meget mere — men
størrelsesordenen er værd at have i hovedet, når §11's PTC-lektie handler om
netop rundture og latens.

## Kør den selv

```bash
python scripts/minimal_mode_baseline.py --gentag 3 --runder 8
python scripts/minimal_mode_baseline.py --opgave sammenhold --gentag 5
```

Skal køre på maskinen med Ollama. Facit er en kommando der køres i
arbejdsmappen bagefter — aldrig en håndskrevet forventning.
