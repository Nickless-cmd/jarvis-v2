# Notes from Linux-side Claude → Windows-side Claude

**Skrevet:** 2026-05-27 19:30 lokal tid
**Til:** Den Claude-instans der starter på Windows efter Bjørn dual-boots
**Formål:** Lade dig bygge en signed `JarvisX.exe` til distribution til Mikkel

---

## Sammenhæng

Bjørn arbejder på Jarvis V2 — en persistent digital agent. JarvisX er
Electron-app'en der giver Jarvis adgang til Bjørns desktop via et
WebSocket bridge. Tidligere på dagen (27. maj 2026) byggede vi:

- **Multi-user auth** via JWT tokens (HS256, 365-dage gyldighed)
- **Backend kører** på `https://api.srvlab.dk` (LXC 105 på Proxmox)
- **TLS pass-through** gennem pfsense + Caddy + Let's Encrypt
- **First-run UI:** `apps/jarvisx/src/components/SetupScreen.tsx` —
  user indtaster API URL + token ved første start
- **Old OnboardingModal er FJERNET** — den havde et "Owner"-knap-hul

Linux .deb + .AppImage builds er allerede gennemtestet og virker.
Du skal lave Windows-versionen.

## Din opgave

**Mål:** Producer `JarvisX-0.1.0-poc-Setup.exe` (nsis installer) som
Bjørn kan sende til Mikkel via Discord.

### Steps

1. **Pull seneste kode** (vigtigt — vi har lavet meget i dag):
   ```cmd
   cd C:\projects\jarvis-v2
   git pull origin main
   ```

2. **Installer dependencies** (hvis ikke allerede gjort):
   ```cmd
   cd apps\jarvisx
   set PATH=C:\Program Files\nodejs;%PATH%
   npm install
   ```

3. **Build:**
   ```cmd
   npm run package:win
   ```

4. **Output ligger i:**
   `C:\projects\jarvis-v2\apps\jarvisx\release\`
   - `JarvisX Setup 0.1.0-poc.exe` ← det Mikkel skal have
   - `win-unpacked\JarvisX.exe` ← portable version

### Hvis electron-builder fejler

Tidligere på dagen (transcript fra 26. maj) løste vi et 7za-related
issue ved at wrap'e binaryen. Hvis du støder på `snld`-errors eller
lignende ved `npm run package:win`, prøv først:

```cmd
del /s /q C:\Users\onkel\AppData\Local\electron-builder\Cache\winCodeSign
```

Og hvis 7za fejler, find tidligere session transkriptet under
`C:\Users\onkel\.claude\projects\C--Users-onkel\` (det er fra Mikkels
forrige Windows-session).

## Hvad er ÆNDRET siden Windows-builden i går

Mange ting. De vigtigste:

| Område | Commit | Hvad |
|---|---|---|
| icons | `ef752420` | Nyt flamme-icon (assets/icon.png + icon.ico) |
| auto-scroll | `939adee7` | Chat scroller nu korrekt med ny besked + streaming |
| status pill | `75cf6481` | "Tænker via ..."-pille flyttet til navnerækken |
| bridge robustness | `78e5f81c` | 3 timeout/watchdog-fixes i bridge.ts |
| update banner | `7978eb1e` | "No published versions"-fejl suppressed |
| auth setup | `1ffc6fa7` | SetupScreen.tsx ny — first-run token validation |
| auth security | `6c404ee8` | OnboardingModal slettet (havde "Owner"-knap-hul) |

Den seneste version Mikkel modtager skal have ALLE disse fixes inkluderet.

## Sikkerhedstjek inden du sender til Mikkel

1. `apps/jarvisx/release/JarvisX Setup 0.1.0-poc.exe` skal eksistere
2. Open the .exe i hex-editor/file properties — den må IKKE indeholde
   ordet "Owner" som tegn — det bekræfter OnboardingModal er væk
3. Test installer'en på en frisk bruger-profil:
   - Installer
   - Start → forventet: SetupScreen vises (ingen mulighed for at vælge "Owner")
   - Indtast `https://api.srvlab.dk` + Mikkels token (Bjørn har den)
   - Forventet: validering går igennem, app starter normalt

## Mikkels token (til Bjørn at sende, ikke skrive ind i kode)

Token er gemt i `/home/bs/.jarvis-v2-tokens-distribute.md` på Linux-siden.
Den fil ligger IKKE på Windows-partitionen. Bjørn copy-paster manuelt
fra Discord eller andet privat kanal.

## Test fra Bjørn-bruger på Windows

Hvis Bjørn vil teste fra Windows-siden:
- Hans personlige token er også i `.jarvis-v2-tokens-distribute.md`
- Hans config skal pege på `apiBaseUrl=https://api.srvlab.dk` (IKKE
  `http://10.0.0.39` — det interne LAN er kun tilgængeligt fra Linux)

## Næste skridt efter du har lavet .exe'en

1. Bekræft .exe størrelse virker (~120-150 MB normalt)
2. Send Bjørn besked: "JarvisX.exe ligger i release/ — send den + Mikkels token til Mikkel via Discord"
3. Bjørn booter tilbage til Linux når .exe'en er klar

## Hvis du har spørgsmål

- Backend API: `https://api.srvlab.dk` (kører — du kan teste mod den)
- Token til at teste auth: brug Bjørns egen (Bjørn har den)
- Codebase: alt under `C:\projects\jarvis-v2\` — `git log -20` viser de seneste commits
- Tests: `cd C:\projects\jarvis-v2; pytest tests/test_visible_runs.py` (kræver dog conda ai env — ikke nødvendigt for Windows-build)

Held og lykke! 🔥

— Claude (Linux-side, 2026-05-27)
