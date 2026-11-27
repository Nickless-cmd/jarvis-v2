"""Tests for core.services.consolidation_judge_daemon — oprydnings-grenene.

Dækker to fejl målt 5/10-2026:

  1. `_enforce_reject` importerede `update_decision_status`, som ikke findes
     NOGEN steder i kodebasen. ImportError blev slugt af `except Exception`,
     så hele revoke-grenen var død kode — den kunne aldrig rydde noget.
     Den rigtige funktion er `set_status`.

  2. `list_decisions(status="active", limit=50)` skjulte de nederste 30 af 80
     aktive beslutninger. Sorteringen er `priority DESC`, så skæringen flyttede
     sig — og en beslutning der skulle ryddes kunne ligge i det skjulte bånd.
"""
from __future__ import annotations


def _alle_aktive(n: int = 60, graense: int = 50) -> list[dict]:
    return [
        {
            "decision_id": f"d{i}",
            "directive": f"x{i}",
            "priority": 100 - i,
            "adherence_score": (0.1 if i >= graense else 0.9),
        }
        for i in range(n)
    ]


def _falsk_liste(alle: list[dict], *, status: str = "active", limit: int | None = 50):
    """Respekterer `limit` — så testen kun består når grenen spørger uden grænse."""
    raekker = sorted(alle, key=lambda d: -int(d["priority"]))
    return raekker if limit is None else raekker[: int(limit)]


def _stille_bus(monkeypatch) -> None:
    """Daemp `publish` PAA det aegte bus-objekt — udskift ikke modul-navnet.

    MAALT 6/10-2026: den gamle udgave gjorde `monkeypatch.setattr(cjd,
    "event_bus", _StilleBus)`. `cjd.event_bus` ER singletonen
    (`cjd.event_bus is bus.event_bus`), saa lappen lagde en attrappe ind i
    modulet. Et modul der importeres FOERSTE gang i det vindue binder
    attrappen for altid — og `monkeypatch` gendanner kun modul-navnet, aldrig
    kopien inde i det modul der naaede at importere den. Vagten
    `test_event_bus_singleton_maa_ikke_udskiftes.py` fangede det.

    At lappe metoden paa det aegte objekt rammer enhver der holder bussen,
    foer eller efter — og `monkeypatch` ruller den tilbage.
    """
    from core.services import consolidation_judge_daemon as cjd

    monkeypatch.setattr(cjd.event_bus, "publish", lambda *_a, **_k: None,
                        raising=False)


def test_set_status_findes_i_db_decisions():
    """Revoke-grenen importerer `set_status` — den SKAL findes i butikken."""
    from core.runtime import db_decisions

    assert hasattr(db_decisions, "set_status"), (
        "revoke-grenen importerer en funktion der ikke findes — grenen dør i stilhed"
    )


def test_revoke_kalder_set_status_for_alle_aktive(monkeypatch):
    """Grenen skal VIRKE og se hele listen — ikke kun de første 50."""
    from core.runtime import db_decisions
    from core.services import consolidation_judge_daemon as cjd

    alle = _alle_aktive()
    revoked: list[tuple[str, str]] = []

    monkeypatch.setattr(db_decisions, "list_decisions",
                        lambda **kw: _falsk_liste(alle, **kw))
    monkeypatch.setattr(db_decisions, "set_status",
                        lambda did, st: revoked.append((did, st)) or {})
    _stille_bus(monkeypatch)

    cjd._enforce_reject({"item_type": "broken_decisions", "choice": "revoke"})

    assert revoked, "revoke-grenen gjorde intet — importen eller kaldet fejler"
    assert ("d50", "revoked") in revoked, (
        "beslutningen laa uden for de foerste 50 — skaeringen skjuler den for oprydningen"
    )


def test_recommit_ser_alle_aktive(monkeypatch):
    """Samme skaering i recommit-grenen."""
    from core.runtime import db_decisions
    from core.services import consolidation_judge_daemon as cjd

    alle = _alle_aktive()
    limits: list[object] = []

    def fanger(**kw):
        limits.append(kw.get("limit"))
        return _falsk_liste(alle, **kw)

    monkeypatch.setattr(db_decisions, "list_decisions", fanger)
    _stille_bus(monkeypatch)

    cjd._enforce_accept({"item_type": "broken_decisions", "choice": "recommit"})

    assert limits, "recommit-grenen kaldte ikke list_decisions"
    assert all(lim is None for lim in limits), (
        f"grenen spoerger med en graense ({limits}) — den skjuler beslutninger"
    )


# --- 27/10-2026: samme fejlklasse igen, nu i `_render_judgments` ------------
#
# Importen stod inde i funktionen og pegede på `heartbeat_runtime`, hvor
# `daemon_llm_call` ikke findes længere (den bor i `daemon_llm`). Fordi den er
# lazy, lykkedes modul-importen — fejlen dukkede først op ved kald, hvor
# medlemmet fangede sin egen ImportError og lagde den i `member_errors`.
# Familien meldte `fired: True`, så den natlige dommer var død i ugevis uden
# at nogen alarm gik. Fundet af runtime-inspektionen 27/10 kl. 20:40.
#
# Testene herunder maaler BAADE adfaerden (kalder stien) og klassen (statisk
# vagt over alle lazy imports i filen), saa en ny forkeret import ikke kan
# snige sig ind uden at blive set.


def test_render_judgments_kan_faktisk_kalde_daemon_llm(monkeypatch):
    """Stien skal KUNNE kalde modellen — ikke do paa en ImportError."""
    from core.services import consolidation_judge_daemon as cjd
    from core.services import daemon_llm

    kaldt: list[str] = []

    def falsk_kald(prompt, *, max_len=200, fallback="", daemon_name=""):
        kaldt.append(daemon_name)
        return "Dom: accept\nValg: review_all\nBegrundelse: test\nHandling: ingen"

    monkeypatch.setattr(daemon_llm, "daemon_llm_call", falsk_kald)
    monkeypatch.setattr(cjd, "build_identity_preamble", lambda: "TEST")

    domme = cjd._render_judgments(
        [{
            "title": "proeve",
            "type": "broken_decisions",
            "severity": "low",
            "evidence": "bevis",
            "options": ["review_all"],
        }],
        {},
    )

    assert kaldt, "importen eller kaldet fejler — dommeren er doed i stilhed"
    assert domme and domme[0]["verdict"] == "accept", domme


def test_ingen_lazy_import_peger_paa_et_navn_der_ikke_findes():
    """Vagt for KLASSEN: hver `from X import Y` inde i en funktion skal holde.

    Top-level-imports bliver fanget af `test_governance_bootstrap`, men en
    import inde i en funktion naar kun at fejle ved kald — praecis den vej
    den natlige dommer doede ad.
    """
    import ast
    import importlib
    from pathlib import Path

    fil = Path("core/services/consolidation_judge_daemon.py")
    trae = ast.parse(fil.read_text(encoding="utf-8"))

    # Kun imports der ligger inde i en funktion — top-level fejler straks.
    def inde_i_funktion(node: ast.AST, inde: bool = False):
        for barn in ast.iter_child_nodes(node):
            if isinstance(barn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from inde_i_funktion(barn, True)
            else:
                if inde and isinstance(barn, ast.ImportFrom) and barn.module:
                    yield barn
                yield from inde_i_funktion(barn, inde)

    fejl: list[str] = []
    for node in inde_i_funktion(trae):
        modul = node.module
        if not modul.startswith("core."):
            continue
        try:
            maal = importlib.import_module(modul)
        except Exception as exc:  # modulet findes ikke
            fejl.append(f"{modul} kan ikke importeres: {exc}")
            continue
        for alias in node.names:
            if not hasattr(maal, alias.name):
                fejl.append(
                    f"`from {modul} import {alias.name}` (linje {node.lineno}) "
                    f"— navnet findes ikke i {modul}"
                )

    assert not fejl, "lazy import peger paa et navn der ikke findes:\n" + "\n".join(fejl)


# --- 9/11-2026: dommeren ABANDONEDE alle stale mål i ét sving ---------------
#
# `_enforce_reject` kaldte `update_goal(new_status="abandoned")` for HVERT
# stale mål, så snart dommen var reject + «abandon». Målt: tre mål fik samme
# millisekund som `updated_at` (29/10 06:10:13), og systemet stod tilbage med
# NUL aktive mål. Uden et mål kan reaktion-leddet i tick-scoren ikke fyres
# (max 20 af 45), så scoren låste på 40 — dommeren fjernede den retning den
# dømte om. «pause_stale» havde slet ingen gren (tavs no-op).
#
# Kontrakten er nu: flag, mutér ikke. Testen måler BEGGE valg, fordi begge er
# tilstandsmutationer og begge skal gå gennem samme flag-sti.


def _stale_goal_stub() -> list[dict]:
    return [{"goal_id": "goal_a", "title": "Bevis pålidelighed over tid"}]


def test_stale_goals_flagges_uden_at_mutere_maalet(monkeypatch):
    """Dommerens stale-valg må IKKE ændre målstatus — kun efterlade et flag."""
    from core.runtime import db_central_incidents as dci
    from core.services import agent_self_evaluation as ase
    from core.services import consolidation_judge_daemon as cjd
    from core.services import long_horizon_goals as lhg

    muteret: list[dict] = []
    flagget: list[str] = []

    monkeypatch.setattr(ase, "detect_stale_goals", _stale_goal_stub)
    monkeypatch.setattr(
        lhg, "update_goal", lambda **kw: muteret.append(kw) or {}
    )
    monkeypatch.setattr(
        dci, "record_central_incident",
        lambda **kw: flagget.append(str(kw.get("message") or "")) or 1,
    )
    _stille_bus(monkeypatch)

    cjd._enforce_reject({"item_type": "stale_goals", "choice": "abandon_stale"})

    assert not muteret, (
        "dommeren muterede målstatus — den fjerner den retning den dømmer om: "
        f"{muteret}"
    )
    assert flagget, "målet blev hverken muteret eller flagget — tavs no-op"
    assert "goal_a" in flagget[0], flagget


def test_pause_stale_flaggger_ogsaa(monkeypatch):
    """«pause_stale» havde ingen gren. Den skal gå gennem samme flag-sti."""
    from core.runtime import db_central_incidents as dci
    from core.services import agent_self_evaluation as ase
    from core.services import consolidation_judge_daemon as cjd
    from core.services import long_horizon_goals as lhg

    muteret: list[dict] = []
    flagget: list[str] = []

    monkeypatch.setattr(ase, "detect_stale_goals", _stale_goal_stub)
    monkeypatch.setattr(
        lhg, "update_goal", lambda **kw: muteret.append(kw) or {}
    )
    monkeypatch.setattr(
        dci, "record_central_incident",
        lambda **kw: flagget.append(str(kw.get("message") or "")) or 1,
    )
    _stille_bus(monkeypatch)

    cjd._enforce_reject({"item_type": "stale_goals", "choice": "pause_stale"})

    assert not muteret, f"pause_stale muterede målet: {muteret}"
    assert flagget, "pause_stale er stadig en tavs no-op"


def test_stale_goal_titel_bruger_den_faktiske_taerskel():
    """Prompten sagde «3+ dage» mens tærsklen er 14 — dommeren dømte på et forkert grundlag."""
    from core.services import agent_self_evaluation as ase
    from core.services import consolidation_judge_daemon as cjd

    items = cjd._build_stillingtagen({"stale_goals": _stale_goal_stub()})
    stale_items = [i for i in items if i["type"] == "stale_goals"]
    assert stale_items, items
    titel = stale_items[0]["title"]
    assert f"{ase._GOAL_STALE_DAYS}+ dage" in titel, (
        f"titlen lyver om tærsklen: {titel!r} (faktisk {ase._GOAL_STALE_DAYS})"
    )


# --- 27/11-2026: den natlige dom blev ALDRIG gemt ---------------------------
#
# Kaldet i `_record_judgment_session` stod med `write_density_note`s skema
# (`kind`/`title`/`what_happened`/`what_it_meant`/`mood`/`visibility`) mod
# `insert_private_brain_record`, som tager
# `record_type`/`focus`/`summary`/`detail`/`confidence`/`domain`.
#
# Syv parametre fandtes ikke, saa hvert kald kastede TypeError — og fejlen blev
# fanget og logget som advarsel. Foerste forekomst i journalen: 10/11-2026.
# Maalt 27/11: NUL poster med `record_type='judgment'` i private_brain_records
# efter 17 dage. Dommen blev skrevet, logget som fejlet, og glemt.
#
# Testen binder den AEGTE signatur. Et forkert parameter-navn kaster TypeError
# her, i stedet for om natten hvor ingen laeser advarslen.


def test_den_natlige_dom_skrives_med_funktionens_faktiske_signatur(monkeypatch):
    """Kaldet skal matche `insert_private_brain_record`s signatur — ikke density-skemaet."""
    import inspect

    from core.runtime.db import insert_private_brain_record as aegte
    from core.services import consolidation_judge_daemon as cjd

    kaldt: list[dict] = []

    def _fang(**kwargs):
        aegte_sig.bind(**kwargs)  # forkert navn => TypeError, ikke tavshed
        kaldt.append(kwargs)
        return {"record_id": kwargs.get("record_id", "")}

    aegte_sig = inspect.signature(aegte)
    monkeypatch.setattr(cjd, "insert_private_brain_record", _fang)

    cjd._record_judgment_session(
        [
            {
                "item_title": "Test-dom",
                "verdict": "accept",
                "choice": "gem",
                "rationale": "verifikation",
                "action": "observation",
            }
        ],
        {"decision_adherence": {"score": 80.0}, "tick_quality": {"avg_score": 66.9}},
    )

    assert len(kaldt) == 1, "dommen blev ikke skrevet til private brain"
    k = kaldt[0]
    assert k["record_type"] == "judgment"
    assert "Natlig revision" in k["focus"]
    assert "1 stillingtagen" in k["summary"]
    assert k["detail"], "den fulde dom mangler i detail"
    assert k["domain"] == "self"


def test_dom_kaldet_bruger_ingen_parametre_uden_for_signaturen():
    """Vagt for KLASSEN: ingen `kind=`/`what_happened=` mod private_brain.

    Den statiske del fanger det ogsaa hvis nogen genindfoerer et forkert navn
    i en gren testen ovenfor ikke rammer.
    """
    import ast
    from pathlib import Path

    from core.runtime.db import insert_private_brain_record as aegte
    import inspect

    gyldige = set(inspect.signature(aegte).parameters)
    trae = ast.parse(
        Path("core/services/consolidation_judge_daemon.py").read_text(encoding="utf-8")
    )

    fejl: list[str] = []
    for node in ast.walk(trae):
        if not isinstance(node, ast.Call):
            continue
        navn = getattr(node.func, "id", None)
        if navn != "insert_private_brain_record":
            continue
        for kw in node.keywords:
            if kw.arg and kw.arg not in gyldige:
                fejl.append(f"linje {node.lineno}: ukendt parameter `{kw.arg}=`")

    assert not fejl, "kald til insert_private_brain_record med ukendte parametre:\n" + "\n".join(fejl)
