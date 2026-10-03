"""Værktøjskald som baggrundsjob — den kilde der manglede.

Bjørn 3/10-2026: «alle hans opgaver/bash commandoer bliver vist i baggrunds
panelet... det sker ikk på vores?». De øvrige kilder er BEHOLDERE — supervisor-
processer, åbne shells, scout-agenter. Et `bash`-kald er en kommando inde i en
shell: den kører, svarer og forsvinder, og den blev aldrig til en række.

Kilden læser de `tool.invoked`/`tool.completed`-events runtime allerede udgiver
og parrer dem. Testene her maaler de fire ting der kan gaa galt i den parring:

  1. Et kald uden svar skal staa som kørende — ellers viser panelet ingenting.
  2. Et kald MED svar skal forsvinde — ellers vokser listen uden grænse.
  3. Kald uden `run_id` skal UDELUKKES — ellers viser panelet sit eget poll.
  4. To samtidige kald af samme værktøj skal parres paa id, ikke paa rækkefølge.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from core.services import background_jobs as bj

#: Fast «nu» — ellers ville hvert testkald afhænge af vægurets gang.
NU = 1_000_000.0


def _iso(sekunder_siden: float) -> str:
    return datetime.fromtimestamp(NU - sekunder_siden, UTC).isoformat()


def _invoked(event_id: int, tool: str, *, run: str = "visible-1",
             tool_use_id: str = "", siden: float = 5.0, **args) -> tuple:
    a = dict(args)
    if run:
        a["_runtime_turn_id"] = run
    if tool_use_id:
        a["_runtime_tool_use_id"] = tool_use_id
    return (event_id, "tool.invoked", json.dumps({
        "tool": tool, "run_id": run, "session_id": "chat-1", "arguments": a,
    }), _iso(siden))


def _completed(event_id: int, tool: str, *, tool_use_id: str = "",
               status: str = "ok", siden: float = 1.0) -> tuple:
    return (event_id, "tool.completed", json.dumps({
        "tool": tool, "status": status, "tool_use_id": tool_use_id,
    }), _iso(siden))


def _sql_rækkefølge(*events: tuple) -> list[tuple]:
    """SQL henter nyeste først (`ORDER BY id DESC`); kilden vender dem selv."""
    return list(reversed(events))


def _med_db(monkeypatch, rows: list[tuple]) -> None:
    """Bind `_tool_jobs` til en attrap-DB i stedet for den levende."""
    class _Cursor:
        def fetchall(self):
            return rows

    class _Conn:
        def execute(self, sql, params=()):
            return _Cursor()

    class _Ctx:
        def __enter__(self):
            return _Conn()

        def __exit__(self, *a):
            return False

    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda: _Ctx())
    monkeypatch.setattr(bj, "_nu", lambda: NU)


@pytest.fixture(autouse=True)
def ingen_andre_kilder(monkeypatch):
    monkeypatch.setattr(bj, "_supervisor_jobs", lambda: [])
    monkeypatch.setattr(bj, "_scout_jobs", lambda: [])
    monkeypatch.setattr(bj, "_shell_sessioner", lambda: [])


# ── 1. Det kørende kald ─────────────────────────────────────────────────────

def test_et_kald_uden_parret_svar_staar_som_KOERENDE(monkeypatch):
    """Kernen i det hele. Uden den er panelet lige så tomt som før."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="t1", command="npm test",
                 description="Kører hele testsuiten", siden=137.0),
    ))
    j = bj._tool_jobs()
    assert len(j) == 1
    assert j[0]["status"] == "running"
    assert j[0]["navn"] == "Kører hele testsuiten"
    assert j[0]["sekunder"] == 137
    assert j[0]["kilde"] == "tool"


def test_et_parret_kald_FORSVINDER(monkeypatch):
    """Bjoern: «de skal automatisk forsvinde naar opgave er fuldfoert». Et
    panel der samlede alt op ville vokse uden graense."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="t1", command="ls"),
        _completed(2, "bash", tool_use_id="t1"),
    ))
    assert bj._tool_jobs() == []


def test_et_FEJLENDE_kald_forsvinder_ogsaa(monkeypatch):
    """Med vilje. Fejlen staar i samtalen, hvor man kan laese hvad der skete;
    panelet viser «hvad koerer NU». Det er en afgraenset halv sandhed, ikke en
    forglemmelse — og den er skrevet ned i `_tool_jobs`."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="t1", command="boom"),
        _completed(2, "bash", tool_use_id="t1", status="error"),
    ))
    assert bj._tool_jobs() == []


# ── 2. Panelets eget poll maa ikke vise sig selv ────────────────────────────

def test_kald_uden_run_id_kommer_IKKE_med(monkeypatch):
    """Den vigtigste udelukkelse, og den er maalt.

    3/10-2026: panelets eget 5-sekunders poll af `/api/jobs` kalder
    `operator_bash` gennem `execute_tool` uden om `simple_tool_executor`. Den
    baerer derfor hverken run eller session. Maalt i et kvarters events:
    **151 af 152** `operator_bash`-kald var netop dét poll.

    Uden reglen ville panelet vise sin egen puls som om det var arbejde."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "operator_bash", run="", command="for f in /tmp/jarvis-bg/*.pid"),
    ))
    assert bj._tool_jobs() == []


def test_run_id_UKENDT_taeller_som_manglende(monkeypatch):
    """`tool_call_telemetry` skriver UKENDT naar identiteten ikke kan
    fastslaas. Det er samme sag som et tomt felt, ikke en anden."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "operator_bash", run="UKENDT", command="ls"),
    ))
    assert bj._tool_jobs() == []


def test_et_rigtigt_operator_kald_kommer_med_og_peger_paa_hans_maskine(monkeypatch):
    """Reglen maa ikke kaste barnet ud med badevandet: et operator_bash-kald
    FRA et run er rigtigt arbejde — og det koerer derovre, ikke her."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "operator_bash", run="visible-9", command="ls ~",
                 description="Kigger i hjemmemaper"),
    ))
    j = bj._tool_jobs()
    assert len(j) == 1
    assert j[0]["kilde"] == "tool_operator"


# ── 3. Parringen naar to kald af samme værktøj kører samtidig ───────────────

def test_to_samtidige_kald_parres_paa_ID_ikke_paa_raekkefoelge(monkeypatch):
    """Hele grunden til at `tool.completed` fik et `tool_use_id`.

    Maalt 3/10-2026: jeg kaldte to bash-kommandoer i ÉN runde. Parrede man
    blot «foerste ledige af samme værktøj», ville den andens svar lukke den
    foerste — og panelet ville vise den gale som koerende. Testen er derfor
    skaanselsoes: det ER den foerste der svarer."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="t1", command="lang", description="Den lange"),
        _invoked(2, "bash", tool_use_id="t2", command="kort", description="Den korte"),
        _completed(3, "bash", tool_use_id="t2"),
    ))
    j = bj._tool_jobs()
    assert [x["navn"] for x in j] == ["Den lange"]


def test_et_completed_UDEN_id_lukker_aeldste_af_samme_vaerktoej(monkeypatch):
    """Events skrevet foer 3/10-2026 bar intet id. De skal stadig kunne lukkes —
    ellers stod gamle kald som koerende for evigt. Upraecist, men afgraenset."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="", command="a", description="Foerste"),
        _invoked(2, "bash", tool_use_id="", command="b", description="Anden"),
        _completed(3, "bash", tool_use_id=""),
    ))
    j = bj._tool_jobs()
    assert [x["navn"] for x in j] == ["Anden"]


# ── 4. Grænser og fallbacks ─────────────────────────────────────────────────

def test_et_kald_ældre_end_vinduet_staar_ikke_som_koerende(monkeypatch):
    """Et kald der aldrig fik sit svar — fx fordi processen blev genstartet
    midt i det — ville ellers staa som kørende for evigt."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="t1", command="x",
                 siden=bj._TOOL_SPOEGER_VINDUE_S + 60),
    ))
    assert bj._tool_jobs() == []


def test_titlen_falder_tilbage_paa_kommandoen_og_saa_paa_vaerktoejet(monkeypatch):
    """Beskrivelsen er det Jarvis selv skrev — men den findes ikke altid
    (`bash_session_run` har ingen `description`). Et kort uden titel ville
    vaere en tom raekke."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash_session_run", tool_use_id="t1", command="make -j8"),
        _invoked(2, "analyze_image", tool_use_id="t2"),
    ))
    navne = {x["id"].split("#")[0]: x["navn"] for x in bj._tool_jobs()}
    assert navne["bash_session_run"] == "make -j8"
    assert navne["analyze_image"] == "analyze_image"


def test_et_vaerktoejskald_tilbyder_HVERKEN_pause_eller_stop(monkeypatch):
    """Der findes ingen rute der kan stoppe et kald inde i et run uden at rive
    turen i stykker. Panelet tegner en stop-knap for hver koerende raekke, saa
    uden `can_stop` fik raekken en knap der saa levende ud og gjorde intet."""
    _med_db(monkeypatch, _sql_rækkefølge(
        _invoked(1, "bash", tool_use_id="t1", command="x"),
    ))
    j = bj._tool_jobs()[0]
    assert j["can_pause"] is False
    assert j["can_stop"] is False


def test_en_ulaesbar_raekke_tager_ikke_hele_listen(monkeypatch):
    """Et enkelt oedelagt event maa koste sin egen raekke — ikke panelet."""
    _med_db(monkeypatch, _sql_rækkefølge(
        (1, "tool.invoked", "{ikke json", _iso(5)),
        _invoked(2, "bash", tool_use_id="t2", command="ok", description="Den gode"),
    ))
    assert [x["navn"] for x in bj._tool_jobs()] == ["Den gode"]


def test_en_doed_DB_giver_tom_liste_og_ikke_en_undtagelse(monkeypatch):
    """Kilden er en TILFOEJELSE til panelet, ikke dets fundament: fejler den,
    skal supervisor- og shell-raekkerne stadig vises."""
    import core.runtime.db as db

    def _braek():
        raise RuntimeError("databasen svarer ikke")

    monkeypatch.setattr(db, "connect", _braek)
    monkeypatch.setattr(bj, "_nu", lambda: NU)
    assert bj._tool_jobs() == []


def test_liste_taaler_at_vaerktoejskilden_fejler(monkeypatch):
    """Samme afvejning ét niveau oppe: `liste` maa ikke vaelte."""
    def _braek():
        raise RuntimeError("nede")

    monkeypatch.setattr(bj, "_tool_jobs", _braek)
    ud = bj.liste(exec_fn=lambda n, a: {"status": "ok", "result": {"stdout": ""}})
    assert ud["bridge_ok"] is True
    assert isinstance(ud["jobs"], list)
