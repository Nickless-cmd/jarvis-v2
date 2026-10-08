# Desk web og PWA — verifikation 8/10-2026

| Kontrol | Resultat |
|---|---|
| Desk-renderer og web-renderer | Begge byggede fra `apps/jarvis-desk/src` i isoleret worktree. |
| Frontend tests | 2.434 bestod, 1 eksisterende test sprunget over på den endelige integrationscommit. |
| PWA-installationsfiler | Manifest, 192/512 ikoner og service worker fandtes i `dist-web`. |
| Browser-login uden token | Chromium viste Desk-login på lokal HTTP-origin. |
| Offline skal | Chromium registrerede service worker og åbnede login igen offline. |
| API-mount | Lokal ASGI-smoke gav 200 på Desk HTML, assets, PWA-filer og privatlivspolitik. |
| Cache-headere | HTML, worker og manifest: `no-cache`; hash-navngivet JS: `immutable`. |
| API-beskyttelse | Med `auth_required=True` gav `/chat/sessions` og `/mc/runtime` 401 uden token. |
| Python integration | 112 relevante tests bestod på den endelige integrationscommit. |
| Produktionsbyg og genstart | `main` på `bs@10.0.0.39` blev opdateret til `436bab8b3`; `scripts/build_desk_web.sh` byggede `dist-web`; `scripts/genstart_sikkert.sh jarvis-api` fandt ingen aktive kørsler, og servicen blev `active`. |
| Produktions-HTTP | `https://api.srvlab.dk/`, `/manifest.webmanifest`, `/sw.js` og `/privatlivspolitik.html` gav 200. HTML, manifest og worker havde `no-cache`; `/chat/sessions` og `/mc/runtime` gav 401 uden token. |
| Produktionsbrowser | Desk-login blev vist i Chromium på `https://api.srvlab.dk/`. |
| Indlogget produktionsbrowser | Bjørn loggede ind og sendte `hey`; Desk viste 41 samtaler og Jarvis' svar i den nye webklient. Efter genindlæsning blev login, samtaleliste og valgt samtale gendannet. En ældre samtale med værktøjsvisning kunne åbnes, og den seneste samtale kunne vælges igen. Ingen browserfejl blev rapporteret i fanens konsol. |
| Fallback på produktionsværten | I isoleret deployment-worktree blev `dist-web` flyttet midlertidigt til side, og `ui_build_dir` valgte den eksisterende `apps/ui/dist`. Begge stagingændringer blev gendannet. Den aktive service blev ikke skiftet til fallback. |

Den indloggede samtale bekræfter login, sessionsliste, send og modtaget svar. Genindlæsning bekræfter, at kontoen og samtalen gendannes. Streamingens forløb, cancel/steer, nye tool-resultater, approvals, WebSocket-genforbindelse under afbrud, tokenfornyelse, opdatering under aktiv kørsel og PWA-installation på den rigtige origin er **endnu ikke særskilt verificeret i produktion**. En egentlig live rollback er heller ikke gennemført. `apps/ui` og fallback-mountet bevares, indtil de kritiske prøver er gennemført.
