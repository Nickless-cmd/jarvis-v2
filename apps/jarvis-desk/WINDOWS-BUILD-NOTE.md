# Besked til Windows-Claude — byg jarvis-desk til Windows

Hej kollega 👋 — Linux-Claude her. Bjørn har booted ind i Windows for at få en
Windows-build af **jarvis-desk** (Electron-appen, productName "Jarvis"). Alt er
committet og pushet til GitHub (`origin`, branch `main`). Du arbejder på samme
repo, bare på Windows.

## Hvad du skal gøre

```powershell
cd apps\jarvis-desk
npm install                 # frisk node_modules på Windows (rebuild'er ws m.m.)
npm run build               # bygger renderer (vite) + electron (tsc)
npx electron-builder --win  # producerer NSIS-installer (.exe) i release\
```

Resultatet er `release\Jarvis Setup 0.2.6.exe` (NSIS-installer — versionen er
**0.2.6**, ikke 0.1.0; den blev bumpet da Linux/Mac blev udgivet). Installér den og
verificér at appen starter og kan forbinde til `api.srvlab.dk` (Bjørns backend).

## Læg den op på GitHub-releasen når den er klar

Linux + Mac er allerede udgivet som release **`jarvis-desktop-v0.2.6`**
(https://github.com/Nickless-cmd/jarvis-v2/releases/tag/jarvis-desktop-v0.2.6).
Smid Windows-`.exe`'en op på samme release:

```powershell
gh release upload jarvis-desktop-v0.2.6 "release\Jarvis Setup 0.2.6.exe"
```

(Kræver at `gh` er logget ind som `Nickless-cmd`. Så har releasen alle tre platforme.)

## Vigtigt at vide

- **win-target er allerede sat op** i `package.json` (`build.win.target = ["nsis"]`,
  icon `assets/icon.png`). Du behøver ikke ændre config.
- **Usigneret build.** Code-signing er ikke sat op → Windows SmartScreen vil
  advare ("Ukendt udgiver"). Det er forventet; Bjørn klikker "Kør alligevel".
  (Signering kan vi tilføje senere med et cert.)
- **Operator-broen** (`electron/bridge.ts`) er en verbatim port fra JarvisX med
  `// @ts-nocheck` øverst. Den bruger **valgfri dynamiske imports** for GUI-værktøjer
  (nut-js mus/tastatur, puppeteer browser) — de fejler pænt hvis deps mangler.
  **Fil + bash + webfetch + clipboard er ren node** og virker. Du behøver IKKE
  installere nut-js/puppeteer for at bygge.
- **`ws`** er en runtime-dependency (i `dependencies`) — `npm install` henter den.
- **Tests** (valgfrit, men rart): `npx vitest run` (138 tests) og `npx tsc -b`
  skal være grønne før build.
- **Ingen backend-ændringer** her — det er kun frontend/Electron-pakning. Backend
  kører på Bjørns container (`api.srvlab.dk`), uafhængigt.

## Hvis electron-builder klager

- Mangler `app-builder.exe` / download fejler → kør igen (netværks-hikke), eller
  `npm config set ELECTRON_BUILDER_BINARIES_MIRROR` hvis bag proxy.
- Native rebuild-fejl på `ws` → `ws` er ren JS, men hvis `npm install` brokker sig
  over native deps, tjek at Node 18+ er aktivt og kør `npm install` igen.

## Kontekst (hvad appen kan, så du ved hvad du bygger)
jarvis-desk har tre modes: **chat** (snak), **code** (Jarvis koder i workspace via
operator-bro), **cowork** (rolle-bevidst dashboard: godkendelser/planer/todo/kanaler).
Plus live thinking-trace, drejende presence-ring, native notifikationer, emoji-input.
Alt er bygget og testet på Linux i dag; Windows-build'et er sidste platform.

God arbejdslyst — sig til Bjørn hvis noget brokker sig, så finder I ud af det. 💙
— Linux-Claude
