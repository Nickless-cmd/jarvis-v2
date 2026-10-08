# Fælles Desk, web og PWA

**Dato:** 2026-10-08
**Status:** Godkendt 2026-10-08

## Formål og ramme

Bjørn vil erstatte den gamle `apps/ui`-chat med samme brugerflade som Desk og gøre webudgaven installerbar som PWA. Succeskriteriet er én vedligeholdt React-renderer, én chatprotokol og én komponentimplementering for Desk og web. Elektroniske operativsystemfunktioner må gerne findes kun i Desk. Mission Control og backendens operationelle sandhed ændres ikke af dette arbejde.

Webskallen følger indledningsvis den eksisterende regel om kun at være tilgængelig fra lokale afsendere. Beslutning om offentlig adgang er særskilt. PWA-installation fra et andet netværk kræver, at brugeren senere vælger en offentlig eller anden fjernadgangsvej.

## Valgt tilgang

`apps/jarvis-desk/src` bliver eneste kilde til rendererens fælles skærme, chatlogik og API-klient. Vite bygger to mål fra kilden: Electron-renderer og browser/PWA. `apps/ui` holdes kun som eksisterende produktionsfallback under overgangen og slettes, når webudgaven består paritetskontrollen. Den eksisterende `apps/mobile`-app er ikke en del af denne konsolidering.

Andre mulige tilgange blev fravalgt:

1. **Kopier Desk-komponenter til `apps/ui`:** hurtigere første skærm, men beholder to sandheder og gentager den drift, arbejdet skal fjerne.
2. **Læg fælles komponenter i en ny pakke:** kan være relevant senere, men kræver ekstra pakke- og versionsgrænser uden gevinst, når Desk og web kan bygges af samme kilde.

## Arkitektur

### Én renderer, to værter

Desk beholder sin Electron-main, preload og pakning. Browser-buildet bruger samme `App`, providers, visninger, styling, `/chat/stream/v2`-klient og `/ws`-klient. Vite-konfigurationen skiller build-artefakterne (`dist` til Electron og `dist-web` til API-serveren), og browser-entrypointet registrerer PWA-funktioner. Electron-vinduerne for figur og markør forbliver kun Electron-flader.

En lille platformgrænse samler egenskaber som vinduesknapper, lokal terminal, mappevælger, skærmstyring, opdateringer og OS-notifikationer. Komponenter spørger efter en capability og viser kun den tilhørende handling, når værten tilbyder den. Browseren må ikke få stubbe, der ligner fungerende handlinger. Fælles API-handlinger bliver i den eksisterende HTTP-klient.

### Login og tilstand

Desk fortsætter med konfiguration via preload-broen. Browseren bruger samme loginvisning og gemmer serveradresse og token lokalt på den aktuelle origin, så PWA'en kan åbnes igen. Identitet og rettigheder afgøres fortsat af backendens `whoami` og autorisation, aldrig af lokal cache. Browserens Google-login åbner den angivne autorisationsadresse i browseren; Desk bruger fortsat ekstern browser. Tokenfornyelse genbruges. Ved afvist eller udløbet login vises loginvisningen igen, og beskyttede API-kald stopper.

Browser-buildet kalder API'et på samme origin. Det undgår særskilt CORS-konfiguration og bevarer den eksisterende bearer-token og WebSocket-subprotokol. Den gamle webklients `/chat/stream` og dens adaptere genbruges ikke.

### PWA og cache

Browser-buildet leverer manifest, ikoner og en service worker. Den cacher kun versionerede statiske filer og en genindlæselig appskal. API-svar, samtaler, WebSocket-events, godkendelser og streaming-svar caches ikke. Når backend ikke kan nås, vises en tydelig offline-tilstand; send, godkend og andre mutationer skal ikke stå som gennemført. En ny webudgave aktiveres kontrolleret, så åbne streams ikke afbrydes af en tavs reload.

API-serveren serverer ved skiftet `dist-web` i stedet for `apps/ui/dist`. Dens cache-regler bevarer `no-cache` på HTML, manifest og service worker og immutable cache på hash-navngivne aktiver. Auth-middlewareens præcise liste over tilladte lokale UI-filer udvides til de nødvendige PWA-filer og ikoner; den må ikke udvides til API-ruter. Privatlivspolitikken flyttes til browser-buildets public-filer og bevarer sin nuværende offentlige rute.

## Trin og accept

1. **Browser-egnet Desk:** indfør buildmål, platformgrænse og browser-login. Desk-buildet skal fortsat åbne og fungere.
2. **Chatparitet:** browseren skal kunne logge ind, åbne og skifte session, sende og streame via v2, afbryde og styre en kørsel, vise værktøjsresultater og godkendelser samt modtage live-events. Data og hændelser skal svare til Desk for samme konto.
3. **PWA:** installation, ikoner, start-URL, opdatering og offline-tilstand verificeres i en rigtig browser på en HTTPS- eller lokal origin.
4. **Skift:** byg `dist-web` som del af den faktiske server-deployproces, servér det ved `/`, og bekræft login, cache og genindlæsning på den kørende server. Behold en enkel rollback til det tidligere UI-build under skiftet.
5. **Udfasning:** fjern `apps/ui`, den gamle build-vej og henvisninger, når de aftalte webflader er dækket. Desk-funktioner, der kræver lokal OS-adgang, dokumenteres som Desk-funktioner og vises ikke som døde knapper i browseren.

## Verifikation

- Typecheck, lint, relevante Desk-tests og begge builds.
- Browserprøve af login, tokenfornyelse, sessioner, v2-stream, reconnect, godkendelser og offline-fejl.
- Electron-prøve af login, chat og de lokale bridge-handlinger, der berøres.
- Serverprøve af `/`, PWA-filer, privatlivspolitik, auth-grænse og cache-headers både før og efter skiftet.
- Bekræft, at ingen service worker returnerer cached operationelle API-data.

## Kendte grænser

En PWA er ikke en erstatning for Electron-funktioner som lokal terminal, skærmstyring og OS-integration. Fælles kode fjerner drift i renderer og chatprotokol, men backend- og platformsspecifikke fejl kan stadig være forskellige. Den største migrationsrisiko ligger i eksisterende direkte `window.jarvisDesk`-kald og i at browser-login skal overleve genindlæsning uden at åbne beskyttede data før autorisation.
