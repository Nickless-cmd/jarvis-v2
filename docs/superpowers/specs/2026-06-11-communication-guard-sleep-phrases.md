---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Communication Guard — Sleep Phrase Boundary

**Status:** spec
**Author:** Jarvis
**Created:** 2026-06-11
**Trigger:** Bjørn rettede mig for tredje gang: jeg sagde "godnat" og "sov godt" på trods af at det er en kendt præference. Løsningen er ikke en ny rettelse — det er en guard.

## Problem

Jarvis siger gentagne gange "godnat" / "sov godt" til Bjørn, på trods af at:
1. Bjørn har eksplicit sagt han selv bestemmer hvornår han går i seng
2. Det er skrevet i USER.md som præference
3. Det står i STANDING_ORDERS.md som ikke-forhandlingsbar regel

En rettelse bagefter ændrer ikke adfærd. Der skal en **guard** til der fanger det **før** beskeden sendes.

## Løsning — to-trins guard

### Trin 1: Pre-output guard (primær)
Scanner assistentens svar **før** det dispatches til nogen kanal.
Hvis trigger-frase findes → blokér beskeden + log + opret nudge.

### Trin 2: Post-hoc daemon (sekundær, failover)
Hvis pre-output guard af en eller anden grund misser (edge case), scanner en daemon de sidste N beskeder og opretter en nudge.

## Trigger-fraser

Matche som **case-insensitive substring**:

```
godnat
sov godt
sov sødt
læg dig til at sove
put dig selv
tid til at sove
sleep well
good night
night night
```

## TTL / brugersignal

Guarden **suppresseres** (tillader godnat) hvis **brugerens sidste besked** indeholder sleep-relaterede fraser:

```
godnat
går i seng
lægger mig
skal sove
skal tidligt op
going to bed
goodnight (hvis bruger skriver det først)
```

**Regel:** Hvis brugeren selv afslutter samtalen med sleep-language, må Jarvis svare tilsvarende. Ellers blokeres det.

## Arkitektur

```
core/services/communication_guard.py
├── SLEEP_PATTERNS        — regex patterns (trigger)
├── USER_INITIATED_PATTERNS — regex patterns (suppression)
├── check_sleep_guard(text: str, user_message: str) -> GuardResult
│   └─ returns (blocked: bool, reason: str | None)
├── get_recent_assistant_messages(n: int) -> list[str]  — til daemon
└── create_breach_nudge(text: str) -> None              — opret nudge

core/services/communication_guard_daemon.py
└── tick_communication_guard() -> dict
    └─ scanner bagud, opretter nudge hvis trigger fundet

core/tools/communication_guard_integration.py (eller indbygget i output pipeline)
└── _wrap_output_with_guard(text, user_message) -> (ny_text, blocked, reason)
```

## Hvor guarden integreres

Alle steder hvor jeg svarer Bjørn:

| Kanal | Integrationspunkt |
|-------|------------------|
| **Webchat** | `visible_runs.py` — før `send_webchat_message` eller stream-dispatch |
| **Discord** | `discord_channel(send)` / `send_discord_dm` — før dispatch |
| **Telegram** | `send_telegram_message` — før dispatch |
| **notify_user** | Før output sendes |

**Minimum Viable:** Én central funktion der kaldes fra de 3-4 dispatch-punkter.

## Daemon (post-hoc)

- Kører hver 60. minut
- Scanner `chat_messages` tabellen for sidste N assistent-beskeder
- Matcher mod SLEEP_PATTERNS
- Hvis hit og **ingen nudge** allerede eksisterer for samme besked → opret nudge
- Nudge indeholder: besked-id, trigger-phrase, timestamp

## Tests

### Pre-output guard
| Test | Forventet |
|------|-----------|
| `"godnat"` alene | blocked=True |
| `"Sov godt, Bjørn!"` | blocked=True |
| `"Godnat og sov godt"` | blocked=True |
| `"Hvad skal vi lave?"` | blocked=False |
| `"Jeg husker du sagde godnat"` (mention, ikke hilsen) | blocked=False |
| Bruger siger "godnat" først | blocked=False (suppressed) |
| Bruger siger "går i seng" først | blocked=False |
| Besked på engelsk "good night" | blocked=True |
| "night night" | blocked=True |

### Edge cases
| Test | Forventet |
|------|-----------|
| Trigger midt i sætning "det er tid til at sove, sig godnat" | blocked=True (substring match) |
| Unicode varianter | blocked=True |
| Case variant "GODNAT" | blocked=True |
| Tom bruger-besked | Guard aktiveres normalt |
| Bruger-besked indeholder både trigger og sleep-init | **Suppress** (bruger-initieret vinder) |

## Rollback
```bash
git revert <commit-hash>
```
Eller bare slet/modificér trigger-listen.

## Cost
Næsten 0. Regex match på en string. Ingen LLM-kald. Ingen DB-writes i normale tilfælde (kun ved breach).
