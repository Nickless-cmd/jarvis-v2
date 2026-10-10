"""Arvede haler i kompaktions-markører (målt 10/10-2026).

Markøren = resumé + hale. Den mekaniske fallback førte den forrige markør videre
ORDRET — inklusive dens hale — så den nye markør fik en hale inde i resumé-delen
oven på sin egen friske hale. Målt i DB'en: 25 af 231 markører var nestede, ALLE
fra den mekaniske vej, og i dem var 88% af resumé-delen (median 26.739 tegn) en
arvet hale.
"""
from __future__ import annotations

from core.context.compaction_policy import (
    HALE_OVERSKRIFT,
    render_transcript_for_summary,
    strip_embedded_tail,
)
from core.context.kompaktering import TIDLIGERE_RESUME, mekanisk_opsummering


def _markoer(resume: str, hale: str) -> str:
    return f"<summary>{resume}</summary>{HALE_OVERSKRIFT}{hale}"


# ── strip_embedded_tail ────────────────────────────────────────────────────

def test_strip_fjerner_halen_og_beholder_resumeet():
    tekst = _markoer("DETTE ER RESUMÉET", "[Bjørn] gammel runde\n[tool] output")
    assert strip_embedded_tail(tekst) == "<summary>DETTE ER RESUMÉET</summary>"


def test_strip_er_urort_naar_der_ikke_er_nogen_hale():
    tekst = "<summary>kun et resumé</summary>"
    assert strip_embedded_tail(tekst) == tekst


def test_strip_klarer_den_sammenfoldede_variant():
    # mekanisk opsummering kollapser whitespace FØR den klipper.
    tekst = ("<summary>R</summary> "
             "## Seneste udveksling (ordret bevaret siden compaction): gammel hale")
    assert strip_embedded_tail(tekst) == "<summary>R</summary>"


def test_strip_af_tom_streng_er_tom():
    assert strip_embedded_tail("") == ""


# ── den mekaniske fallback arver ikke ──────────────────────────────────────

def test_mekanisk_opsummering_arver_ikke_hale():
    forrige = _markoer("FORRIGE RESUMÉ", "[Bjørn] gammel runde " + "x" * 5000)
    ud = mekanisk_opsummering([
        {"role": TIDLIGERE_RESUME, "content": forrige},
        {"role": "user", "content": "ny besked"},
    ])
    assert "FORRIGE RESUMÉ" in ud          # resuméet bæres videre
    assert "gammel runde" not in ud        # halen gør ikke
    assert HALE_OVERSKRIFT.strip() not in ud


# ── transskriptet til opsummereren ─────────────────────────────────────────

def test_render_transcript_stripper_arvede_haler():
    forrige = _markoer("FORRIGE", "[Bjørn] hale-tekst " + "y" * 4000)
    tekst = render_transcript_for_summary([{"role": TIDLIGERE_RESUME, "content": forrige}])
    assert "FORRIGE" in tekst
    assert "hale-tekst" not in tekst


# ── end-to-end: to komprimeringer i træk ───────────────────────────────────

def test_to_komprimeringer_giver_praecis_en_hale(monkeypatch):
    from core.context import session_compact

    stored: dict = {}
    msgs = []
    for k in range(6):
        msgs.append({"role": "user", "content": f"U{k} " + "x" * 300})
        msgs.append({"role": "assistant", "content": f"A{k} " + "z" * 300})

    monkeypatch.setattr(session_compact, "_get_all_session_messages", lambda sid: msgs)
    monkeypatch.setattr(
        session_compact, "_store_marker",
        lambda sid, text, git_sha="": stored.update(m1=text) or "m1",
    )
    session_compact.compact_session_history(
        "s", keep_recent_tokens=200, summarise_fn=mekanisk_opsummering,
    )
    m1 = stored["m1"]
    assert m1.count(HALE_OVERSKRIFT) == 1

    # Anden komprimering: markøren fra første kørsel er nu "den forrige".
    msgs2 = [{"role": TIDLIGERE_RESUME, "content": m1}] + msgs
    monkeypatch.setattr(session_compact, "_get_all_session_messages", lambda sid: msgs2)
    monkeypatch.setattr(
        session_compact, "_store_marker",
        lambda sid, text, git_sha="": stored.update(m2=text) or "m2",
    )
    session_compact.compact_session_history(
        "s", keep_recent_tokens=200, summarise_fn=mekanisk_opsummering,
    )
    assert stored["m2"].count(HALE_OVERSKRIFT) == 1, "markøren arvede en hale"
