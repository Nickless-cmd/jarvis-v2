# Teams — Design Spec

**Status:** Godkendt design (2026-06-20). Klar til implementerings-plan.

**Mål:** Indbyggede delte team-samtaler + delt team-workspace i desktop- og mobil-appen, så Jarvis selv bliver det multi-user-lag vi i dag bruger Discord til. "Væk fra Discord" = deling bliver eksplicit i kernen i stedet for at låne en ekstern chat-tjeneste.

**Relaterer til:** V2-vision §5 (`docs/superpowers/specs/2026-06-18-jarvis-mobile-companion-v2-vision.md`), multi-user-sikkerhed (#154 per-bruger-scope), code-mode/git-infrastruktur, device-presence + proactive_router.

---

## 1. Kernekoncepter

- **Team** = navngivet beholder med medlemmer + ét delt git-workspace + MANGE delte sessioner (Discord-server-agtigt, ikke én gruppe-chat).
- **Team-session** = en chat-session med `team_id` sat. Synlig for alle teamets medlemmer på alle deres enheder.
- **Privat session** = `team_id` NULL (som i dag) — fuldstændig urørt af denne feature.
- **Enhver indlogget bruger kan oprette et team** og bliver automatisk **owner (admin)** for sit eget team. (En global "member" kan altså eje de teams hen selv laver.) Team-oprettelse er derfor en baseline-evne i `permission_engine` — IKKE owner-gatet. Skaberen repræsenteres BÅDE som `teams.owner_user_id` OG som en `team_members`-række med `team_role='owner'` (så medlemskabs-opslag er ensartede).
- **Jarvis er conversational deltager** — han kan oprette teams og invitere via tools, og han svarer i team-sessioner når han kaldes (MVP) eller selv vurderer det er relevant (v2).

---

## 2. Datamodel

Tre nye SQLite-tabeller (kun SQLite — **intet dual-store** som users.json):

```sql
CREATE TABLE teams (
    team_id        TEXT PRIMARY KEY,        -- uuid
    name           TEXT NOT NULL,
    owner_user_id  TEXT NOT NULL,           -- skaberen = admin
    created_at     TEXT NOT NULL,
    workspace_path TEXT NOT NULL            -- ~/.jarvis-v2/teams/<team_id>/workspace
);

CREATE TABLE team_members (
    team_id    TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    team_role  TEXT NOT NULL,               -- 'owner' | 'editor' | 'viewer'
    joined_at  TEXT NOT NULL,
    PRIMARY KEY (team_id, user_id)
);

CREATE TABLE team_invites (
    token         TEXT PRIMARY KEY,         -- ugætteligt
    team_id       TEXT NOT NULL,
    invited_email TEXT NOT NULL DEFAULT '', -- gemmes ALTID (muliggør email-onboarding i fase 2)
    invited_by    TEXT NOT NULL,
    status        TEXT NOT NULL,            -- 'pending' | 'accepted' | 'revoked' | 'expired'
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL
);
```

**Sessioner får ét felt:** `chat_sessions.team_id TEXT DEFAULT NULL`.

### 2.1 Den load-bearing sikkerhedsgrænse

I dag er sessions-adgang *implicit*: en bruger ser en session hvis hen selv har postet i den (`session_search._user_scope_clause` + `chat_messages.user_id`). Vi tilføjer ÉN regel:

> En bruger må se en session hvis **(A)** hen har skrevet i den (eksisterende privat-regel) **ELLER (B)** sessionen har et `team_id` og brugeren er medlem af det team.

- Per-bruger-scopingen fra #154 er **fuldstændig urørt for private sessioner**. Hullet åbnes *kun* for sessioner der eksplicit har `team_id`, og kun for teamets medlemmer.
- `cross_user_share_guard` udvides til at vide: "inde i en team-session er cross-user-beskeder tilladt" — ellers ville den blokere medlemmer i at se hinandens beskeder.
- Roller håndhæves serverside (defense-in-depth), ikke kun i UI: owner kan invitere/kicke/slette; editor kan skrive + oprette sessioner + uploade; viewer er read-only.

---

## 3. Team-workspace (git + auto-commit)

- **Sti:** `~/.jarvis-v2/teams/<team_id>/workspace/` — git-init ved team-oprettelse. En **tredje workspace-art** ved siden af `workspaces/<user>/` (personlig) og code-mode container/workstation.
- **`workspace_paths` får `team_dir(team_id)`** ved siden af `workspace_dir(user)`.
- **Adgang:** kun teamets medlemmer (gatet på `team_members`). Delt git-repo → **ingen per-bruger-kryptering** (#137 gælder kun personlige workspaces). Kryptering-at-rest på host-niveau = deferet.
- **Auto-commit:** hver app-upload eller Jarvis-fil-skrivning i team-workspacet → automatisk git-commit med den handlende bruger som author og en beskrivende besked (`"upload rapport.pdf"` / `"jarvis edit src/auth.py"`). Giver rollback + revisionsspor ("hvem lagde hvad ind hvornår").
- **Sessioner bruger det** via code-mode pegende på team-workspacet — genbruger eksisterende code-mode + git-diff-panel.

---

## 4. Invite & medlemskab (hybrid identitets-model)

**Fase 1 (MVP):** invite kobler kun **eksisterende** brugere. **Fase 2 (deferet):** email kan onboarde nye personer (token bærer allerede `invited_email`, så ingen omskrivning).

**Roller:** owner / editor / viewer. MVP håndhæver **owner + editor**; viewer/read-only bygges sidst.

**Invite-flow:**
1. Team-owner (eller Jarvis på dennes vegne) vælger eksisterende bruger **eller** indtaster email.
2. `team_invites`-token genereres (med `invited_email`).
3. Token leveres ad **to kanaler samtidig:**
   - **Live in-app:** hvis modtagerens enhed er online (presence) → `proactive_router` pusher et kort *"X inviterede dig til Team Y [Acceptér]"*.
   - **Email:** `jarvis@srvlab.dk`-tool'et sender invite-link med samme token.
4. Modtageren åbner → **accept-skærm** med samtykke-tekst:
   > "Forbindelsen er sikker og krypteret. Det her er en delt samtale — del ikke fortrolige oplysninger; det er dit eget ansvar."
5. Accept → `team_members`-række (default rolle **editor**). I MVP afvises token pænt hvis modtageren ikke allerede har en konto ("bed admin oprette dig først").

---

## 5. Jarvis som conversational deltager

### 5.1 Native tools (som geo-tools'ene)
- `create_team(name)` — opretter team + git-workspace, opretteren bliver owner.
- `invite_to_team(team, email_or_user)` — genererer + leverer invite.
- `list_teams()` — brugerens teams + medlemmer.
- **Verificér-trin:** fordi invite sender email/notifikation (udadvendt handling) bekræfter Jarvis med brugeren før udførelse — *"Jeg opretter Team Engineering og inviterer mikkel@… — okay?"* → ja → udfør.

### 5.2 Hvornår svarer Jarvis i en team-session?
Ét beslutningspunkt: **`should_jarvis_respond(besked, kontekst) → bool`**.
- **MVP (summoned baseline):** funktionen = *"er @jarvis nævnt, eller er det et svar på Jarvis?"*. Forudsigeligt, billigt (intet run pr. menneske-besked).
- **v2 (interjection-motor, deferet):** funktionens indmad skiftes til en billig-model-dommer (OllamaFreeAPI) der vurderer om Jarvis bør byde ind — eksponeret som per-team-toggle "Lad Jarvis blande sig selv". Med tærskel + cooldown (som R2-gaten) så han ikke afbryder. Samme rør, intet redesign.

### 5.3 @mentions
Parses fra beskedtekst (regex `@navn`, slås op mod `team_members`):
- **@jarvis** → ind i `should_jarvis_respond` → run.
- **@medlem** → `proactive_router.route(medlem)` → notifikation *"X nævnte dig i Team Y · Session Z"* på medlemmets bedste enhed (ren genbrug af presence).

---

## 6. UI

### 6.1 Desktop (jarvis-desk) — fuld admin
- **Venstre panel:** ny **"Teams"-sektion** under sessions-listen. Hvert team foldbart → viser sine sessioner. "+ Nyt team"-knap.
- **Team-session:** normal chat (genbruger ChatView/CodeView) + medlems-presence-prikker i header, "delt"-indikator, **@mention-autocomplete** i composer (`@` → dropdown med medlemmer + `@jarvis`).
- **Team-styring** (panel i Settings eller egen visning): opret, inviter (vælg bruger / email), medlemsliste m. roller, kick, forlad.
- **Invite-modtagelse:** accept-kort med samtykke-tekst.

### 6.2 Mobil (companion) — deltagelse
- Samme **Teams-sektion** i sessions-listen.
- Deltag: åbn team-session, chat, @mention, **modtag @mention-notifikationer** via FCM.
- Acceptér invites via notifikation.
- **Opret team via Jarvis** virker overalt; tung admin-UI (kick/roller) bor på desktop i MVP (spec §5: "desktop = admin, mobil = deltagelse").

---

## 7. MVP-afgrænsning

**I MVP (bevis modellen ende-til-ende):**
- 3 tabeller + `chat_sessions.team_id` + scoping-reglen (A eller B)
- Team-CRUD backend + Jarvis-tools (create/invite/list) med verificér-trin
- Invite: kun eksisterende brugere (hybrid fase 1), begge leverings-kanaler
- Roller: owner + editor håndhævet
- Team-workspace git-repo + auto-commit ved upload
- Trigger: @jarvis (summoned) + @person notify via presence
- Desktop: Teams-sidebar + sessioner + opret/inviter + medlemsliste + accept-kort + @mention-autocomplete
- Mobil: Teams-sektion + deltag + @mention-FCM + accept invite + opret-via-Jarvis

**Deferet til v2+ (skrevet ind så det ikke glemmes):**
- 🧠 Interjection-motoren ("Lad Jarvis blande sig selv")
- 📧 Email-onboarding af nye (ikke-eksisterende) brugere (hybrid fase 2)
- 👁 viewer/read-only-håndhævelse overalt
- 🔇 mute/unmute, per-team permission-overstyringer
- 🔗 Discord-kanal ↔ team-bro
- 🔐 Kryptering-at-rest på team-repos

---

## 8. Test

- **Backend (pytest):** team-CRUD; scoping-reglen A/B (privat urørt, team-medlem ser, ikke-medlem afvist); invite-token livscyklus (pending→accepted/expired/revoked); auto-commit-author; rolle-håndhævelse serverside (editor kan ikke kicke, viewer kan ikke skrive).
- **Klient (vitest/jest):** @mention-parser; Teams-sidebar-state (fold/udfold, team→sessioner); accept-flow; invite-kort-rendering.
- **Sikkerhed:** eksplicit test at en ikke-medlem IKKE kan læse en team-session (regressionsværn på #154-grænsen).

---

## 9. Implementerings-rækkefølge (til planen)

Selv MVP'en deles i ~3 under-faser med check-in mellem hver (som geolocation):
1. **Backend-fundament:** tabeller + migration + `team_dir` + scoping-regel A/B + cross_user_share_guard-udvidelse + serverside rolle-håndhævelse + tests.
2. **Jarvis-tools + invite-flow:** create/invite/list-tools + verificér-trin + token-livscyklus + email-tool + proactive_router-invite-kort + auto-commit-hook.
3. **App-UI:** desktop Teams-sidebar + team-styring + @mention-autocomplete; mobil Teams-sektion + deltag + @mention-FCM + accept.

Hver fase skal efterlade et kørende, testbart system.
