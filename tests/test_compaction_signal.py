"""Komprimerings-signalet skal kunne ses paa TVAERS af processer.

Bjoern 18/9-2026: indikatoren over composeren viste aldrig at der blev
komprimeret, og markoeren «samtalen er blevet komprimeret» dukkede foerst op
efter en manuel opdatering.

Flaget var et in-process `set`. Prompten bygges baade i jarvis-api og
jarvis-runtime, og desk spoerger kun den ene. Komprimeringen kl. 22:20 koerte
~74 sekunder — tolv polls — uden at desk saa den.
"""
from __future__ import annotations

from core.context import compaction_signal as cs


def test_starter_og_slutter(isolated_runtime) -> None:
    assert cs.er_i_gang("s1") is False
    cs.marker_start("s1")
    assert cs.er_i_gang("s1") is True
    cs.marker_slut("s1")
    assert cs.er_i_gang("s1") is False


def test_sessionerne_er_adskilt(isolated_runtime) -> None:
    cs.marker_start("s1")
    assert cs.er_i_gang("s2") is False


def test_flaget_bor_i_det_DELTE_lager_ikke_i_processen(isolated_runtime) -> None:
    # Hele fejlen: et flag der kun findes i én proces' hukommelse. Laeses det
    # direkte fra shared_cache, er det synligt for den anden proces ogsaa.
    from core.services import shared_cache

    cs.marker_start("s1")
    assert shared_cache.get("compaction:inflight:s1") is not None


def test_tom_session_giver_aldrig_et_falsk_ja(isolated_runtime) -> None:
    cs.marker_start("")
    assert cs.er_i_gang("") is False


def test_seneste_komprimering_foelger_markoeren(isolated_runtime) -> None:
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = create_chat_session(title="t")["id"]
    assert cs.seneste_komprimering(sid) == ""

    append_chat_message(session_id=sid, role="user", content="hej")
    append_chat_message(session_id=sid, role="compact_marker", content="resume")

    # Det er DENNE vaerdi klienten sammenligner for at vide at den skal hente
    # beskederne igen. Et skift = ny markoer.
    assert cs.seneste_komprimering(sid) != ""


# ── Markoeren skal bindes til PROCES-IDENTITET (19/10-2026) ──────────────────
#
# Maalt i drift: markoeren blev sat 18:08:10 og API'et genstartet 18:08:19 — ni
# sekunder senere. Ingen komprimerings-proces koerte, alligevel viste desk
# «komprimerer...» indtil TTL'en udloeb 18:18:10. TTL'en kunne ikke svare,
# fordi den maaler TID, ikke LIV.


def test_markoeren_baerer_proces_identitet(isolated_runtime) -> None:
    """`marker_start` skal skrive HVEM, ikke kun hvornaar."""
    from core.services import shared_cache
    from core.services.in_flight_runs import current_owner

    cs.marker_start("s1")
    markoer = shared_cache.get("compaction:inflight:s1")

    assert isinstance(markoer, dict)
    assert markoer.get("owner") == current_owner(), (
        "markoeren bar ikke den saettende proces — saa kan en doed markoer "
        "aldrig skelnes fra en levende"
    )


def test_markoer_fra_doed_proces_afvises_med_det_samme(isolated_runtime) -> None:
    """Den maalte fejl: en markoer hvis ejer er vaek maa ikke lyse i 600 s."""
    from core.services import shared_cache

    noegle = "compaction:inflight:s1"
    # pid 999999 findes ikke → `owner_still_alive` svarer False (bevis).
    shared_cache.set(noegle, {"startet": 0.0, "owner": "999999:12345"}, ttl_seconds=600)
    assert shared_cache.get(noegle) is not None, "forudsaetning: markoeren staar"

    assert cs.er_i_gang("s1") is False, (
        "en markoer fra en doed proces blev laest som «komprimerer»"
    )
    # Og den skal ryddes, saa naeste poll ikke spoerger forgaeves.
    assert shared_cache.get(noegle) is None, "den doede markoer blev ikke ryddet"


def test_markoer_fra_levende_proces_taelles(isolated_runtime) -> None:
    """Den anden retning: en LEVENDE proces' markoer maa ikke afvises."""
    from core.services import shared_cache
    from core.services.in_flight_runs import current_owner

    shared_cache.set(
        "compaction:inflight:s1",
        {"startet": 0.0, "owner": current_owner()},
        ttl_seconds=600,
    )
    assert cs.er_i_gang("s1") is True


def test_uafgoerbar_ejer_afviser_ikke(isolated_runtime) -> None:
    """``None`` er ikke ``False``: et gaet maa ikke slukke en levende indikator.

    Samme regel som `owner_still_alive` selv foelger — en post vi ikke kan
    afgoere ejerskabet paa maa ikke stemples paa et gaet.
    """
    from core.services import shared_cache

    shared_cache.set(
        "compaction:inflight:s1",
        {"startet": 0.0, "owner": "ikke-et-pid"},
        ttl_seconds=600,
    )
    assert cs.er_i_gang("s1") is True


def test_gammel_markoer_uden_ejer_taelles(isolated_runtime) -> None:
    """Markoerer skrevet foer kolonnen fandtes skal stadig virke.

    De har ingen `owner` at spoerge om — TTL'en er deres eneste udloeb, som
    foer. At afvise dem ville slukke indikatoren for en komprimering der
    faktisk koerer, under en udrulning.
    """
    from core.services import shared_cache

    shared_cache.set("compaction:inflight:s1", {"startet": 0.0}, ttl_seconds=600)
    assert cs.er_i_gang("s1") is True


def test_komprimeringen_saetter_og_fjerner_det_delte_flag(isolated_runtime, monkeypatch) -> None:
    """Koblingen i selve komprimeringen — ikke kun modulet for sig."""
    from core.services import prompt_contract as pc
    from core.services.prompt_sections import transcript_sections as ts

    set_undervejs: list[bool] = []

    def _falsk_komprimering(session_id, keep_recent, **kw):
        set_undervejs.append(cs.er_i_gang(session_id))
        # Samme oprydning som den rigtige `_run_session_compaction` gør.
        with ts._compact_inflight_lock:
            ts._compact_inflight.discard(session_id)
        cs.marker_slut(session_id)

    monkeypatch.setattr(pc, "_run_session_compaction", _falsk_komprimering)

    class _Beslutning:
        should_compact = True
        low_water_target = 1000

    import core.context.compaction_policy as cp
    monkeypatch.setattr(cp, "compaction_decision", lambda *a, **k: _Beslutning())

    class _Tråd:
        def __init__(self, target, args, kwargs, **_): self.t, self.a, self.k = target, args, kwargs
        def start(self): self.t(*self.a, **self.k)

    monkeypatch.setattr(ts._threading_mod, "Thread", _Tråd)

    class _S:
        context_keep_recent = 20

    ts._maybe_auto_compact_session("s9", [], _S())

    assert set_undervejs == [True], "flaget var ikke sat mens komprimeringen koerte"
    assert cs.er_i_gang("s9") is False, "flaget blev ikke fjernet bagefter"
