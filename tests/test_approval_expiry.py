"""Et sent ja maa ikke kunne udfoere en gammel handling — Fase 4.

«duplicate, late, and cross-user answers cannot authorize execution» og
«missing answerer, audit-write failure, expiry, cancellation, and restart fail
closed».

Der var INTET aldersstjek. Ordet «expired» stod i fejlbeskeden for en
godkendelse der ikke fandtes — ikke for en der var for gammel.

MAALT 9/9-2026 paa produktionen: 26 ventende godkendelser i
`state/pending_approvals.json`, alle `bash`, den aeldste fra 29. august —
elleve dage. De blev genindlaest ved HVER procesopstart, saa en genstart
genoplivede dem. Et ja i dag ville have koert en kommando fra i forgaars med
de argumenter der blev fanget dengang.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import core.services.visible_runs as VR
from core.services.visible_runs_approvals import _er_udloebet


def _kort(alder_s: float) -> dict:
    t = datetime.now(UTC) - timedelta(seconds=alder_s)
    return {"tool_name": "bash", "arguments": {"command": "ls"},
            "created_at": t.isoformat(), "status": "pending",
            "run_id": "r1", "session_id": "s1"}


# ── selve aldersreglen ───────────────────────────────────────────────────

def test_et_frisk_kort_er_gyldigt():
    assert _er_udloebet(_kort(60)) == ""


def test_graensen_er_broens_TTL_ikke_et_nyt_tal():
    """Ét tal, ikke to. Ellers ville broen og den gamle sti kunne vaere uenige
    om hvornaar noget er udloebet."""
    from core.runtime.db_approval_bridge import DEFAULT_TTL_S
    assert _er_udloebet(_kort(DEFAULT_TTL_S - 30)) == ""
    assert _er_udloebet(_kort(DEFAULT_TTL_S + 30)) != ""


def test_et_ELLEVE_DAGE_gammelt_kort_er_udloebet():
    """Den faktiske tilstand paa produktionen."""
    grund = _er_udloebet(_kort(11 * 86400))
    assert "dage" in grund and grund.startswith("11")


def test_grunden_er_LAESELIG_i_hver_stoerrelsesorden():
    assert "minutter" in _er_udloebet(_kort(3700))
    assert "timer" in _er_udloebet(_kort(5 * 3600))
    assert "dage" in _er_udloebet(_kort(3 * 86400))


def test_et_kort_UDEN_tidsstempel_spaerres_IKKE():
    """En manglende tidsstempel er husets fejl, ikke brugerens. At afvise paa
    den ville laase ham ude af sine egne kort."""
    assert _er_udloebet({"tool_name": "bash"}) == ""
    assert _er_udloebet({"created_at": "noget vroevl"}) == ""


def test_et_naivt_tidsstempel_laeses_som_UTC():
    """DB-tider er lokale nogle steder og ISO andre — se husets tidligere
    query-faelde. Et naivt stempel maa ikke give en tilfaeldig alder."""
    t = (datetime.now(UTC) - timedelta(seconds=120)).replace(tzinfo=None)
    assert _er_udloebet({"created_at": t.isoformat()}) == ""


# ── genstart genopliver dem ikke ─────────────────────────────────────────

def test_opstart_genopliver_kun_FRISKE_kort(caplog):
    import logging
    raa = {"frisk": _kort(60), "gammel": _kort(11 * 86400),
           "ogsaa-gammel": _kort(3 * 86400)}
    with caplog.at_level(logging.WARNING):
        ud = VR._friske_godkendelser(raa)
    assert set(ud) == {"frisk"}
    assert "2 udloebne" in caplog.text


def test_opstart_taaler_vroevl_i_filen():
    assert VR._friske_godkendelser({"x": "ikke en dict"}) == {"x": "ikke en dict"}
    assert VR._friske_godkendelser({}) == {}
    assert VR._friske_godkendelser(None) == {}


# ── og at resolve faktisk afviser ────────────────────────────────────────

def test_et_sent_ja_udfoerer_INTET(isolated_runtime, monkeypatch):
    """Hele pointen: kommandoen fra i forgaars maa ikke koere i dag."""
    import core.services.visible_runs_approvals as A
    import core.tools.simple_tools as ST

    kaldt: list[str] = []
    monkeypatch.setattr(ST, "execute_tool_force",
                        lambda n, a, **k: (kaldt.append(n), {"status": "ok"})[1])
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    VR._PENDING_APPROVALS["gammel"] = _kort(11 * 86400)

    ud = A.resolve_pending_approval("gammel", approved=True)

    assert kaldt == [], "en elleve dage gammel kommando blev udfoert"
    assert ud["status"] == "error" and "udloebet" in ud["error"]
    assert "gammel" not in VR._PENDING_APPROVALS, "kortet blev liggende"


def test_et_frisk_ja_slipper_igennem(isolated_runtime, monkeypatch):
    import core.services.visible_runs_approvals as A
    import core.tools.simple_tools as ST

    kaldt: list[str] = []
    monkeypatch.setattr(ST, "execute_tool_force",
                        lambda n, a, **k: (kaldt.append(n), {"status": "ok"})[1])
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    VR._PENDING_APPROVALS["frisk"] = _kort(60)

    A.resolve_pending_approval("frisk", approved=True)
    assert kaldt == ["bash"]


# ── og HVEM der svarer — Fase 4 ──────────────────────────────────────────
#
# Endepunktet `POST /chat/approvals/{id}/approve` tog INGEN bruger og lavede
# intet ejerskabstjek: enhver autentificeret kalder kunne godkende et hvilket
# som helst kort ved at kende dets id. Identiteten fandtes hele tiden i
# auth-middleware'ens ContextVar — den naaede bare aldrig frem til `resolve`.


def _kort_med_ejer(ejer: str) -> dict:
    k = _kort(60)
    k["owner_user_id"] = ejer
    return k


def _fang(monkeypatch) -> list[str]:
    import core.tools.simple_tools as ST
    kaldt: list[str] = []
    monkeypatch.setattr(ST, "execute_tool_force",
                        lambda n, a, **k: (kaldt.append(n), {"status": "ok"})[1])
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    return kaldt


def test_EJEREN_kan_svare(isolated_runtime, monkeypatch):
    import core.services.visible_runs_approvals as A
    kaldt = _fang(monkeypatch)
    VR._PENDING_APPROVALS["a"] = _kort_med_ejer("bjorn")
    A.resolve_pending_approval("a", approved=True, answered_by="bjorn")
    assert kaldt == ["bash"]


def test_en_ANDEN_bruger_kan_IKKE(isolated_runtime, monkeypatch, caplog):
    import logging
    import core.services.visible_runs_approvals as A
    kaldt = _fang(monkeypatch)
    VR._PENDING_APPROVALS["a"] = _kort_med_ejer("bjorn")

    with caplog.at_level(logging.WARNING):
        ud = A.resolve_pending_approval("a", approved=True, answered_by="mikkel")

    assert kaldt == [], "en fremmed fik kommandoen udfoert"
    assert ud["status"] == "error" and "anden bruger" in ud["error"]
    assert "KRYDSBRUGER" in caplog.text


def test_et_afvist_krydssvar_BRUGER_ikke_kortet(isolated_runtime, monkeypatch):
    """Kortet skal stadig kunne godkendes af den rigtige bagefter. Ellers ville
    en fremmed kunne OEDELAEGGE en godkendelse uden at kunne bruge den."""
    import core.services.visible_runs_approvals as A
    kaldt = _fang(monkeypatch)
    VR._PENDING_APPROVALS["a"] = _kort_med_ejer("bjorn")

    A.resolve_pending_approval("a", approved=True, answered_by="mikkel")
    assert "a" in VR._PENDING_APPROVALS, "kortet forsvandt"

    A.resolve_pending_approval("a", approved=True, answered_by="bjorn")
    assert kaldt == ["bash"]


def test_et_kort_UDEN_ejer_spaerres_ikke(isolated_runtime, monkeypatch):
    """De 26 paa produktionen har ingen ejer. En manglende identitet er husets
    fejl, ikke brugerens."""
    import core.services.visible_runs_approvals as A
    kaldt = _fang(monkeypatch)
    VR._PENDING_APPROVALS["a"] = _kort(60)
    A.resolve_pending_approval("a", approved=True, answered_by="hvem_som_helst")
    assert kaldt == ["bash"]


def test_en_svarer_UDEN_identitet_spaerres_ikke(isolated_runtime, monkeypatch):
    """Interne kaldere uden bruger-kontekst maa stadig kunne afgoere."""
    import core.services.visible_runs_approvals as A
    kaldt = _fang(monkeypatch)
    VR._PENDING_APPROVALS["a"] = _kort_med_ejer("bjorn")
    A.resolve_pending_approval("a", approved=True, answered_by=None)
    assert kaldt == ["bash"]


def test_ALLE_answerers_giver_svareren_med():
    """Koblingen. Én answerer der glemmer den, er hele vejen udenom tjekket."""
    import inspect
    from apps.api.jarvis_api.routes import chat, cowork
    for navn, kilde in (("chat", inspect.getsource(chat)),
                        ("cowork", inspect.getsource(cowork))):
        for i, linje in enumerate(kilde.splitlines()):
            if "resolve_pending_approval(" in linje and "def " not in linje:
                vindue = "\n".join(kilde.splitlines()[i:i + 4])
                assert "answered_by" in vindue, f"{navn}: {linje.strip()[:60]}"


# ── engangs-forbrug: én beslutning, ét kald — Fase 4 ─────────────────────
#
# MAALT 9/9-2026: to samtidige svar paa samme kort udfoerte kommandoen TO
# GANGE. `rm -rf noget` koert tvefold i proeven. Hullet var vinduet mellem at
# TAGE kortet og at skrive at det var taget: traad A poppede det fra
# hukommelsen, traad B fandt None dér og faldt tilbage til den DELTE tilstand,
# som stadig sagde «pending» — for A skrev foerst «approved» EFTER kaldet.


def _kort_i_begge_lagre(navn: str = "a") -> None:
    kort = {**_kort(60), "arguments": {"command": "rm -rf noget"}}
    VR._PENDING_APPROVALS[navn] = dict(kort)
    VR._set_visible_approval_state(navn, {**kort, "approval_id": navn})


def test_seks_samtidige_svar_giver_ET_kald(isolated_runtime, monkeypatch):
    """Hele kriteriet: «a decision is consumed at most once by atomic claim»."""
    import threading
    import time

    import core.services.visible_runs_approvals as A
    import core.tools.simple_tools as ST

    kaldt: list[str] = []

    def _langsom(n, a, **k):
        time.sleep(0.3)          # hold vinduet aabent for de oevrige
        kaldt.append(n)
        return {"status": "ok"}

    monkeypatch.setattr(ST, "execute_tool_force", _langsom)
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    _kort_i_begge_lagre()

    traade = [threading.Thread(
        target=lambda: A.resolve_pending_approval("a", approved=True))
        for _ in range(6)]
    for t in traade:
        t.start()
    for t in traade:
        t.join(timeout=15)

    assert kaldt == ["bash"], f"kommandoen koerte {len(kaldt)} gange"


def test_kortet_markeres_taget_FOER_udbyder_graensen(isolated_runtime,
                                                     monkeypatch):
    """Selve mekanismen. Ser en anden svarer stadig «pending» mens kaldet
    koerer, er laasen uden virkning."""
    import core.services.visible_runs_approvals as A
    import core.tools.simple_tools as ST

    set_undervejs: list[str] = []

    def _kig(n, a, **k):
        tilstand = VR._get_visible_approval_state("a") or {}
        set_undervejs.append(str(tilstand.get("status")))
        return {"status": "ok"}

    monkeypatch.setattr(ST, "execute_tool_force", _kig)
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    _kort_i_begge_lagre()

    A.resolve_pending_approval("a", approved=True)
    assert set_undervejs == ["resolving"], set_undervejs


def test_et_ANDET_svar_efter_overtagelsen_afvises(isolated_runtime, monkeypatch):
    import core.services.visible_runs_approvals as A
    import core.tools.simple_tools as ST

    kaldt: list[str] = []
    monkeypatch.setattr(ST, "execute_tool_force",
                        lambda n, a, **k: (kaldt.append(n), {"status": "ok"})[1])
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")
    _kort_i_begge_lagre()

    A.resolve_pending_approval("a", approved=True)
    ud = A.resolve_pending_approval("a", approved=True)
    assert kaldt == ["bash"]
    assert ud["status"] == "error" and "already resolved" in ud["error"]
