"""Et sent godkendt resultat skal have en LÆSER, ikke kun en række.

Målt 22/11-2026 (side-aa429f4212, 4.028 kort): 41 kort blev afgjort efter
deres tur var slut, og 40 af dem kørte kommandoen færdig. Resultatet blev
skrevet i `chat_messages` — så Bjørn SÅ det — men den tur der bad om lov var
væk, så ingen læste svaret og sagde hvad det betød.

Prøverne her vogter især de tre værn mod at en opfølgningstur føder den næste:
idempotensen, kæde-stemplet og kravet om en fri session. Hvert af dem er
fail-closed, og hvert af dem skal kunne ses at FEJLE hvis det fjernes.
"""
from __future__ import annotations

import pytest

from core.runtime import db_core
from core.services import approval_followup as F


@pytest.fixture(autouse=True)
def _ren(isolated_runtime):
    # `get_runtime_state_value` har en read-cache med 2s TTL. Uden denne
    # nulstilling kan en markør fra den FORRIGE test give et falsk hit — og så
    # består idempotens-prøven af den forkerte grund.
    db_core.clear_runtime_state_cache()
    yield
    db_core.clear_runtime_state_cache()


class _Fake:
    def __init__(self):
        self.terminal: bool | None = True
        self.levende: str | None = None
        self.start_ok = True
        self.starts: list[dict] = []


@pytest.fixture
def fake(monkeypatch):
    f = _Fake()

    monkeypatch.setattr(
        "core.services.visible_runs_outcomes.run_er_terminal",
        lambda _rid: f.terminal)

    monkeypatch.setattr(
        "core.services.run_event_log.active_run_for_session",
        lambda _sid: f.levende)

    def _start(**kw):
        if not f.start_ok:
            raise RuntimeError("start fejlede")
        f.starts.append(kw)
        return f"visible-ny{len(f.starts)}"

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached",
        _start)
    return f


def _kald(**kw):
    args = dict(approval_id="a1", tool_name="bash", session_id="s1",
                oprindeligt_run_id="r1", force_user_id="u1")
    args.update(kw)
    return F.start_opfølgning(**args)


# ── den vej der skal virke ───────────────────────────────────────────────
def test_glad_vej_starter_praecis_en_tur(fake):
    ud = _kald()

    assert ud["started"] is True
    assert len(fake.starts) == 1
    assert ud["run_id"] == "visible-ny1"


def test_beskeden_naevner_vaerktoejet_og_resultatet(fake):
    _kald(tool_name="bash")

    besked = fake.starts[0]["message"]
    assert "bash" in besked
    assert "efter turen var slut" in besked
    # Den skal bede om en LÆSNING, ikke om en ny kommando.
    assert "resultatet ligger" in besked


def test_origin_er_sat_saa_klienten_ser_en_selvstaendig_tur(fake):
    _kald()

    # Tom origin får reduceren til at flette teksten ind i den FORRIGE besked
    # (målt 12/11-2026). Værdien skal desuden ligge uden for ORIGINS.
    from core.services.autonomous_sessions import ORIGINS

    origin = fake.starts[0]["origin"]
    assert origin
    assert origin not in ORIGINS


def test_ejeren_foeres_med(fake):
    _kald(force_user_id="u-42")

    assert fake.starts[0]["force_user_id"] == "u-42"


# ── de tre værn mod løkker ───────────────────────────────────────────────
def test_tur_der_lever_faar_resultatet_selv(fake):
    fake.terminal = False

    ud = _kald()

    assert ud["started"] is False
    assert "lever stadig" in ud["grund"]
    assert fake.starts == []


def test_kan_ikke_afgoere_terminal_starter_ikke(fake):
    # `None` er «ved ikke», ikke «slut». En ekstra tur oveni ville give to svar
    # på samme kort.
    fake.terminal = None

    ud = _kald()

    assert ud["started"] is False
    assert fake.starts == []


def test_optaget_session_starter_ikke(fake):
    fake.levende = "visible-anden"

    ud = _kald()

    assert ud["started"] is False
    assert "optaget" in ud["grund"]
    assert fake.starts == []


def test_samme_kort_foeder_kun_en_tur(fake):
    foerste = _kald()
    anden = _kald()

    assert foerste["started"] is True
    assert anden["started"] is False
    assert "allerede fulgt op" in anden["grund"]
    assert len(fake.starts) == 1


def test_kaeden_stopper_ved_en_opfølgningstur(fake):
    # Turen der bad om godkendelsen var SELV en opfølgning → ingen ny.
    assert F._skriv(F._run_markoer_noegle("r1"), {
        "approval_id": "tidligere", "oprindeligt_run": "r0",
    })

    ud = _kald()

    assert ud["started"] is False
    assert "kæden stopper" in ud["grund"]
    assert fake.starts == []


def test_forskellige_kort_faar_hver_sin_tur(fake):
    _kald(approval_id="a1")
    _kald(approval_id="a2")

    assert len(fake.starts) == 2


# ── fail-closed: vi gætter ikke ──────────────────────────────────────────
def test_manglende_id_starter_ikke(fake):
    ud = _kald(session_id="")

    assert ud["started"] is False
    assert fake.starts == []


def test_start_fejl_efterlader_markoer_saa_vi_ikke_forsoeger_igen(fake):
    fake.start_ok = False

    foerste = _kald()
    assert foerste["started"] is False
    assert "start fejlede" in foerste["grund"]

    # Markøren blev skrevet FØR starten. Derfor forsøger vi ikke igen på samme
    # kort — en fejlende start må ikke blive et uendeligt retry-loop.
    anden = _kald()
    assert anden["started"] is False
    assert "allerede fulgt op" in anden["grund"]


def test_markoer_kan_ikke_skrives_starter_ikke(fake, monkeypatch):
    monkeypatch.setattr(F, "_skriv", lambda _n, _v: False)

    ud = _kald()

    assert ud["started"] is False
    assert "markøren" in ud["grund"]
    assert fake.starts == []


def test_utloebet_markoer_blokerer_ikke_for_evigt():
    # En markør ældre end levetiden skal ikke spærre for en legitim ny tur på
    # samme kort-id (id'er genbruges ikke, men state skal ikke vokse for evigt).
    gammel = {"oprettet": "2020-01-01T00:00:00+00:00"}
    assert F._er_utloebet(gammel) is True

    frisk = {"oprettet": "2099-01-01T00:00:00+00:00"}
    assert F._er_utloebet(frisk) is False

    uten_tid = {}
    assert F._er_utloebet(uten_tid) is False
