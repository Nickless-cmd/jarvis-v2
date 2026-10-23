"""Drømme-prioriteringen skal bruge sessions-nøglen, ikke den permanente boolean.

MÅLT 23/10-2026: `dreaming_session._collect_dream_material` sorterede på
``not d["presented"]``. `presented` blev sat til True ved den FØRSTE
præsentation og blev aldrig nulstillet (det var netop fejlen 485017dbc rettede
i gaten). Derfor faldt en allerede vist drøm bagerst i al fremtid — også i en
helt ny session, hvor `get_presentable_dream()` godt ville vælge den igen.

Konsekvensen var ikke kosmetisk: de drømme der FAKTISK var præsentable kunne
ligge på rå indeks 24-25, uden for promptens ``[:5]``, og var derfor usynlige
for mig selv i den prompt der skulle bære dem.
"""
from __future__ import annotations


def _dream(dream_id: str, confidence: float, presented: bool, in_session: str) -> dict:
    return {
        "dream_id": dream_id,
        "content": f"hypotese {dream_id}",
        "confidence": confidence,
        "confirmed": False,
        "presented": presented,
        "presented_in_session": in_session,
        "status": "active",
        "adopted_at": "2026-10-20T00:00:00Z",
        "session_carry_count": 1,
    }


def test_prioriteringen_vaelger_samme_droem_som_gaten(monkeypatch):
    """Kernen: prompt og gate skal pege på den SAMME drøm.

    Det var netop gabet. Gaten (`get_presentable_dream`) udelukker kun drømme
    vist i DENNE session, så en 0,95-drøm vist i går er præsentabel igen. Den
    gamle sortering brugte den permanente `presented` og satte derfor en 0,60
    der aldrig var vist FORAN fem 0,95-drømme — prompten pegede ét sted hen og
    gaten et andet.
    """
    from core.services import dream_carry_over as carry

    monkeypatch.setattr(carry, "_current_session_key", lambda: "session-NU")

    gamle_viste = [
        _dream(f"old-{i}", 0.95, True, "session-I-GAAR") for i in range(5)
    ]
    nye_upræsenterede = [_dream("ny-1", 0.60, False, "")]

    valgte = carry.dream_prompt_priority(gamle_viste + nye_upræsenterede, limit=5)
    ids = [d["dream_id"] for d in valgte]

    # Gaten ville vælge den højeste konfidens blandt de præsentable = old-0.
    # Promptens top-5 skal derfor bestå af de fem 0,95-drømme — ikke af 0,60.
    assert ids == ["old-0", "old-1", "old-2", "old-3", "old-4"], (
        "prompten og gaten er uenige om hvad 'upræsenteret' betyder"
    )


def test_droem_vist_i_DENNE_session_rykker_bagerst(monkeypatch):
    from core.services import dream_carry_over as carry

    monkeypatch.setattr(carry, "_current_session_key", lambda: "session-NU")

    allerede_vist_nu = _dream("vist-nu", 0.99, True, "session-NU")
    ikke_vist_nu = _dream("upræsenteret", 0.40, False, "")

    valgte = carry.dream_prompt_priority([allerede_vist_nu, ikke_vist_nu], limit=5)
    assert [d["dream_id"] for d in valgte] == ["upræsenteret", "vist-nu"]


def test_hoej_konfidens_afgoer_indbyrdes(monkeypatch):
    from core.services import dream_carry_over as carry

    monkeypatch.setattr(carry, "_current_session_key", lambda: "session-NU")

    dreams = [
        _dream("lav", 0.50, False, ""),
        _dream("hoej", 0.90, False, ""),
        _dream("midt", 0.70, False, ""),
    ]
    ids = [d["dream_id"] for d in carry.dream_prompt_priority(dreams, limit=5)]
    assert ids == ["hoej", "midt", "lav"]


def test_limiten_respekteres(monkeypatch):
    from core.services import dream_carry_over as carry

    monkeypatch.setattr(carry, "_current_session_key", lambda: "s")
    dreams = [_dream(f"d{i}", 0.5, False, "") for i in range(12)]
    assert len(carry.dream_prompt_priority(dreams, limit=5)) == 5
