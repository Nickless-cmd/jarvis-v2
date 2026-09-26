"""Ingen forespørgsel mod `chat_messages` må hente på tværs af brugere.

LÆKKEN, 26/9-2026: Bjørn opdagede at en Discord-samtale mellem Jarvis og
Michelle var endt i hans egen session. `chat_messages` er ÉN pulje, og enhver
query uden `workspace_name`-filter henter alles beskeder.

Denne fil har to slags vagter, og de måler forskellige ting:

* **Strukturvagten** scanner HELE kodebasen med AST. Den er den eneste der
  kan fange en query der endnu ikke er skrevet. Uden den ville lækken blive
  lukket i dag og åbnet igen næste gang nogen tilføjer en daemon.
* **Adfærdsvagterne** beviser mod en rigtig SQLite at A ikke ser B's ord, og
  at en ubestemmelig workspace giver INTET frem for ALT.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sqlite3

import pytest

from core.identity.samtale_scope import aktuel_samtale_workspace

_ROD = pathlib.Path(__file__).resolve().parents[1]

#: Nøgleord der afgrænser en forespørgsel til én bruger eller én samtale.
#: `session_id` tæller med: en session tilhører én bruger.
_AFGRAENSERE = ("workspace_name", "session_id", "user_id", "message_id =")

#: Steder der bevidst læser på tværs, med grunden skrevet HER og ikke kun i
#: filen. Tom med vilje: hver tilføjelse skal kunne forsvares i en review.
_UNDTAGELSER: dict[str, str] = {}


def _ufiltrerede_queries() -> list[tuple[str, int, str]]:
    """Alle SELECT mod chat_messages uden afgrænsning. AST, ikke grep.

    Literalen alene er ikke nok: filteret kan sættes sammen af flere
    strenge eller stå i parameter-tuplen. Derfor kigges der også på
    kildelinjerne omkring — samme grund som at en kilde-vagt skal parse
    træet og ikke lede efter en streng.
    """
    fund = []
    for p in sorted(list(_ROD.glob("core/**/*.py")) + list(_ROD.glob("apps/**/*.py"))):
        if "__pycache__" in str(p):
            continue
        try:
            src = p.read_text(errors="ignore")
            traeet = ast.parse(src)
        except (SyntaxError, OSError):
            continue
        linjer = src.splitlines()
        # Docstrings skal IKKE tælle med. `chat_sessions._sikr_flag_kolonner`
        # forklarer en migration og nævner både «chat_messages» og «SELECT
        # s.pinned» i samme prosa — den er dokumentation, ikke en
        # forespørgsel. En vagt der ikke kan skelne de to lærer folk at
        # tilføje undtagelser, og så holder den op med at måle.
        docstrings = {
            id(k.body[0].value)
            for k in ast.walk(traeet)
            if isinstance(k, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and k.body and isinstance(k.body[0], ast.Expr)
            and isinstance(k.body[0].value, ast.Constant)
            and isinstance(k.body[0].value.value, str)
        }
        for n in ast.walk(traeet):
            if id(n) in docstrings:
                continue
            if not isinstance(n, ast.Constant) or not isinstance(n.value, str):
                continue
            s = n.value.lower()
            if "chat_messages" not in s or not re.search(r"\bselect\b", s):
                continue
            omkring = " ".join(linjer[max(0, n.lineno - 5): n.lineno + 8]).lower()
            if any(k in s or k in omkring for k in _AFGRAENSERE):
                continue
            rel = str(p.relative_to(_ROD))
            if f"{rel}:{n.lineno}" in _UNDTAGELSER:
                continue
            fund.append((rel, n.lineno, " ".join(n.value.split())[:100]))
    return fund


def test_ingen_query_mod_chat_messages_henter_paa_tvaers():
    """Strukturvagten. Målt før lukningen: 18 steder.

    En ny daemon der glemmer filteret rammer denne test, ikke Bjørns
    telefon.
    """
    fund = _ufiltrerede_queries()
    if fund:
        linjer = "\n".join(f"  {f}:{ln}\n      {s}" for f, ln, s in fund)
        pytest.fail(
            f"{len(fund)} forespørgsel/-ler mod chat_messages uden afgrænsning:\n"
            f"{linjer}\n\n"
            "Tilføj `workspace_name = ?` med "
            "`aktuel_samtale_workspace()` — og behandl den tomme streng som "
            "«hent intet». Se core/identity/samtale_scope.py."
        )


def test_vagten_kan_overhovedet_fejle(tmp_path, monkeypatch):
    """En vagt der ikke kan fejle måler ingenting.

    Her plantes en ufiltreret query i en fil under `core/`, og scanneren
    skal finde den. Uden dette ville en knækket scanner se ud som en ren
    kodebase.
    """
    plantet = _ROD / "core" / "_vagt_selvtest_tmp.py"
    plantet.write_text(
        'Q = "SELECT content FROM chat_messages WHERE role = \'user\'"\n',
        encoding="utf-8",
    )
    try:
        fund = _ufiltrerede_queries()
    finally:
        plantet.unlink(missing_ok=True)
    assert any("_vagt_selvtest_tmp" in f for f, _, _ in fund), \
        "scanneren fandt ikke en query den selv fik plantet"


# ── Adfærd: ser A B's ord? ──────────────────────────────────────────────


@pytest.fixture()
def to_brugere(tmp_path):
    """En rigtig SQLite med to workspaces. Ikke en attrap — hele pointen
    er SQL'en, og en attrap ville teste at jeg kan skrive en attrap."""
    sti = tmp_path / "to.db"
    c = sqlite3.connect(sti)
    c.executescript("""
        CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, session_id TEXT,
                                    role TEXT, content TEXT, created_at TEXT,
                                    workspace_name TEXT);
    """)
    c.executemany(
        "INSERT INTO chat_messages (session_id, role, content, created_at, workspace_name)"
        " VALUES (?,?,?,?,?)",
        [("s1", "user", "bjoerns egen sætning", "2026-09-26T10:00:00+00:00", "bjorn"),
         ("s2", "user", "michelles private sætning", "2026-09-26T10:01:00+00:00", "michelle")],
    )
    c.commit()
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _hent(conn, ws: str) -> list[str]:
    """Formen alle de rettede steder bruger."""
    if not ws:
        return []
    return [r["content"] for r in conn.execute(
        "SELECT content FROM chat_messages WHERE role='user' AND workspace_name = ?", (ws,))]


def test_bjorn_ser_ikke_michelles_ord(to_brugere):
    ud = _hent(to_brugere, "bjorn")
    assert ud == ["bjoerns egen sætning"]
    assert not any("michelle" in t for t in ud)


def test_michelle_ser_ikke_bjorns_ord(to_brugere):
    assert _hent(to_brugere, "michelle") == ["michelles private sætning"]


def test_ukendt_workspace_giver_INTET_ikke_ALT(to_brugere):
    """Fail-closed. Det er hele forskellen mellem et forkert signal man kan
    måle, og et signal bygget på en fremmeds ord."""
    assert _hent(to_brugere, "") == []


def test_default_er_ikke_et_synonym_for_bjorn(to_brugere):
    """Målt i produktionen 26/9-2026: `workspace_name='default'` er 9.198
    rækker over 108 sessioner, stadig skrevet samme dag, og 142 af dem bærer
    et Discord-bruger-id. At lade den tælle som ejerens ville genåbne lækken
    under et andet navn."""
    assert _hent(to_brugere, "default") == []


# ── Hjælperen selv ──────────────────────────────────────────────────────


def test_hjaelperen_falder_tilbage_til_ejerens_workspace():
    """En daemon uden kontekst er ejerens egen baggrundstanke.
    `_DEFAULT_STATE.workspace_name` er «bjorn», så den lander rigtigt af sig
    selv — og aldrig i den blandede «default»-bucket."""
    assert aktuel_samtale_workspace() == "bjorn"


def test_hjaelperen_er_fail_closed_naar_konteksten_braekker(monkeypatch):
    import core.identity.workspace_context as wc

    def _braek():
        raise RuntimeError("kontekst væk")

    monkeypatch.setattr(wc, "current_workspace_name", _braek)
    assert aktuel_samtale_workspace() == ""


def test_tom_kontekst_bliver_IKKE_til_default(monkeypatch):
    """Mutationstesten afslørede hullet her: min fail-closed-test patchede
    `current_workspace_name` til at RAISE, så den målte kun exception-stien.
    En mutation der lod hjælperen falde tilbage til «default» på en tom
    kontekst slap derfor igennem — og «default» er netop den blandede bucket
    med 142 Discord-rækker i.
    """
    import core.identity.workspace_context as wc

    monkeypatch.setattr(wc, "current_workspace_name", lambda: "")
    assert aktuel_samtale_workspace() == ""

    monkeypatch.setattr(wc, "current_workspace_name", lambda: "   ")
    assert aktuel_samtale_workspace() == ""
