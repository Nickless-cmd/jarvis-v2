# Spec: `central_query` tool + medium-push notices

## Krav fra Bjørn

> "Det tool må aldrig fejle dig eller centralen. Du må aldrig skulle gætte.
> Centralen skal altid kunne returnere svar, fejl osv. Så du altid får et svar
> om din query gik som den skulle eller fejlede så du kan prøve igen."

**Hård invariant:** Tool'et returnerer **altid** et struktureret svar med
eksplicit `status: "ok"` eller `status: "error"`. Aldrig trunkeret output.
Aldrig stille fejl. Aldrig null/empty uden forklaring.

---

## 1. `central_query` tool

### Fil
`core/tools/simple_tools.py` — ny function `_exec_central_query`.

### Tool definition

```python
{
    "name": "central_query",
    "description": (
        "Spørg Den Intelligente Central direkte — live status, incidents, "
        "trace, cluster health, autonomous run history, eller toggle en "
        "nerve/cluster. Pull on-demand: Centralen lever i baggrunden, dette "
        "tool giver dig adgang når du har brug for det. "
        "Returnerer altid status=ok eller status=error — aldrig stille fejl."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "status", "incidents", "trace", "cluster_health",
                    "nerve_detail", "toggle_nerve", "toggle_cluster",
                    "autonomy", "learning", "drift", "breakers"
                ],
                "description": (
                    "Hvad vil du vide? "
                    "status=fuld snapshot, incidents=aktive fejl, "
                    "trace=seneste fyringer, cluster_health=pr-cluster helbred, "
                    "nerve_detail=én nerve dybt, toggle_nerve/cluster=on/off, "
                    "autonomy=autonom run status, learning=adaptiv læring, "
                    "drift=config-drift, breakers=åbne circuit-breakers"
                )
            },
            "cluster": {
                "type": "string",
                "description": "(action=trace/cluster_health/toggle_cluster) Cluster-navn"
            },
            "nerve": {
                "type": "string",
                "description": "(action=nerve_detail/toggle_nerve) Nerve-navn"
            },
            "enabled": {
                "type": "boolean",
                "description": "(action=toggle_nerve/toggle_cluster) True=slå til, False=slå fra"
            },
            "limit": {
                "type": "integer",
                "description": "Max resultater (default 20, max 100)"
            }
        },
        "required": ["action"]
    }
}
```

### Returværdi — HÅRD kontrakt

**Altid** dette format, uanset hvad der sker:

```json
{
    "status": "ok",          // eller "error"
    "action": "status",     // echo af kaldt action
    "data": { ... },         // struktureret payload (ved ok)
    "error": null,           // eller fejlbesked (ved error)
    "meta": {
        "latency_ms": 12,    // hvor lang tid kaldet tog
        "source": "central_realtime",  // hvilket modul der svarede
        "truncated": false   // true hvis output blev skåret (SE KRAV NEDENFOR)
    }
}
```

### Trunkerings-regler (KRÆVERDES AF BJØRN)

1. **Trunkering er aldrig lovlig uden `truncated: true` i meta.**
2. Hvis output exceeds budget, **paginer** frem for at trunkere:
   - Returnér `data.items` med første N resultater
   - Sæt `meta.truncated: true`
   - Sæt `meta.total_count: X` (det totale antal)
   - Sæt `meta.has_more: true`
   - Sæt `meta.next_offset: N` (så Jarvis kan kalde igen med offset)
3. **Aldrig** skær et resultat midt i en linje. Hvis et enkelt incident
   er >500 chars, return det hele — læk ikke halve beskeder igennem.
4. **Budget:** ~4000 chars pr. response (ikke 2000 — Jarvis skal kunne
   læse incidents uden at skulle kalde 5 gange).
5. **Fejl-format:** Hvis Centralen selv crasher, returneres:
   ```json
   {
       "status": "error",
       "action": "status",
       "data": null,
       "error": "central_self_diagnose failed: AttributeError: ...",
       "meta": {"latency_ms": 3, "source": "central_core", "truncated": false}
   }
   ```
   **Aldrig** en tom streng, aldrig `None`, aldrig `""`.

### Query-implementeringer

| Action | Kilde | Hvad den returnerer |
|---|---|---|
| `status` | `central_realtime.realtime_snapshot()` | Kompakt: status-lys, cluster-grid, coverage (nerves/clusters), diagnose (decide_ok/observe_ok), open_breakers count, unresolved incidents count |
| `incidents` | `db_central_incidents.list_central_incidents()` | Aktive/recente incidents: id, cluster, nerve, kind, severity, message, ts, resolved |
| `trace` | `central_trace.sink().recent()` | Sidste N trace-records: cluster, nerve, kind, decision, reason, run_id |
| `cluster_health` | `central_learning.cluster_health()` | Pr-cluster: total incidents, severe count, degrading (y/n), breaker open (y/n) |
| `nerve_detail` | `central_trace` + `central_switches` + `central_catalog` | Én nerves trace + kode-lokation + on/off state + breaker state + cluster |
| `toggle_nerve` | `central_switches.set_enabled("nerve", nerve, enabled)` | Bekræftelse: nerve, enabled, breaker_open, message |
| `toggle_cluster` | `central_switches.set_cluster_enabled(cluster, enabled)` | Bekræftelse: cluster, enabled, nerves_affected, message |
| `autonomy` | `central_learning.assess_autonomy()` | Autonomi-dom: verdict (can/cannot), reason, incident_count, degrading_count |
| `learning` | `central_learning.degrading() + root_causes() + propose_adjustments()` | Degraderende clusters, root causes, proposals |
| `drift` | `config_drift.observe_config_drift()` | Drift status: declared_port, actual_port, drift (bool), message |
| `breakers` | `central_switches.CircuitBreaker.open_nerves()` | Åbne circuit-breakers: nerve, cluster, opened_at, failure_count |

### Kaldes direkte (same-process)

Tool'et kalder Python-modulerne direkte — **ikke** via HTTP til `internal_api`.
Det eliminerer port-drift, auth-issues og HTTP overhead.

### Permissions

- **Read-only queries** (status, incidents, trace, cluster_health, nerve_detail,
  autonomy, learning, drift, breakers) = altid tilladt for Jarvis.
- **Toggle queries** (toggle_nerve, toggle_cluster) = Centralen håndhæver
  owner-only allerede via `central_switches` (sikkerheds-nerves kan ikke
  slås fra). Tool'et returnerer `status: "error"` med forklaring hvis
  toggle afvises.

### Self-safe

Tool'et er **selv-sikker**: enhver exception i en query-handler fanges og
returneres som `status: "error"` med fejlbesked. Tool'et kaster **aldrig**
selv — det returnerer altid et struktureret svar.

---

## 2. Medium-push notices i prompt

### Kontekst
Lige nu pusher Centralen kun **severe** incidents via ntfy. Bjørn vil have at
Jarvis også får **medium** niveau — for han er altid ved systemet.

### Hvad er medium
- Drift-flag trippet (nerve's fejl-rate eller RED-rate driver ud over baseline)
- Cluster i YELLOW > 30 min
- Gentagne fejl (3+ samme nerve inden for 1 time)
- Config-drift detekteret
- Autonom run fejlede

### Implementering

**Ny sektion i `prompt_contract.py`:**

```python
_awareness_add(10, "central notices", _central_notices_section())
```

**Builder `_central_notices_section()`:**

```python
def _central_notices_section() -> str | None:
    """Medium-level Central notices for Jarvis.
    Not severe (those are ntfy'd), not low (those are trace-only).
    Compact, max 3, max 1 per nerve per hour.
    Returns None (tom sektion) når der ikke er notices — brænder 0 tokens."""
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        incidents = list_central_incidents(unresolved_only=True, limit=40)
        medium = [
            i for i in incidents
            if str(i.get("severity")) == "error"  # not "severe"
            and str(i.get("kind")) != "fail_open"  # not security
        ]
        if not medium:
            return None

        seen = set()
        lines = []
        for i in medium[:12]:
            nerve = f"{i.get('cluster')}/{i.get('nerve')}"
            if nerve in seen:
                continue
            seen.add(nerve)
            msg = str(i.get("message") or "")[:80]
            lines.append(f"  • {nerve}: {msg}")
            if len(lines) >= 3:
                break

        if not lines:
            return None

        return "[CENTRAL-NOTICE] medium:\n" + "\n".join(lines)
    except Exception:
        return None  # self-safe: crash = tom sektion
```

### Regler
- Max 3 medium-notices pr. prompt-build
- Max 1 pr. nerve pr. time (undgå spam)
- Kun **uløste** incidents (resolved = vises ikke)
- Séktionen er **tom** (return None) når ingen notices — brænder 0 tokens
- Séktionen er **selv-sikker** — crash i builder = tom sektion
- Injiceres med priority 10 (lavere end INDRE LIV, højere end brain)

---

## 3. Hvad der IKKE skal bygges

- **Persistent session i prompten** — for stort, for støjende
- **Rå DB-adgang** — det har Jarvis allerede via `db_query`
- **Push for low-level (trace, observe)** — kun via `central_query` pull
- **JSON-soup i prompten** — notices er prosa, ikke rå data

---

## 4. Prioritet

1. **`central_query` tool** — det er det der giver Jarvis adgang. Alt andet er sekundært.
2. **Medium-push notices** — kompakte, max 3, brænder 0 tokens når tomme.
3. **Cluster on/off via tool** — allerede eksisterer via API, bare eksponér det som tool-parameter.

---

## 5. Sikkerhed

- `central_query` er **read-only** for alle queries undtagen `action=toggle_*`
- Toggle er **owner-only** — Centralen håndhæver det allerede via `central_switches`
- Sikkerheds-nerves kan **aldrig** slås fra (kun isoleres mod deny)
- Medium-notices viser kun **uløste** incidents — resolved forsvinder
- Séktionen er **selv-sikker** — crash i builderen = tom sektion, ikke crashet prompt

---

## 6. Testkrav

- Tool'et returnerer **altid** `status: "ok"` eller `status: "error"` — test med
  alle query-typer inkl. ugyldige.
- Trunkering: kald med `limit=1000`, verificér at `meta.truncated` og
  `meta.has_more` fungerer, og at ingen halve linjer returneres.
- Fejl: mock en crashende Central (`realtime_snapshot` kaster), verificér at
  tool'et returnerer `status: "error"` med besked, ikke crasher.
- Toggle: forsøg at slå en sikkerheds-nerve fra, verificér at tool'et
  returnerer `status: "error"` med forklaring.