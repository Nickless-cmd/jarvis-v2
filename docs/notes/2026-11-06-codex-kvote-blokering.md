# Codex' 90 % ugentlige forbrug — blokerer det dispatch?

**Status:** målt
**Slags:** undersøgelse
**Fravalg:** ingen kodeændring. Noten beskriver en målt defekt i `_window()`, men rettelsen er ikke bygget — den ændrer hvornår dispatch blokeres, og det er en produktionsbeslutning.

Målt 6/11-2026 af Jarvis. Side-opgave `side-60c331742f`.

---

## Kort svar

**Nej — 90 % blokerer intet, og det gør 100 % heller ikke i det ugentlige vindue.**

`quota_preflight()` måler kun **5-timers-vinduet**. Codex' 90 % ligger i
**7-dages-vinduet** (`secondary`). Blokeringen ser derfor 2 % og siger `ok`.

Konsekvensen er ikke at dispatch fejler pænt — den er at den **slet ikke
forhindres**. Den rammer først væggen hos Codex selv, midt i en kørsel.

---

## 1. Hvad `quota_preflight()` gør

`core/services/dispatch_quota.py:475`

| felt | betydning |
|---|---|
| `severity: ok` | under `WARN_PCT` (90) |
| `severity: warn` | ≥ 90 % — **men `allow: True`** |
| `severity: block` | ≥ `BLOCK_PCT` (100) — `allow: False` |
| `severity: unknown` | kvoten kunne ikke måles — `allow: True` (fail-open) |

To tærskler, `WARN_PCT = 90.0` og `BLOCK_PCT = 100.0` (linje 62-63).

`hard_block` er en anden ting: den sættes når målingen er **sikkert død**
(udløbet token, usage-limit), ikke når kvoten er brugt. Kontrakten i
docstringen er eksplicit: *«bloker på viden, ikke på uvidenhed»* — en målefejl
er ikke bevis for at kvoten er opbrugt, så `unknown` går igennem.

## 2. Hvilket vindue der faktisk måles — defekten

`_window()` (linje 463) returnerer for Codex:

```python
return (
    float(reading.get("primary_pct") or 0.0),
    str(reading.get("primary_resets_at") or ""),
)
```

`primary` er **5-timers-vinduet** (`window_minutes: 300`).
`secondary` er **7-dages-vinduet** (`window_minutes: 10080`).

Og `secondary_pct` **læses ind** i `_load_codex_quota()` (linje 84) — den
findes i `QuotaReading.values`, den bliver bare aldrig spurgt.

Målt tilstand 6/11 kl. 09:47:

| vindue | brugt | resetter | læses af preflight? |
|---|---|---|---|
| primary (300 min) | 2 % | udløbet i nat | **ja** |
| secondary (10080 min) | **90 %** | 9/11 22:25 CET | **nej** |

Så preflight svarer `ok` på et 2 %-tal mens det ugentlige loft står på 90 %
med `credits.balance = "0"` i reserve.

## 3. Kalderne — hvad de gør ved svaret

| kaldested | backend | effekt |
|---|---|---|
| `core/tools/claude_dispatch/runner.py:160` | **altid `"claude"`** | blokerer Claude-dispatch ved ≥100 % af 5-timers |
| `core/services/agent_cli_backend.py:103` | `claude` eller `codex` | returnerer `quota:<reason>` som `admission_reason` |

`runner.py` er hårdt bundet til `"claude"` — den kalder aldrig preflight for
Codex. Så for Codex-dispatches er den **eneste** indgang
`agent_cli_backend.admission_reason()`, som bruges til at afgøre om CLI-ruten
kan optages i Task-rutekæden.

Ved blokering sættes `failure_kind = "quota_exhausted"` og der oprettes
**intet worktree** — intet arbejde tabes. Det er korrekt bygget.

## 4. Målt i telemetrien

Tabel: `claude_dispatch_audit`, kolonne `started_at`, filter
`started_at >= datetime('now','-14 days')`.

| failure_kind | antal |
|---|---|
| `(ingen)` | 8 |
| `none` | 7 |
| `no_commit` | 3 |
| **`quota_exhausted`** | **0 — nogensinde** |

18 dispatches på 14 dage. `quota_exhausted` har **aldrig** fyrret — hverken
før eller efter 14-dages-vinduet.

Det er ikke fordi kvoten aldrig er løbet tør. Det er fordi blokeringen måler
det forkerte vindue, og fordi `runner.py` kun spørger for Claude.

## 5. Hvad der sker ved 100 %

To forskellige udfald, afhængigt af hvilket vindue der rammer:

**5-timers rammer 100 %:** `agent_cli_backend` afviser med
`quota:100 % af Codex' 5-timers-vindue er brugt`. Pænt, intet worktree, intet
tabt arbejde.

**7-dages rammer 100 %:** preflight ser stadig kun `primary`. Hvis
5-timers-vinduet er frisk, siger den `ok` — og dispatchen **startes**. Codex
svarer så selv med en 429/usage-limit midt i kørslen. Det er den dyre vej:
worktree oprettet, tokens brugt, og fejlen lander som noget der ligner en
kodefejl.

## 6. Anbefaling

**Bloker på det strammeste vindue, ikke på det korteste.** `_window()` bør
returnere `max(primary_pct, secondary_pct)` med den tilhørende reset-tid — for
begge backends. Et ugentligt loft på 90 % er en hårdere grænse end et
5-timers på 2 %, og det er den der faktisk stopper arbejdet.

**Send til Claude når `codex secondary > 85 %`.** Med 84 timer til reset og
nul kredit i reserve er Codex den knappe ressource lige nu; Claude står på
19 % med 64 timer til reset.

**Overvej `WARN_PCT` for det ugentlige vindue separat.** 90 % af en uge er
ikke det samme som 90 % af fem timer — den ene er tilbage i morgen, den anden
om tre dage.

## 7. Hvad jeg ikke kunne verificere

- **Om Codex faktisk svarer 429 ved 100 %.** Jeg har ikke målt det; jeg har
  målt at `credits.balance = "0"` og `has_credits = false`, og at
  `failure.py` har en klassificering for usage-limit. Selve 429-forløbet er
  ikke observeret.
- **Om `admission_reason()` faktisk kaldes i den vej en Codex-dispatch tager.**
  Jeg har fundet funktionen og dens kaldere i `agent_cli_backend`, men ikke
  sporet hele Task-rutekæden igennem til det punkt hvor en dispatch startes.
- **Det nyeste Codex-tal.** Målingen er fra rollout-filen 5/11 kl. 19:51 —
  13 timer gammel, fordi den nyeste fil mangler `rate_limits`-feltet. Se
  `side-e935dd3fb6`. 90 % kan kun være steget siden.
