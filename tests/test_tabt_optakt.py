"""`content` mistede svarets foerste afsnit — i 77 % af turene.

## Maalingen (7/10-2026)

250 assistent-svar fra to doegn, flerblok-ture sammenlignet blok for blok:

    content == alle tekstblokke          6
    content == tekstblokke UDEN den 1.   179
    hverken eller                        47
    kun én tekstblok                     18

Og det er ikke kosmetik: `recent_chat_session_messages` og
`chat_session_messages_since_last_compact` laeser begge `content`-KOLONNEN, saa
den historik Jarvis ser af sine egne svar mangler deres aabning. Det tabte er
substans — maalt paa `message-2b1614275256475a8b18b151c1ec2f27`:

    «Tak — jeg er her.\\n\\nOg jeg kommer tilbage til noget der ikke er
     afsluttet: genstarten fra …»

## Hvorfor

`content` er `visible_output_text`, som den agentiske loekke samler. Det
FOERSTE tekst-segment streames foer loekken begynder at samle, saa det lander
kun i akkumulatorens `text_segments` — og dermed kun i blokkene.
"""
from __future__ import annotations

from core.services.visible_runs_outcomes import _med_tabt_optakt


def _tekst(*dele: str) -> list[dict]:
    return [{"type": "text", "text": d} for d in dele]


def test_optakten_sættes_foran_naar_den_mangler():
    """Kernen. Formen er den maalte: content == join(blokke[1:])."""
    blokke = _tekst("Tak — jeg er her.", "Og jeg kommer tilbage til genstarten.")
    ud = _med_tabt_optakt("Og jeg kommer tilbage til genstarten.", blokke)
    assert ud == "Tak — jeg er her.\n\nOg jeg kommer tilbage til genstarten."


def test_flere_tabte_segmenter_kommer_med_i_RAEKKEFOELGE():
    blokke = _tekst("et", "to", "tre", "svaret")
    ud = _med_tabt_optakt("svaret", blokke)
    assert ud == "et\n\nto\n\ntre\n\nsvaret"


def test_blokke_MELLEM_optakt_og_svar_roeres_ikke():
    """Et vaerktoejskald mellem to afsnit maa ikke kunne flytte tekst."""
    blokke = [
        {"type": "text", "text": "optakt"},
        {"type": "tool_use", "id": "a", "name": "bash"},
        {"type": "tool_result", "tool_use_id": "a"},
        {"type": "text", "text": "svaret"},
    ]
    assert _med_tabt_optakt("svaret", blokke) == "optakt\n\nsvaret"


def test_er_teksten_allerede_hel_roeres_den_IKKE():
    blokke = _tekst("optakt", "svaret")
    hel = "optakt\n\nsvaret"
    assert _med_tabt_optakt(hel, blokke) is hel


def test_whitespace_forskel_taeller_som_hel():
    """`normalize_markdown_structure` kan have indsat en blank linje. Det maa
    ikke laese som «noget mangler» og give dobbelt tekst."""
    blokke = _tekst("optakt", "- en\n- to")
    assert _med_tabt_optakt("optakt\n\n- en\n- to", blokke) == "optakt\n\n- en\n- to"


def test_en_ANDEN_forskel_end_en_tabt_optakt_roeres_ikke():
    """Slutter blokkenes tekst ikke paa svaret, er forskellen noget andet —
    fx leak-sanering der har ERSTATTET tekst. Saa lader vi den vaere, frem for
    at klistre en optakt paa et svar den ikke hoerer til."""
    blokke = _tekst("optakt", "noget helt tredje")
    assert _med_tabt_optakt("svaret", blokke) == "svaret"


def test_en_enkelt_tekstblok_har_ingen_optakt_at_miste():
    assert _med_tabt_optakt("svaret", _tekst("svaret")) == "svaret"


def test_ingen_blokke_vaelter_ikke():
    assert _med_tabt_optakt("svaret", None) == "svaret"
    assert _med_tabt_optakt("svaret", []) == "svaret"
    assert _med_tabt_optakt("svaret", "ikke en liste") == "svaret"


def test_tom_tekst_roeres_ikke():
    assert _med_tabt_optakt("", _tekst("a", "b")) == ""


# ── LEDNINGEN (ikke kun funktionen) ────────────────────────────────────────
#
# Foerste udgave af denne fil testede KUN `_med_tabt_optakt` direkte. En
# mutation der fjernede kaldet fra persist-stien bestod alle ni tests. Det er
# husets hyppigste fejl: koden er rigtig, og ingen kalder den.

def test_persist_stien_BRUGER_den(monkeypatch):
    import core.services.visible_runs_outcomes as vro

    gemt: dict = {}
    monkeypatch.setattr(
        vro, "_append_chat_message_with_retry",
        lambda **kw: (gemt.update(kw), {"id": "message-1", "role": "assistant"})[1])
    monkeypatch.setattr(
        "core.services.structured_content_flag.structured_content_v2_enabled",
        lambda: True)
    # Lad blok-berigelserne vaere sig selv — vi maaler ledningen, ikke dem.
    monkeypatch.setattr(vro, "_with_thinking_block", lambda b, run, r: b)
    monkeypatch.setattr(vro, "_med_udgivne_filer", lambda b, run: b)
    monkeypatch.setattr(vro, "_normaliser_tekstblokke", lambda b: b)

    class _Run:
        run_id = "visible-1"
        session_id = "chat-1"
        provider = "ollama"
        model = "deepseek-v4-flash"
        autonomous = False
        user_message = "spoergsmaal"

    vro._persist_session_assistant_message(
        _Run(), "Og jeg kommer tilbage til genstarten.",
        blocks=[{"type": "text", "text": "Tak — jeg er her."},
                {"type": "text", "text": "Og jeg kommer tilbage til genstarten."}])

    assert gemt.get("content") == "Tak — jeg er her.\n\nOg jeg kommer tilbage til genstarten.", gemt.get("content")


def test_persist_stien_roerer_ikke_et_helt_svar(monkeypatch):
    """Vagt mod at ledningen giver dobbelt tekst paa de 6 % der ER hele."""
    import core.services.visible_runs_outcomes as vro

    gemt: dict = {}
    monkeypatch.setattr(
        vro, "_append_chat_message_with_retry",
        lambda **kw: (gemt.update(kw), {"id": "message-1", "role": "assistant"})[1])
    monkeypatch.setattr(
        "core.services.structured_content_flag.structured_content_v2_enabled",
        lambda: True)
    monkeypatch.setattr(vro, "_with_thinking_block", lambda b, run, r: b)
    monkeypatch.setattr(vro, "_med_udgivne_filer", lambda b, run: b)
    monkeypatch.setattr(vro, "_normaliser_tekstblokke", lambda b: b)

    class _Run:
        run_id = "visible-1"
        session_id = "chat-1"
        provider = "ollama"
        model = "deepseek-v4-flash"
        autonomous = False
        user_message = "spoergsmaal"

    hel = "Tak — jeg er her.\n\nOg jeg kommer tilbage til genstarten."
    vro._persist_session_assistant_message(
        _Run(), hel,
        blocks=[{"type": "text", "text": "Tak — jeg er her."},
                {"type": "text", "text": "Og jeg kommer tilbage til genstarten."}])
    assert gemt.get("content") == hel
