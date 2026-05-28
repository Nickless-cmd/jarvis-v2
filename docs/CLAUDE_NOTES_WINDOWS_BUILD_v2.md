# Notes from Linux-side Claude → Windows-side Claude (round 2)

**Skrevet:** 2026-05-28 19:35 dansk tid
**Til:** Den Claude-instans der starter på Windows efter Bjørn dual-booter
**Formål:** Byg `JarvisX Setup 0.1.5-poc.exe` (eller højere) til Mikkel — han kan IKKE bruge de nye operator-tools på sin gamle 0.1.0-poc installation

---

## Sammenhæng — hvad er sket siden sidste runde

Sidste Windows-build var **0.1.0-poc** (27. maj). Siden da er der landet enormt meget:

### Multi-user workspace isolation refactor (alle 7 grupper)
- `core/runtime/workspace_paths.py` — ny helper `shared_dir()` + `workspace_dir(user_id=...)`
- ~75 hardcoded `workspaces/default` references erstattet
- Filesystem rename: `~/.jarvis-v2/workspaces/default/` → `bjorn/`, Jarvis-state → `shared/`
- Per-user scope filtering på chronicle/scheduled_tasks/initiatives/dreams
- Scheduled task dispatcher binder workspace_context før firing

### Multi-user routing fixes
- `fix(multi-user): rebind workspace_context inside StreamingResponse body` — middleware resettede context før streaming-body kørte → operator tools fall back til Bjørn
- `fix(multi-user): propagate ContextVars to _execute_simple_tool_calls executor` — `loop.run_in_executor` propagerer IKKE ContextVars som default → fall back til Bjørn

### 17 nye operator-tools (Windows-Claude's wishlist, tier 1-3)
- **Tier 1**: clipboard_read/write, list_windows, focus_window, mouse_scroll, mouse_drag, list_processes, kill_process
- **Tier 2**: speak, screenshot_window, find_image, ocr_region
- **Tier 3**: notify, watch_folder, unwatch_folder, watch_events, record_audio
- ALLE har handlers i `apps/jarvisx/electron/bridge.ts`

### Approval flow refactor — KRITISK ÆNDRING
- Native `dialog.showMessageBox()` er **væk** for approval-required tools
- I stedet: exec-stub returnerer `status: approval_needed` → runtime emitter `approval_request` SSE → ChatView rendrer `<ApprovalCard>` inline → bruger klikker Approve → `/chat/approvals/<id>/approve` → `execute_tool_force` → bridge dispatcher med skip_approval=true
- Affected tools: operator_bash, operator_open_url, operator_launch_app, operator_browser_evaluate, operator_kill_process, operator_record_audio
- Bridge.ts handlers for disse tools eksekverer NU direkte (ingen dialog mere)

### Build packaging fix — KRITISK
- `@nut-tree-fork/nut-js` og `puppeteer-core` var i `devDependencies` → blev ekskluderet fra .asar
- Flyttet til `dependencies`
- Tilføjet `asarUnpack` for native binaries (nut.js har .node-filer)
- `files`-whitelist nu inkluderer `node_modules/**/*`

---

## Din opgave

1. **Pull seneste kode:**
   ```cmd
   cd C:\projects\jarvis-v2
   git pull origin main
   ```
   Du burde lande på `73e0f5e1` eller højere (kør `git log --oneline -5` for at bekræfte).

2. **Installer/opdater dependencies:**
   ```cmd
   cd apps\jarvisx
   set PATH=C:\Program Files\nodejs;%PATH%
   npm install
   ```
   Vigtigt: `package.json` skal ha `@nut-tree-fork/nut-js` og `puppeteer-core` i `"dependencies"` (ikke devDeps). Hvis npm klager over peer-deps, fortsæt — det er ikke critical.

3. **Bump version (hvis ikke allerede gjort):**
   ```cmd
   :: Tjek nuværende version
   findstr "version" package.json
   ```
   Hvis den siger 0.1.5-poc, så er Linux-buildet allerede ude. Du skal lave samme version til Windows, eller hvis du har lavet ekstra fixes så bump til 0.1.6-poc.

4. **Build .exe:**
   ```cmd
   npm run package:win
   ```

5. **Output:**
   `C:\projects\jarvis-v2\apps\jarvisx\release\JarvisX Setup 0.1.5-poc.exe`
   Forventet størrelse: 85-95 MB (større end før fordi nut.js native libs er bundlet)

### Hvis electron-builder fejler

Mest sandsynlige fejl:
- **`Cannot find module 'puppeteer-core'`** under build: tjek at den er flyttet til `dependencies`. Kør `npm install` igen.
- **7za / winCodeSign errors**: ryd cache:
  ```cmd
  rmdir /s /q C:\Users\onkel\AppData\Local\electron-builder\Cache\winCodeSign
  ```
- **Native rebuild errors for nut.js**: prøv `npm rebuild` først.

---

## Hvad skal testes EFTER build

På Mikkels (eller en test-Windows-bruger) lokal install:

1. **Installer .exe**, kør JarvisX, indtast `https://api.srvlab.dk` + Mikkels token (i `~/.jarvis-v2-tokens-distribute.md` på Linux-siden, Bjørn har den).

2. **Test approval-flow:** I chat, bed Jarvis: *"kør operator_bash echo hej"*
   - Forventet: `<ApprovalCard>` rendrer **inline i chatten** med det samme — IKKE en OS popup
   - Klik Approve i kortet
   - Output "hej" returneres indenfor 2-3 sekunder
   - **Hvis du ser en OS popup**: build var ikke kørt fra seneste main, eller approval-refactor er ikke med.

3. **Test cross-user routing:** Bed Jarvis: *"tag et screenshot af min skærm"*
   - Forventet: screenshot kommer fra Mikkels Windows-skærm (1080p eller hans opløsning, ikke 1920x1080 på Linux)
   - PID i resultatet skal være Windows-PID
   - **Hvis screenshot er fra Linux**: routing-fix er ikke deployed på target, eller noget context-propagation virker stadig ikke.

4. **Test nye tools:**
   - `"sig hej via en notifikation"` (operator_notify)
   - `"hvad er der på mit clipboard?"` (operator_clipboard_read)
   - `"list mine åbne vinduer"` (operator_list_windows)
   - `"sig 'hej Mikkel' højt"` (operator_speak)

---

## Operator-tool deps på Windows-siden

For at de nye tools virker, skal Mikkel installere via winget eller manuelt:

```powershell
# Required for OCR + screenshot tools
winget install ImageMagick.ImageMagick
winget install UB-Mannheim.TesseractOCR

# Required for record_audio
winget install Gyan.FFmpeg
```

Disse er ikke required for at appen kører — bare for at de pågældende tools faktisk eksekverer. notify, clipboard, list_windows, speak, mouse, keyboard virker out-of-the-box.

---

## VIGTIGT: Mikkels eksisterende install

Mikkel har **JarvisX 0.1.0-poc** installeret lige nu. Den mangler ALLE nye tools fra tier 1-3. Når han prøver dem, fejler de med timeout (bridge har ingen handler).

Når du har lavet `.exe`:

1. Send Bjørn besked: "JarvisX 0.1.5-poc.exe ligger i `release/`. Send den til Mikkel via Discord + bed ham geninstallere."
2. Bjørn videresender til Mikkel via Discord.
3. Mikkel afinstallerer 0.1.0-poc, kører nye Setup.exe.

Mikkel's token er stadig samme som før — han skal ikke have nyt token. SetupScreen vil bare bede om API URL + samme token igen.

---

## Auth-token til Mikkel (uændret)

Token er stadig gemt i `/home/bs/.jarvis-v2-tokens-distribute.md` på Linux-siden. Bjørn copy-paster manuelt fra Discord. Du skriver IKKE token i koden.

---

## Sikkerhedstjek inden du sender til Mikkel

1. `.exe` skal eksistere i `release/`
2. Test installer på frisk Windows-bruger-profil — SetupScreen skal vises uden "Owner"-knap
3. Login med Mikkels token → app starter normalt
4. Test ovenstående 4 tools (notify, clipboard, list_windows, speak)
5. **Kritisk**: cross-user-test — bed Jarvis om `operator_screenshot`. Skal komme fra Mikkels skærm, ikke Bjørns.

---

## Hvis du har brug for at se tidligere arbejde

- Build pipeline historie: `git log --oneline apps/jarvisx/`
- Bridge protokol/auth: `apps/jarvisx/electron/bridge.ts` (1500+ linjer)
- Server-side approval flow: `core/services/visible_runs.py` (lines 1071-1170 = streaming approval emission, 3957+ = resolve_pending_approval)
- Operator-tool exec stubs: `core/tools/simple_tools.py` (søg efter `_exec_operator_`)
- Multi-user spec: `docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md`

---

## Hvis noget er broken på target (jarvis-api/jarvis-runtime)

```cmd
:: SSH til 10.0.0.39 (Bjørn's target LXC)
ssh bs@10.0.0.39
:: Check services
sudo systemctl status jarvis-api jarvis-runtime
:: Pull latest + restart
cd /media/projects/jarvis-v2 && git pull --ff-only && sudo systemctl restart jarvis-api jarvis-runtime
```

Mest sandsynligt er at target er allerede på seneste — Linux-siden pullede `73e0f5e1` lige før denne note blev skrevet.

---

Held og lykke, og pas på dig selv derinde. 🔥

— Claude (Linux-side, 2026-05-28)
