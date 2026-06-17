# Code-mode Git + Workstation + Dependency-Doctor + Auto-Update — Design

**Dato:** 2026-06-17
**Status:** Godkendt af Bjørn 2026-06-17

## Formål

Gøre jarvis-desk code-mode reelt brugbar på tværs af roller og maskiner, og gøre
selve app'en selvhjulpen ved install og opdatering. Fire moduler oven på
eksisterende fundament (`github_connector`, `operator_bash`, `autoUpdate.ts`-stub,
`/chat/git/*`-endpoints landet samme dag).

## Beslutninger (Bjørn 2026-06-17)

- **PR-mekanisme:** Begge — GitHub-OAuth-connector (API) primært, `gh` CLI som fallback.
- **Dependency-doctor:** Bredt sæt (git, gh, node, ripgrep) på Linux/Mac/Windows.
- **Auto-update:** In-app prompt → ja → opdatér + selv-genstart.
- **Workstation-git:** Owner + members, fuldt fra start (rolle-gated).

## Rolle-regler (gælder hele spec'en)

- **Server-repoet** (`{kind:'container', root:'repo'}`): KUN owner (Bjørn). Members må aldrig.
- **Workstation** (`{kind:'workstation', root}`): brugerens EGEN maskine via dennes operator-bro.
  Owner og members må begge — gated til egen bro (`{_user_id: uid}`-routing, jf.
  `reference_operator_bridge_uid_routing`). Members rammer aldrig server-repoet.
- Git-actions kræver: et git-repo til stede (commit) og/eller forbundet GitHub-plugin (PR).

---

## Modul 1 — Git-eksekverings-lag (rolle-aware, server + workstation)

### Ansvar
Ét service-lag der udfører git-operationer mod enten server-repoet (subprocess) eller
en brugers workstation (via `operator_bash`), med ens svar-form.

### Operationer
`status`, `commit_all`, `create_branch`, `push`, `create_pr` (PR delegeres til Modul 2).

### Arkitektur
- Nyt: `core/services/git_actions.py` — `run_git_action(op, target, uid, **kw) -> dict`.
  - `target = {"kind": "container"|"workstation", "root": str}`.
  - **container/'repo'** (owner-gate): kør `git -C <repo>` via `subprocess` (genbrug
    `_commit_all_sync`/`_create_pr_sync`-logik fra `chat.py`, flyttet hertil).
  - **workstation**: kør `git -C <root> …` via `operator_bash` på brugerens bro:
    `execute_tool("operator_bash", {"command": "...", "_user_id": uid})`. Parse stdout/rc.
- `apps/api/jarvis_api/routes/chat.py`: erstat de owner-only endpoints med routede:
  - `POST /chat/git/commit-all {target}` og `POST /chat/git/create-pr {target, title?, body?}`.
  - Rolle-gate: hvis `target.kind=='container'` → owner-only; `workstation` → ejeren af broen (uid).

### Fejlhåndtering
- Intet git-repo → `{"status":"no_repo"}` (UI viser hint, ikke fejl).
- Bro ikke forbundet (workstation) → `{"status":"bridge_not_connected"}` (502-agtig, UI-besked).
- Git-fejl → `{"status":"error","detail":...}` (trunkeret stderr).

### Test
`tests/test_git_actions.py`: mock `subprocess.run` (container) og `execute_tool`
(workstation); verificér routing, rolle-gate, commit/no-change/fejl-stier.

---

## Modul 2 — PR-oprettelse (OAuth-API + gh-fallback)

### Ansvar
Opret en pull request for det aktuelle workspace, primært via GitHub-API med brugerens
OAuth-token, ellers via `gh` CLI.

### Flow
1. `commit_all` (Modul 1) hvis der er uncommittede ændringer.
2. Branch: hvis på default → `create_branch jarvis/work-<sha>`.
3. `push` (Modul 1): på workstation bruger brugerens egne git-creds; på server serverens.
4. PR:
   - **Primært:** `github_connector.create_pr(uid, owner, repo, head, base, title, body)`
     via `https://api.github.com/repos/{owner}/{repo}/pulls` med `get_fresh_token(uid,"github")`.
     `owner/repo` udledes fra `git remote get-url origin` (parse SSH+HTTPS-former).
     `base` = default-branch (origin/HEAD → fallback main).
   - **Fallback:** intet token → `gh pr create --base <base> --head <branch> --fill` der hvor
     repoet er (subprocess for server, `operator_bash` for workstation).
5. Returnér `{"status":"ok","url":...}` eller ærlig fejl (`github_not_connected` + `gh` mangler).

### Arkitektur
- `core/services/github_connector.py`: tilføj `create_pr(...)` + `GITHUB_CREATE_PR` til
  tool-defs hvis relevant. Genbrug eksisterende `_API`/token-mønster.
- Branch/remote-parsing i `git_actions.py`.

### Test
`tests/test_github_connector.py` (udvid): mock token + `requests`/urllib → verificér
korrekt API-kald + url-parsing af remote. PR-fallback testes i `test_git_actions.py`.

---

## Modul 3 — Dependency-doctor (git, gh, node, ripgrep · Linux/Mac/Windows)

### Ansvar
Detektér manglende eksterne værktøjer, vis brugeren hvad der mangler, og tilbyd at
installere dem for brugeren — så app'en virker "før git er installeret".

### Arkitektur (Electron main + renderer)
- `electron/depDoctor.ts`: `detect(): {tool, present, version?, installable}[]` for
  `git, gh, node, ripgrep`. Detektion: `which`/`command -v` (Linux/Mac), `where` (Windows).
- `electron/depInstall.ts`: `install(tool): {ok, log}` per-OS:
  - **Linux:** detektér pkg-manager (apt/dnf/pacman) → `pkexec <pm> install -y <pkg>`.
  - **Mac:** `brew install <pkg>` (hvis brew mangler → vis instruktion, installér ikke brew selv).
  - **Windows:** `winget install <id>` (`--accept-source-agreements`).
- IPC: `dep:detect`, `dep:install` (preload bridge). Renderer: `DependencyCard.tsx` viser
  manglende værktøjer + "Installér"-knap pr. værktøj + live-log; og features der kræver et
  manglende værktøj viser inline "Installér X" i stedet for at fejle.

### Graceful degradation
- Code-mode workstation-git: hvis `git` mangler → env-felt/knap viser "Installér git" (Modul 3-kort)
  i stedet for at kalde Modul 1.
- App'en starter og kører chat uanset manglende værktøjer.

### Test
`depDoctor.test.ts` / `depInstall.test.ts`: mock `child_process` → verificér detektion-parsing
og korrekt-konstrueret install-kommando pr. OS. **Installerer aldrig rigtigt i test.**

---

## Modul 4 — Auto-update (in-app prompt → opdatér + genstart)

### Ansvar
App'en opdager nye versioner, spørger brugeren in-app, og ved ja: downloader + genstarter sig selv.

### Arkitektur
- `npm i electron-updater`.
- `package.json` build: `"publish": [{"provider":"github","owner":"Nickless-cmd","repo":"jarvis-v2"}]`.
- CI (jf. `reference_jarvis_desk_release_ci`): sørg for at `latest.yml` (+ `.deb`/blockmap)
  uploades til GitHub-release.
- `electron/autoUpdate.ts` (erstat no-op-stub): brug eksplicitte events i stedet for
  `checkForUpdatesAndNotify`:
  - `autoUpdater.autoDownload = false`.
  - `on('update-available', info)` → IPC `update:available` → renderer `UpdateCard.tsx`.
  - Bruger "Opdatér" → IPC `update:download` → `autoUpdater.downloadUpdate()`.
  - `on('download-progress')` → IPC `update:progress`. `on('update-downloaded')` →
    IPC `update:ready` → kort "Genstart for at opdatere" → `quitAndInstall()`.
  - Config-gated (`enabled`, `channel`, `checkIntervalHours`).
- `main.ts`: kald `initAutoUpdate(cfg)` (allerede wiret som no-op).

### Test
`autoUpdate.test.ts`: mock `electron-updater` → verificér event→IPC-mapping + at
`downloadUpdate`/`quitAndInstall` kun kaldes ved bruger-ja.

---

## Byggerækkefølge

1. **Modul 1** (git-lag, rolle-aware) — fundament for resten.
2. **Modul 2** (PR via API + gh-fallback) — bygger på 1.
3. **Modul 4** (auto-update) — uafhængig, stillads findes, hurtig.
4. **Modul 3** (dependency-doctor) — størst cross-OS-flade, til sidst.

## Sikkerhed / governance

- Outadvendte handlinger (push, PR, app-opdatering, dep-install via sudo/pkexec) sker
  KUN ved brugerens eget klik i app'en (per-handling-godkendelse).
- Server-repoet er strengt owner-only. Members isoleres til egen bro.
- Ingen secrets i repoet; GitHub-token via krypteret `oauth_store` (eksisterende).

## Out of scope (v-næste)

- Auto-installation af Homebrew på Mac (kun instruktion).
- Selv-opdatering af operator-broen.
- PR-review/merge fra app'en (kun oprettelse).
