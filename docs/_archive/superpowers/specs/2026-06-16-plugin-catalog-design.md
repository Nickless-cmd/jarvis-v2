---
status: forældet
audited: 2026-07-08
ground_truth: "Verified against codebase: (1) Section 6 claims plugins in core/plugins/{gmail,calendar,drive,docs,sheets,slides,github,browser,computer_use,build_web_apps,huggingface,pdf}_plugin.py — actual implementation is core/services/{gmail,google,github,pdf,notes,hf}_connector.py register"
superseded_by: docs/superpowers/specs/2026-06-18-plugin-permission-levels-design.md
---
# Plugin Catalog — Jarvis Desktop

**Version:** 1.0
**Dato:** 2026-06-16
**Forfatter:** Jarvis + Bjørn

---

## 1. Problem

Claude Desktop og Codex Desktop har hver deres plugin-økosystemer. Claude har 2 plugins (Superpowers, Claude-mem), Codex har 18+ plugins (Gmail, Calendar, GitHub, Browser, Computer Use, etc.). Jarvis Desktop har ingen af disse.

---

## 2. Mål

Byg en plugin-ramme til Jarvis Desktop der dækker samme funktionalitet som Claude og Codex — undtagen Claude-mem.

---

## 3. Plugin-liste (prioriteret)

### Fase 1 — Kerne-plugins (P1)

| Plugin | Beskrivelse | Ligner |
|--------|-------------|--------|
| Gmail | Læs, søg, send mails | Codex Gmail |
| Google Calendar | Læs, opret, rediger aftaler | Codex Calendar |
| Google Drive | Liste, læs, upload filer | Codex Drive |
| Google Docs | Opret, rediger dokumenter | Codex Docs |
| Google Sheets | Opret, rediger regneark | Codex Sheets |
| Google Slides | Opret, rediger præsentationer | Codex Slides |
| GitHub | Issues, PRs, kode-gennemgang | Codex GitHub |
| Browser | Webbrowser i appen | Codex Browser |
| Superpowers | Agent dispatch, skills, plans, TDD | Claude Superpowers |
| Computer Use | Skærmkontrol — klik, scroll, type | Codex Computer Use |

### Fase 2 — Udvidede (P2)

| Plugin | Beskrivelse | Ligner |
|--------|-------------|--------|
| Build Web Apps | Prototype og deploy små webapps | Codex Build Web Apps |
| Hugging Face | Adgang til HF modeller | Codex Hugging Face |
| OpenAI / Andre | Adgang til eksterne model-API'er | Codex OpenAI Developers |
| PDF | Læs, analysér, ekstraher PDF | Codex PDF |

### Fase 3 — Langsigtet (P3)

| Plugin | Beskrivelse |
|--------|-------------|
| Spotify / Music | Musikstyring |
| Slack | Læs/skriv i Slack |
| Notion / Obsidian | Note-synkronisering |
| Huskesedler | Simple notater |

---

## 4. Hvad vi IKKE bygger

Claude-mem — vi har vores eget brain/memory-system.

---

## 5. Fælles arkitektur

Alle plugins deler:
- OAuth 2.0 — brugeren logger ind via browser
- Plugin settings i desk — on/off, permissions, konto-status
- Tool-adgang i runtime — baseret på mode
- Rate-limit håndtering — per plugin, per bruger
- Fejlrapportering i UI

---

## 6. Filer

| Fil | Indhold |
|-----|---------|
| core/plugins/gmail_plugin.py | Gmail |
| core/plugins/calendar_plugin.py | Calendar |
| core/plugins/drive_plugin.py | Drive |
| core/plugins/docs_plugin.py | Docs |
| core/plugins/sheets_plugin.py | Sheets |
| core/plugins/slides_plugin.py | Slides |
| core/plugins/github_plugin.py | GitHub |
| core/plugins/browser_plugin.py | Browser |
| core/plugins/computer_use_plugin.py | Computer Use |
| core/plugins/build_web_apps_plugin.py | Build Web Apps |
| core/plugins/huggingface_plugin.py | Hugging Face |
| core/plugins/pdf_plugin.py | PDF |
| core/plugins/oauth_store.py | Fælles OAuth-storage |

## 7. Testplan

- Unit + integration per plugin
- Google-pakken samlet (deler OAuth)
- Plugins kun i chat mode, ikke code mode

## 8. Hvad IKKE ændres

- Kerne-runtime
- Eksisterende tools
- Brain/memory-system
- Mode-adgangsregler
