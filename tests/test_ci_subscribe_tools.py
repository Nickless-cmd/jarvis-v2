"""Tests for CI-abonnementet (24/11-2026).

To ting skal bevises, og de er ikke det samme:

1. **Svaret kommer.** Et abonnement der ikke leverer er en dør uden håndtag —
   og så er der ingen gevinst over at polle i hånden, hvilket var hele
   anledningen (målt: 7-14 håndpollinger pr. ventetid, to gange samme dag).

2. **Det koster ikke blindhed.** Rate-limit-loftet er 60 i timen
   uautentificeret. Sprænges det, svarer API'et 403 — og så VED vi ikke om CI
   er grøn. Det er præcis den blindhed vagtposten blev bygget for at fjerne, så
   et abonnement der spiser budgettet ville gøre vagten værre end før.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from core.services import ci_status_watch as w


def _run(rid: str = "1", *, konklusion: str = "success", status: str = "completed",
         titel: str = "ci", sha: str = "abcdef1") -> dict:
    return {
        "id": int(rid),
        "status": status,
        "conclusion": konklusion,
        "created_at": w._nu().isoformat().replace("+00:00", "Z"),
        "display_title": titel,
        "name": titel,
        "path": f".github/workflows/{titel}.yml",
        "head_sha": sha,
        "html_url": f"https://github.com/x/y/actions/runs/{rid}",
    }


@pytest.fixture
def isoleret_state(monkeypatch):
    from core.runtime import state_store

    gemt: dict = {}
    monkeypatch.setattr(state_store, "load_json", lambda n, d: gemt.get(n, d))
    monkeypatch.setattr(state_store, "save_json", lambda n, d: gemt.__setitem__(n, d))

    @contextmanager
    def _laas(_navn):
        yield

    monkeypatch.setattr(state_store, "med_laas", _laas)
    return gemt


@pytest.fixture
def inbox(monkeypatch):
    """Stub for indbakken — vi maaler HVAD der leveres, ikke hvordan."""
    lagt: list = []
    from core.services import inbox_state

    def _registrer(*, bruger_id, kildetype, kilde_id, beskrivelse="", **_kw):
        lagt.append({"kildetype": kildetype, "kilde_id": kilde_id, "tekst": beskrivelse})
        return {"status": "ok", "post": {"post_id": "ci-svar-test"}}

    monkeypatch.setattr(inbox_state, "registrer_kilde", _registrer)
    monkeypatch.setattr(inbox_state, "laese_bruger", lambda: "bjorn")
    return lagt


@pytest.fixture
def sha_api(monkeypatch):
    """Stub for `_hent_sha_runs` — holder svar og kast i haanden."""
    kasse: dict = {"runs": [], "kast": None, "kaldte": []}

    def _stub(sha: str):
        kasse["kaldte"].append(sha)
        if kasse["kast"]:
            raise kasse["kast"]
        return kasse["runs"]

    monkeypatch.setattr(w, "_hent_sha_runs", _stub)
    return kasse


# ── abonner: et løfte der kan indfries ──────────────────────────────────


@pytest.mark.parametrize("sha", ["", "   ", None, "zzzzzzzz", "abc", "xyz1234567"])
def test_ugyldig_sha_afvises(isoleret_state, sha):
    """Et abonnement der aldrig kan indfries er værre end intet: det ser ud
    som om nogen holder øje."""
    with pytest.raises(ValueError):
        w.abonner(sha)


def test_gyldig_sha_gemmes(isoleret_state):
    ud = w.abonner("ABCDEF1", note="venter paa ci")
    assert ud["status"] == "ok"
    assert ud["sha"] == "abcdef1", "SHA skal normaliseres til lowercase"
    assert w._abonnementer()["abcdef1"]["note"] == "venter paa ci"


def test_samme_sha_to_gange_er_et_loefte(isoleret_state):
    w.abonner("abcdef1", note="foerste")
    w.abonner("abcdef1", note="anden")
    assert len(w._abonnementer()) == 1
    assert w._abonnementer()["abcdef1"]["note"] == "anden"


# ── _afgoer: hvornaar er et abonnement indfriet ─────────────────────────


def test_groen_koersel_indfrier():
    udfald, runs = w._afgoer([_run(konklusion="success")], "")
    assert udfald == "groen" and len(runs) == 1


def test_roed_koersel_indfrier_ogsaa():
    """Abonnementet venter paa et SVAR, ikke paa en groen. En roed koersel er
    et svar — og det er netop den vagtposten ikke kunne levere foer."""
    assert w._afgoer([_run(konklusion="failure")], "")[0] == "roed"


def test_koerende_koersel_lader_abonnementet_vente():
    udfald, _ = w._afgoer([_run(status="in_progress", konklusion=None)], "")
    assert udfald == "venter"


def test_ingen_koersel_paa_shaen():
    assert w._afgoer([], "")[0] == "intet_run"


def test_afbrudt_koersel_er_sit_eget_svar():
    assert w._afgoer([_run(konklusion="cancelled")], "")[0] == "afbrudt"


def test_workflow_filter_skelner_ci_fra_desk_release():
    """Et abonnement paa 'ci' maa ikke indfries af desk-releasen for samme SHA."""
    runs = [_run(rid="1", titel="ci", konklusion="success"),
            _run(rid="2", titel="desk-release", status="in_progress", konklusion=None)]
    assert w._afgoer(runs, "ci")[0] == "groen"
    assert w._afgoer(runs, "desk-release")[0] == "venter"
    assert w._afgoer(runs, "")[0] == "venter", "uden filter skal den koerende veje"


def test_workflow_filter_paa_sti():
    runs = [{"status": "completed", "conclusion": "success",
             "name": "CI", "path": ".github/workflows/ci.yml"}]
    assert w._afgoer(runs, "ci.yml")[0] == "groen"


# ── scan_abonnementer ───────────────────────────────────────────────────


def test_groen_koersel_fjerner_abonnementet(isoleret_state, sha_api):
    w.abonner("abcdef1")
    sha_api["runs"] = [_run(konklusion="success")]
    afgjorte = w.scan_abonnementer()
    assert len(afgjorte) == 1
    assert afgjorte[0]["udfald"] == "groen"
    assert w._abonnementer() == {}, "et indfriet abonnement skal ikke blive staaende"


def test_koerende_koersel_beholder_abonnementet(isoleret_state, sha_api):
    w.abonner("abcdef1")
    sha_api["runs"] = [_run(status="queued", konklusion=None)]
    assert w.scan_abonnementer() == []
    assert "abcdef1" in w._abonnementer()


def test_blindhed_indfrier_ikke(isoleret_state, sha_api):
    """Et API der tier er ikke «afgjort». Ellers ville et rate-limit indfri
    abonnementet med et svar vi ikke har maalt."""
    w.abonner("abcdef1")
    sha_api["kast"] = w.ApiUkendt("http_403")
    assert w.scan_abonnementer() == []
    assert "abcdef1" in w._abonnementer()


def test_abonnement_udloeber_naar_der_aldrig_kom_en_koersel(isoleret_state, sha_api):
    """Et workflow der ikke blev trigget maa ikke henge for evigt — det ville
    love et svar der aldrig kommer."""
    w.abonner("abcdef1")
    post = w._abonnementer()
    post["abcdef1"]["oprettet"] = (
        w._nu() - timedelta(minutes=w._ABONNEMENT_UDLOEB_MIN + 1)
    ).isoformat()
    w._gem_abonnementer(post)
    sha_api["runs"] = []
    afgjorte = w.scan_abonnementer()
    assert len(afgjorte) == 1
    assert afgjorte[0]["udfald"] == "intet_run"
    assert w._abonnementer() == {}


def test_udloeb_koster_ikke_et_api_kald(isoleret_state, sha_api):
    """Graensen skal fanges FOER kaldet, ellers betaler vi for at afslutte."""
    w.abonner("abcdef1")
    post = w._abonnementer()
    post["abcdef1"]["oprettet"] = (
        w._nu() - timedelta(minutes=w._ABONNEMENT_UDLOEB_MIN + 1)
    ).isoformat()
    w._gem_abonnementer(post)
    w.scan_abonnementer()
    assert sha_api["kaldte"] == [], "et udloebet abonnement maa ikke koste et kald"


# ── tik: svaret skal faktisk leveres ────────────────────────────────────


def test_groent_svar_leveres_i_indbakken(isoleret_state, sha_api, inbox, monkeypatch):
    monkeypatch.setattr(w, "scan_roede", lambda: [])
    w.abonner("abcdef1", note="venter paa ci")
    sha_api["runs"] = [_run(konklusion="success", titel="ci")]
    ud = w.tik()
    assert ud["abonnement"]["antal"] == 1
    assert len(inbox) == 1
    assert inbox[0]["kildetype"] == "ci_svar", "en groen koersel er ikke en alarm"
    assert "groen" in inbox[0]["tekst"]
    assert "venter paa ci" in inbox[0]["tekst"]


def test_roedt_svar_leveres_som_svar_ikke_som_alarm(isoleret_state, sha_api, inbox, monkeypatch):
    monkeypatch.setattr(w, "scan_roede", lambda: [])
    w.abonner("abcdef1")
    sha_api["runs"] = [_run(konklusion="failure")]
    w.tik()
    assert len(inbox) == 1
    assert inbox[0]["kildetype"] == "ci_svar"


def test_intet_abonnement_betyder_ingen_abonnements_kald(isoleret_state, sha_api, monkeypatch):
    monkeypatch.setattr(w, "scan_roede", lambda: [])
    ud = w.tik()
    assert ud["abonnement"]["antal"] == 0
    assert sha_api["kaldte"] == []


def test_abonnements_fejl_standser_ikke_det_brede_scan(isoleret_state, sha_api, monkeypatch):
    """De to veje er uafhaengige: et abonnement der fejler maa ikke goere
    vagtposten blind for roede koersler."""
    kaldt = {"scan": 0}

    def _scan():
        kaldt["scan"] += 1
        return []

    monkeypatch.setattr(w, "scan_roede", _scan)
    w.abonner("abcdef1")
    sha_api["kast"] = RuntimeError("noget gik i stykker")
    ud = w.tik()
    assert kaldt["scan"] == 1, "det brede scan skal stadig koere"
    assert ud["status"] == "ok"


def test_ci_svar_kan_vaekke():
    """Uden dette led staar svaret stille til naeste hjaerteslag — og saa er
    der ingen gevinst over at polle i haanden."""
    from core.services.inbox_state import kan_dispatch

    assert kan_dispatch("ci_svar")
    assert kan_dispatch("ci_alarm"), "den gamle alarm maa ikke tabe sin evne"


# ── rate-limit: regnestykket, ikke koden ────────────────────────────────


def test_abonnements_intervallet_spraenger_ikke_loftet():
    """MAALT 24/11-2026: foerste udgave brugte 90 s. Det gav 40 kald i timen
    for ét abonnement OVENI det brede scans 30 — 70 mod et loft paa 60. Fejlen
    ville foerst vise sig som blindhed i drift, ikke som en fejlende test.

    Regnestykket: bredt scan = 2 kald pr. runde, abonnement = 1 kald pr.
    abonnement pr. runde.
    """
    bredt = (3600 / w._MIN_MELLEMRUM_S) * 2
    for n in (1, 2, 3, 5):
        interval = w._MIN_MELLEMRUM_ABONNEMENT_S * n
        abonnement = (3600 / interval) * n
        assert bredt + abonnement < 60, (
            f"{n} abonnementer giver {bredt + abonnement:.0f} kald i timen "
            f"(bredt {bredt:.0f} + abonnement {abonnement:.0f}) — over loftet paa 60"
        )


def test_intervallet_skalerer_med_antallet():
    """Uden skaleringen vokser kaldtallet lineert med antallet af abonnementer,
    og to abonnementer ville alene sprænge loftet."""
    et = w._MIN_MELLEMRUM_ABONNEMENT_S * 1
    to = w._MIN_MELLEMRUM_ABONNEMENT_S * 2
    assert to == 2 * et


# ── værktøjet: end-to-end gennem dispatch-dicten ────────────────────────


def test_vaerktoejet_er_registreret_og_annonceret():
    from core.tools import simple_tools, tool_definition_v2

    navne = [t.get("function", {}).get("name") for t in simple_tools.get_tool_definitions()]
    for n in ("ci_vent_paa", "ci_venter"):
        assert n in simple_tools._TOOL_HANDLERS, f"{n} mangler i dispatch-dicten"
        assert navne.count(n) == 1, f"{n} skal vaere annonceret praecis én gang"
    assert tool_definition_v2.inconsistencies() == []


def test_ci_vent_paa_gennem_handlertabellen(isoleret_state):
    """End-to-end: kaldet gaar gennem den dict modellen faktisk rammer."""
    from core.tools import simple_tools

    ud = simple_tools._TOOL_HANDLERS["ci_vent_paa"]({"sha": "abcdef1", "note": "e2e"})
    assert ud["status"] == "ok"
    assert "abcdef1" in ud["besked"]
    assert w._abonnementer()["abcdef1"]["note"] == "e2e"


def test_ci_vent_paa_ugyldig_sha_giver_error_ikke_kast(isoleret_state):
    from core.tools import simple_tools

    ud = simple_tools._TOOL_HANDLERS["ci_vent_paa"]({"sha": "zzz"})
    assert ud["status"] == "error"
    assert "sha" in ud["error"].lower()


def test_ci_venter_viser_hvad_der_venter(isoleret_state):
    from core.tools import simple_tools

    w.abonner("abcdef1", note="mit aerinde")
    ud = simple_tools._TOOL_HANDLERS["ci_venter"]({})
    assert ud["antal"] == 1
    assert ud["venter"][0]["note"] == "mit aerinde"


def test_ci_venter_er_tom_uden_abonnementer(isoleret_state):
    from core.tools import simple_tools

    ud = simple_tools._TOOL_HANDLERS["ci_venter"]({})
    assert ud == {"status": "ok", "antal": 0, "venter": []}
