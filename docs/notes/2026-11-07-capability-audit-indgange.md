# Capability-audit: indgangs-sættet var for smalt (2026-11-07)

## Hvad der var forkert

`scripts/capability_audit.py` regnede kun en service for «nået» hvis den kunne
findes ved statisk import fra tre filer (`app.py`, `jarvis.py`,
`heartbeat_runtime.py`) plus routes og pipelines. Alt der startes på anden vis
var usynligt:

- **systemd.** `core/services/runtime_guard.py` køres hvert minut af
  `jarvis-runtime-guard.timer` via `python3 -m core.services.runtime_guard`.
  Målingen gav `reachable_from_entry=False` og dermed 🔴 SUSPICIOUS — på vagten
  der blev bygget fordi runtime lå død i 55 minutter.
- **registry-tupler.** `("navn", "core.services.modul", "funktion")` slås op med
  `getattr` og er ikke et import, så modulet så «ukaldt» ud.

Enheden `jarvis-runtime-guard.service` ligger **ikke i repoet**, kun i
`/etc/systemd/system/`. Derfor læser auditten nu også den mappe (kun
`jarvis-*.service`), ud over `deploy/` og `scripts/`.

## Hvad der er ændret

Tre nye kilder, hver sin detektion (`discover_systemd_entries`,
`discover_module_entries`, `discover_registry_entries`), og et nyt felt
`ServiceSignals.entry_paths`:

| Kilde | Etiket | Detektion |
|---|---|---|
| import (uændret) | `import:app.py` | ENTRY_FILES / ENTRY_GLOBS |
| systemd | `systemd:jarvis-runtime-guard.service` | `ExecStart`: `-m modul`, `/sti/script.py`, `uvicorn pkg.mod:app` |
| `-m`-kald | `module:-m core.services.X` | `python[3] -m` i `.sh`/Makefile/`.service`/`.timer` (kommentarer fjernet) og i Python-strenge der ikke er docstrings |
| registry | `registry:<navn>` | AST: 3-tuple af strenge, midterste er et kendt modul, tredje en identifier; i `core/services/` og `apps/` |

Etiketten er bar kun på selve rod-modulet. Moduler der blot importeres længere
nede får `<etiket> (transitive)`, så en unit aldrig ser ud til at have startet
et modul direkte. `import:`-etiketter dækker hele import-lukningen som før.
`main()` udskriver nu hvilke services der er nået via ikke-import veje.

Rørt ikke: score_service, tærsklerne, docs-generatoren. Ingen eksisterende test
antog det gamle indgangs-sæt, så ingen blev rettet. Nye tests i
`tests/test_capability_audit.py` måler hver kilde mod en syntetisk fixture; jeg
har slået hver kilde (og kommentar-/docstring-filtrene) fra enkeltvis og set
testen fejle.

## Målt før/efter

| | før | efter |
|---|---|---|
| `runtime_guard` reachable | False | True |
| `runtime_guard` entry_paths | — | `systemd:jarvis-runtime-guard.service` |
| `runtime_guard` dom | 🔴 SUSPICIOUS | 🟢 LIVE |
| LIVE / PARTIAL / STALE / SUSPICIOUS / ORPHAN | 729 / 403 / 91 / 16 / 1 | 732 / 404 / 91 / 12 / 1 |

12 services er stadig SUSPICIOUS og 1 ORPHAN; det er ikke undersøgt om de er døde.

## Hvad der stadig er falske negativer (og nogle falske positiver)

- **Afhænger af maskinen.** Systemd-vejen for `runtime_guard` findes kun hvis
  auditten kører på hosten med `/etc/systemd/system/jarvis-runtime-guard.service`.
  I en CI-checkout uden den fil falder vagten tilbage til SUSPICIOUS. Rigtig
  løsning: tjek enheden ind i `scripts/` (uden for denne opgaves scope).
- **Cron.** En linje i en crontab (egen eller en anden brugers) er usynlig.
- **Units med wrapper-script.** `ExecStart=/usr/local/bin/foo.sh` der selv kalder
  Python (`jarvis-mem-guard.sh`, `jarvis-memtrack.sh`) ligger uden for repoet og
  læses ikke.
- **`.timer` følges ikke.** Vi læser kun `.service`; en timer der peger på en
  service med andet navn er dækket kun fordi vi læser servicens ExecStart.
  Drop-ins (`*.service.d/override.conf`) med tilsidesat ExecStart ses ikke.
- **`python -m` bygget dynamisk** (f-string, `sys.executable, "-m", mod` som
  liste) matches ikke; kun den litterale streng `python… -m modul`.
- **Registry er ikke betinget af at registret selv er nået.** Et tuple i en død
  fil markerer stadig sit mål som nået (falsk positiv). Kun 3-tuples af
  strenge; en dict eller to separate konstanter findes ikke.
- **Shell-kald uden for scan-rødderne** (`scripts/`, `deploy/`, `core/`,
  `apps/`) ses ikke, fx `~/.jarvis-v2/` eller en Makefile i roden af en anden mappe
  end disse; rodens `Makefile` er ikke med.
- **`-m`-kald i Python-strenge** tæller også når strengen blot er en
  beskrivelse (fx `my_projects.py`) — en let falsk positiv.
- **`getattr`/`importlib` med tal- eller sammensatte navne** som ikke er
  litteraler er stadig kun fanget af den eksisterende `__import__`-analyse.
