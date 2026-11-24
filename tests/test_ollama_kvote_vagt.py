"""Kvote-vagten skal svare rigtigt — og aldrig gætte når Ollama ikke svarer.

BAGGRUND (målt 24/11-2026): Ollama mailede «90% of your monthly limit» kl.
04:05 UTC. ``kvote_reference()`` fandtes allerede i ``ollama_usage``, men INGEN
kaldte den — en mekanisme hvis indgangsbetingelse intet kunne opfylde. Disse
tests holder vagten fast på tre ting:

1. Den regner procenten ud fra Ollamas EGET tal, ikke fra vores pris-tabel
   (som overestimerer 1,8x).
2. Den fejler ÅBENT: kan Ollama ikke nås, bremser den ingenting.
3. Tærsklerne ligger under de 90% hvor mailen kommer — ellers er vagten en
   efternøler der først vågner når skaden er sket.
"""

from __future__ import annotations

import pytest

from core.services import ollama_kvote_vagt as vagt


@pytest.fixture(autouse=True)
def _ren_cache():
    vagt._nulstil_cache()
    yield
    vagt._nulstil_cache()


def _stub_reference(monkeypatch, *, usage_usd: float, kald: int = 1000):
    """Stub Ollamas svar uden at røre netværket."""
    from core.services import ollama_usage

    monkeypatch.setattr(
        ollama_usage,
        "kvote_reference",
        lambda timeout=20.0, range_="30d": {
            "range": range_,
            "fra": "2026-10-25T00:00:00Z",
            "til": "2026-11-24T18:00:00Z",
            "kald": kald,
            "usage_usd": usage_usd,
            "input_tokens": 1_800_000_000,
            "cached_input_tokens": 1_500_000_000,
            "output_tokens": 41_000_000,
            "buckets": [],
        },
    )


def test_vagten_maa_ler_30_dage_ikke_ollamas_default(monkeypatch):
    """Ollamas default-range er 7 dage — en vagt der måler en uge mod et
    månedsloft bremser aldrig.

    MÅLT 24/11-2026, og det var en ægte fejl i første version: vagten kaldte
    ``kvote_reference()`` uden range, fik 7-dagstallet ($34,35) og rapporterede
    29,9% — mens 30-dagstallet var $106,55, altså ~93% af loftet. Vagten ville
    have stået på «normal» indtil kvoten var brugt op.
    """
    set_range = {}

    # INGEN default på ``range_`` med vilje: med en default ville vagten få
    # "30d" tilbage uanset hvad den bad om, og testen ville måle sin egen
    # default i stedet for vagtens kald. Det gjorde den blind i første forsøg —
    # mutationen (fjern range_) blev IKKE fældet.
    def _fang(timeout=20.0, **kwargs):
        set_range["range"] = kwargs.get("range_")
        return {"range": kwargs.get("range_"), "kald": 1, "usage_usd": 10.0, "buckets": []}

    from core.services import ollama_usage

    monkeypatch.setattr(ollama_usage, "kvote_reference", _fang)
    vagt.kvote_status(force=True)
    assert set_range["range"] == "30d", (
        "vagten bad om %r — Ollamas default er 7 dage, så procenten ville være "
        "beregnet på en uge mod et månedsloft" % set_range.get("range")
    )


def test_procenten_kommer_fra_ollamas_eget_tal(monkeypatch):
    """$57,50 af et $115-loft er 50% — ikke 50% af vores egen pris-tabel."""
    _stub_reference(monkeypatch, usage_usd=57.5)
    s = vagt.kvote_status(force=True)
    assert s["kendt"] is True
    assert s["procent"] == 50.0
    assert s["niveau"] == "normal"
    assert s["usage_usd"] == 57.5


def test_bremse_taersklen_ligger_under_mailens_90_procent(monkeypatch):
    """Vagten skal vågne FØR Ollama sender sin 90%-mail, ikke bagefter.

    Målt: mailen kom ved 90%. Lå bremsen på 90 eller derover, ville det første
    signal vi fik være det samme som Ollamas — altså ingen vagt, kun en
    gengivelse.
    """
    assert vagt.BREMSE_PROCENT < vagt.MAIL_PROCENT
    assert vagt.STOP_PROCENT > vagt.BREMSE_PROCENT

    _stub_reference(monkeypatch, usage_usd=115.0 * 0.86)
    assert vagt.kvote_status(force=True)["niveau"] == "bremse"
    assert vagt.skal_bremse() is True
    assert vagt.skal_stoppe() is False


def test_stop_niveau_ved_97_procent(monkeypatch):
    _stub_reference(monkeypatch, usage_usd=115.0 * 0.98)
    s = vagt.kvote_status(force=True)
    assert s["niveau"] == "stop"
    assert vagt.skal_stoppe() is True


def test_ukendt_kvote_bremser_intet(monkeypatch):
    """Kan Ollama ikke nås, må vagten IKKE stoppe driften.

    En vagt der fejler lukket ville stoppe hele systemet på en netværksfejl.
    Det er en værre fejl end den den vogter, og den ville ramme hver gang
    ollama.com er nede.
    """
    from core.services import ollama_usage

    monkeypatch.setattr(ollama_usage, "kvote_reference", lambda timeout=20.0, range_="30d": None)
    s = vagt.kvote_status(force=True)
    assert s["kendt"] is False
    assert s["niveau"] == "ukendt"
    assert s["procent"] is None
    assert vagt.skal_bremse() is False
    assert vagt.skal_stoppe() is False


def test_cache_sparer_kald_mod_ollama(monkeypatch):
    """Heartbeat må ikke lave et HTTP-kald til ollama.com ved hvert tick."""
    kald = {"n": 0}

    def _taeller(timeout=20.0, range_="30d"):
        kald["n"] += 1
        return {"range": "30d", "kald": 1, "usage_usd": 10.0, "buckets": []}

    from core.services import ollama_usage

    monkeypatch.setattr(ollama_usage, "kvote_reference", _taeller)
    vagt.kvote_status(force=True)
    vagt.kvote_status()
    vagt.kvote_status()
    assert kald["n"] == 1, "cachen skulle have sparet de to sidste kald"


def test_loftet_er_en_udledning_og_staar_som_saadan(monkeypatch):
    """Månedsloftet kan ikke aflæses i API'et — det skal fremgå af svaret.

    ``/api/usage`` har intet ``limit``-felt (målt 24/11-2026). Loftet er udledt
    af mailens 90% og forbruget på det tidspunkt. Det skal stå i svaret, så
    ingen læser det som en aflæsning.
    """
    _stub_reference(monkeypatch, usage_usd=10.0)
    s = vagt.kvote_status(force=True)
    assert s["maaned_loft_usd"] == 115.0
    assert "maaned_loft_usd" in s


def test_heartbeat_spoerger_vagten_foer_den_rammer_ollama(monkeypatch):
    """Koblingen skal være ÆGTE: heartbeat må ikke gå på Ollama uden at spørge.

    Det er præcis den fejlform Bjørn kalder teater — en mekanisme der findes,
    men som ingen kalder. ``kvote_reference`` sad i ``ollama_usage`` i timevis
    uden en eneste kalder. Denne test fælder det hvis koblingen forsvinder.

    Målt 24/11-2026: 92,7% af månedsloftet var brugt, og heartbeat kørte
    alligevel direkte på ``deepseek-v4.1-flash:cloud``.
    """
    from core.services import heartbeat_runtime as hb

    kaldt = {"vagt": 0, "ollama": 0, "billig": 0}

    def _vagt():
        kaldt["vagt"] += 1
        return True

    def _ollama(**kwargs):
        kaldt["ollama"] += 1
        return {"text": "ollama-svar", "cost_usd": 0.0}

    def _billig(prompt, **kwargs):
        kaldt["billig"] += 1
        return {"text": "billig-svar", "cost_usd": 0.0}

    monkeypatch.setattr(
        "core.services.ollama_kvote_vagt.skal_bremse", _vagt, raising=True
    )
    monkeypatch.setattr(hb, "_execute_ollama_prompt", _ollama, raising=True)
    monkeypatch.setattr(
        "core.services.heartbeat_provider_fallback.try_heartbeat_cheap_fallback",
        _billig,
        raising=True,
    )

    # ``_execute_heartbeat_model`` er den funktion der omslutter provider-
    # dispatch. Navnet er SLÅET OP i kilden (heartbeat_runtime.py:3628), ikke
    # gættet — jeg gættede først og fik en falsk «findes ikke».
    assert hasattr(hb, "_execute_heartbeat_model"), (
        "heartbeat_runtime har ikke _execute_heartbeat_model — er dispatch flyttet?"
    )
    hb._execute_heartbeat_model(
        prompt="hej",
        target={"provider": "ollama", "model": "m", "base_url": ""},
        policy={},
        open_loops=[],
    )

    assert kaldt["vagt"] >= 1, "heartbeat spurgte ALDRIG kvote-vagten"
    assert kaldt["billig"] >= 1, "vagten sagde brems, men cheap-lanen blev ikke prøvet"
    assert kaldt["ollama"] == 0, "heartbeat ramte Ollama selv om kvoten er ved at være brugt"
