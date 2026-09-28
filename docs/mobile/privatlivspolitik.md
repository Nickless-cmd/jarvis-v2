# Privatlivspolitik — kilden

> Skrevet 28/9-2026, da mobil-appen blev undersøgt mod Google Plays krav (#4).
> Den offentlige side ligger i `apps/ui/public/privatlivspolitik.html` og
> serveres på **https://api.srvlab.dk/privatlivspolitik.html** — uden login,
> fordi en Play-reviewer skal kunne nå den.

Dette er kilde-teksten. HTML-siden er den udgivne form; retter man den ene,
skal den anden følge med. Der er ingen generator — filerne holdes i sync i hånden,
fordi der kun er to af dem.

## Hvorfor den ligger der, den ligger

`apps/ui/dist` monteres på `/` i `apps/api/jarvis_api/app.py` (linje ~1028) med
`html=True`. `dist/` er gitignored — men Vite kopierer alt i `apps/ui/public/`
ukritisk med ved build. Derfor er `public/` den eneste hylde hvor filen både
**versioneres i git** og **bliver offentligt tilgængelig uden auth**.

Alternativet — at lægge den bag API'ets auth — ville fejle i Play-review, fordi
revieweren ikke har en token til Bjørns server.

## Fakta den bygger på (verificeret 28/9-2026)

| Påstand | Hvor det er verificeret |
|---|---|
| Ingen analytics/tracking-SDK | `apps/mobile/package.json` — ingen Sentry/Amplitude/Mixpanel/Segment. Kun `@react-native-firebase/*` til push |
| Lyd transskriberes **lokalt** | `apps/api/jarvis_api/routes/transcribe.py:4` — «lokalt via faster-whisper (core.services.dictation)» |
| Baggrundslokation: 5 min / 250 m, opt-in | `apps/mobile/src/lib/backgroundLocation.ts` — `timeInterval: 300000`, `distanceInterval: 250`, kræver `requestBackgroundPermissionsAsync` |
| Fire datalag, lagvis sletning | `apps/mobile/src/lib/accountData.ts` + `core/services/encryption.py` §16.2 |
| Ejerens data er plaintext, andres krypteret | `core/services/encryption.py` — `should_encrypt()`: «Owner (Bjørns egen workspace) er plaintext» |
| Tredjeparter | `core/services/vision_backend.py` (DeepSeek), `core/tools/openrouter_image_tools.py` (OpenRouter), `apps/api/jarvis_api/routes/tts.py` (ElevenLabs/edge-tts), Firebase FCM, Cloudflare, **`apps/mobile/src/lib/location.ts` (Nominatim/OpenStreetMap)** |

## Det bevidste valg: ærlighed om kryptering

Politikken siger **ikke** «alle data er krypteret». Den siger, at data for andre
konti end ejerens er krypteret i hvile, og at ejeren har sit eget indhold i
klartekst på sin egen maskine.

Det er samme rettelse som `DataControlsScreen` fik samme dag (commit `b9c41671c`):
en påstand om kryptering, der ikke gælder for den, der læser den, er en løgn —
også når den er velment.

## Skal den opdateres

1. Ret `apps/ui/public/privatlivspolitik.html` (den udgivne side).
2. Ret fakta-tabellen ovenfor hvis en verifikation ændrer sig.
3. Opdater datoen i `<p class="sub">` øverst i HTML'en.
4. Committ begge filer.
