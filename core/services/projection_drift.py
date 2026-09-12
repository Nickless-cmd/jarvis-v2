"""Drift-detektion — er ledgeren og `chat_messages` enige?

Spec: Fase 1, «drift detection reports no mismatch for canary fixtures».

## Hvad skygge-tilstanden er til for

I `shadow` skrives der BEGGE steder, og ledgeren afgør ingenting. Det er kun
værd at gøre hvis nogen faktisk SAMMENLIGNER. Uden en sammenligning er skyggen
bare dobbelt arbejde der giver falsk tryghed: man har skrevet begge steder i
uger og ved stadig ikke om de er enige.

Derfor er dette den funktion der bestemmer om et skifte må ske. Kriteriet er
ikke «ledgeren virker» — det er «ledgeren giver PRÆCIS det samme».

## Hvad der sammenlignes, og hvad der ikke gør

Sammenligningen sker på det der udgør samtalen: rolle, indhold, ræsonnement,
`content_json` og tidsstemplet — i rækkefølge. Alt det Fase 0 fandt at læserne
faktisk bruger.

Kompakt-markører tælles MED. De blev udeladt i første udgave, og det var en
fejl: de er `chat_messages`-rækker som alle andre, og en projektion der ikke
kendte dem, ville tabe dem ved et skifte. Produktionen har 102 af dem fordelt
på 14 sessioner — herunder en af de to kanarie-sessioner.

`message_id` sammenlignes IKKE. Det oprindelige skrive-kald finder sit id med
`uuid4()`, projektoren udleder sit af hændelsen — de kan aldrig blive ens, og
skulle heller ikke: id'et er en nøgle, ikke indhold. At kræve dem ens ville
gøre hver eneste session til en falsk uenighed og dermed gøre målingen
værdiløs.

## Den må ikke skrive noget

En sammenligning der ændrer det den måler, måler ikke. Derfor folder den til
en SIDESTILLET udregning i hukommelsen frem for at køre projektoren — at kalde
projektoren ville skrive rækkerne den skal sammenlignes med.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def _normaliser_json(v: Any) -> str:
    """`content_json` kan være tekst ét sted og et objekt et andet. Det er
    ikke uenighed om INDHOLD, kun om form — så begge sider måles som tekst
    med samme nøglerækkefølge."""
    if v in (None, ""):
        return ""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            return v
    try:
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(v)


def _felt(raekke: dict[str, Any], navn: str) -> str:
    if navn == "content_json":
        return _normaliser_json(raekke.get(navn))
    return str(raekke.get(navn) or "")


#: Navn → modul. Hver projektion beskriver sig selv med KIND, TABEL, NOEGLE
#: og SAMMENLIGN, så denne fil ikke behøver kende nogen af dem indefra.
_MODULER = {
    "chat_messages": "core.services.projection_chat_messages",
    "tool_router_decisions": "core.services.projection_tool_router",
}


def _modul(projektion: str):
    """Slå projektionen op. Et ukendt navn er en fejl, ikke et tomt svar —
    en sammenligning af ingenting ville melde «enige»."""
    import importlib
    sti = _MODULER.get(str(projektion or ""))
    if not sti:
        raise ValueError(
            f"ukendt projektion {projektion!r}; kendte: {sorted(_MODULER)}")
    return importlib.import_module(sti)


def _samme_tid(a: str, b: str) -> bool:
    """Samme øjeblik skrevet på to måder er ikke uenighed.

    Det gamle `tool_router`-skrivested brugte `datetime('now')`, som giver
    `2026-09-11 19:38:09` — mellemrum og ingen zone. Projektionen skriver ISO
    med `+00:00`. Uden denne sammenligning ville HVER eneste række se ud som
    en afvigelse, og drift-målingen ville være værdiløs netop dér hvor den
    skulle bruges.

    Den slører ikke ægte forskelle: den svarer kun sandt når de to strenge
    peger på det SAMME øjeblik. SQLites `datetime('now')` er altid UTC — den
    siger det bare ikke — så en naiv tid læses som UTC.
    """
    from datetime import datetime, timezone

    def _parse(v: str):
        t = str(v or "").strip()
        if not t:
            return None
        try:
            d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except ValueError:
            return None
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d

    da, db = _parse(a), _parse(b)
    return da is not None and db is not None and da == db


def _fra_ledger(session_id: str, m) -> list[dict[str, Any]]:
    """Fold i HUKOMMELSEN. At kalde projektoren ville skrive de rækker vi
    netop skal sammenligne med — og så målte vi vores eget svar."""
    from core.runtime.db_session_ledger import read_session_events

    ud: list[dict[str, Any]] = []
    for e in read_session_events(session_id):
        if str(e.get("kind") or "") != m.KIND:
            continue
        if m.valider(e.get("payload") or {}) is not None:
            continue
        ud.append(m._raekke(str(e["session_id"]), e))
    return ud


def _fra_tabellen(session_id: str, m) -> list[dict[str, Any]]:
    from core.runtime.db import connect
    kolonner = list(m.SAMMENLIGN)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(kolonner)} FROM {m.TABEL} "
            f"WHERE {m.NOEGLE} = ? ORDER BY id",
            (str(session_id or ""),),
        ).fetchall()
    return [dict(zip(kolonner, r)) for r in rows]


def compare(session_id: str, projektion: str = "chat_messages") -> dict[str, Any]:
    """Sammenlign de to sider. `enige` er svaret på om sessionen må skifte.

    Uenigheder returneres HVER FOR SIG med position og felt. En bool alene
    ville sige at noget er galt uden at sige hvad — og så bliver den ignoreret.
    """
    m = _modul(projektion)
    ledger = _fra_ledger(session_id, m)
    tabel = _fra_tabellen(session_id, m)

    uenigheder: list[dict[str, Any]] = []
    for i in range(max(len(ledger), len(tabel))):
        a = ledger[i] if i < len(ledger) else None
        b = tabel[i] if i < len(tabel) else None
        if a is None:
            uenigheder.append({"plads": i, "felt": "*", "ledger": None,
                               "tabel": _felt(b, m.SAMMENLIGN[0])})
            continue
        if b is None:
            uenigheder.append({"plads": i, "felt": "*", "ledger": _felt(a, m.SAMMENLIGN[0]),
                               "tabel": None})
            continue
        for f in m.SAMMENLIGN:
            if _felt(a, f) == _felt(b, f):
                continue
            if f == "created_at" and _samme_tid(_felt(a, f), _felt(b, f)):
                continue
            uenigheder.append({"plads": i, "felt": f,
                               "ledger": _felt(a, f)[:200],
                               "tabel": _felt(b, f)[:200]})

    return {
        "session_id": str(session_id),
        "projektion": str(projektion),
        "enige": not uenigheder,
        "ledger_beskeder": len(ledger),
        "tabel_beskeder": len(tabel),
        "uenigheder": uenigheder,
        # BEVIS ER IKKE DET SAMME SOM ENIGHED (fase 11). `enige` er sandt naar
        # der ingen uenigheder er — ogsaa naar der ingenting er at vaere uenig
        # om. MAALT 10/9-2026: kanariefuglen sad paa to sessioner der havde
        # vaeret DOEDE i 20 timer, og timepulsen meldte «ledger enige (+0)»
        # hver time. Det lyder som loebende verifikation og er tavshed.
        #
        # Et skifte maa aldrig hvile paa tavshed, saa dommen staar for sig:
        #   "verificeret"  — der ER sammenlignede beskeder, og de stemmer
        #   "intet-bevis"  — ingen af siderne har noget
        #   "uenig"        — der er fundet forskelle
        "bevis": ("uenig" if uenigheder
                  else ("verificeret" if (ledger and tabel) else "intet-bevis")),
        "nyeste_ledger": _nyeste(ledger),
        "nyeste_tabel": _nyeste(tabel),
    }


def _nyeste(raekker: list) -> str:
    """Tidsstemplet paa den nyeste raekke — saa en laeser kan se om «enige»
    hviler paa noget der skete i dag eller i sidste uge."""
    nyeste = ""
    for r in raekker or []:
        t = str((r or {}).get("created_at") or "") if isinstance(r, dict) else ""
        if t > nyeste:
            nyeste = t
    return nyeste


def may_cut_over(session_id: str, projektion: str = "chat_messages") -> tuple[bool, str]:
    """Må denne session skifte til `ledger`?

    Tre ting skal holde, og de er alle tre negative erfaringer:

    * Ledgeren må ikke være TOM. En tom ledger og en tom sammenligning ser ens
      ud — og et skifte dér ville gøre en samtale til ingenting.
    * Siderne skal være enige.
    * Sessionen skal allerede være i `shadow`. Et spring direkte fra `legacy`
      ville betyde at ledgeren aldrig har været prøvet mod virkeligheden.
    """
    from core.runtime.db_session_ledger import storage_mode

    mode = storage_mode(session_id)
    if mode != "shadow":
        return False, f"sessionen er {mode!r}, ikke 'shadow'"
    r = compare(session_id, projektion)
    if r["ledger_beskeder"] == 0:
        return False, "ledgeren er tom — en tom sammenligning beviser ingenting"
    if not r["enige"]:
        return False, f"{len(r['uenigheder'])} uenighed(er), første: {r['uenigheder'][0]}"
    return True, f"{r['ledger_beskeder']} beskeder, ingen uenigheder"
