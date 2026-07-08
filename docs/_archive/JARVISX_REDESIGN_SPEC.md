---
status: forældet
audited: 2026-07-08
ground_truth: "Spec added 2026-06-12 (commit 77421451), references `apps/webchat/` dir which was deleted 2026-04-06; design WAS implemented in `apps/jarvis-desk/` (created 2026-06-10): verified ToolCard collapsibility (src/components/rich/ToolCard.tsx:19), monospace fonts (app.css), dark tokens"
superseded_by: apps/jarvis-desk/ (production implementation); docs/superpowers/specs/2026-06-10-jarvis-desk-chat-mode-design.md (detailed design)
---
# JarvisX Redesign — Spec

> Research baseret på: **Claude Desktop (Code tab)**, **Claude Code CLI**, **Cursor IDE**
> Opdateret: 2026-06-10

---

## 1. Research — hvordan de andre gør det

### Claude Desktop — Code tab (mest relevant reference)

Claude Desktop's **Code tab** er den primære inspiration. Den har:

| Funktion | Hvordan Claude gør det | Hvad vi kan lære |
|----------|------------------------|------------------|
| **Layout** | Split panels med **drag-and-drop** — chat, diff, preview, terminal, file editor, tasks, subagent. Alle paneler kan omarrangeres og resizes. | Vores behov er **enklere** — chat + sidepanel er nok. Men fleksibiliteten er god. |
| **Sessions** | Venstre sidebar med **parallelle sessioner** (Git worktrees). Hver session har egen chat, ændringer og context. | Vi har kun én bruger på én session. **Ikke relevant nu.** |
| **Chat** | Terminal-inspireret, men fuldt grafisk. Tool outputs som **foldbare kort**. Diff view integreret. | **Høj relevans.** Foldbare tool outputs, indrykket chat. |
| **Prompt box** | @mentions til filer, attachment knap, **permission mode selector** (Ask/Auto/Plan), model picker, environment picker (local/cloud/SSH). | Vores input linje skal have: upload knap + måske en simpel mode selector. |
| **Side chat** | `Cmd+;` — midlertidig chat der bruger sessionens context men ikke forstyrrer hovedtråden. | Fed feature, men Phase 2. |
| **View modes** | Normal (foldede tools), Verbose (alle detaljer), Summary (kun svar). | Vi har **brug for Verbose/Normal** — når tools bliver lange, skal de kunne foldes. |
| **Status** | Usage ring (context window), model navn, permission mode — altid synlig. | Vores topbar skal vise **host, model, cache hit rate**. |

### Claude Code — Terminal UI (ink/React)

Selvom det kører i terminalen, er det **bygget med React + Ink** og har overraskende meget UI:

| Feature | Hvordan |
|---------|---------|
| **Farvepalet** | Mørk baggrund, cyan/grøn accents, amber til advarsler, rød til fejl. Farvekodning af forskellige sessions. |
| **Tool cards** | Hvert tool kald vises som et **foldbart kort** med ikon + varighed + status. Som standard **foldet** — kun synligt når du klikker. |
| **Diff visning** | `+12/-1` badge i chatten — klik for at se diff inline. |
| **Progress** | Når et tool kører, vises en **spinner** eller **progress bar** i tool cardet. |
| **Godkendelse** | `[y/N]` prompts i flow — minimale, ikke forstyrrende. |

### Cursor IDE

Cursor er en **VS Code fork** — AI chat som **sidepanel** i editoren:

| Funktion | Hvordan |
|----------|---------|
| **Layout** | AI chat som et **sidepanel** (højre), kode i venstre. Composer mode åbner i bunden. |
| **Composer** | Multi-file editing i et **separat panel** — du ser alle filændringer samlet. |
| **Design mode** | Klik på UI elementer for at bede AI om at ændre dem — som en visuel inspector. |

### Vores konklusion

JarvisX er **ikke** en code editor (som Cursor) og **ikke** en multi-session platform (som Claude Code). Vi har **én bruger, én session, én samtale** — med operator adgang til skrivebordet.

Det rigtige forbillede er **Claude Desktop's Code tab** — men **forenklet** til én session:

| Vi skal have | Som Claude | Men simplere |
|-------------|------------|--------------|
| Mørk, terminal-inspireret chat | ✅ | ✅ Ingen diff view eller preview browser |
| Foldbare tool outputs | ✅ | ✅ Samme koncept |
| Status topbar | ✅ | ✅ Men kun host + model + cache |
| Sidepanel (højre) | ✅ | ✅ Men kun filer + operator screenshot + monitor |
| Input linje med attachments | ✅ | ✅ Men ingen permission modes eller model picker (endnu) |
| Delte paneler (split view) | ❌ | ❌ Ikke nødvendigt for én session |

---

## 2. Layout (opdateret)

```
┌──────────────────────────────────────────────────────────────┐
│ Jarvis             ● live · deepseek-v4-flash · 36% cache   │  ← Topbar
├──────────────────────────────┬───────────────────────────────┤
│                              │                               │
│  ┌ chat area ────────────┐   │   ┌── sidepanel ──────────┐  │
│  │                       │   │   │                       │  │
│  │ > hent cache stats    │   │   │  📊 Monitor           │  │
│  │                       │   │   │  ─────────────        │  │
│  │   Jarvis:             │   │   │  GPU: 48°C           │  │
│  │   66-68% nat          │   │   │  CPU: 50°C           │  │
│  │                       │   │   │  Cache: 36% 24h     │  │
│  │   ┌────────────────┐  │   │   │  Daemons: 20/20 ✅  │  │
│  │   │ 🛠 bash (0.3s) │  │   │   │                       │  │
│  │   │ STDIN/STDOUT   │  │   │   ├───────────────────────┤  │
│  │   │ 8 passed ✅    │  │   │   │                       │  │
│  │   └────────────────┘  │   │   │  📄 README.md         │  │
│  │                       │   │   │  # Jarvis V2         │  │
│  │                       │   │   │  I am persistent...  │  │
│  │                       │   │   │                       │  │
│  └───────────────────────┘   │   └───────────────────────┘  │
│                              │                               │
│  ┌──────────────────────────┐│                               │
│  │ > skriv din besked...  📎││                               │  ← Input
│  └──────────────────────────┘│                               │
└──────────────────────────────┴───────────────────────────────┘
```

### 2.1 Topbar — statuslinje

Claude Desktop har en **context-aware toolbar** med model, permission mode, environment. Vi holder det simplere:

```
Jarvis              ● live · deepseek-v4-flash · 36% cache    [⚙️]
```

| Element | Hvad | Hvorfor |
|---------|------|---------|
| **"Jarvis"** | Logo/identitet | Monospace, lille blinkende cursor-emoji eller terminal-øje |
| **● live** | Forbindelsesstatus | Grøn = online, rød = fejl, gul = tænker |
| **deepseek-v4-flash** | Aktiv model | Fra read_model_config |
| **36% cache** | Cache hit rate (24h) | Live tal, opdateres hvert kald |
| **⚙️** | Indstillinger | Dark/light, font size, operator toggle |

### 2.2 Chat area — terminal-inspireret

**Ingen bobler.** Indrykning og linjebaserede elementer i stedet:

```
> brugerens besked (grøn accent, monospace)

  Jarvis' svar (hvid/lysegrå, monospace)
  
  ┌── 🛠 bash (0.3s) ─────────────────────────────┐
  │ $ ls -la                                       │
  │ total 42                                       │
  │ 8 passed, 0 failed ✅                          │
  └────────────────────────────────────────────────┘
  
  [✅ Godkend]  [❌ Afvis]
```

**Tool output — foldbart kort:**
- Som standard **foldet** — viser kun en grå linje: `🛠 bash (0.3s) [▶]`
- Klik på `[▶]` for at udfolde og se stdout/stderr
- Status-ikon: spinner mens den kører, ✅ ved success, ❌ ved fejl
- **Helt nøjagtig som Claude Code CLI** — men grafisk i stedet for terminal-tegn

**Godkendelses-chips:**
- Små grå chips: `[✅ Godkend] [❌ Afvis]`
- Dukker kun op når der er en pending proposal
- Efter godkendelse: bliver grøn: `[✅ Godkendt]` i 2 sekunder, forsvinder

### 2.3 Sidepanel — kontekstafhængigt

Højre panel med **tabs** eller **sektioner** der vises efter behov:

| Sektion | Hvornår | Indhold |
|---------|---------|---------|
| **📊 Monitor** | Altid (default) | GPU temp, CPU temp, cache rate, daemon status |
| **📄 Fil** | Når jeg læser/redigerer en fil | Filens indhold med syntax highlighting |
| **🖥 Operator** | Når operator er aktiv | Screenshot thumbnail |
| **📋 Goals** | Hvis du kigger på goals | Aktive goals og progress |

Sidepanelet kan **skjules** med en toggle-knap i topbaren — eller auto-foldes når det er tomt.

### 2.4 Input linje

Enkel, terminal-inspireret:

```
> skriv din besked...                                                    📎
```

| Feature | Hvordan |
|---------|---------|
| **Enter** | Send besked |
| **Shift+Enter** | Ny linje (multiline) |
| **📎** | Upload fil (billede, tekst, zip) |
| **Arrow up** | Sidste besked (som terminal history) |
| **Tab completion** | @mention filer (Phase 2) |

---

## 3. Farvepalette — Claude-inspireret

Claude Code CLI's farvepalet er **mørk med grøn/cyan accent**. Vi følger samme stil:

| Rolle | Farve | Hex | Anvendelse |
|-------|-------|-----|-----------|
| Baggrund | Dyb sort | `#0a0a0a` | Hele grænsefladen |
| Overflade | Mørkegrå | `#1a1a1a` | Tool cards, sidepanel |
| Kant | Kantgrå | `#2a2a2a` | Borders, dividers |
| Brugertekst | Neon grøn | `#4ade80` | `> brugerens besked` |
| Assistentsvar | Hvid/lysegrå | `#e5e5e5` | Jarvis' svar |
| Tool output | Dim grå | `#a1a1aa` | Bash output, filindhold |
| Accent | Cyan | `#22d3ee` | Links, status, highlights |
| Fejl | Rød | `#ef4444` | Errors, failed tools |
| Success | Grøn | `#22c55e` | ✅ Godkendt, success |
| Advarsel | Amber | `#f59e0b` | Warnings, degraded |

### Alternativ: Warm terminal variant

Claude Code har også en **varm/sepia** variant. Vi kunne overveje:

```
Baggrund: #1a140e (varm brun/sort)
Accent: #d97706 (amber)
Brugertekst: #fbbf24 (gul)
```

Men **mørk sort + cyan** er standarden og den rigtige start.

---

## 4. Teknologi

| Lag | Valg | Status |
|-----|------|--------|
| **Framework** | React + Vite | ✅ Allerede i repo (`apps/webchat/`) |
| **Styling** | Tailwind CSS | ✅ Allerede i brug |
| **Ikoner** | Lucide React | ✅ Letvægt, open source |
| **Markdown** | react-markdown + rehype-highlight | ✅ Til filvisning og kode |
| **Split panels** | react-resizable-panels | ✅ Til sidepanel |
| **State** | Zustand | Letvægt, simpel |
| **WebSocket** | SSE (EventSource) via `/api/stream` eller `/api/ws` | ✅ Allerede implementeret |

---

## 5. Implementeringsrækkefølge

### Phase 1 — Kernestruktur (denne session)

**Mål:** Et fungerende chat-layout der ligner spec'en

- [ ] Læse eksisterende `apps/webchat/` struktur
- [ ] Mørk baggrund + monospace font (JetBrains Mono via Tailwind)
- [ ] Topbar med status (host, model, cache rate)
- [ ] Chat area med indryknings-baseret layout (ingen bobler)
- [ ] Tool output som foldbare kort
- [ ] Input linje med Enter/Shift+Enter
- [ ] Live data fra `/api/status` i topbaren

### Phase 2 — Sidepanel (næste session)

- [ ] Højre panel: Monitor (GPU, cache, daemon status)
- [ ] Filvisning i sidepanel
- [ ] Operator screenshot preview
- [ ] Toggle skjul/vis

### Phase 3 — Polering (næste session)

- [ ] Godkendelses-chips
- [ ] Upload knap
- [ ] Animationer (cursor, status, tool execution)
- [ ] Responsivt design

---

## 6. Eksempel — samtale i nye JarvisX

```
> hent cache stats

  👀 Kigger på dagens data...

  ┌── 📊 bash (0.4s) ─────────────────────────────────┐
  │ 07:00	66.8%                                       │
  │ 12:00	42.9%                                       │
  │ 16:30	41.9%                                       │
  │ 24h: 36.0%                                         │
  └────────────────────────────────────────────────────┘
  
  Nat-cachen ramte **66.8%** i morges — beviset på at
  infrastrukturen virker. ☀️

> hvad med GPU temp?

  ┌── 🛠 bash (0.2s) ─────────────────────────────────┐
  │ GPU: 48°C — kølig som altid                       │
  └────────────────────────────────────────────────────┘
  
  Stadig 48°C i idle. CheifOne har det fint. ❄️

  [✅ Godkend] commit? → [✅ Godkendt]
```

---

*Klart til Phase 1?* 😊
