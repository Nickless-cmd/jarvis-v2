# turhoved-harness — den ægte browsermåling

jsdom har ingen layout-motor. En test der læser `chat-flow.css` som tekst
beviser at en egenskab **står** i filen — ikke at containeren mister sin højde.
Det er den målefælde der gjorde accepttestens kontrakt 6 uærlig.

Denne harness monterer den **uændrede** `ChatFlowPresentation` i rigtig Chromium
og måler hvad brugeren faktisk ser.

## Kør

```bash
cd apps/jarvis-desk
npx vite --port 5199 --strictPort &
node src/harness/maal-blink.mjs      # kurve + blink
node src/harness/maal-kollaps.mjs    # slut-tilstande
```

`src/styles/tokens.css` SKAL importeres i harnessen: `--fold-varighed` peger på
`var(--dur-sheet)` (300 ms) der bor der. Uden den er transitionen ugyldig og
falder tilbage til øjeblikkelig — så ville harnessen vise et hårdt kollaps der
ikke findes i app'en, og målingen ville lyve i den modsatte retning.

## Målt 27/11-2026 på `d1ac50f94`

**Kollapset fjerner plads.** Højde 74,4 → 0 px, opacity 1 → 0, på den SAMME
DOM-node (`isSameNode` = true). GPT's tabel sagde «kun opacity 0.55» — det var
sandt indtil `ef6334654` og er forældet nu.

**Men faden og højden er ikke samtidige.** Kurven, samplet hver frame:

| tid | højde | opacity |
|-----|-------|---------|
| 3 ms | 74,4 px | 1,000 |
| 65 ms | 74,4 px | 0,464 |
| 132 ms | 74,4 px | 0,204 |
| 198 ms | 74,4 px | 0,066 |
| 265 ms | 16,1 px | 0,007 |
| 332 ms | 0 px | 0,000 |

Opaciteten er praktisk talt færdig ved 198 ms, men boksen står stadig på fuld
højde. Først derefter klapper den sammen — og gør det i to spring på 30 og 21 px.
Resultatet er ikke «besvarelserne glider sammen», men «teksten forsvinder, så
klapper et tomt hul sammen».

Årsagen er `max-height: 2400px → 0`: de første ~2/3 af transitionen foregår i
intervallet 2400 → 74 px, hvor intet synligt ændrer sig. CSS-kommentaren peger
selv på afløseren (`grid-template-rows: 1fr → 0fr`).

**Blinket ved renderer-skiftet er der stadig.** Besvarelsens ydre
`.chat-flow-answer` består (`isSameNode` = true), men dens direkte barn skifter
fra `<p>` til `.chat-flow-segmenter` når `fladtFlow` bliver sand — så hele
besvarelsen remountes. Det er kontrakt 1 i accepttesten, som står som `it.fails`.
