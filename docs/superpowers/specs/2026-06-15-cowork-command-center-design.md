---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Cowork Command Center — Design

**Version:** 1.0  
**Dato:** 2026-06-15  
**Forfatter:** Jarvis + Bjørn

---

## 1. Problem

Cowork er den eneste krydsforbindelse mellem chat og code mode. Lige nu er cowork et tomt panel uden struktur. Vi mangler et **command center** hvor både jeg og brugeren kan styre alt: todos, approvals, agenter, indstillinger, og app-navigation.

---

## 2. To zoner i cowork

| Zone | Formål | Hvem har adgang |
|------|--------|-----------------|
| **Mission Control** | Fælles arbejdsrum — todos, approvals, agenter, scheduled, plans | Både Jarvis og bruger |
| **Indstillinger** | Konfiguration — account, plugins, permissions, osv. | Primært bruger — Jarvis kan foreslå |

---

## 3. Mission Control

### 3.1 Todos

- Bruger og Jarvis kan oprette, redigere, pause, prioritere
- Todos har TTL (time-to-live) — udløber automatisk hvis ikke fuldført
- Jarvis foreslår todos, bruger godkender
- Status: pending → in_progress → completed / expired

### 3.2 Approvals

- Jarvis foreslår handlinger der kræver godkendelse
- Bruger godkender eller afviser
- Typer: source edit, memory write, mode switch, permission escalation
- Queue-baseret — vises kronologisk

### 3.3 Agents

- Se aktive agenter og deres status
- Se agent-samtaler i realtid
- Bruger kan inddrage sig selv i en agent-samtale
- Member-brugere har ikke adgang til multi-agent (kun owner)

### 3.4 Scheduled tasks

- Reminders, recurring tasks, status
- Både Jarvis og bruger kan oprette
- Viser næste køretid og sidste resultat

### 3.5 Plans

- Spec, implementation, status
- Jarvis foreslår plan, bruger godkender
- Plan-trin kan dispatches til agenter eller udføres inline

---

## 4. Indstillinger — menu-sektioner

### 4.1 Account

- Email, password, sprog
- TOTP setup (QR-kode, seed, status)
- API-nøgler (opret, roter, slet)
- Email-verifikation status

### 4.2 Jarvis

- Model-valg per lane (visible, local, cheap, coding)
- Reasoning effort (fast / medium / deep)
- Mood read-only (kun owner kan justere)
- Diagnostics: tick-kvalitet, adherence, uptime

### 4.3 Memory

- Workspace memory (MEMORY.md, USER.md)
- Jarvis brain (kryds-reference, share_guard status)
- Sanserne Arkiv (seneste indtryk)
- Søg i memory på tværs

### 4.4 Plugins

- Installerede plugins med on/off
- Plugin-markedsplads (git-baseret)
- Approval mode per plugin (auto / ask / deny)
- Skill-scanning status (prompt injection + malware)

### 4.5 Apps

- Connectede apps: Gmail, Calendar, Drive, GitHub, etc.
- Tilføj/fjern app-forbindelser
- App-status og seneste aktivitet

### 4.6 MCP

- Model Context Protocol endpoints
- Tilføj/fjern MCP-servere
- Status per endpoint

### 4.7 Permissions

- Fulde adgang vs. begrænset (per mode)
- Computer-use access (on/off per tool)
- Tool-adgang: vælg hvilke værktøjer der er tilgængelige
- Default permission pr. mode:
  - Chat: samtale-tools kun
  - Code: alle tools (med fuld adgang eller begrænset)
  - Cowork: plans, todos, approval

### 4.8 Workspace

- Filer og mapper
- Kryptering status (encrypted / plain)
- Trust level per workspace
- Disk-forbrug

### 4.9 Kvote

- Nuværende forbrug (chat beskeder, code timer, cowork approvals)
- Tier (Free / Plus / Pro / Owner)
- Opgradering (Stripe integration)
- Ordblinde/blinde: Plus gratis

### 4.10 Sprog

- Dansk, engelsk, auto-detection
- Sprog fra registrering bruges som default
- Jarvis tilpasser sig automatisk hvis bruger skifter sprog

### 4.11 Tema

- Mørkt, lyst, høj kontrast
- Tilgængelighed: store knapper, stor tekst

---

## 5. Jarvis kan navigere appen indefra

Når brugeren har brug for hjælp, kan Jarvis:

| Handling | Tool | Eksempel |
|----------|------|---------|
| Åbn preview panel | `open_ui_panel` | "Lad mig vise dig filen" |
| Luk panel | `open_ui_panel action=close` | "Lukker preview" |
| Åbn file tree | `open_ui_panel panel=file_tree` | "Lad mig vise hvor filen ligger" |
| Highlight fil | `open_ui_panel panel=file_tree highlight=[...]` | "Her er auth-filen" |
| Skift mode | `request_app_action switch_to_code_mode` | "Vi skal bruge code mode" |
| Anmod fuld adgang | `request_app_action request_full_access` | "Jeg skal bruge fuld adgang" |
| Åbn indstilling | `open_ui_panel panel=settings` | "Lad mig vise dig TOTP-opsætningen" |

---

## 6. Sammenligning med Claude Desktop og Codex Desktop

| Feature | Claude Desktop | Codex Desktop | Jarvis (nu) | Jarvis (mål) |
|---------|---------------|---------------|--------------|----------------|
| Settings UI | Minimal | TOML-baseret | ❌ | ✅ Cowork side-menu |
| Plugin-styring | On/off | On/off + approval | Delvist | ✅ Fuldt plugin-panel |
| Account | Ingen | Ingen | ❌ | ✅ Email, TOTP, API |
| Model-valg | Ingen | Model + effort | Delvist | ✅ Per-lane model-valg |
| Project trust | Ingen | Per-mappe | ❌ | ✅ Workspace trust |
| Computer-use | Ingen | Approval per tool | ❌ | ✅ Permission per tool |
| Marketplace | Ekstra repos | Git-baserede | ❌ | ✅ Plugin-markedsplads |
| Read-aloud | Ingen | Enabled | ❌ | ✅ Stemme-mode |
| Browser | Ingen | Chrome-integration | ❌ | Fremtidig |
| Memory | Ingen | Claude-mem | ✅ Brain | ✅ Memory menu |
| Todos | Ingen | Ingen | ✅ Todos | ✅ Mission Control |
| Approvals | Ingen | Ingen | ❌ | ✅ Approval queue |
| Agents | Ingen | Ingen | ✅ Agent dispatch | ✅ Agent panel |

---

## 7. Edge cases

| Situation | Håndtering |
|-----------|------------|
| Bruger åbner cowork første gang | Vis velkomst + forklaring af zoner |
| Member-bruger åbner indstillinger | Nogle sektioner skjult (TOTP, API keys) |
| Jarvis foreslår mode-skift i chat mode | `request_app_action` → bruger godkender → app skifter |
| Bruger afviser permission-escalation | Jarvis fortsætter i begrænset mode |
| Broen er nede | Indstillinger vises fra cache, MC er read-only |
| Member prøver at åbne Jarvis diagnostics | Adgang nægtet — owner only |

---

## 8. Testplan

| Test | Hvad |
|------|------|
| `test_cowork_opens_from_chat` | Cowort tilgængelig i chat mode |
| `test_cowork_opens_from_code` | Cowork tilgængelig i code mode |
| `test_mc_todos_crud` | Opret, rediger, slet todo |
| `test_mc_approvals_queue` | Approval vises og kan godkendes |
| `test_settings_account` | Account-sektion viser korrekt data |
| `test_settings_permissions` | Permission-valg gemmes og håndhæves |
| `test_jarvis_navigates_app` | `open_ui_panel` + `request_app_action` virker |
| `test_member_cannot_see_owner_settings` | TOTP, API keys skjult for members |

---

## 9. Filer der skal ændres eller oprettes

| Fil | Handling |
|-----|----------|
| `apps/jarvis-desk/src/components/CoworkPanel.tsx` | Ny — hovedkomponent |
| `apps/jarvis-desk/src/components/MissionControl.tsx` | Ny — MC zone |
| `apps/jarvis-desk/src/components/SettingsPanel.tsx` | Ny — indstillingszone |
| `apps/jarvis-desk/src/stores/coworkStore.ts` | Ny — state management |
| `core/routes/cowork.py` | Ny — API endpoints for cowork |
| `core/routes/mc.py` | Ny — Mission Control API |

---

## 10. Hvad IKKE ændres

- Chat mode (samtale forbliver samtale)
- Code mode (terminal og filer forbliver lokale)
- Eksisterende open_ui_panel flow
- Eksisterende request_app_action flow
- Jarvis' brain og memory-system
