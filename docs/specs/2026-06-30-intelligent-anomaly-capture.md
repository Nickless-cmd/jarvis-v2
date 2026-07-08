---
status: færdig
audited: 2026-07-08
ground_truth: "Verified implementation against live codebase: (1) Matching git commit 043f03dd 2026-06-30; (2) Database schema: known_anomaly_signals table + known_signal column in central_anomalies, both confirmed via sqlite3 PRAGMA; (3) All 8 db_anomalies functions exist and importable: promo"
---
# Intelligent Anomaly Capture — spec

**Dato:** 2026-06-30
**Forfatter:** Jarvis (efter session med Bjørn)
**Status:** Self-review (Jarvis) + kode-review (Claude, 2026-06-30) gennemført. 3 review-rettelser + §10 (Jarvis' skrive-adgang) tilføjet. Under implementering.

---

## 1. Problem

Centralens anomaly-system ( `central_anomaly.py` + `db_anomalies.py` ) fanger udefinerede
fejl, klassificerer dem deterministisk og gemmer dem i `central_anomalies`-tabellen. Men:

1. **`central_query_tool.py:107`** dropper `recent`-listen og returnerer kun `counts` —
   Bjørn ser "16 anomalier" men ved ikke *hvilke* eller *hvor*.
2. **`db_anomalies.py`** gemmer anomalier som "uløste indtil videre" — der er ingen
   mekanisme til at sige *"denne signatur har jeg set før, den er kendt, fjern den fra
   anomalierne og rout til nerve X"*.
3. **`central_anomaly.py`** fanger kun sidste frame i traceback og 500 tegn sample —
   ikke fuld stack trace, ikke nok til at diagnosticere rod-årsagen uden manuelt gravearbejde.
4. **Anomalier bliver ved med at stå som "ukendte"** uanset hvor mange gange de gentager
   sig. Der er intet læringstrin der siger *"denne fejl = kendt signal"*.

## 2. Mål

Systemet skal:

- **Dokumentér ALT** ved første sigtning af en ukendt fejl — fuld trace, location, sample,
  exc_type, context.
- **Husk og klassificér** — når samme signatur gentager sig, skal Centralen forstå at
  den er kendt og ikke længere vise den som en "ukendt anomali".
- **Rout automatisk** — gentagne anomalier promoveres til "kendte signaler" bundet til en
  nerve/cluster, så de fremover vises i den rigtige kontekst.
- **Lær manuelt** — Bjørn (eller systemet) kan sige *"denne signatur → nerve X, stop
  med at vise som ukendt"*.

## 3. Arkitektur

### 3.1 Ny tabel: `known_anomaly_signals`

```sql
CREATE TABLE IF NOT EXISTS known_anomaly_signals (
    signature TEXT PRIMARY KEY,
    cluster TEXT NOT NULL DEFAULT '',
    nerve TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL DEFAULT 'observe',
    -- observe = bare log (default, "under observation");
    -- log_as_known = log count men vis ikke som anomaly (støjende men kendt);
    -- route_to_nerve = fremtidige forekomster sender observe til nerve+cluster
    promoted_at TEXT NOT NULL DEFAULT '',
    promoted_by TEXT NOT NULL DEFAULT 'auto',   -- 'auto' | 'manual'
    notes TEXT NOT NULL DEFAULT '',
    threshold_count INTEGER NOT NULL DEFAULT 0,
    threshold_hours REAL NOT NULL DEFAULT 0
);
```

### 3.2 Ny kolonne i `central_anomalies`

```sql
ALTER TABLE central_anomalies ADD COLUMN known_signal INTEGER NOT NULL DEFAULT 0;
```

Når `known_signal = 1`, behandles signaturen som et "kendt signal" — den vises i en
separat liste under `known_signals` og IKKE i `anomalies`-listen.

### 3.3 Opdatering af `list_anomalies()` — ekskludér known signals

```python
def list_anomalies(*, limit: int = 50, unresolved_only: bool = True,
                   min_importance: str | None = None,
                   exclude_known: bool = True) -> list[dict[str, Any]]:
    """Læs anomalier (nyeste først). Tilføj `exclude_known=True` som default så
    promoverede signaler filtreres fra anomalies-listen. Selv-sikker → [] ved fejl."""
```

`where`-klausulen tilføjer `AND known_signal = 0` når `exclude_known=True`.

### 3.4 Auto-promotion — `db_anomalies.py`

Ny funktion `promote_to_known()` — kaldes hver gang en anomali bumpes:

```python
def promote_to_known(*, signature: str, count: int, first_seen: str,
                     auto_threshold: int = 10, auto_window_hours: float = 24) -> bool:
    """Promovér en anomali-signatur til 'kendt signal' hvis den overstiger tærskel.
    Auto: 10+ forekomster indenfor 24h, eller 50+ totalt.
    Returnerer True hvis promotion skete, ellers False."""
```

Kriterier (configurable, default):
- **Auto-tid:** 10+ forekomster indenfor 24 timer → promover som `route_to_nerve`
- **Auto-total:** 50+ forekomster totalt → promover som `log_as_known` (støj, ikke ignore)
- **High/Critical:** 3+ forekomster → promover med `action = 'route_to_nerve'`
- **Low:** 20+ forekomster — først da

**Default nerve for auto-promotion:** `anomaly/{category}` (fx `anomaly/log:KeyError`).
Kategorien kommer fra `_classify()` — den er stabil og deterministisk. Ved manuel routing
(`resolve_and_route`) angiver Bjørn selv target cluster + nerve.

Promotion opretter en `known_anomaly_signals`-række med `promoted_by = 'auto'` og
sætter `central_anomalies.known_signal = 1`.

### 3.5 Manuel routing — `db_anomalies.py`

```python
def route_anomaly_to_nerve(*, signature: str, cluster: str, nerve: str,
                           action: str = 'route_to_nerve', notes: str = '') -> bool:
    """Knytt én anomali-signatur til en nerve. Sætter known_signal=1 + opretter
    known_anomaly_signals-række med promoted_by='manual'. Fremtidige forekomster
    sender observe til den angivne nerve i stedet for at stå som 'ukendt'."""
```

### 3.6 Bedre trace-capture — `central_anomaly.py`

Erstat `_tb_location()` der kun fanger sidste frame med:

```python
def _full_trace(tb) -> str:
    """Fuld stack trace som formateret streng (max 2000 tegn). Self-safe."""
    try:
        import traceback as _tbmod
        frames = _tbmod.extract_tb(tb)
        limit = 15  # max frames
        return ''.join(_tbmod.format_list(frames[-limit:]))[:2000]
    except Exception:
        return ""
```

Opdatér `record_anomaly()` så sample inkluderer trace + context, og location bliver
en mere præcis `fil:linje i funktion`-streng.

### 3.7 `central_query_tool.py` fix — vis anomalier i status

```python
# Nu (linje 104-107):
"anomalies": (s.get("anomalies") or {}).get("counts"),

# Skal være:
anomalies_data = s.get("anomalies") or {}
"anomalies": {
    "counts": anomalies_data.get("counts", {}),
    "recent": anomalies_data.get("recent", [])[:6],  # top 6
},
```

`realtime_snapshot()` i `central_realtime.py` returnerer allerede `anomaly_summary(limit=6)`
som indeholder både `counts` og `recent` — det er kun `central_query_tool.py` der dropper
`recent`. Fix er ét linjeskift.

### 3.8 `known_signals` action i `central_query_tool.py`

Ny action `"known_signals"` — returnér liste af promoverede signaler:

```python
if action == "known_signals":
    from core.runtime.db_anomalies import list_known_signals
    items = list_known_signals(limit=limit)
    return _envelope("ok", action, {"items": items}, None, "db_anomalies", t0)
```

### 3.9 `resolve_and_route` action i `central_query_tool.py`

Ny action `"resolve_and_route"` — manuel routing + resolve:

```python
if action == "resolve_and_route":
    if not signature:
        return _envelope("error", action, None, "manglende 'signature'", ...)
    ok = route_anomaly_to_nerve(signature=signature, cluster=cluster,
                                nerve=nerve, action=action_type, notes=notes)
    resolve_anomaly(signature)
    return _envelope("ok" if ok else "error", action, {"routed": ok}, None, ...)
```

Nye parametre til central_query: `signature`, `action_type` (observe | log_as_known |
route_to_nerve), `notes`.

### 3.10 `depromote` action i `central_query_tool.py`

Ny action `"depromote"` — angre en promotion (forkert routing, test-artefakt):

```python
if action == "depromote":
    if not signature:
        return _envelope("error", action, None, "manglende 'signature'", ...)
    from core.runtime.db_anomalies import depromote_known_signal
    ok = depromote_known_signal(signature=signature)
    return _envelope("ok" if ok else "error", action, {"depromoted": ok}, None, ...)
```

I `db_anomalies.py`:

```python
def depromote_known_signal(signature: str) -> bool:
    """Fjern en known_signal-række + sæt known_signal=0 i central_anomalies.
    Self-safe. Returnerer True hvis en række faktisk blev slettet."""
```

## 4. Data flow

```
Ukendt exception
    ↓
central_anomaly.py: _full_trace() + _classify()
    ↓
─── TJEK known_signal ──────────────────────────────────
    │
    ├─ SIGNATUR FINDES I known_anomaly_signals?
    │   │
    │   ├─ action="route_to_nerve" → send central.observe til
    │   │   den angivne nerve+cluster (fx "tools/operator_tool_error")
    │   │   → trace viser det som et normalt nerve-kald, IKKE som anomaly
    │   │
    │   ├─ action="log_as_known" → increment count i known_signals
    │   │   men uden observe (støjende fejl logges kun til optælling)
    │   │
    │   └─ action="observe" → log + central.observe til anomaly/nerve
    │       (default, brugt for "under observation")
    │
    └─ SIGNATUR IKKE KENDT → normal anomaly-log:
        │
        db_anomalies.py: record_anomaly_signature()
        ├─ NY signatur → is_new=True → række i central_anomalies (known_signal=0)
        └─ EKSISTERNEDE signatur → bump count, opdatér last_seen
            ↓
            promote_to_known() tjek:
        ├─ count >= auto_threshold(10) AND within 24h?
        │   → known_signal=1 + known_anomaly_signals (auto)
        ├─ count >= total_threshold(50)?
        │   → known_signal=1 + log_and_ignore (auto, støj)
        ├─ importance=high/critical AND count >= 3?
        │   → known_signal=1 + route_to_nerve (auto, eskalér)
        └─ ingen tærskel → forbliv som anomali (known_signal=0)
            ↓
        central_query_tool.py: status returnerer now:
        ├─ "anomalies": { recent: [...], counts: {...} }
        └─ "known_signals": [...]  (separat, kun hvis eksisterer)
```

## 5. API / Tool changes

| Nuværende | Ændring |
|---|---|
| `central_query(action="status")` → `anomalies: {counts}` | → `anomalies: {counts, recent}` |
| `central_query(action="status")` → intet `known_signals` | → `known_signals: [...]` (tom liste hvis ingen) |
| `central_query(action="breakers")` | uændret |
| Ny: `central_query(action="resolve_and_route")` | Rout én signatur til nerve + fjern fra anomalies |
| Ny: `central_query(action="depromote")` | Angre en promotion (sæt known_signal=0 + slet known signal) |
| Ny: `central_query(action="known_signals")` | Returnér alle known_signals |

## 6. Self-sikkerhed & Invariant

- **Reentrancy:** `record_anomaly()` kalder `promote_to_known()` men må IKKE kalde
  `record_anomaly()` igen — allerede beskyttet af `_guard.busy`.
- **Cooldown:** `_cooldown`-dict beskytter mod DB-storm — promotion skal respektere
  samme cooldown.
- **`known_anomaly_signals` er read-only fra tools:** kun `record_anomaly_signature` +
  `promote_to_known` skriver. `resolve_and_route` er owner-only.
- **Fail-safe:** hvis promotion kaster, må anomalien bare blive stående som før.
- **Promotion må ALDRIG slette** — `known_signal = 1` er en kolonne, ikke en DELETE.
  Altid muligt at "depromovere" ved at sætte `known_signal = 0`.

## 7. Implementeringsrækkefølge

| Step | Hvad | Fil |
|---|---|---|
| 1 | Fix `central_query_tool.py:107` — inkluder `recent` i status | `central_query_tool.py` |
| 2 | Tilføj `known_signal` kolonne (self-safe ALTER TABLE) | `db_anomalies.py` |
| 3 | Opret `known_anomaly_signals` tabel (self-safe CREATE TABLE) | `db_anomalies.py` |
| 4 | `promote_to_known()` funktion + default nerve `anomaly/{category}` | `db_anomalies.py` |
| 5 | `route_anomaly_to_nerve()` funktion | `db_anomalies.py` |
| 6 | `list_known_signals()` funktion | `db_anomalies.py` |
| 7 | `depromote_known_signal()` funktion | `db_anomalies.py` |
| 8 | Bedre trace-capture i `record_anomaly()` — `_full_trace()` + `force` parameter | `central_anomaly.py` |
| 9 | Kald `promote_to_known()` efter bump i `record_anomaly_signature()` | `db_anomalies.py` |
| 10 | Known-signal check i `record_anomaly()` før anomaly-log (guard) | `central_anomaly.py` |
| 11 | `known_signals` + `resolve_and_route` + `depromote` actions i central_query | `central_query_tool.py` |
| 12 | `realtime_snapshot()` — tilføj `known_signals` felt | `central_realtime.py` |
| 13 | Integrationstest: anomaly → auto-promotion → forsvinder fra anomalies | test |

## 8. Self-review & fund

**Dato:** 2026-06-30
**Reviewer:** Jarvis (automatisk deep_analyze + manuel gennemgang)

| # | Fund | Alvor | Handling |
|---|---|---|---|
| 1 | **Manglende `known_signal`-filter i `list_anomalies()`.** `list_anomalies(unresolved_only=True)` returnerer i dag alle u-resolved — inkl. dem med `known_signal=1`. Skal have `exclude_known: bool = True` parameter så promoted signaler filtreres fra. | **høj** | Tilføj `exclude_known=True` som default i `list_anomalies()` |
| 2 | **Manglende flow: hvad sker når et kendt signal fyres IGEN?** Spec'en siger "promoveres" men ikke hvad der sker ved næste exception på samme signatur. Efter promotion skal `record_anomaly()` tjekke `known_anomaly_signals` — hvis signatur findes → send observe til den routede nerve i stedet for at logge som anomali. | **høj** | Tilføj data flow i §4: tjek known_signal FØR anomaly-log |
| 3 | **`realtime_snapshot()` mangler `known_signals`.** Centralens realtime snapshot bygger `anomalies` via `anomaly_summary()` men har i dag intet `known_signals` felt. Skal tilføjes i §3.6 så status fra central_query inkluderer dem. | **medium** | Tilføj `known_signals` i realtime_snapshot() + central_query.status (se §3.7) |
| 4 | **`log_and_ignore` kan blive en stille død.** Hvis en error auto-promoveres til `log_and_ignore` efter 50 forekomster, forsvinder den helt fra anomalier — en bug der burde fikses bliver usynlig. | **medium** | Omdøb `log_and_ignore` til `log_as_known` (mere ærligt), og tilføj en ugentlig summary i `central_learning` der lister alle aktive known_signals. |
| 5 | **Race condition: to processer promoverer samme signatur.** API og runtime deler SQLite DB. `known_anomaly_signals` har `signature TEXT PRIMARY KEY` — hvis begge INSERT samme signatur giver den ene UNIQUE constraint violation. | **medium** | Brug `INSERT OR IGNORE` i `promote_to_known()` så anden skriver taber stille. Funktionen skal returnere True ved succes. |
| 6 | **Auto-promotion til `route_to_nerve` mangler target-nerve.** Spec'en siger "promover som `route_to_nerve`" men ikke *hvilken* nerve. Skal have default: brug `category` (fx `log:KeyError`) som nerve-navn i "anomaly"-cluster. | **medium** | Default nerve = "anomaly/`{category}`". Tilføj i §3.3. |
| 7 | **Manglende depromovering.** Spec'en siger "sæt `known_signal=0`" men har intet tool til det. Hvis en routing var forkert, skal Bjørn kunne angre den. | **lav** | Tilføj `depromote_known_signal` action i central_query + funktion i db_anomalies. |
| 8 | **Tærskler ikke runtime-konfigurerbare.** `auto_threshold` og `auto_window_hours` er hardcodet som default-parametre. Skal kunne overstyres runtime. | **lav** | Læs threshold overrides fra `central_switches` scope="anomaly" (kan tilføjes senere). |
| 9 | **`_full_trace()` kan være for stor i sample-kolonnen.** 2000 tegn trace + 500 tegn sample = 2500 tegn i `sample`-kolonnen som i dag er `sample TEXT NOT NULL DEFAULT ''` (unlimited, men query-ydelse). Overvej at gemme trace i en separat `trace` kolonne, eller truncate til 1000 tegn. | **lav** | Gem trace i sample-feltet (det er ikke query-kritisk), max 2000 tegn. |
| 10 | **Test af auto-promotion kræver mock.** At vente på 10 forekomster i integrationstest er upraktisk. `promote_to_known()` bør kunne tvinges med `force=True` | **lav** | Tilføj `force: bool = False` parameter i `promote_to_known()` |

### 8.1 Samlet vurdering

Spec'en er **implementerbar** og har **ingen fatale huller**. De to høje fund (#1 og #2) skal
rettes før implementering (#1 er ét parameter, #2 er en tidlig guard i data flowet). De
medium-lav fund kan adresseres undervejs i implementeringen.

**Inkrementel sikkerhed:** Step 1 (central_query fix) kan implementeres ISOLERET uden
risiko. Step 2-6 (DB ændringer) er additive og bagudkompatible. Step 8 (kald promotion)
er det eneste der kan ændre adfærd — skal testes isoleret.

---

## 9. Eksempel — flow fra start til slut

1. **Første gang:** `operator_read_file ENOENT` fanges
   → `db_anomalies.py:` insert med count=1, is_new=True
   → `central_query status`: `anomalies: {counts: {total:1, medium:1}, recent: [...denne...]}`

2. **Efter 10. gang indenfor 24t:** `promote_to_known()` trigger
   → `known_signal=1`, `known_anomaly_signals` række oprettes
   → `central_query status`: `anomalies: {counts: {total:0}}`, `known_signals: [1 entry]`
   → Signatur forsvinder fra `anomalies.recent`, dukker op i `known_signals`

3. **Bjørn manuelt:** `central_query(action="resolve_and_route",
   signature="log:Error|...ENOENT...", cluster="tools", nerve="operator_tool_error")`
   → Fremtidige ENOENT-fejl sender observe til `tools/operator_tool_error`
   → Synligt i trace som `tools/operator_tool_error`, ikke som anomaly

---

## Review-rettelser (Claude, 2026-06-30)

Kode-review mod den faktiske Central afslørede tre ting spec'en under-specificerede:

- **R1 — `_full_trace` kræver tb-objektet, ikke `location`-strengen.** `record_anomaly()` modtager
  i dag kun `location: str` (allerede beregnet af kalderne via `_tb_location`). De fire hooks
  (`_excepthook`, `_thook`, asyncio-`_handler`, `_AnomalyLogHandler.emit`) skal beregne
  `_full_trace(tb)` og tråde en NY `trace: str = ""`-param igennem til `record_anomaly` →
  `record_anomaly_signature(sample=...)`. Uden dette har §3.6 ingen tb at arbejde på.
- **R2 — owner-gating mangler.** `central_query` er IKKE i `OWNER_ONLY_TOOLS`, og
  `central_switches.set_enabled` håndhæver kun sikkerheds-nerve-invarianten — IKKE owner-only.
  Så de EKSISTERENDE toggles er reelt ikke owner-gatede. ALLE muterende actions (toggles + §10's
  skrive-actions) skal have et eksplicit `effective_role() in ("owner","")`-check øverst i
  `central_query` (returnér `status=error, error="owner-only"` ellers). Read-actions forbliver åbne.
- **R3 — `promote_to_known()` behøver `count` efter bump.** `record_anomaly_signature` returnerer
  i dag kun `is_new: bool`. Den skal også returnere/oplyse `count` (eller promote_to_known slår det
  selv op) så tærskel-tjek virker. Valgt: `record_anomaly_signature` kalder selv `promote_to_known`
  efter bump (den har count i samme transaktion) → ingen ekstra round-trip.

## §10 — Jarvis' skrive-adgang til Centralen (fælles terminal)

I dag kan Jarvis kun LÆSE (`central_query` read-actions) + OBSERVERE (automatisk via nerverne).
Han mangler skrive-kanalen. Bjørn foretrækker ÉN indgang (actions i `central_query`) frem for et
separat `central_tell`-tool. Skrive-actions (alle **owner-gatet**, jf. R2):

| Action | Hvad | Backend |
|---|---|---|
| `resolve_and_route` | Anomali-signatur → nerve, fjern fra ukendt-listen (§3.9) | `route_anomaly_to_nerve` + `resolve_anomaly` |
| `depromote` | Angre en promotion (§3.10) | `depromote_known_signal` |
| `resolve_incident` | Luk incident N når verificeret håndteret | `resolve_central_incident(incident_id)` |
| `nerve_observe` | Injicér en observation direkte til en nerve (fund uden for hooks) | `central().observe({cluster,nerve,...})` |
| `note` | Fri-tekst note ind i Centralens bevidsthed (let "tell") | `central().observe({cluster:"central",nerve:"owner_note",text})` |

**Bevidst UDELADT (v1):** `toggle_breaker` (redundant — Jarvis kan isolere via eksisterende
`toggle_nerve`/`toggle_cluster`); fuld intentions-parser for `tell` (NLU-tolk der selv vælger
action — fremtid; `note` er den lette version nu); `learning_suggest` (central_learning er
observationelt — afventer en konkret skrive-API). Nye params til central_query: `signature`,
`action_type`, `notes`, `incident_id`, `text`, `importance`, `category`.

**Sikkerheds-invariant:** member/guest-sessioner (selv via Jarvis) kan ALDRIG mutere Centralen —
`effective_role()`-gaten fail-closer. Sikkerheds-nerver/-clusters forbliver u-slukbare (R2 ændrer
ikke central_switches' egen invariant).
