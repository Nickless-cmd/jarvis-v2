"""Tester for CI-vagtposten — hullet der blev lukket 3/10-2026.

Kernen er ikke at den kan læse en liste af kørsler. Det er to ting:

1. Den skal SKELNE mellem «der var ingen nye røde» og «vi kunne ikke se CI».
   En vagt der siger «alt fint» når API'et tier, er samme fejlklasse som
   `test_publish_scan` blev skrevet for at fange.

2. Den skal have en GRUNDLINJE. Der er historik her, i modsætning til
   baggrunds-shellene: et rødt run fra i går er ikke nyt. En vagtpost der
   råber op om 30 gamle fejl ved første kørsel bliver slukket igen.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from core.services import ci_status_watch as w


def _run(rid: str = "1", *, konklusion: str = "failure", status: str = "completed",
         oprettet: datetime | None = None, titel: str = "fix: et eller andet",
         sha: str = "3b10ee5caa6e76018809b0fcf46bd53f8da8398d") -> dict:  # pragma: allowlist secret
    return {
        "id": int(rid),
        "status": status,
        "conclusion": konklusion,
        "created_at": (oprettet or w._nu()).isoformat().replace("+00:00", "Z"),
        "display_title": titel,
        "head_sha": sha,
        "html_url": f"https://github.com/x/y/actions/runs/{rid}",
    }


@pytest.fixture
def isoleret_state(monkeypatch):
    """state_store i hukommelsen. Filen er delt mellem to processer i drift;
    i testen ville den bare lække mellem kørsler."""
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
def api(monkeypatch):
    """Stub for `_hent_runs` — holder svar og kast i hånden."""
    kasse: dict = {"runs": [], "kast": None}
    monkeypatch.setattr(w, "_hent_runs",
                        lambda: (_ for _ in ()).throw(kasse["kast"]) if kasse["kast"] else kasse["runs"])
    return kasse


@pytest.fixture
def followups(monkeypatch):
    lagt: list = []
    from core.runtime import heartbeat_triggers

    def _set(*, reason, source, text=""):
        lagt.append({"reason": reason, "source": source, "text": text})
        return {"created_at": "2026-10-03T13:00:00+00:00"}

    monkeypatch.setattr(heartbeat_triggers, "set_trigger_for_default_workspace", _set)
    return lagt


# ── hvad tæller som rødt ────────────────────────────────────────────────


def test_groen_koersel_taelles_ikke(isoleret_state, api):
    api["runs"] = [_run(konklusion="success")]
    assert w.scan_roede() == []


def test_igangvaerende_koersel_er_ikke_roed(isoleret_state, api):
    """`status != completed` betyder «kører endnu», ikke «rød»."""
    api["runs"] = [_run(status="in_progress", konklusion=None)]
    assert w.scan_roede() == []


def test_afbrudt_koersel_alarmerer_ikke(isoleret_state, api):
    """`cancelled` er med vilje ikke en fejl — et afbrudt run kan være et
    bevidst valg, og en alarm der råber op om det bliver ignoreret."""
    api["runs"] = [_run(konklusion="cancelled")]
    assert w.scan_roede() == []


def test_roed_koersel_efter_grundlinjen_fanges(isoleret_state, api):
    """Grundlinjen er sat nu; et run oprettet om lidt er nyt."""
    w._grundlinje()
    api["runs"] = [_run(oprettet=w._nu() + timedelta(seconds=30))]
    nye = w.scan_roede()
    assert len(nye) == 1


def test_historisk_roed_koersel_tier(isoleret_state, api):
    """Det afgørende: 30 gamle fejl er ikke 30 nye. Vagten må ikke råbe op om
    historik ved første kørsel — så bliver den slukket igen."""
    w._grundlinje()
    api["runs"] = [_run(oprettet=w._nu() - timedelta(days=1))]
    assert w.scan_roede() == []


def test_samme_koersel_siges_kun_en_gang(isoleret_state, api):
    w._grundlinje()
    api["runs"] = [_run(oprettet=w._nu() + timedelta(seconds=30))]
    assert len(w.scan_roede()) == 1
    assert w.scan_roede() == []


def test_groenne_i_vinduet_huskes_ogsaa(isoleret_state, api):
    """Uden det ville et run vi allerede har vurderet blive vurderet igen hver
    gang — og et gammelt rødt run i vinduet kunne dukke op som «nyt»."""
    w._grundlinje()
    api["runs"] = [_run(rid="7", konklusion="success")]
    w.scan_roede()
    assert "7" in w._rapporterede()


# ── tik: beskeden må kun komme når vi VED det ───────────────────────────


def test_roed_koersel_giver_en_followup(isoleret_state, api, followups):
    w._grundlinje()
    api["runs"] = [_run(oprettet=w._nu() + timedelta(seconds=30), titel="fix: mobile")]
    ud = w.tik()
    assert ud["status"] == "ok" and ud["nye"] == 1
    assert len(followups) == 1
    assert followups[0]["reason"] == "ci-failed"
    assert "fix: mobile" in followups[0]["text"]


def test_api_der_tier_giver_ingen_besked(isoleret_state, api, followups):
    """Det afgørende: et tysk API er ikke «CI er grøn». Vi ved det ikke — og så
    siger vi ingenting frem for at sige alt er fint."""
    w._grundlinje()
    api["kast"] = w.ApiUkendt("http_403")
    ud = w.tik()
    assert ud["status"] == "ukendt"
    assert followups == []


def test_blindhed_roerer_ikke_tidsstemplet(isoleret_state, api):
    """Ellers ville et rate-limit kunne udsætte næste forsøg med 4 minutter
    oveni den ventetid loftet selv giver."""
    w._grundlinje()
    api["kast"] = w.ApiUkendt("http_403")
    w.tik()
    from core.runtime import state_store
    assert state_store.load_json(w._GRUNDLINJE, {}).get("foerste_ved")  # grundlinjen står
    assert state_store.load_json(w._SIDSTE_TJEK, None) is None  # men vi målte ikke


def test_throttle_springer_andet_kald_over(isoleret_state, api, followups):
    api["runs"] = []
    assert w.tik()["status"] == "ok"
    andet = w.tik()
    assert andet["status"] == "skip" and andet["grund"] == "for-tidligt"


def test_trigger_der_returnerer_none_meldes_som_fejl(isoleret_state, api, monkeypatch):
    """`set_trigger_for_default_workspace` sluger sin egen fejl og giver None.
    Uden et tjek ville vi melde «sendt» om en besked der ikke findes — og
    runnene er allerede markeret sete."""
    from core.runtime import heartbeat_triggers
    monkeypatch.setattr(heartbeat_triggers, "set_trigger_for_default_workspace",
                        lambda **_: None)
    w._grundlinje()
    api["runs"] = [_run(oprettet=w._nu() + timedelta(seconds=30))]
    ud = w.tik()
    assert ud["status"] == "fejl"
    assert ud["grund"] == "trigger-blev-ikke-lagt"


# ── beskrivelsen ────────────────────────────────────────────────────────


def test_beskrivelsen_viser_sha_konklusion_og_link():
    linje = w._beskriv(_run(rid="42", konklusion="failure", titel="fix: noget"))
    assert "3b10ee5ca" in linje
    assert "failure" in linje
    assert "fix: noget" in linje
    assert "runs/42" in linje


def test_beskrivelsen_klipper_lange_titler():
    linje = w._beskriv(_run(titel="x" * 400))
    assert len(linje) < 200
