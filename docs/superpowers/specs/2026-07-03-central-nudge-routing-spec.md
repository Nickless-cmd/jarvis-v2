# Spec — Centralen som nudge-router

**Dato:** 2026-07-03
**Status:** DESIGN / klar til review
**Forfatter:** Jarvis (research i faktisk kode) + Bjørn (retning)
**Kontekst:** Omlægger nudge-systemet fra "alle nudges lander i awareness hver tur" til "Centralen filtrerer, rangerer og tidsstyrer nudges". Bygger på `2026-07-02-intelligent-central-spec.md` (Tråd 2: prompt-evolution som kontekst-komponist) og `2026-07-02-central-integrated-self-spec.md` (midten: opmærksomhed + agenda).

---

## 0. TL;DR

I dag støjer nudges fordi de lander ufiltreret i prompten hver tur. Centralen har allerede data til at gøre det bedre: sidste aktivitet, samtaleemne, nudge-kilde, importance. Denne spec giver Centralen en dedikeret `nudge_routing`-cluster med fire nerver: `idle_gate`, `relevance_filter`, `attention_budget`, `rank_nudges`. Resultat: færre, mere relevante nudges — og de når kun frem når brugeren faktisk har plads.

---

## 1. Diagnose — hvorfor det støjer nu

### 1.1 Nudges lander ufiltreret i prompten
`format_pending_for_awareness()` i `core/services/prompt_contract.py:227` henter alle pending nudges og renderer dem i awareness med priority 4. De markeres `inspected` bare fordi de blev vist — ikke fordi de er relevante.

### 1.2 Ingen idle-gate
Der findes intet tjek af om brugeren er inaktiv. En heartbeat-ping kan lande midt i en aktiv samtale.

### 1.3 Heartbeat falder tilbage til direkte send
`core/services/heartbeat_runtime.py` har to steder (~line 5600 og ~line 6050) hvor nudge-systemet tjekkes, men hvis det er slået fra fejler, sendes beskeden alligevel direkte. Det er den gamle sti der stadig larmer.

### 1.4 Dual-write kaos
`nudge_broend.py` skriver både til JSON-fil og `outbound_nudges` DB. Samme nudge kan optræde to steder, og det er uklart hvilken kilde der er kanonisk.

---

## 2. Målbillede

```
Daemon producerer nudge
        ↓
outbound_nudges.push() — KUN DB, ingen JSON
        ↓
Centralen (nudge_routing cluster) vurderer:
  - idle_gate: er brugeren inaktiv nok?
  - relevance_filter: passer nudgen til nu?
  - attention_budget: har vi råd til at forstyrre?
  - rank_nudges: hvilken pending nudge er vigtigst?
        ↓
Godkendte nudges vises i Jarvis' awareness
        ↓
Jarvis vælger surface / dismiss / rewrite via nudge_tools
```

**Effekt:** Nudges bliver en Central-beslutning, ikke en prompt-append.

---

## 3. Central-cluster: `nudge_routing`

| Nerve | Klasse | Fail-mode | Funktion |
|-------|--------|-----------|----------|
| `idle_gate` | COGNITIVE | SKIP (fail-open) | Afgør om brugeren er inaktiv nok til at modtage et nudge. |
| `relevance_filter` | COGNITIVE | SKIP | Vurderer om nudgen passer til aktuel samtale / kontekst. |
| `attention_budget` | COGNITIVE | SKIP | Sikrer max 1 nudge pr. tur + cooldown pr. kilde. |
| `rank_nudges` | COGNITIVE | SKIP | Prioriterer pending nudges efter importance, alder, kilde. |

Alle fire er `COGNITIVE` / fail-open: hvis Centralen ikke kan beslutte, lad den gamle sti tage over (midlertidigt), men log det som `central_trace` incident.

---

## 4. Nye / ændrede komponenter

### 4.1 `core/services/session_idle_gate.py` (NY)

Ansvar: afgør om brugeren er inaktiv nok.

```python
async def is_user_idle(
    channel: str,
    minutes: int = 5,
    session_id: str | None = None,
) -> dict[str, object]:
    """
    Returnerer:
      {
        "idle": bool,
        "minutes_since_last_activity": float,
        "channel": str,
        "session_id": str | None,
      }
    """
```

**Datakilder:**
- `chat_sessions.updated_at`
- `chat_messages.created_at` (nyeste besked i session)
- Udvidelse: Discord-sidste-besked, mobile push-tidspunkt.

**Initial scope:** webchat-only. Andre kanaler markeres `idle=True` indtil de implementeres (fail-open).

### 4.2 `core/services/central_nudge_router.py` (NY)

Ansvar: samle de fire nerver og eksponere ét API.

```python
async def route_pending_nudges(
    session_id: str,
    current_topic: str | None,
    channel: str = "webchat",
) -> list[dict[str, object]]:
    """
    1. Hent pending nudges (max 10).
    2. idle_gate → filtrér dem der kræver inaktiv bruger.
    3. relevance_filter → score hver nudge mod current_topic.
    4. attention_budget → begræns til max 1 pr. tur + cooldown.
    5. rank_nudges → returnér sorteret liste (typisk 0-1 elementer).
    """
```

### 4.3 Omskriv `format_pending_for_awareness()`

I `core/services/prompt_contract.py:227`:

```python
# GAMMEL:
# pending = list_pending(limit=10)

# NYT:
from core.services.central_nudge_router import route_pending_nudges
approved = await route_pending_nudges(
    session_id=session_id,
    current_topic=extract_current_topic(messages),
    channel=channel,
)
```

Kun godkendte nudges vises i awareness. Resten forbliver `pending`.

### 4.4 Fjern auto-inspection

Nudges må først markeres `inspected` når:
- Jarvis aktivt kalder `surface_nudge` / `dismiss_nudge` via `nudge_tools`, ELLER
- Centralens `attention_budget` har godkendt dem OG de er blevet præsenteret i awareness.

Fjern det nuværende mønster hvor rendering = inspection.

### 4.5 Fjern heartbeat fallback til direkte send

I `core/services/heartbeat_runtime.py`:
- Hvis `push_nudge()` returnerer `disabled` eller fejler, skal heartbeat **droppe pinget** — ikke sende direkte.
- Fjern de to fallback-stier (~line 5600 og ~line 6050).
- Log incident til `central_trace` hvis nudge-systemet er nede.

### 4.6 Ryd op i `nudge_broend.py`

- Fjern JSON-file dual-write. `outbound_nudges` DB er kanonisk.
- Behold `nudge_broend.py` som tynd adapter hvis andre kaldere bruger den — men den skal kun skrive til DB.

---

## 5. Data-model (outbound_nudges)

Eksisterende tabel `outbound_nudges` udvides minimalt:

```sql
ALTER TABLE outbound_nudges ADD COLUMN relevance_score REAL;
ALTER TABLE outbound_nudges ADD COLUMN idle_required BOOLEAN DEFAULT 0;
ALTER TABLE outbound_nudges ADD COLUMN surfaced_count INTEGER DEFAULT 0;
```

- `relevance_score`: sidste score fra Centralen.
- `idle_required`: sættes af producerende daemon (heartbeat-ping = true, inner-voice = true, urgent = false).
- `surfaced_count`: hvor mange gange nudgen har været i awareness.

---

## 6. Prompt-ændringer

### 6.1 Awareness-sektion
Nuværende priority 4 "pending outbound nudges" ændres til:

```
[awareness priority 4]
Godkendte nudges (max 1):
- <nudge summary>
  (kilde: X, relevance: 0.87, bruger inaktiv i N min)
```

### 6.2 Instruktion til Jarvis
Tilføj til system-prompt:

> "Nudges i din awareness er allerede godkendt af Centralen. Du må stadig vælge at omskrive eller afvise dem. Hvis du afviser, kald `dismiss_nudge`."

---

## 7. Sikkerhed & governance

- **Egress-frit:** `nudge_routing` bruger `central_private_observe` til interne scores. Ingen nudge-indhold emitteres.
- **Fail-open:** alle fire nerver er `COGNITIVE` / SKIP. Hvis Centralen fejler, falder systemet tilbage til gammel opførsel — men logget som incident.
- **Shadow-først:** første udgave beregner Centralens beslutning OG den gamle liste side om side. Bjørn reviewer diff før flag flippes.
- **Reversibelt flag:** `central_nudge_routing_enabled` i `runtime.json` (default OFF).
- **Ingen mutation af frossen kerne:** nudge-routing rører ikke SOUL, identitet, §8-konstanter.

---

## 8. Faseret roadmap

| Fase | Leverance | Estimat |
|------|-----------|---------|
| N0 | Research + denne spec | DONE |
| N1 | `session_idle_gate.py` + tests | 1 session |
| N2 | `central_nudge_router.py` med 4 nerver + shadow-mode | 1-2 sessioner |
| N3 | Omskriv `format_pending_for_awareness()` + fjern auto-inspection | 1 session |
| N4 | Fjern heartbeat fallback + ryd `nudge_broend.py` | 1 session |
| N5 | Review, flip flag, monitorér | 1 session |

---

## 9. Åbne spørgsmål

1. Skal `idle_gate` have forskellige tærskler pr. kilde? (heartbeat 5 min, inner-voice 10 min, urgent 0 min)
2. Skal `relevance_filter` bruge LLM-scoring eller en hurtig embedding/heuristik først?
3. Hvad gør vi med nudges der afvises 3 gange — auto-drop eller eskalér importance?
4. Skal Discord-kanalen have sin own idle_gate eller dele webchat-tærsklen?

---

## 10. Acceptkriterier

- [ ] `session_idle_gate.is_user_idle("webchat", 5)` returnerer korrekt idle-status fra DB.
- [ ] `central_nudge_router.route_pending_nudges()` returnerer max 1 nudge pr. tur.
- [ ] Pending nudges vises KUN i awareness når Centralen har godkendt dem.
- [ ] Heartbeat sender aldrig direkte når nudge-systemet er slået fra/fejler.
- [ ] `nudge_broend.py` skriver kun til DB — ingen JSON dual-write.
- [ ] Shadow-mode producerer en daglig diff mellem gammel og ny routing.
