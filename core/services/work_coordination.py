"""Arbejdskoordinering: «er det jeg overvejer allerede dækket af eksisterende arbejde?»

ÅRSAG (målt 24/11-2026, se DEVLOG): et initiativ bærer kun en TEKST. Ordlyds-
dedup (`initiative_queue._gentaget_paastand`) ser kun sin egen kø, og
30-minutters-porten ser kun at en samtale fandt sted — ikke HVAD den arbejdede
på. Ingen af dem kan svare på spørgsmålet, så den ene blev for løs (samme emne
= dublet) og den anden for grov (al aktivitet = konflikt).

Dette modul genbruger de eksisterende identiteter — `runtime_tasks` (atomisk
claim + lease + reaper), `agent_assignments` og `visible_runs` — og tilføjer
kun ét: et **arbejdsfingeraftryk** der bygger på KONKRETE relationer
(id'er, filer, kode-identifikatorer) + HANDLINGSKLASSE, ikke på emneord.

* To formuleringer af samme handling på samme anker → samme fingeraftryk.
* Samme emne men forskellig handling (verificér vs. skriv test) → forskellige.
* Intet anker eller ingen genkendelig handling → intet fingeraftryk, og så
  gætter vi ikke: initiativet går fri (hellere en dublet end et tabt initiativ).
* Fingeraftrykket er scopet til bruger; privat arbejde krydser aldrig brugere.
  Svaret indeholder kun referencer (id, art, status) — aldrig indhold.

Hver beslutning publiceres som `coordination.decision` med årsag, så ingen
afvisning er tavs.
"""
from __future__ import annotations

import hashlib
import math
import re
import sqlite3
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any

SYSTEM_SCOPE = "system"

#: Hvor længe en blokeret opgave tæller som «afventer noget». Ældre → genoptag.
_BLOKERET_FRISK_TIMER = 6
#: En afsluttet opgave dækker samme arbejde så længe — derefter kræver det ikke
#: ny evidens at gøre det igen (verdenen har flyttet sig).
_AFSLUTTET_FRISK_TIMER = 24
#: Synlig samtale: så længe tæller dens arbejde som «igangværende».
_SYNLIG_VINDUE_MINUTTER = 30

_ID_RE = re.compile(r"\b(?:task|asg|init|dec|run|flow|agent|visible|autonomous)-[0-9a-f]{6,}\b")
_COMMIT_RE = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
_FIL_RE = re.compile(r"[\w./-]*\w\.(?:py|md|json|ts|tsx|db|yaml|yml|sh|sql|toml)\b")
_SNAKE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_CAMEL_RE = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")
_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Handlingsklasser: STAMMER af verber, ikke sætningsstart. Første forekomst i
#: teksten afgør klassen, så en refleksion der indeholder en konkret handling
#: stadig genkendes (se `action_class`).
_HANDLINGER: dict[str, tuple[str, ...]] = {
    "verify": ("verific", "verify", "tjek", "check", "undersoeg", "investigat",
               "bekraeft", "confirm", "inspic", "inspect", "gennemgaa", "review",
               "valider", "validate", "afklar"),
    "fix": ("ret", "rette", "fix", "reparer", "repair", "patch", "luk"),
    "write": ("skriv", "write", "tilfoej", "add", "implement", "opret", "create",
              "lav", "byg", "build"),
    "measure": ("maal", "measure", "taell", "count", "profil"),
    "search": ("soeg", "search", "find", "slaa", "hent", "fetch", "laes", "read"),
    "clean": ("ryd", "clean", "slet", "delete", "fjern", "remove"),
}


def _normaliser(tekst: str) -> str:
    t = str(tekst or "").lower()
    for a, b in (("æ", "ae"), ("ø", "oe"), ("å", "aa")):
        t = t.replace(a, b)
    # «verificér» → «verificer»; øvrige diakritika fjernes.
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def extract_anchors(tekst: str) -> frozenset[str]:
    """Konkrete arbejds-ankre i en tekst: id'er, filer, kode-identifikatorer."""
    raa = str(tekst or "")
    ankre: set[str] = set()
    for m in _ID_RE.findall(raa.lower()):
        ankre.add(f"id:{m}")
    for m in _COMMIT_RE.findall(raa.lower()):
        ankre.add(f"commit:{m[:12]}")
    for m in _FIL_RE.findall(raa):
        navn = m.lower().rsplit("/", 1)[-1]
        stamme, _, ende = navn.rpartition(".")
        # En kodefil og dens modulnavn er SAMME anker (decision_gate.py ≙ decision_gate).
        ankre.add(f"kode:{stamme}" if ende in ("py", "ts", "tsx", "sh", "sql") else f"fil:{navn}")
    for m in _SNAKE_RE.findall(raa):
        ankre.add(f"kode:{m.lower()}")
    for m in _CAMEL_RE.findall(raa):
        ankre.add(f"kode:{m.lower()}")
    return frozenset(ankre)


def action_class(tekst: str) -> str:
    """Handlingsklasse ud fra FØRSTE genkendte verbum-stamme. '' = ukendt."""
    bedste = ("", 10**9)
    for i, tok in enumerate(_TOKEN_RE.findall(_normaliser(tekst))):
        for klasse, stammer in _HANDLINGER.items():
            if any(tok == s or (len(s) >= 4 and tok.startswith(s)) for s in stammer):
                if i < bedste[1]:
                    bedste = (klasse, i)
                break
    return bedste[0]


def _scope(user_id: str | None) -> str:
    return str(user_id or "").strip() or SYSTEM_SCOPE


def work_fingerprint(tekst: str, *, user_id: str | None = None) -> str:
    """Stabilt fingeraftryk. '' når der ikke findes både anker og handling."""
    ankre = _arbejds_ankre(tekst)
    handling = action_class(tekst)
    if not ankre or not handling:
        return ""
    raa = "|".join([_scope(user_id), handling, *sorted(ankre)])
    return "wf-" + hashlib.sha256(raa.encode()).hexdigest()[:20]


def _arbejds_ankre(tekst: str) -> frozenset[str]:
    # Rene id-ankre (task-…) peger på en identitet, ikke på selve handlingen;
    # de bruges til eksplicit relation (`_eksplicit_relation`), ikke til fingeraftrykket.
    return frozenset(a for a in extract_anchors(tekst) if not a.startswith("id:"))


def _samme_arbejde(a_tekst: str, b_tekst: str) -> bool:
    """Samme handlingsklasse OG ankrene overlapper væsentligt (≥ halvdelen af det mindste)."""
    a, b = _arbejds_ankre(a_tekst), _arbejds_ankre(b_tekst)
    ha, hb = action_class(a_tekst), action_class(b_tekst)
    if not a or not b or not ha or ha != hb:
        return False
    faelles = len(a & b)
    return faelles >= max(1, math.ceil(0.5 * min(len(a), len(b))))


def _nu() -> datetime:
    return datetime.now(UTC)


def _ts(v: object) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v or ""))
    except ValueError:  # ikke et tidsstempel — behandles som «ukendt tid»
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _ref(art: str, ref: str, tilstand: str, **ekstra: Any) -> dict[str, Any]:
    return {"kind": art, "ref": ref, "state": tilstand, **ekstra}


def _eksplicit_relation(tekst: str, user_id: str | None) -> dict[str, Any] | None:
    """Teksten NÆVNER en task/assignment — relationen er givet, ikke gættet."""
    from core.runtime.db import connect

    ider = [a[3:] for a in extract_anchors(tekst) if a.startswith("id:")]
    if not ider:
        return None
    scope = _scope(user_id)
    try:
        with connect() as conn:
            for i in ider:
                if i.startswith("task-"):
                    r = conn.execute(
                        "SELECT task_id, status FROM runtime_tasks WHERE task_id=?", (i,)
                    ).fetchone()
                    if r and r[1] in ("queued", "running"):
                        return _ref("task", r[0], r[1], why="eksplicit-relation")
                if i.startswith("asg-"):
                    r = conn.execute(
                        "SELECT assignment_id, status, owner_user_id FROM agent_assignments"
                        " WHERE assignment_id=?", (i,),
                    ).fetchone()
                    if r and r[1] in _AKTIVE_ASSIGNMENT and _bruger_matcher(scope, r[2]):
                        return _ref("assignment", r[0], r[1], why="eksplicit-relation")
    except sqlite3.Error:  # fejl åbent: et ægte initiativ må ikke dø af en db-fejl
        return None
    return None


_AKTIVE_ASSIGNMENT = ("queued", "active", "running", "in_progress", "assigned")


def _bruger_matcher(scope: str, raekke_bruger: object) -> bool:
    """Privat arbejde krydser aldrig brugere. System ser kun referencer, ikke indhold."""
    if scope == SYSTEM_SCOPE:
        return True
    return str(raekke_bruger or "") == scope


def find_covering_work(
    tekst: str, *, user_id: str | None = None, new_evidence: bool = False,
) -> dict[str, Any] | None:
    """Er denne handling allerede dækket? Returnér en reference + årsag, ellers None.

    ``state`` er én af: ``in_progress`` (kører), ``delegated`` (agent),
    ``waiting`` (blokeret/afventer), ``done`` (afsluttet uden ny evidens).
    ``new_evidence=True`` genåbner afsluttet arbejde — gentagelse ER tilladt når
    noget har ændret sig.
    """
    from core.runtime.db import connect

    eks = _eksplicit_relation(tekst, user_id)
    if eks:
        return eks
    fp = work_fingerprint(tekst, user_id=user_id)
    if not fp:
        return None
    scope = _scope(user_id)
    nu = _nu()
    for kilde in (_kilde_opgaver, _kilde_agenter, _kilde_synlige):
        try:
            with connect() as conn:
                conn.row_factory = sqlite3.Row
                fund = kilde(conn, tekst, fp, scope, nu, new_evidence)
        except sqlite3.Error:
            continue  # én manglende/fejlende kilde må ikke blinde de andre
        if fund:
            return fund
    return None


def _kilde_opgaver(conn, tekst, fp, scope, nu, new_evidence):
    # 1. Opgaver (initiativ-materialisering, rutiner, autonome runs).
    for r in conn.execute(
        "SELECT task_id, status, goal, work_fingerprint, updated_at, blocked_reason"
        " FROM runtime_tasks WHERE status IN ('queued','running','blocked','succeeded')"
        " ORDER BY id DESC LIMIT 400"
    ):
        if r["work_fingerprint"]:
            samme = r["work_fingerprint"] == fp
        else:  # historisk række uden fingeraftryk: kun system-scope kan dømmes
            samme = scope == SYSTEM_SCOPE and _samme_arbejde(tekst, r["goal"])
        if not samme:
            continue
        opd = _ts(r["updated_at"]) or nu
        st = r["status"]
        if st in ("queued", "running"):
            return _ref("task", r["task_id"], "in_progress", why="samme-arbejde")
        if st == "blocked" and nu - opd < timedelta(hours=_BLOKERET_FRISK_TIMER):
            return _ref("task", r["task_id"], "waiting", why="afventer-eksisterende")
        if st == "succeeded" and not new_evidence and \
                nu - opd < timedelta(hours=_AFSLUTTET_FRISK_TIMER):
            return _ref("task", r["task_id"], "done", why="allerede-udfoert")
    return None


def _kilde_agenter(conn, tekst, fp, scope, nu, new_evidence):
    # 2. Agenter: samme bruger, aktive assignments.
    marks = ",".join("?" * len(_AKTIVE_ASSIGNMENT))
    for r in conn.execute(
        "SELECT assignment_id, status, goal, owner_user_id FROM agent_assignments"
        f" WHERE status IN ({marks}) ORDER BY created_at DESC LIMIT 200",
        _AKTIVE_ASSIGNMENT,
    ):
        if _bruger_matcher(scope, r["owner_user_id"]) and _samme_arbejde(tekst, r["goal"]):
            return _ref("assignment", r["assignment_id"], "delegated",
                        why="afventer-eksisterende-agent")
    return None


def _kilde_synlige(conn, tekst, fp, scope, nu, new_evidence):
    # 3. Synlige ture (seneste vindue) — brugerens EGET arbejde.
    graense = (nu - timedelta(minutes=_SYNLIG_VINDUE_MINUTTER)).isoformat()
    for r in conn.execute(
        "SELECT r.run_id, r.user_id, r.text_preview AS svar,"
        " w.user_message_preview AS spoerg"
        " FROM visible_runs r LEFT JOIN visible_work_units w ON w.run_id=r.run_id"
        " WHERE r.started_at >= ? AND r.run_id NOT LIKE 'autonomous-%'"
        " ORDER BY r.id DESC LIMIT 20", (graense,),
    ):
        if not _bruger_matcher(scope, r["user_id"]):
            continue
        if _samme_arbejde(tekst, f"{r['spoerg'] or ''} {r['svar'] or ''}") or \
                _delt_anker_og_handling(tekst, r["spoerg"], r["svar"]):
            return _ref("visible_run", r["run_id"], "in_progress",
                        why="synlig-samtale-samme-arbejde")
    return None


def _delt_anker_og_handling(tekst: str, *dele: object) -> bool:
    """En samtale blander ofte flere handlinger; her kræves kun delt ANKER + samme klasse
    et sted i teksten (ikke at ankrene udgør ≥ halvdelen af hele samtalen)."""
    mine = _arbejds_ankre(tekst)
    h = action_class(tekst)
    if not mine or not h:
        return False
    joined = " ".join(str(d or "") for d in dele)
    return bool(mine & _arbejds_ankre(joined)) and h in {
        action_class(s) for s in re.split(r"[.!?\n]", joined) if s.strip()
    }


def has_independent_work_signal(tekst: str) -> bool:
    """Har teksten et konkret anker + en handling? Så kan den dømmes mod arbejdsrelationer
    i stedet for et tidsvindue."""
    return bool(_arbejds_ankre(tekst)) and bool(action_class(tekst))


def record_decision(
    *, decision: str, reason: str, subject: str, covering: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    """Ingen tavse afvisninger: årsagen går i eventbussen (Mission Control læser derfra)."""
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish("coordination.decision", {
            "decision": decision, "reason": reason, "subject": str(subject)[:120],
            "covering": covering or {}, "scope": _scope(user_id),
        })
    except Exception:  # observabilitet, ikke kontrol
        pass


def claim_work(
    *, tekst: str, user_id: str | None = None, owner: str, kind: str = "work",
    origin: str = "coordination", origin_ref: str = "", priority: str = "medium",
    new_evidence: bool = False,
) -> dict[str, Any]:
    """Atomisk reservation. ``{"claimed": True, "task": …}`` eller ``{"claimed": False, "covering": …}``.

    Atomikken ligger i det unikke partial-index på `runtime_tasks.work_fingerprint`
    (kun queued/running) — to samtidige kald kan ikke begge indsætte. Kun den
    KONKRETE handling låses, aldrig hele emnet. Uden fingeraftryk reserveres
    intet (ingen identitet at konkurrere om).
    """
    from core.services import runtime_tasks

    dæk = find_covering_work(tekst, user_id=user_id, new_evidence=new_evidence)
    if dæk:
        record_decision(decision="coordinated", reason=dæk["why"], subject=tekst,
                        covering=dæk, user_id=user_id)
        return {"claimed": False, "covering": dæk}
    fp = work_fingerprint(tekst, user_id=user_id)
    try:
        task = runtime_tasks.create_task(
            kind=kind, goal=tekst[:200], origin=origin, scope=tekst[:200],
            priority=priority, origin_ref=origin_ref, owner=owner, work_fingerprint=fp,
        )
    except sqlite3.IntegrityError:
        # Tabte løbet: en anden worker nåede det samme ene skridt først.
        dæk = find_covering_work(tekst, user_id=user_id, new_evidence=new_evidence) or \
            _ref("task", "ukendt", "in_progress", why="tabt-klaim-race")
        record_decision(decision="coordinated", reason="tabt-klaim-race", subject=tekst,
                        covering=dæk, user_id=user_id)
        return {"claimed": False, "covering": dæk}
    record_decision(decision="accepted", reason="ny-handling" if fp else "uden-identitet",
                    subject=tekst, user_id=user_id)
    return {"claimed": True, "task": task, "fingerprint": fp}


def find_pending_initiative_same_work(tekst: str, *, user_id: str | None = None) -> str:
    """Id på et ventende initiativ med SAMME fingeraftryk og bruger. '' = ingen."""
    from core.runtime.db import connect

    fp = work_fingerprint(tekst, user_id=user_id)
    if not fp:
        return ""
    scope = _scope(user_id)
    try:
        with connect() as conn:
            for iid, focus, uid in conn.execute(
                "SELECT initiative_id, focus, scheduled_for_user_id FROM runtime_initiatives"
                " WHERE status='pending' AND initiative_type='initiative'"
                " ORDER BY id DESC LIMIT 60"
            ):
                if _scope(uid) == scope and work_fingerprint(focus, user_id=uid) == fp:
                    return str(iid)
    except sqlite3.Error:  # fejl åbent: intet fund er bedre end et blokeret initiativ
        return ""
    return ""


def er_forskellig_handling(ny: str, gammel: str, *, user_id: str | None = None) -> bool:
    """Begge har identitet og de er FORSKELLIGE → deler kun emne, ikke arbejde."""
    a = work_fingerprint(ny, user_id=user_id)
    b = work_fingerprint(gammel, user_id=user_id)
    return bool(a and b and a != b)
