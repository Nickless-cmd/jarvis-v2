# Discord/webchat-fallback: `queued` læses som blokering

**Status:** diagnose — ingen kodeændring uden Bjørns ord
**Dato:** 6/11-2026
**Side-opgave:** `side-5d80175e9c`
**Slags:** rodårsagsanalyse
**Fravalgt:** patch af kalderen (se «Hvad der skal besluttes»)

## Konklusion

Fallbacken fejler ikke. Den **lykkes**, og kalderen læser succesen som en blokering.

`_deliver_heartbeat_ping_directly` returnerer `status: "queued"` når nudgesystemet er
tændt (`nudge_system_enabled: True`, målt 6/11). Kalderen i `heartbeat_runtime.py:4437`
accepterer **kun** `status == "sent"`:

```python
if str(fallback_result.get("status") or "") == "sent":
    return {... "ping_result": "sent-webchat-fallback-from-discord" ...}
return {... "blocked_reason": "discord-no-active-dm-and-webchat-fallback-blocked" ...}
```

`queued` falder derfor i `return`-grenen og bliver til en blokering. `blocked_reason`
er tom i `queued`-svaret, og `or 'unknown'` i beskeden gør den til `unknown` — derfor
står der «was unavailable: unknown» i 19 af 20 ticks.

## Målt

`heartbeat_runtime_ticks`, `blocked_reason='discord-no-active-dm-and-webchat-fallback-blocked'`:

| | |
|---|---|
| i alt | **176** ticks |
| 20 nyeste | **19 × `unknown`**, 1 × `generic-templated-ping-rejected` |

`unknown` er ikke en fejlgrund — det er en **tom streng** fra en vellykket `queued`-retur.

Funktionens mulige statusser (`heartbeat_delivery.py`): `blocked` (13 steder),
`recorded` (2), `queued` (1), `sent` (2). Kun de to `sent` accepteres af kalderen.

## Hvorfor det er den rigtige fejlform at fange

Koden advarer **selv** om den, to steder — `heartbeat_delivery.py:203` og `:453`:

> «"queued" ER en succes. Kalderen tjekker `status == "sent"` præcist, saa koeningen
> maa IKKE aendre status — den staar i summary og artifact i stedet. Et "queued" laest
> som fejl kostede en dobbelt-levering 23/9.»

Advarslen blev skrevet til **Discord-stien** (linje 203). Webchat-stien fik den samme
kommentar (linje 453) — men den kalder, der læser webchat-fallbacken, blev aldrig rettet.
Så rettelsen blev anvendt på den ene af to stier.

## Hvad der skal besluttes

Der er to mulige rettelser, og de har forskellig betydning:

1. **Kalderen accepterer `queued` som succes** (som Discord-stien gør). Det er den
   konsistente rettelse — men den betyder at et ping der ligger i nudge-ledgeren
   rapporteres som leveret, selv om Jarvis endnu ikke har vist det.
2. **Webchat-stien returnerer `sent` når nudgen er køet.** Det gør status-feltet
   løgnagtigt på en anden måde.

Anbefaling: **(1)**, fordi `queued` allerede er defineret som succes i samme fil, og
fordi `action_status` kan bære nuancen (`queued-webchat-fallback`) uden at
`blocked_reason` lyver.

**Ingen ændring er lavet.** Den rører hvordan proaktive leverancer rapporteres, og det
er en produktionsadfærd der skal besluttes, ikke gættes.

## Det jeg ikke har undersøgt

Spørgsmål 2 i opgaven — hvorfor der ikke er en aktiv Discord DM — er ikke besvaret.
Målingen viser at det er **irrelevant** for de 19 ticks: de blev ikke blokeret af
Discord, de blev blokeret af en fejllæst succes. Om DM-tråden findes er en separat sag.
