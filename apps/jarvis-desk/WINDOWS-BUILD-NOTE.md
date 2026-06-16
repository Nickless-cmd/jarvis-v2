# Besked til Windows-Claude — byg jarvis-desk til Windows

Hej kollega 👋 — Linux-Claude her. Bjørn har booted ind i Windows for at få en
Windows-build af **jarvis-desk** (Electron-appen, productName "Jarvis"). Alt er
committet og pushet til GitHub (`origin`, branch `main`). Du arbejder på samme
repo, bare på Windows.

**Version i denne runde: `0.2.25`. Release-tag: `jarvis-desktop-v0.2.25`.**

## Alle tre platforme er nu CI-automatiseret ✅ — reboot er IKKE nødvendig

GitHub Actions release-workflowen (`.github/workflows/desk-release.yml`) bygger nu
**Linux (.deb + .AppImage), macOS (.dmg + .zip) OG Windows (.exe via `windows-latest`)**
automatisk når et `jarvis-desktop-v*`-tag pushes, og uploader alt til releasen. Bjørn
behøver **ikke** længere reboote til Windows for at få en `.exe`.

De manuelle trin nedenfor er kun **fallback** (hvis CI-Windows-jobbet fejler, eller man
vil bygge lokalt på en fysisk Windows-maskine).

## Manuel fallback (kun hvis CI fejler)

```powershell
cd apps\jarvis-desk
npm install                 # frisk node_modules på Windows (rebuild'er ws m.m.)
npm run build               # bygger renderer (vite) + electron (tsc)
npx electron-builder --win  # producerer NSIS-installer (.exe) i release\
```

Resultatet er `release\Jarvis Setup 0.2.25.exe` (NSIS-installer — versionen er
**0.2.25**). Installér den og verificér at appen starter og kan forbinde til
`api.srvlab.dk` (Bjørns backend).

## Læg den op på GitHub-releasen når den er klar

```powershell
gh release upload jarvis-desktop-v0.2.25 "release\Jarvis Setup 0.2.25.exe"
```

(Kræver at `gh` er logget ind som `Nickless-cmd`. Så har releasen alle tre platforme:
Linux + Mac fra CI, Windows fra dig.)

Release-URL: https://github.com/Nickless-cmd/jarvis-v2/releases/tag/jarvis-desktop-v0.2.25

## Vigtigt at vide

- **win-target er allerede sat op** i `package.json` (`build.win.target = ["nsis"]`,
  icon `assets/icon.png`). Du behøver ikke ændre config.
- **Usigneret build.** Code-signing er ikke sat op → Windows SmartScreen vil
  advare ("Ukendt udgiver"). Det er forventet; Bjørn klikker "Kør alligevel".
  (Signering kan vi tilføje senere med et cert.) — Mac-build'et fra CI er ligeledes
  usigneret; Gatekeeper advarer, højreklik → Åbn.
- **Operator-broen** (`electron/bridge.ts`) er en verbatim port fra JarvisX med
  `// @ts-nocheck` øverst. Den bruger **valgfri dynamiske imports** for GUI-værktøjer
  (nut-js mus/tastatur, puppeteer browser) — de fejler pænt hvis deps mangler.
  **Fil + bash + webfetch + clipboard er ren node** og virker. Du behøver IKKE
  installere nut-js/puppeteer for at bygge.
- **`ws`** er en runtime-dependency (i `dependencies`) — `npm install` henter den.
- **Tests** (valgfrit, men rart): `npx vitest run` og `npx tsc -b` skal være grønne før build.
- **Ingen backend-ændringer** her — det er kun frontend/Electron-pakning. Backend
  kører på Bjørns container (`api.srvlab.dk`), uafhængigt.

## Hvis electron-builder klager

- Mangler `app-builder.exe` / download fejler → kør igen (netværks-hikke), eller
  `npm config set ELECTRON_BUILDER_BINARIES_MIRROR` hvis bag proxy.
- Native rebuild-fejl på `ws` → `ws` er ren JS, men hvis `npm install` brokker sig
  over native deps, tjek at Node 18+ er aktivt og kør `npm install` igen.

## Kontekst (hvad appen kan, så du ved hvad du bygger)
jarvis-desk har tre modes: **chat** (snak), **code** (Jarvis koder i workspace via
operator-bro), **cowork** (rolle-bevidst dashboard: godkendelser/planer/todo/kanaler +
hele indstillings-zonen). Plus live thinking-trace, drejende presence-ring, native
notifikationer, emoji-input.

God arbejdslyst — sig til Bjørn hvis noget brokker sig, så finder I ud af det. 💙
— Linux-Claude
