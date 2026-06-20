# Mobil auto-updater — Design

**Dato:** 2026-06-20
**Status:** Godkendt design, klar til implementeringsplan
**Vision-reference:** `2026-06-18-jarvis-mobile-companion-v2-vision.md` §2 (Auto-updater)

Del-projekt C af de resterende mobil-features (rækkefølge: A+B ✓ → **C auto-updater** →
D chatboble). Backend (FastAPI) + mobil (React Native/Expo bare). Fjerner den manuelle
adb-bygge/installer-smerte: efter denne version OTA-opdaterer appen sig selv.

## Mål

Appen detekterer en nyere version, viser en banner med versionsnoter, og — ved tryk —
henter APK'en (med download-progress i appen) og fyrer systemets install-dialog.
Bootstrap: DENNE version (med updateren) installeres manuelt én gang via adb; derefter
OTA.

## Bærende valg (afklaret med Bjørn)

1. **Kilde:** eget srvlab.dk-endpoint (manifest + APK), fuldt kontrolleret. IKKE GitHub
   releases (ingen CI nødvendig).
2. **Install-måde:** in-app download (`expo-file-system`) + install-intent
   (`expo-intent-launcher` + `getContentUriAsync`) — glat, men kræver de moduler +
   `REQUEST_INSTALL_PACKAGES`-tilladelse.
3. **Auth:** opdaterings-endpoints er auth-scopede (appen har allerede et token).

## Server (backend)

`apps/api/jarvis_api/routes/mobile_update.py` (NY, auth-scopet via `_current_user`):
- `GET /mobile/latest` → læs `latest.json` fra opdaterings-mappen, returnér
  `{version, version_code, notes, filename}`. Hvis filen mangler → `{}` (ingen opdatering).
- `GET /mobile/download` → `FileResponse(apk_path, media_type="application/vnd.android.package-archive")`
  af APK'en angivet i `latest.json["filename"]`. FastAPI's `FileResponse` streamer via
  anyio-threadpool → fryser IKKE `--workers 1` (jf. async-blocking-lektien). 404 hvis
  filen mangler.

**Opdaterings-mappe:** `~/.jarvis-v2/mobile/` (læses via en konstant/helper, ikke
hardcodet sti spredt ud). Indeholder `latest.json` + `jarvis-mobile-<versionCode>.apk`.
Mit build-step (i implementerings-planen) kopierer APK'en derhen + skriver `latest.json`.

Registrér routeren i `apps/api/jarvis_api/app.py` (som de øvrige routere).

## Klient (mobil)

**Nye Expo-moduler (config-plugin autolinket, ingen håndlavet native kode):**
- `expo-application` — `Application.nativeBuildVersion` = installeret Android `versionCode`.
- `expo-file-system` — download m. progress; `getContentUriAsync` → content:// URI via
  Expos egen FileProvider (ingen manuel FileProvider-config).
- `expo-intent-launcher` — `startActivityAsync` til install-intent.

**`src/lib/appUpdate.ts` (REN, testbar):**
- `compareVersion(installedVc: number, manifest: { version_code?: number }): boolean`
  — true hvis `manifest.version_code > installedVc`.
- `checkForUpdate(config: ApiConfig, installedVc: number): Promise<UpdateManifest | null>`
  — fetch `/mobile/latest` (auth-header); hvis `compareVersion` true → returnér manifest,
  ellers null. Fejl/malformet → null (stille).
- Type `UpdateManifest = { version: string; version_code: number; notes: string; filename: string }`.

**`src/lib/installApk.ts` (TYND, native-wiring):**
- `downloadAndInstall(config, manifest, onProgress): Promise<void>`:
  - `FileSystem.createDownloadResumable('/mobile/download' m. auth-header, dest, {}, onProgress)`
    → download til `documentDirectory + filename`.
  - `const uri = await FileSystem.getContentUriAsync(localPath)`
  - `await IntentLauncher.startActivityAsync('android.intent.action.VIEW', { data: uri,
    flags: 1 /* GRANT_READ_URI_PERMISSION */, type: 'application/vnd.android.package-archive' })`
  - Fejl → kast (UI viser fejl-toast).

**`src/components/UpdateBanner.tsx` (NY):** vises når en opdatering er fundet — viser
`version` + `notes` + knap "Opdatér" (→ download m. progress-bjælke) + "Senere" (skjul).
Glas-look i tråd med §3-temaet. `accessibilityRole`-knapper.

**`src/App.tsx` (MOD):** app-niveau (altid monteret mens logget ind, som PresenceHost):
- Ved opstart + når `AppState` → 'active': `checkForUpdate(config, Application.nativeBuildVersion)`.
- Hvis ikke-null → vis `UpdateBanner` med manifestet. "Opdatér" → `downloadAndInstall`.

**`android/app/src/main/AndroidManifest.xml` (MOD):** tilføj
`<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>`. Android
beder brugeren om "tillad installation af ukendte apps" første gang (system-flow).

## Dataflow

1. App i forgrund → `checkForUpdate` → `GET /mobile/latest` → `{version_code: 28}`.
2. `Application.nativeBuildVersion` = 27 → `compareVersion(27, {28})` = true → banner.
3. Tryk "Opdatér" → `GET /mobile/download` (auth) → APK til `documentDirectory`
   (progress-bjælke) → `getContentUriAsync` → install-intent → system-dialog → bruger
   bekræfter → in-place opgradering (samme debug-nøgle).

## Fejlhåndtering

- `/mobile/latest` fetch fejler / timeout → null → ingen banner (stille, prøv igen ved
  næste foreground).
- `latest.json` mangler server-side → `{}` → ingen opdatering.
- Download fejler → fejl-toast, behold nuværende app.
- `REQUEST_INSTALL_PACKAGES` ikke givet → system viser indstillings-prompt; bruger
  aktiverer → install fortsætter.

## Testplan (jest)

- `appUpdate.test.ts`: `compareVersion` (nyere/ældre/samme/manglende version_code);
  `checkForUpdate` med mocket fetch (nyere → manifest, samme → null, fetch-fejl → null,
  malformet JSON → null).
- `installApk` + intent er tynde native-wiring → mockes (expo-file-system/intent-launcher
  i jest.setup); ingen dyb logik at teste.
- Eksisterende ~94 jest-tests skal forblive grønne (App.test får evt. mock for de nye
  Expo-moduler + checkForUpdate).
- Backend: `tests/test_mobile_update_routes.py` (FastAPI TestClient): `/mobile/latest`
  (manifest-form + tom når fil mangler) + `/mobile/download` (FileResponse 200 / 404).

## Filer

**Nye:** `apps/api/jarvis_api/routes/mobile_update.py`, `tests/test_mobile_update_routes.py`;
mobil `src/lib/appUpdate.ts`, `src/lib/installApk.ts`, `src/components/UpdateBanner.tsx`
(+ `appUpdate.test.ts`).
**Modificerede:** backend `apps/api/jarvis_api/app.py`; mobil `src/App.tsx`,
`android/app/src/main/AndroidManifest.xml`, `package.json` (3 deps), `jest.setup.js`
(mocks for de nye Expo-moduler).

## Ikke i scope (YAGNI)
- GitHub-release-CI (valgt srvlab.dk-endpoint i stedet).
- OTA JS-bundle-opdatering (expo-updates) — kan ikke levere native ændringer (D kræver
  native), så vi opdaterer hele APK'en.
- Baggrunds-download / silent install (kræver device-owner; sideloaded app kan ikke).
- Rollback / flere kanaler (single-user, én kanal).
