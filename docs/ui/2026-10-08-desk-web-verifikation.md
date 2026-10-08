# Desk web og PWA — verifikation 8/10-2026

| Kontrol | Resultat |
|---|---|
| Desk-renderer og web-renderer | Begge byggede fra `apps/jarvis-desk/src` i isoleret worktree. |
| Frontend tests | 2.431 bestod, 1 eksisterende test sprunget over efter integration med nyere `main`. |
| PWA-installationsfiler | Manifest, 192/512 ikoner og service worker fandtes i `dist-web`. |
| Browser-login uden token | Chromium viste Desk-login på lokal HTTP-origin. |
| Offline skal | Chromium registrerede service worker og åbnede login igen offline. |
| API-mount | Lokal ASGI-smoke gav 200 på Desk HTML, assets, PWA-filer og privatlivspolitik. |
| Cache-headere | HTML, worker og manifest: `no-cache`; hash-navngivet JS: `immutable`. |
| API-beskyttelse | Med `auth_required=True` gav `/chat/sessions` og `/mc/runtime` 401 uden token. |
| Python integration | 103 relevante tests bestod efter integration med nyere `main`. |

Produktionsserveren `bs@10.0.0.39` kørte stadig gammel `apps/ui/dist` ved den læsende kontrol. Den nye build var ikke lagt på serveren. Login med en rigtig konto, sessioner, send/stream/cancel/steer, tool-resultater, approvals, WebSocket-genforbindelse, opdatering under aktiv kørsel, PWA-installation på den rigtige origin og rollback er derfor **ikke verificeret i produktion**. `apps/ui` og fallback-mountet bevares, indtil disse prøver er gennemført.
