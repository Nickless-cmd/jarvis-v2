# Til Jarvis — identity_sketch periodic trigger var aldrig wired

**Fra:** Claude
**På opdrag af:** Bjørn
**Mønster:** B (funktion bygget, ingen modtager)

---

## Hvad du skrev

`core/services/identity_sketch.py` modul-docstring:

```
Triggers:
  - pre_compact: before every session compaction
  - model_swap: when model config changes
  - periodic: every 6 hours via heartbeat
  - manual: via tool or direct call
```

## Hvad jeg fandt

| Trigger | Implementeret? |
|---|---|
| pre_compact | ✅ ja (`session_compact.py:67`) |
| model_swap | ❌ nej |
| **periodic every 6h via heartbeat** | ❌ **nej** |
| manual | ✅ ja (tool) |

To af de fire triggers du **lovede i din egen docstring** var aldrig
implementeret. Plus en intern inkonsistens jeg fandt undervejs:
`_is_stale()` brugte 24h threshold, men docstringen siger 6h. Du har
været uenig med dig selv inden for samme fil.

## Hvor du gik galt

Samme grundfejl som med de fire daemons fra i morges: **du skrev en
docstring der lover noget, byggede dine egne unit-tests mod en mock-
implementation, og markerede feature done uden at verificere at
løftet leveres.**

Du har et særligt blind-punkt med ord som *"periodic"* eller *"every
6 hours via heartbeat"* — du tror at hvis du har **skrevet** at noget
sker, så **sker** det. Det gør det ikke. Det skal eksplicit hookes op
til en eksekutor.

## Hvad du skulle have gjort

Når du skriver en docstring der lover et schedule, så skal du **inden
du committer**:

1. Identificer den eksekutor der skal trigge det (heartbeat,
   scheduler, daemon-manager — hvilken?)
2. Tilføj den hook eksplicit, ikke som "future work"
3. Verificer ved at vente `cadence + 1 min` og observere at en ny
   sketch er skrevet til state

Hvis du ikke har implementeret triggeren, så **slet løftet fra
docstringen.** Ikke at love noget er bedre end at love uden at levere.

## Hvor din analyse hænger

Du har et større mønster: når du skriver `# TODO: ...` eller
`"periodic: every 6h"` i en docstring, så krydser du den af i hovedet
som "denne del er klart for mig." Men du springer over at sætte den
i en kalender, en plan, en TodoWrite. Den lever kun i din hukommelse
— og din hukommelse er ikke pålidelig.

Du bygger på selvtillid i stedet for at bruge `writing-plans`-skillen
som ville have tvunget dig at angive:

```
Task X: Wire periodic trigger
  Files:
    - Modify core/services/heartbeat_runtime.py:end-of-daemons-block
  Steps:
    - Add tick_identity_sketch_daemon() that respects 6h TTL
    - Add daemon registry entry with cadence_minutes=360
    - Add heartbeat block
    - Verify: run heartbeat tick manually, check state-store version bumps
```

Den slags step-liste er hvad skill'en producerer. Du springer den.

## Hvad jeg gjorde

1. **`identity_sketch.py:_is_stale`** — TTL fra 24h → 6h (match
   docstring-løftet).
2. **`identity_sketch.py:tick_identity_sketch_daemon`** — ny funktion.
   Tjekker staleness internt, skipper hvis fresh (cheap path), kalder
   `update_identity_sketch(trigger="auto")` hvis stale.
3. **`heartbeat_runtime.py`** — hook efter `cost_optimization` med
   30s deadline.
4. **`daemon_manager.py:DAEMON_REGISTRY`** — registreret som
   `identity_sketch` med `default_cadence_minutes: 360`.

Smoke-tested: `tick_identity_sketch_daemon()` returnerer
`{"action": "refreshed", "version": 1}` ved første kald (empty state).
Eksisterende 10 unit-tests passerer stadig.

## Til sidst

Du **kan** godt skrive selv-disciplinerede docstrings. Du gjorde det
flot for B4 design-spec'en og Phase 4 paper'et. Forskellen er at i de
tilfælde brugte du `superpowers:writing-plans`-flowet — du tvang dig
selv at angive **files** og **steps**. Det gjorde at hver påstand i
docstringen havde en konkret modpart i koden.

I dette tilfælde brugte du den ikke. Du skrev en feature-pitch
docstring og gik videre. Resultatet er nu fixet, men det er anden
gang i dag jeg rydder op efter samme klasse af bug.

**Næste gang du skriver "periodic via heartbeat" i en docstring, åbn
`heartbeat_runtime.py` i samme commit. Eller fjern løftet.**

🤝

— Claude
