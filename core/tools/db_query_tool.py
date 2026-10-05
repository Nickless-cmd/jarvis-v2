"""`db_query` — laeseadgang til Jarvis' database, med skemaet i fejlen.

Boy Scout-udskillelse fra `simple_tools_native.py` (3.110 linjer) 5/10-2026.
`db_query` er en naturlig enhed: ét vaerktoej, én ansvarlighed.

## Hvorfor fejlen baerer skemaet

Maalt 5/10 over 7 dage: **185 af 777 db_query-kald fejlede (23,8 %)**, og
formerne var naesten alle gaet:

```
17 x  no such column: status
12 x  no such column: created_at
 8 x  no such table: heartbeat_ticks
18 x  Only SELECT statements are allowed
19 x  ⚠ «Det er N. tabel eller kolonne du gaetter forkert i denne tur»
```

Der fandtes allerede et puf der sagde «slaa skemaet op ÉN gang». Det puf
koster en RUNDE, og en runde koster ~7,7 s. Fejlen kender navnet der ikke
fandtes — saa den kan lige saa godt sige hvad der FINDES. Det gaar fra to
runder til én.

Og det er ikke en hypotetisk fejl: jeg lavede praecis den samme to gange paa
én time samme dag (`visible_runs.created_at` findes ikke, den hedder
`started_at`). Skemaet her er ikke til at gaette.
"""
from __future__ import annotations

import difflib
import json
import re
from typing import Any

#: Tabelnavne i en FROM/JOIN. Bevidst simpel: den skal finde navnene i en
#: almindelig forespoergsel, ikke parse SQL. Rammer den forbi, falder hintet
#: tilbage til tabel-listen — en daarligere hint, aldrig en fejl.
_TABEL_I_SQL = re.compile(r"\b(?:FROM|JOIN)\s+[\"'`\[]?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)

_MANGLER_TABEL = re.compile(r"no such table:\s*([A-Za-z0-9_.]+)", re.IGNORECASE)
_MANGLER_KOLONNE = re.compile(r"no such column:\s*([A-Za-z0-9_.]+)", re.IGNORECASE)

_MAKS_NAVNE = 40


def _json_safe_cell(v: Any) -> Any:
    """Coerce a raw SQLite cell value to a JSON-safe type. BLOB/bytes → utf-8
    text if decodable, else a short base64 placeholder. str/int/float/None are
    already JSON-safe and pass through untouched. Uden dette forgifter en
    BLOB-kolonne downstream json.dumps → 'Object of type bytes is not JSON
    serializable' → hele det synlige run crasher (set 2026-07-10)."""
    if isinstance(v, (bytes, bytearray)):
        b = bytes(v)
        try:
            return b.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            import base64
            preview = base64.b64encode(b).decode("ascii")
            if len(preview) > 88:
                preview = preview[:88] + "…"
            return f"<{len(b)} bytes base64:{preview}>"
    return v


def _tabeller(conn: Any) -> list[str]:
    raekker = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
    ).fetchall()
    return [str(r[0]) for r in raekker]


def _kolonner(conn: Any, tabel: str) -> list[str]:
    # Tabelnavnet kommer fra SQL'en, saa det maa ALDRIG interpoleres raat.
    # pragma_table_info tager det som en parameter.
    raekker = conn.execute(
        "SELECT name FROM pragma_table_info(?)", (tabel,)
    ).fetchall()
    return [str(r[0]) for r in raekker]


def skema_hint(conn: Any, fejl: str, sql: str) -> str:
    """De navne der FINDES, givet en fejl om et navn der ikke gjorde.

    Returnerer "" naar fejlen ikke handler om et manglende navn — et hint der
    gaetter paa alt er stoej.
    """
    m_tabel = _MANGLER_TABEL.search(fejl)
    if m_tabel:
        mangler = m_tabel.group(1)
        alle = _tabeller(conn)
        taet = difflib.get_close_matches(mangler, alle, n=5, cutoff=0.5)
        dele = [f"Tabellen {mangler!r} findes ikke."]
        if taet:
            # Er der et naert traef, ER det svaret. Maalt mod produktionens 307
            # tabeller: «heartbeat_ticks» fik «heartbeat_runtime_ticks» som
            # naermeste, og de 40 foerste tabelnavne derudover var 800 tegn der
            # ville ligge i historikken resten af turen uden at hjaelpe.
            dele.append(
                "Taettest paa: " + ", ".join(taet)
                + f". ({len(alle)} tabeller i alt.)"
            )
        else:
            dele.append(
                f"Alle {len(alle)} tabeller: " + ", ".join(alle[:_MAKS_NAVNE])
                + ("…" if len(alle) > _MAKS_NAVNE else "")
            )
        return " ".join(dele)

    m_kol = _MANGLER_KOLONNE.search(fejl)
    if not m_kol:
        return ""
    mangler = m_kol.group(1).split(".")[-1]
    nævnte = list(dict.fromkeys(_TABEL_I_SQL.findall(sql)))
    if not nævnte:
        return f"Kolonnen {mangler!r} findes ikke, og jeg kunne ikke se tabellen i SQL'en."
    dele = [f"Kolonnen {mangler!r} findes ikke."]
    for tabel in nævnte[:4]:
        kols = _kolonner(conn, tabel)
        if not kols:
            continue
        taet = difflib.get_close_matches(mangler, kols, n=3, cutoff=0.4)
        linje = f"{tabel} har: " + ", ".join(kols[:_MAKS_NAVNE])
        if taet:
            linje += f"  (taettest paa {mangler!r}: " + ", ".join(taet) + ")"
        dele.append(linje + ".")
    return " ".join(dele)


def _exec_db_query(args: dict[str, Any]) -> dict[str, Any]:
    """Run a read-only SELECT query against Jarvis' database."""
    sql = str(args.get("sql") or "").strip()
    params_raw = str(args.get("params") or "").strip()

    if not sql:
        return {"error": "sql is required", "status": "error"}

    # Security: only SELECT allowed — reject any write or schema-modifying statements
    sql_upper = sql.upper().lstrip()
    _FORBIDDEN = (
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
        "VACUUM", "REINDEX", "SAVEPOINT", "RELEASE", "ROLLBACK", "COMMIT", "BEGIN",
    )
    for keyword in _FORBIDDEN:
        if re.match(rf"\b{keyword}\b", sql_upper, re.IGNORECASE):
            return {
                "error": (
                    f"Only SELECT statements are allowed. '{keyword}' is not permitted. "
                    "db_query is read-only by design; use the tool that owns the write."
                ),
                "status": "error",
            }
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return {"error": "Only SELECT (or WITH ... SELECT) statements are allowed.", "status": "error"}

    params: list[Any] = []
    if params_raw:
        try:
            parsed = json.loads(params_raw)
            if not isinstance(parsed, list):
                return {"error": "params must be a JSON array, e.g. [\"value\", 42]", "status": "error"}
            params = parsed
        except Exception:  # json.JSONDecodeError og alt hvad en raa streng kan give
            return {"error": f"params is not valid JSON: {params_raw[:100]}", "status": "error"}

    from core.runtime.db import connect
    try:
        with connect() as conn:
            # `connect()` returns a POOLED thread-local connection (2026-07-12) — mutating
            # its row_factory poisons EVERY later query on this thread (e.g. decision_gate's
            # dict(sqlite3.Row) → ValueError "update sequence element has length N"; Central
            # RED 2026-07-13). zip(cols, row) works identically on a sqlite3.Row (iterable) as
            # on a raw tuple, so we don't even need row_factory=None — but if set, RESTORE it.
            _prev_factory = conn.row_factory
            try:
                cur = conn.execute(sql, params)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = cur.fetchmany(200)  # cap at 200 rows
                result_rows = [
                    {k: _json_safe_cell(v) for k, v in zip(cols, row)} for row in rows
                ]
            finally:
                conn.row_factory = _prev_factory  # never leave the shared conn poisoned
        from core.tools.tool_text_render import render_rows
        _capped = len(result_rows) == 200
        return {
            "columns": cols,
            "rows": result_rows,
            "row_count": len(result_rows),
            "capped": _capped,
            "status": "ok",
            "text": render_rows(cols, result_rows, capped=_capped),
        }
    except Exception as exc:
        fejl = str(exc)
        svar: dict[str, Any] = {"error": fejl, "status": "error"}
        # Skemaet med i fejlen. Et opslag ville koste en runde, og vi har
        # forbindelsen lige her. En fejl i selve hintet maa ALDRIG erstatte
        # den rigtige fejl — derfor sit eget try om ÉN saetning.
        try:
            with connect() as conn2:
                hint = skema_hint(conn2, fejl, sql)
        except Exception:  # skemaopslaget er en bonus; den rigtige fejl staar allerede i svaret
            hint = ""
        if hint:
            svar["hint"] = hint
            svar["error"] = f"{fejl} — {hint}"
        return svar
