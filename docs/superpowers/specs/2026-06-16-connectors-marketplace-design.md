# Connectors / Marketplace — Jarvis Desktop

**Dato:** 2026-06-16 · **Forfatter:** Bjørn + Claude · **Status:** design (godkendt visuelt)

Bygger på `docs/superpowers/specs/2026-06-16-plugin-catalog-design.md` (kataloget).
Dette spec dækker **rammen + UI + v1 (GitHub)** — ikke hver enkelt connector.

---

## 1. Mål
En connector/plugin-oplevelse i jarvis-desk som Codex/Claude Desktop, men **privat**
(egen OAuth, data går Jarvis↔provider direkte). Brugeren kan **forbinde, slå til/fra
og slette** connectors. Marketplace bor i **cowork**. Tom session foreslår 2-3 apps.

## 2. Allerede bygget (backend-fundament — live, testet)
- `core/services/oauth_store.py` — per-bruger **krypteret** token-hvælv (AES-256-GCM,
  brugerens keyring-DEK). Kryptografisk isolation bevist. `save/get/has/revoke/list`.
- `core/services/oauth_flow.py` — provider-config (github/google), signeret `state`
  (anti-CSRF + binder uid), `build_authorize_url`, `exchange_code`.
- `apps/api/.../routes/oauth.py` — `GET /api/oauth/{provider}/start` (auth) +
  `/callback` (public). Live-verificeret. GitHub+Google creds i runtime.json.

## 3. Det der mangler

### 3.1 Backend — connectors-registry
**Ny:** `core/services/connectors.py` (katalog) + `apps/api/.../routes/connectors.py`:
- `GET /api/connectors` → liste: `{id, name, desc, icon, kind: "oauth"|"local",
  category, connected: bool, enabled: bool}` for den indloggede bruger. `connected`
  = `oauth_store.has_token`; `local` (computer-use/browser) er altid "aktiv".
- `POST /api/connectors/{id}/enabled` `{enabled}` → slå til/fra (behold token).
  Lagres pr. bruger i runtime_state `connector_enabled`.
- `DELETE /api/connectors/{id}` → `oauth_store.revoke_token` + ryd enabled-flag (GDPR).
- Connector-tools registreres scopet til **mode + permission-motoren (Spor A)** og kun
  hvis `connected && enabled`. (v1: GitHub-tools — issues/PRs.)

### 3.2 Desk — Sidebar bliver mode-bevidst (FJERNER dobbelt-panel)
**Rod:** `CoworkView`→`CoworkZones` har en EGEN `cowork-rail` ved siden af det app-
niveau `Sidebar`. To paneler = grimt (især Linux-build). **Fix:** når
`surface === 'cowork'`, viser `Sidebar` **cowork-menuen** (med ikoner) i stedet for
session-listen; `cowork-rail` i `CoworkZones` fjernes — zonen drives nu fra Sidebar
via den eksisterende `coworkZone`-pub/sub (`src/lib/coworkZone.ts`).
- Menu-punkter (lucide-ikoner): **Mission Control** (`LayoutDashboard`), **Marketplace**
  (`Blocks`/`Puzzle`), **Indstillinger** (`Settings`).
- Filer: `Sidebar.tsx` (betinget render sessions vs cowork-menu), `CoworkZones.tsx`
  (drop intern rail, behold zone-state via `onZone`), `CoworkView.tsx` (uændret grid).

### 3.3 Desk — Marketplace-zone
Ny `src/components/cowork/MarketplacePane.tsx` (zonen "marketplace"):
- **"Forbundet"-sektion** øverst: forbundne connectors m. grøn ●&nbsp;forbundet + **⋯**-
  menu → *Slå fra* / *Afbryd & slet*.
- **"Alle connectors"-grid:** kort = badge-ikon + navn + kort desc + status-pill
  (`Forbind` / `forbundet` / `Aktiv`). Klik `Forbind` → `GET /api/oauth/{id}/start` →
  åbn `authorize_url` i system-browser (Electron `shell.openExternal`) → poll
  `/api/connectors` til `connected`.
- Søgefelt (filtrér). Kategorier (Google/Udvikling/Produktivitet) — P2, kan udelades v1.
- Genbruger/erstatter eksisterende `AppsSection`/`McpSection`/`PluginsPanel` hvor relevant.

### 3.4 Desk — greeting-widget (tom session)
`ChatView` tom-state (ingen beskeder):
- **Tids-bevidst greeting** (`src/lib/greeting.ts`, ren+testbar): lokal time →
  🌅 Godmorgen (5-10) · ☀️ God dag (10-14) · 🌆 God eftermiddag (14-18) ·
  🌙 Godaften (18-23) · 🌙 godnat-tone (23-5). **Roterende tilfældig** under-linje fra
  en lille pulje pr. tidsrum. Presence-ring tonet efter tidspunkt.
- **Connector-forslag:** 2-3 *ikke-forbundne* connectors (badge + navn + desc + Forbind)
  + **"Flere apps →"** (skifter til cowork + zone=marketplace). Skjules når alt forbundet.

## 4. Privatliv (kernen)
Tokens per-bruger krypterede (gjort). Connector-tools scopet til mode + Spor A. Slet =
revoke hos provider-token + wipe (GDPR). En brugers connectors/tokens er usynlige for
andre. Egen OAuth → ingen tredjepart (OpenAI) i data-stien.

## 5. Nice-to-haves (Bjørns green light — tag dem med hvor naturligt)
Tids-bevidst random greeting + presence-tint (§3.4) · ikoner i panel-menuen (§3.2) ·
lille tal-badge "N forbundet" på Marketplace-rail-punktet · subtil "nyligt forbundet ✓"-
toast efter callback (`oauth.connected`-event).

## 6. Connector-faser
**v1 (denne spec):** ramme + Sidebar-mode-fix + Marketplace-zone + greeting + **GitHub**
(lodret bevis, ende-til-ende). **v2:** Google-pakken (deler OAuth) · Browser/Computer Use
(wrap eksisterende `operator_*`). **v3+:** resten af kataloget.

## 7. Test
- Backend: `connectors.py` registry (status pr. bruger), enable/disable/delete, tool-
  gating (kun connected+enabled). pytest.
- Desk: `greeting.ts` (tids-buckets + random-pulje, deterministisk via injiceret `now`),
  Sidebar cowork-mode render (sessions vs menu), MarketplacePane (kort-states, ⋯-menu),
  greeting-widget (forslag skjules når forbundet). vitest + tsc.
- Build: `npm run package:linux` + bump version + dpkg (HUSK version-bump, ellers no-op).

## 8. Hvad IKKE ændres
Kerne-runtime · brain/memory · mode-adgangsregler · den eksisterende OAuth-backend (bygget).
