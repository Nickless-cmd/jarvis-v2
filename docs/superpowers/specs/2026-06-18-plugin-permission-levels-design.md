---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Plugin Permission Levels Design

**Dato:** 2026-06-18
**Status:** Design — klar til implementering

## Problem

Hver plugin (Gmail, Calendar, Drive, GitHub osv.) har forskellige niveauer af adgang. Lige nu er det binært: enten har jeg adgang, eller også har jeg det ikke. Der mangler **granulerede permissions**, så brugeren kan vælge præcis hvor meget adgang hver plugin skal have.

## Permission Levels (generisk model)

Hvert plugin implementerer op til 4 niveauer:

| Niveau | Navn | Hvad det giver | Eksempel (Gmail) |
|--------|------|----------------|------------------|
| 1 | **Read** | Læse, søge, liste | Læse mails, søge i indbakke |
| 2 | **Modify** | Alt fra Read + ændre eksisterende data | Slette/trash, markere som spam/læst, organisere i mapper |
| 3 | **Admin** | Alt fra Modify + ændre indstillinger | Blokere afsendere, oprette labels, skrive regler |
| 4 | **Full Control** | Alt inkl. destruktive handlinger | Slette labels, ændre videresendelse, slette konti |

## Plugin-specifikke niveauer

### Gmail
| Niveau | Scopes | Handlinger |
|--------|--------|------------|
| Read | `gmail.readonly` | Læse, søge, liste |
| Modify | `gmail.modify` | + slette, spam/unspam, arkivér, labels |
| Admin | `gmail.settings.basic` | + blokér afsendere, oprette filtre |
| Full Control | `gmail.settings.sharing` | + videresendelse, delegation, sletning |

### Google Calendar
| Niveau | Scopes | Handlinger |
|--------|--------|------------|
| Read | `calendar.readonly` | Læse events, liste |
| Modify | `calendar.events` | + oprette, ændre, slette egne events |
| Admin | `calendar` | + dele kalendere, ændre indstillinger |

### Google Drive
| Niveau | Scopes | Handlinger |
|--------|--------|------------|
| Read | `drive.readonly` | Læse filer, søge |
| Modify | `drive.file` | + oprette, ændre, slette egne filer |
| Full Control | `drive` | + slette andres, dele, ændre permissions |

### GitHub
| Niveau | Scopes | Handlinger |
|--------|--------|------------|
| Read | `repo` (read-only) | Læse issues, PRs, kode |
| Modify | `repo` | + oprette issues, kommentere |
| Admin | `repo` + `admin:repo_hook` | + merge, administrere |

## UI — hvordan brugeren vælger

I desktop-appens **Settings → Konto** vises hver plugin med en lille pil/nedad. Når brugeren klikker, folder permissions-sektionen ud:

```
📧 Gmail ───────────────── [⚠ Mangler scopes]
  ○ Read (læse, søge)
  ● Modify (slette, spam, organisere) ← valgt
  ○ Admin (blokér, filtre)
  ○ Full Control (alt)

📅 Calendar ────────────── [✅ Forbundet]
  ○ Read
  ● Modify (oprette/ændre) ← valgt
  ○ Admin

📁 Google Drive ─────────── [❌ Ikke forbundet]
  [Forbind Google Drive]
```

Når brugeren vælger et niveau, trigger det OAuth-flowet med de relevante scopes.

## Implementation

1. **Tilføj `permission_level` til plugin-registrering** i backend
2. **Hvert plugin definerer sine niveauer** med tilhørende OAuth-scopes
3. **Frontend renderer niveauerne** dynamisk fra backend
4. **OAuth-flowet anmoder** kun om de scopes der svarer til valgt niveau
5. **Runtime tjekker** at værktøjskald ikke overskrider det givne niveau

## Fremtid

- Midlertidig elevation ("giv mig Modify i 5 minutter")
- Per-session permission ("denne samtale må slette mails")
- Owner override (Bjørn kan altid bede om Full Control uanset indstilling)
