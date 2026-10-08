# Desk som web og PWA

**Status 8/10-2026:** Desk-webbygget kører på `https://api.srvlab.dk/` fra `main` (`436bab8b3`). `apps/ui/dist` beholdes som fallback, indtil browserparitet er målt efter login på den kørende server. Fallback-valget er prøvet i en isoleret kopi på produktionsværten.

## Byg og skift

Den aktive service er `jarvis-api` på `bs@10.0.0.39` (kontrolleret 8/10-2026); `jarvis-api-workers` er inaktiv. Servicen kører FastAPI fra `/media/projects/jarvis-v2` og har intet UI-buildtrin. Efter koden er integreret på serveren køres fra udviklingsmaskinen:

```bash
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && scripts/build_desk_web.sh'
scripts/genstart_sikkert.sh jarvis-api
```

Buildscriptet kører `npm ci` og `npm run build:web` i `apps/jarvis-desk`. API'en vælger `apps/jarvis-desk/dist-web`, hvis mappen findes, og ellers `apps/ui/dist`. API-ruterne registreres før UI-mountet.

## Kontrol efter skift

Åbn `/` fra en lokal klient og bekræft Desk-login, sessioner, beskeder, streaming, afbrydelse, tool-resultater og approvals med en rigtig konto. Tjek også WebSocket-genforbindelse, Google-login, PWA-installation, offline login-skal og opdatering efter en ny build. Kontrollér at `/sw.js`, `/manifest.webmanifest` og ikonerne har `Cache-Control: no-cache`, og at kun hash-navngivne `/assets/*` har `immutable`. `/chat/*` og `/mc/*` skal kræve token. `/privatlivspolitik.html` skal fortsat kunne hentes udefra.

## Rollback

Stop API'en midlertidigt, flyt den nye buildmappe til side og genstart med den gamle build:

```bash
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && mv apps/jarvis-desk/dist-web apps/jarvis-desk/dist-web.rollback'
scripts/genstart_sikkert.sh jarvis-api
```

Gendan den nye build ved at flytte `dist-web.rollback` tilbage til `dist-web` og genstarte igen. Vent på aktive kørsler via `genstart_sikkert.sh`; tving ikke genstart mens Jarvis svarer. Den installerede PWA kan beholde den nye shell offline, indtil den igen når serveren, så test også i en ren browserprofil efter rollback.

Når produktionskontrollen og rollbacken er gennemført, kan fallbacken og `apps/ui` fjernes i samme ændring.
