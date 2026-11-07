# To målefejl rettet — og hvad de skjulte (7/11-2026)

**Status:** rettet, testet og verificeret mod de faktiske tal
**Slags:** fejlretning (måling) — ikke nye features

## Hvorfor denne note

Hele prioriteringslisten i denne uge byggede på to tal fra husets egne værktøjer:
**80 dark edges** (System Cartographer) og **67 theater-fund** (Theater Audit).
Begge tal var forkerte, og de var forkerte på samme måde: en grænse i koden blev
læst som en egenskab ved verden.

Det er samme fejlklasse som `290 funktioner kaldes kun fra tests` tidligere på
dagen — der overvurderede jeg, her undervurderede værktøjet.

## Fejl 1 — theater-auditen målte et funktionsnavn

`identity_preamble_pressure`-detektoren er denne regex:

```python
re.compile(r"build_identity_preamble|identity_preamble", re.IGNORECASE)
```

Den matcher **symbolet**, ikke om værdien er målt. Målt 7/11-2026 er
`build_identity_preamble()` (i `identity_composer.py`) fuldt signal-drevet:

- navn fra `shared/IDENTITY.md`
- `current_bearing` fra personlighedsvektoren
- `energy_level` fra body_state-fladen

Så de **18 fund var navne-artefakter**, ikke teater. Auditen rapporterede 67 fund,
hvor 27 % var dens egen detektor der pegede på et funktionsnavn.

**Rettelse:** mønstret får `verified_signal_driven: True` og undertrykkes — men
**tælles og navngives** i `summary["suppressed_verified"]` (18) og
`suppressed_by_kind`. Undertrykkelsen er ikke en antagelse: `tests/test_theater_audit_evidence.py`
fejler hvis preamblen holder op med at læse signaler, eller hvis undertrykkelsen
bliver tavs.

**Tal efter:** 67 → **49 fund**, 18 navngivet undertrykt.

## Fejl 2 — 80 var et visningsloft, ikke et antal

`_rank_dark_edges()` endte med `return ranked[:80]`, og `summary["dark_edges"]`
blev læst som det faktiske antal blinde vinkler.

Det uklippede tal er **382**.

Hver rapport der brugte tallet — inklusive mine egne til Bjørn — underdrev
problemet **4,8×**. Det er ikke en kosmetisk detalje: 80 ser ud som en liste man
kan tømme; 382 gør det klart at det er en tilstand, ikke en opgave.

**Rettelse:** `_MAX_DARK_EDGES_SHOWN = 80` er nu eksplicit en visningsgrænse, og
`summary` bærer to tal: `dark_edges` (total, 382) og `dark_edges_shown` (80).
`systemHealth` bruger totalen.

## Fejl 3 (mindre) — markøren var for snæver

`_SURFACE_RE` krævede `build_*_surface`, så en offentlig `identity_sketch_surface()`
ikke blev set. `identity_sketch` stod derfor som systemets **#1 dark edge (score 100)**
på en teknikalitet. Målt: fladen er registreret dynamisk i `cluster_daemon.py:1365`,
altså nåbar.

**Rettelse:** regexen accepterer nu enhver offentlig `*_surface`
(`(?:build_)?[a-zA-Z][a-zA-Z0-9_]*_surface`). Private hjælpere (`_x_surface`)
tæller stadig ikke — de er ikke flader.

**Effekt:** `identity_sketch` er ude af listen, og surfaces steg 438 → **461**
(23 offentlige flader var usynlige for kartografen).

## Verifikation

| Måling | Før | Efter |
|---|---|---|
| Theater-fund | 67 | 49 |
| — heraf navngivet undertrykt | 0 | 18 |
| Dark edges (total) | 382 (vist som 80) | **382** |
| Dark edges (vist) | 80 | 80 |
| Services med surface | 438 | 461 |
| `identity_sketch` i dark edges | ja (#1) | nej |

13 tests grønne, heraf 7 nye der fejler hvis nogen af rettelserne skrider tilbage.

## Fravalg

- **Slettede ikke `identity_preamble_pressure`-mønstret.** At fjerne det ville
  slette historikken og begrundelsen. Det står nu med flag og kommentar, så en
  fremtidig læser kan se hvad der blev undertrykt og hvorfor.
- **Hævede ikke visningsloftet fra 80 til 382.** En payload med 382 dark edges
  gør fladen ulæselig. Loftet er fint — det var *rapporteringen* der var fejl.
- **Rørte ikke de øvrige 49 theater-fund.** De skal vurderes enkeltvis; nogle er
  ægte hardcoded tilstand, andre er legitime LLM-instruktioner. Det er næste batch.
- **Rettede ikke de 72 dark edges uden nogen surface.** Det er Claudes batch
  (`ce6f8f29d4d1`), afgrænset til værktøjs-infrastrukturen.
