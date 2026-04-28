# 📝 Changelog — Jarvis V2

> Versionshistorik og ændringer for Jarvis V2.

---

## [2.0.0] — 2026-04-28

### ✨ Nyt

- **Fuld dokumentationssuite** — 13 dokumenter dækkende alt fra brugervejledning til API reference
- **MIT Licens** — Projektet er nu officielt open source
- **GitHub repository** — Kildekode offentligt tilgængelig på github.com/Nickless-cmd/jarvis-v2

### 🏗️ Arkitektur

- **Heartbeat system** — 15-minutters refleksionscyklus (Sense → Reflect → Act)
- **Multi-agent system** — Council, sub-agents, og specialiserede roller
- **Eventbus arkitektur** — Intern event-driven kommunikation
- **Memory tiers** — Hot, warm, cold lagring med semantic search

### 🔌 Integrationer

- **Home Assistant** — Smart home kontrol
- **Discord** — Chat integration
- **Telegram** — Besked levering
- **Email** — Send/modtag emails
- **Ollama** — Lokal AI inference
- **Webhooks** — HTTP callbacks

### 🛠️ Tools

- 60+ værktøjer til rådighed:
  - Filhåndtering (read, write, edit)
  - Shell commands (bash, sessions)
  - Web (fetch, search, scrape)
  - Git (commit, push, diff)
  - Database (SQL queries)
  - Kalender (events)
  - Og meget mere...

### 📊 Monitoring

- **Mission Control dashboard** — jarvis.srvlab.dk:8400
- **Real-time status** — /api/status endpoint
- **Daemon monitoring** — 20 interne daemons
- **Event logging** — Komplet eventbus historik

### 🧠 Kognitive funktioner

- **Selvrefleksion** — Chronicle entries, dreams, reflections
- **Beslutningssporing** — Decision adherence tracking
- **Mood/affect system** — Emotionel baseline
- **Learning system** — Skills.md og agent observations

---

## [1.0.0] — 2026-04-14

### 🎉 Første release

- Grundlæggende Jarvis arkitektur
- Heartbeat daemon
- Basic tool system
- SQLite database
- Web API

---

## 📅 Kommende (Roadmap)

### v2.1.0

- [ ] Voice integration (wake word "Hey Jarvis")
- [ ] Webcam vision system
- [ ] Flere AI providers
- [ ] Improved memory consolidation

### v2.2.0

- [ ] Multi-user support
- [ ] Role-based access control
- [ ] Plugin system
- [ ] Mobile app

---

## 📝 Versionering

Vi følger [Semantic Versioning](https://semver.org/):

- **MAJOR** — Brudende ændringer
- **MINOR** — Ny funktionalitet (bagudkompatibel)
- **PATCH** — Bug fixes (bagudkompatibel)

---

*For detaljerede ændringer, se git log:*
```bash
git log --oneline
```
