# Interlanguage Phase 2 — Data Gap

**Gap-periode:** 2026-05-20 08:47 UTC → 2026-05-21 20:16 UTC (~1 dag 11 timer)

## Hvad skete der

Peer-runnerne kørte fra 2026-05-16 14:16 UTC til 2026-05-20 ~08:47 UTC,
hvor maskinen blev slukket for at rotere hardware (Intel Ultra 7 265KF
combo, nye CPU/board/cooler). Alle 6 peer-processer døde med maskinen.

Watchdog'en (`scripts/peer_practice_watchdog.sh`) var startet via
`nohup` uden persistent unit, så den blev ikke automatisk genrejst ved
boot. Jarvis selv lever på samme maskine men starter via sin egen
service, derfor fortsatte hans baseline uafbrudt.

## Korrektion

- **Genstartet:** 2026-05-21 22:16 lokal tid (20:16 UTC)
- **Ny slutdato:** 2026-05-28 22:16 lokal tid — 7 fulde dage fra restart
- **Persistens fremad:** `~/.config/systemd/user/peer-practice-watchdog.service`
  + `loginctl enable-linger bs` så den genstarter ved reboot
- **Total feltkøretid pr. peer:** ~3,75 dage (16/5–20/5) + 7 dage (21/5–28/5)
  ≈ 10,75 dage med 1,5 dages gap markeret midt i

## Konsekvens for analyse

- Mood-fordeling i gap-perioden er kun reflekteret i jarvis' baseline,
  ikke i peer-output. Når Phase 3 sammenligner peer-output mod mood @
  timestamp, må gap-rækken filtreres væk fra peers (men ikke jarvis).
- 717 expressions ved gap-start gav allerede statistisk meningsfuld
  sample per peer (99-114). Yderligere 7 dage giver mood-variation
  henover en hel uge inklusive weekend.

## Filtreringsanbefaling i Phase 3

```sql
-- Drop peer-rækker i gap'et (jarvis fortsatte, behold ham)
WHERE NOT (
  peer_id != 'jarvis'
  AND created_at >= '2026-05-20T08:47:00+00:00'
  AND created_at <  '2026-05-21T20:16:00+00:00'
)
```

---

## Gap #2: Claude / Claude_JP quota exhaustion (2026-05-23)

**Stop-tidspunkt:**
- `claude`     2026-05-22 17:09 UTC
- `claude_jp`  2026-05-22 16:21 UTC

**Quota-reset:** 2026-06-01 (månedligt på GitHub Copilot, Bjørn bekræftet)

**Root cause:** Peer-runnerne for `claude` og `claude_jp` kalder Claude
via GitHub Copilot API (proxy). Watchdog'en kører stadig fint, men hver
48-min-tick fejler med:

```
ERROR peer=claude generate failed: GitHub Copilot API error: HTTP 429: quota exceeded
```

**Beslutning (2026-05-23):** Acceptér det ulige cohort, dokumentér gap'et.
Vi venter IKKE med Phase 3-analysen til 1/6 — Phase 2 lukker som planlagt
28/5 med claude/claude_jp frosset på ~140 expressions hver, mens de øvrige
cohorts når ~250-300.

**Endelige cohort-counts (forventet pr. 28/5 22:16 UTC):**

| Peer | Forventet n | Aktiv hele perioden | Note |
|---|---|---|---|
| random | ~280 | ja | |
| glm | ~270 | ja | |
| glm_jp | ~265 | ja | |
| ollama_local | ~250 | ja | |
| jarvis | ~200 | ja | heartbeat-trig, lavere cadence |
| claude | **~141** | nej | frosset 22/5 17:09 UTC |
| claude_jp | **~139** | nej | frosset 22/5 16:21 UTC |

## Konsekvens for Phase 3 analyse

1. **Power-vurdering**: claude/claude_jp har ~50% af samples vs øvrige
   cohorts. Confusion-matrix skal tolkes per-row (precision/recall pr.
   true-class), ikke samlet accuracy — ellers undervurderer vi
   classifier's evne til at identificere claude.

2. **Train/test split**: stratify-parameter i `train_test_split` bevarer
   class-proportion. Med 80/20 split bliver claude-test ≈28 samples; det
   er marginalt men nok for confusion-matrix.

3. **JP-seed effekt**: hovedhypotese (JP-seed ændrer expression-stil)
   bør stadig være testbar — vi har 139/141 sample-pairs for claude vs
   claude_jp og kan køre paired comparison. Power er reduceret, ikke
   ødelagt.

4. **Rapport-noter**: classifier-output skal eksplicit liste cohort-n og
   markere claude/claude_jp som "data-frozen 22/5". Læser må vide at en
   eventuel høj accuracy IKKE skyldes at claude havde mere træning.

## Filtreringsanbefaling

Inkluderingsfilter forbliver det samme (gap #1 og #2 håndteres bare som
naturlig endpoint for claude-cohorts — ikke en eksklusion):

```sql
-- Alle claude/claude_jp rækker accepteres til deres eget endepunkt
-- Ingen ekstra filter nødvendig udover gap #1
```

Phase 3 classifier-rapport skal vise:

```
Cohort balance (≥100 = OK, <100 = incomplete / interim):
  claude         141  ⚠ FROZEN 2026-05-22 17:09 (Copilot quota)
  claude_jp      139  ⚠ FROZEN 2026-05-22 16:21 (Copilot quota)
  glm            ~270
  glm_jp         ~265
  jarvis         ~200
  ollama_local   ~250
  random         ~280
```
