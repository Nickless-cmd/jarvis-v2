"""Sprog-broen i routeren: kun embedding-inputtet, aldrig porten.

Målt 6/9-2026 på 60 ægte beskeder — tallene står i _embedding_query's
docstring, og testene her låser den adfærd tallene retfærdiggør.
"""

from __future__ import annotations

import pytest

from core.services import tool_router as R


def test_dansk_broes_foer_embedding():
    assert R._embedding_query("møde i min kalender") == "meeting i min calendar"


def test_engelsk_og_fagord_roeres_ikke():
    """Hans fagord er i forvejen engelske — de virker allerede."""
    for s in ("run the tests", "tool prompt bash session container"):
        assert R._embedding_query(s) == s


def test_kontakten_slukker_broen(monkeypatch):
    monkeypatch.setattr(R, "_sprog_bro_taendt", lambda: False)
    assert R._embedding_query("møde i min kalender") == "møde i min kalender"


def test_broen_maa_aldrig_vaelte_routeren(monkeypatch):
    """En fejl i broen skal give den RÅ besked, ikke en exception."""
    import core.services.query_language_bridge as B

    def eksploder(_t):
        raise RuntimeError("bro nede")

    monkeypatch.setattr(B, "normalise_for_embedding", eksploder)
    assert R._embedding_query("møde i min kalender") == "møde i min kalender"


def test_tom_besked_er_sikker():
    assert R._embedding_query("") == "" and R._embedding_query(None) == ""


def test_scoren_faar_den_RAA_besked_ikke_den_broede():
    """msg_clarity skal måle hans faktiske sprog. Kun embedding-inputtet brydes.

    Ellers ville broen ændre confidence — og målingen viste netop at porten
    er uændret (median +0,0000, ingen tærskel-krydsninger på 60 beskeder).
    """
    import inspect
    kilde = inspect.getsource(R._select_inner)
    assert "top_k_similar(_embedding_query(user_message)" in kilde
    assert "_score(user_message or \"\"" in kilde, "scoren må ikke få den broede tekst"


def test_broen_er_default_TIL(monkeypatch):
    class TomConfig:
        extra: dict = {}

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: TomConfig())
    assert R._sprog_bro_taendt() is True


def test_ulaeselig_config_lader_broen_vaere_taendt(monkeypatch):
    """Modsat nudgen: her er den sikre vej at BLIVE ved med at bro, for uden
    broen er rangordningen målt dårligere — ikke bare anderledes."""
    def eksploder():
        raise RuntimeError("config nede")

    monkeypatch.setattr("core.runtime.settings.load_settings", eksploder)
    assert R._sprog_bro_taendt() is True


# ---------------------------------------------------------------------------
# Tærsklen — kalibreret 6/9 på 189 beskeder over seks måneder
# ---------------------------------------------------------------------------


def test_taersklen_lukker_de_maalte_vaerktoejs_foresporgsler_ind():
    """Fire ægte forespørgsler, målt eksakt. De tre nederste blev afvist ved 0,40.

    Tallene er confidence fra produktion 6/9-2026 med sprog-broen slået til.
    Ændres tærsklen op igen, fejler den her — så det bliver et bevidst valg.
    """
    from core.runtime.settings import RuntimeSettings
    t = float(RuntimeSettings().tool_router_threshold)
    maalte = {
        "hvad er der i min kalender i morgen": 0.40128,
        "kan du lægge et møde ind i min kalender på fredag": 0.38016,
        "kan du læse den fil og rette fejlen": 0.37488,
        "send en mail til bjorn om netværket": 0.37312,
    }
    afvist = [b for b, c in maalte.items() if c < t]
    assert not afvist, f"ægte værktøjs-forespørgsler afvises af tærsklen {t}: {afvist}"


def test_taersklen_ligger_under_formlens_loft():
    """adaptive_floor = max(0,30 · 0,60 − rate·2) er loftet for HELE confidence.

    Ved den nuværende load_more_rate (~0,08) er loftet 0,440. Kommer tærsklen
    for tæt på, kan intet nogensinde passere — det var netop fejlen ved 0,55,
    som gav 100 % fallback.
    """
    from core.runtime.settings import RuntimeSettings
    t = float(RuntimeSettings().tool_router_threshold)
    loft_ved_typisk_rate = max(0.30, 0.60 - 0.08 * 2.0)
    assert t < loft_ved_typisk_rate * 0.90, (
        f"tærskel {t} er for tæt på loftet {loft_ved_typisk_rate:.3f} — "
        "porten ville næsten aldrig åbne"
    )
