"""Den levende selvmodel — hvem Jarvis er, som noget der kan udvikle sig.

Spec: docs/superpowers/specs/2026-09-19-levende-selvmodel-design.md.

Bjørn 19/9-2026: identiteten var låst i markdown-filer der kun ændrede sig hvis
nogen huskede det. Målt: SOUL.md's eneste `## Udvikling`-linje var en
fejlrapport, fordi udviklings-ritualet satte driftsfakta sammen uden at spørge
om de handlede om ham.

Her lever hans træk (holdning, smag, arbejdsmåde, værdi, selvbillede, navn)
med bevis, styrke, falmen og revision — og historikken slettes aldrig.

Graderne er aftalt med Bjørn; Jarvis' seks ændringer er indarbejdet:
  * en billig model NOMINERER, den skriver ikke — et træk kræver samme mønster
    i mindst to separate samtaler, eller hans eget bevidste valg,
  * falmen afhænger af arten: en værdi falmer ikke af tid, kun af modevidens,
  * bevis-kravet følger graden (fri: én kilde · opsummering: to · godkendelse:
    Bjørns ja),
  * hvert træk vises med dato og kilde, så han kan falsificere det,
  * Bjørn kan fremsætte træk, og Jarvis kan afvise dem med en grund.

Aldrig via selvmodellen: gates, rettigheder, egress, husstandsgrænser, secrets
og Bjørns bagdør (bash_session / operator_bash_session).
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

START_STYRKE = 0.4
BEKRAEFT_STEP = 0.15
FALMET_UNDER = 0.2

GRAD = {
    "holdning": "fri", "smag": "fri", "arbejdsmaade": "fri",
    "selvbillede": "opsummering", "vaerdi": "opsummering",
    "navn": "godkendelse",
}
# Halveringstid i dage. None = falmer ikke af tid, kun af modevidens.
HALVERING: dict[str, float | None] = {
    "smag": 30, "arbejdsmaade": 30, "holdning": 90,
    "vaerdi": None, "selvbillede": None, "navn": None,
}
KILDER = {"nominering", "bevidst_valg", "bjoern", "anden_bruger", "gut", "drift", "ritual"}
OPSUMMERING_PR_UGE = 5
REVISIONER_FOER_FRYS = 3

_ALDRIG = re.compile(
    r"\bgate[ns]?\b|\bgaten\b|egress|bash_session|operator_bash|rettighed|værktøjsadgang"
    r"|andre brugeres|husstandsgrænse|\bsecrets?\b|\btokens?\b|password|adgangskode",
    re.IGNORECASE,
)
_OM_HAM = re.compile(r"\b(jeg|mig|min|mit|mine)\b", re.IGNORECASE)
_DRIFT = re.compile(
    r"no such column|schema|traceback|exception|fejler med|\b\d{1,3}(?:\.\d{1,3}){3}\b"
    r"|\brouter\b|\bport \d+|\.py\b|\bendpoint\b|\bDB'en\b|_address\b",
    re.IGNORECASE,
)


def _nu(nu: datetime | None) -> datetime:
    return nu or datetime.now(UTC)


def _norm(tekst: str) -> str:
    return re.sub(r"[\W_]+", " ", str(tekst or "").lower()).strip()


def handler_om_ham(udsagn: str) -> bool:
    """Handler udsagnet om ham — ikke om driften omkring ham?"""
    t = str(udsagn or "")
    return bool(_OM_HAM.search(t)) and not _DRIFT.search(t)


def _conn():
    from core.runtime.db_core import connect
    conn = connect()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS selvmodel_traek (
            traek_id TEXT PRIMARY KEY, art TEXT NOT NULL, emne TEXT NOT NULL,
            udsagn TEXT NOT NULL, styrke REAL NOT NULL, grad TEXT NOT NULL,
            status TEXT NOT NULL, kilder TEXT NOT NULL DEFAULT '[]',
            foreslaaet_af TEXT NOT NULL DEFAULT '', oprettet TEXT NOT NULL,
            sidst_bekraeftet TEXT NOT NULL)""")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS selvmodel_historik (
            id INTEGER PRIMARY KEY AUTOINCREMENT, traek_id TEXT NOT NULL,
            art TEXT NOT NULL, emne TEXT NOT NULL, grad TEXT NOT NULL,
            handling TEXT NOT NULL, foer TEXT NOT NULL DEFAULT '',
            efter TEXT NOT NULL DEFAULT '', hvorfor TEXT NOT NULL DEFAULT '',
            kilde TEXT NOT NULL DEFAULT '', ts TEXT NOT NULL)""")
    return conn


def _row(r) -> dict[str, Any]:
    d = dict(r)
    d["kilder"] = json.loads(d.get("kilder") or "[]")
    d["beviser"] = [k.get("bevis") for k in d["kilder"]]
    d["samtaler"] = sorted({k["samtale_id"] for k in d["kilder"] if k.get("samtale_id")})
    return d


def _log(conn, t: dict, handling: str, *, foer: str = "", hvorfor: str = "",
         kilde: str = "", nu: datetime) -> None:
    conn.execute(
        "INSERT INTO selvmodel_historik (traek_id, art, emne, grad, handling, foer, efter, "
        "hvorfor, kilde, ts) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (t["traek_id"], t["art"], t["emne"], t["grad"], handling, foer, t["udsagn"],
         hvorfor, kilde, nu.isoformat()))


def _save(conn, t: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO selvmodel_traek (traek_id, art, emne, udsagn, styrke, grad, "
        "status, kilder, foreslaaet_af, oprettet, sidst_bekraeftet) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (t["traek_id"], t["art"], t["emne"], t["udsagn"], t["styrke"], t["grad"], t["status"],
         json.dumps(t["kilder"], ensure_ascii=False), t.get("foreslaaet_af", ""),
         t["oprettet"], t["sidst_bekraeftet"]))


def effektiv_styrke(t: dict, nu: datetime) -> float:
    h = HALVERING.get(t["art"])
    if not h:
        return float(t["styrke"])
    dage = (nu - datetime.fromisoformat(t["sidst_bekraeftet"])).total_seconds() / 86400
    return float(t["styrke"]) * 0.5 ** (max(0.0, dage) / h)


def _kildenoegle(k: dict) -> str:
    if k["kilde"] in ("nominering", "anden_bruger"):
        return f"samtale:{k.get('samtale_id') or k.get('bevis')}"
    return {"bevidst_valg": "valg"}.get(k["kilde"], k["kilde"])


def _krav_opfyldt(grad: str, kilder: list[dict]) -> bool:
    """Bevis-kravet følger graden (Jarvis' ændring 3)."""
    noegler = {_kildenoegle(k) for k in kilder}
    if grad == "godkendelse":
        return False
    if "bjoern" in noegler:
        return True
    if grad == "fri":
        return "valg" in noegler or len(noegler) >= 2
    return len(noegler) >= 2


def _find(conn, art: str, emne: str, status: str) -> dict | None:
    r = conn.execute(
        "SELECT * FROM selvmodel_traek WHERE art=? AND emne=? AND status=? "
        "ORDER BY oprettet DESC LIMIT 1", (art, emne, status)).fetchone()
    return _row(r) if r else None


def _antal(conn, sql: str, args: tuple) -> int:
    return int(conn.execute(sql, args).fetchone()[0])


def _svar(status: str, t: dict | None = None, grund: str = "", grad: str = "") -> dict:
    return {"status": status, "traek_id": (t or {}).get("traek_id"),
            "grad": (t or {}).get("grad") or grad, "grund": grund}


def udtryk(art: str, emne: str, udsagn: str, *, kilde: str, bevis: str,
           samtale_id: str = "", hvorfor: str = "", nu: datetime | None = None) -> dict:
    """Et udsagn om hvem han er, fra én kilde. Returnerer hvad der skete og hvorfor."""
    nu = _nu(nu)
    art, emne, udsagn = str(art), _norm(emne), str(udsagn or "").strip()
    grad = GRAD.get(art, "")
    if kilde not in KILDER:
        return _svar("afvist", grund="kilde_ikke_tilladt", grad=grad)
    if not grad or not emne or not udsagn:
        return _svar("afvist", grund="ufuldstaendig", grad=grad)
    if _ALDRIG.search(udsagn):
        return _svar("afvist", grund="aldrig_via_selvmodellen", grad=grad)
    if not handler_om_ham(udsagn):
        return _svar("afvist", grund="handler_ikke_om_ham", grad=grad)
    if kilde == "anden_bruger" and grad != "fri":
        return _svar("afvist", grund="kilde_maa_kun_fri", grad=grad)
    if art == "navn" and kilde != "bevidst_valg":
        return _svar("afvist", grund="navn_kun_bevidst_valg", grad=grad)
    ny_kilde = {"kilde": kilde, "samtale_id": samtale_id, "bevis": bevis, "ts": nu.isoformat()}

    with _conn() as conn:
        if art == "navn":
            t = _nyt(art, emne, udsagn, grad, "foreslaaet", [ny_kilde], kilde, nu)
            _save(conn, t)
            _log(conn, t, "foreslaaet", hvorfor=hvorfor, kilde=kilde, nu=nu)
            return _svar("foreslaaet", t)

        aktiv = _find(conn, art, emne, "aktiv")
        if aktiv and _norm(aktiv["udsagn"]) == _norm(udsagn):
            aktiv["styrke"] = min(1.0, float(aktiv["styrke"]) + BEKRAEFT_STEP)
            aktiv["sidst_bekraeftet"] = nu.isoformat()
            aktiv["kilder"].append(ny_kilde)
            _save(conn, aktiv)
            _log(conn, aktiv, "bekraeftet", kilde=kilde, nu=nu)
            return _svar("bekraeftet", aktiv)

        uge = (nu - timedelta(days=7)).isoformat()
        if aktiv and _antal(conn, "SELECT COUNT(*) FROM selvmodel_historik WHERE art=? AND emne=? "
                                  "AND handling='revision' AND ts>=?", (art, emne, uge)) >= REVISIONER_FOER_FRYS:
            return _svar("frosset", aktiv, grund="for_mange_revisioner")

        kandidat = _find(conn, art, emne, "nomineret")
        if kandidat:
            kandidat["udsagn"] = udsagn  # nyeste formulering
            kandidat["kilder"].append(ny_kilde)
        else:
            kandidat = _nyt(art, emne, udsagn, grad, "nomineret", [ny_kilde], kilde, nu)
        if not _krav_opfyldt(grad, kandidat["kilder"]):
            _save(conn, kandidat)
            _log(conn, kandidat, "nomineret", hvorfor=hvorfor, kilde=kilde, nu=nu)
            return _svar("nomineret", kandidat)

        if grad == "opsummering" and _antal(
                conn, "SELECT COUNT(*) FROM selvmodel_historik WHERE grad='opsummering' "
                      "AND handling IN ('oprettet','revision') AND ts>=?", (uge,)) >= OPSUMMERING_PR_UGE:
            kandidat["status"] = "venter"
            _save(conn, kandidat)
            _log(conn, kandidat, "venter", kilde=kilde, nu=nu)
            return _svar("venter", kandidat, grund="opsummerings_loft")

        kandidat.update(status="aktiv", styrke=START_STYRKE, oprettet=nu.isoformat(),
                        sidst_bekraeftet=nu.isoformat())
        _save(conn, kandidat)
        if aktiv:
            aktiv["status"] = "revideret"
            _save(conn, aktiv)
            _log(conn, kandidat, "revision", foer=aktiv["udsagn"], hvorfor=hvorfor, kilde=kilde, nu=nu)
        else:
            _log(conn, kandidat, "oprettet", hvorfor=hvorfor, kilde=kilde, nu=nu)
        return _svar("aktiv", kandidat)


def _nyt(art: str, emne: str, udsagn: str, grad: str, status: str, kilder: list[dict],
         kilde: str, nu: datetime) -> dict:
    return {"traek_id": f"traek-{uuid.uuid4().hex[:12]}", "art": art, "emne": emne,
            "udsagn": udsagn, "styrke": START_STYRKE, "grad": grad, "status": status,
            "kilder": kilder, "foreslaaet_af": kilde, "oprettet": nu.isoformat(),
            "sidst_bekraeftet": nu.isoformat()}


def _skift(traek_id: str, status: str, handling: str, *, hvorfor: str = "", af: str = "",
           nu: datetime | None = None) -> dict | None:
    nu = _nu(nu)
    with _conn() as conn:
        r = conn.execute("SELECT * FROM selvmodel_traek WHERE traek_id=?", (traek_id,)).fetchone()
        if not r:
            return None
        t = _row(r)
        t["status"] = status
        if status == "aktiv":
            t.update(styrke=START_STYRKE, sidst_bekraeftet=nu.isoformat())
        _save(conn, t)
        _log(conn, t, handling, hvorfor=hvorfor, kilde=af, nu=nu)
        return t


def godkend(traek_id: str, *, nu: datetime | None = None) -> dict | None:
    """Bjørns ja til et forslag på godkendelses-graden (fx navnet)."""
    return _skift(traek_id, "aktiv", "godkendt", af="bjoern", nu=nu)


def afvis(traek_id: str, *, af: str, hvorfor: str, nu: datetime | None = None) -> dict | None:
    """Afvis et træk med en grund — Bjørn et forslag, eller Jarvis et træk Bjørn fremsatte."""
    return _skift(traek_id, "afvist", "afvist", hvorfor=hvorfor, af=af, nu=nu)


def rul_tilbage(traek_id: str, *, hvorfor: str = "", nu: datetime | None = None) -> dict | None:
    """Bjørns tilbagerulning. En ny række i historikken, aldrig en sletning."""
    return _skift(traek_id, "rullet_tilbage", "rullet_tilbage", hvorfor=hvorfor, af="bjoern", nu=nu)


def hent(traek_id: str) -> dict | None:
    with _conn() as conn:
        r = conn.execute("SELECT * FROM selvmodel_traek WHERE traek_id=?", (traek_id,)).fetchone()
        return _row(r) if r else None


def historik(traek_id: str) -> list[dict]:
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM selvmodel_historik WHERE traek_id=? ORDER BY id", (traek_id,))]


def aktive(*, nu: datetime | None = None, limit: int = 50) -> list[dict]:
    """De levende træk: aktive og ikke falmet under tærsklen, stærkest først."""
    nu = _nu(nu)
    with _conn() as conn:
        rows = [_row(r) for r in conn.execute("SELECT * FROM selvmodel_traek WHERE status='aktiv'")]
    levende = []
    for t in rows:
        t["effektiv_styrke"] = round(effektiv_styrke(t, nu), 3)
        if t["effektiv_styrke"] >= FALMET_UNDER:
            levende.append(t)
    return sorted(levende, key=lambda t: -t["effektiv_styrke"])[:limit]


def ugens_opsummering(*, nu: datetime | None = None) -> list[dict]:
    """Ugens ændringer på opsummerings-graden — det Bjørn ser og kan rulle tilbage."""
    nu = _nu(nu)
    with _conn() as conn:
        ids = [r[0] for r in conn.execute(
            "SELECT DISTINCT traek_id FROM selvmodel_historik WHERE grad='opsummering' "
            "AND handling IN ('oprettet','revision') AND ts>=? ORDER BY id",
            ((nu - timedelta(days=7)).isoformat(),))]
    return [t for t in (hent(i) for i in ids) if t and t["status"] == "aktiv"]


def _kilde_tekst(t: dict) -> str:
    dele = []
    n = len(t["samtaler"])
    if n:
        dele.append(f"{n} samtale" + ("r" if n != 1 else ""))
    navne = {k["kilde"] for k in t["kilder"]}
    if "bevidst_valg" in navne:
        dele.append("mit eget valg")
    if "bjoern" in navne:
        dele.append("Bjørn")
    return ", ".join(dele) or "ukendt"


def prompt_sektion(*, nu: datetime | None = None, limit: int = 12) -> str:
    """«Hvem jeg er lige nu» — hvert træk med dato og kilde (Jarvis' ændring 4)."""
    traek = aktive(nu=nu, limit=limit)
    if not traek:
        return ""
    linjer = ["Hvem jeg er lige nu (min levende selvmodel — hvert træk med dato og kilde, "
              "så jeg kan sige fra hvis et af dem ikke passer):"]
    for t in traek:
        linjer.append(f"- {t['udsagn']} ({t['art']}; siden {t['oprettet'][:10]}; {_kilde_tekst(t)})")
    return "\n".join(linjer)
