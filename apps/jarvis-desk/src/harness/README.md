# turhoved-harness — acceptmålingen af oplevelsen

jsdom har ingen layout-motor. En test der læser `chat-flow.css` som tekst
beviser at en egenskab **står** i filen — ikke at containeren mister sin højde,
og slet ikke at besvarelserne glider sammen.

Denne harness monterer den **uændrede** `ChatFlowPresentation` i rigtig Chromium
og måler hvad brugeren faktisk ser. Bjørn 27/11-2026: «Bevar denne
browser-harness. Den skal være acceptmålingen for oplevelsen, ikke blot
dokumentation af enkelte CSS-egenskaber.»

## Kør

```bash
cd apps/jarvis-desk
npx vite --port 5199 --strictPort &
node src/harness/maal-oplevelse.mjs   # ACCEPTMÅLINGEN — exit 1 hvis et krav brydes
```

`src/styles/tokens.css` SKAL importeres i harnessen: `--fold-varighed` peger på
`var(--dur-sheet)` (300 ms) der bor der. Uden den er transitionen ugyldig og
falder tilbage til øjeblikkelig — så ville harnessen vise et hårdt kollaps der
ikke findes i app'en, og målingen ville lyve i den modsatte retning.

## Hvad acceptmålingen kræver

Den måler **afstanden mellem besvarelse A og B** med rundecontaineren imellem —
ikke containerens egen højde. Det er den afstand brugeren ser, og den består af
tre ting: containerens højde, dens opacity, og det grid-gap den efterlader selv
når den er 0 px høj (`.chat-flow-segmenter` har `gap: inherit`).

Fem krav, ved **to** containerhøjder (lav = 1 kald, høj = 6 kald):

1. Afstanden falder **kontinuerligt** — ingen frame må vokse.
2. Intet enkelt spring over 25 % af den samlede ændring.
3. Synlighed og plads følges ad: når opacity < 0,5, må højden ikke være på max.
4. Slutafstanden = afstanden uden runde → gap'et er neutraliseret, ikke skjult.
5. Afmonteringen giver **intet layout-hop**, og noden er væk bagefter.

## Målt 27/11-2026 (efter grid-wrapperen)

```
LAV  (74 px):  74.39 → 22.13 → 0.06 → 0     opacity 1 → 0.38 → 0.12 → 0
HØJ  (446 px): 446.34 → 201.61 → 63.06 → 2.34 → 0
```

Alle fem krav opfyldt ved begge højder. Afmonteringen sker først når rækken er
0fr og gap'et neutraliseret, så fjernelsen kan ikke ses.

### Modprøven bærer

Kørt mod den gamle `max-height`-kode fejler målingen på præcis de to defekter:

- **HUL:** opacity 0,46 mens højden står på fuld 74,4 px i 11 frames.
- **SPRING:** 30 og 21 px i to hak ved slutningen.

Målingen kan altså skelne. Den er ikke grøn af den forkerte grund.

## Fælder målt undervejs

**`grid-template-rows: 1fr` gælder kun den FØRSTE række.** `BlocksRenderer`
giver flere søskende — seks værktøjskald blev seks grid-børn, og de fem
implicitte rækker arvede ikke `1fr`. Målt: `0px 74.8px 74.8px 74.8px 74.8px
74.8px` — kun 1/6 af højden animerede, resten forsvandt ved afmonteringen med et
spring på 361 px. Løsningen er én indre wrapper (`.chat-flow-runde-indhold`).

**`.chat-flow-answer` rammer også det nestede svar** inde i den flade gren. En
simpel klasse-query gav A og B i forkert rækkefølge (negativ afstand). Brug
`[data-segment="besvarelse"]`.

**`gap: inherit` koster plads selv ved 0 px højde.** `.chat-flow` har
`gap: 0.65rem`; en kollapset container efterlod 10,4 px tom luft mellem A og B.
Neutraliseres med `margin-bottom: -0.65rem` der animerer sammen med rækken.

## Stadig åbent

**Blinket ved renderer-skiftet.** Besvarelsens ydre `.chat-flow-answer` består,
men dens direkte barn skifter fra `<p>` til `.chat-flow-segmenter` når
`fladtFlow` bliver sand — så hele besvarelsen remountes. Det er kontrakt 1 i
`ChatFlowPresentation.accept.test.tsx`, som står som `it.fails`. Den bliver rød
i samme øjeblik nogen fixer strukturen, og skal da vendes til `it`.
