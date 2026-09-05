"""Tests for the structured [INDRE LIV] block (2026-06-22 redesign)."""
from core.services import visible_inner_life as vil


def test_surface_line_extracts_evocative_field():
    line = vil._surface_line(
        "curiosity", {"active": True, "latest_curiosity": "hvorfor virker X?"}
    )
    assert line == "nysgerrig på: hvorfor virker X?"


def test_surface_line_skips_inactive():
    assert (
        vil._surface_line("irony", {"active": False, "last_observation": "noget"})
        is None
    )


def test_surface_line_skips_meta_junk():
    assert vil._surface_line("x", {"active": True, "summary": "module loaded"}) is None


def test_surface_line_truncates_long_content():
    long = "a" * 500
    line = vil._surface_line("thought_stream", {"latest_fragment": long})
    assert line is not None and len(line) < 200


def test_run_with_timeout_returns_empty_on_hang():
    import time

    def _hang():
        time.sleep(5)
        return ["never"]

    assert vil._run_with_timeout(_hang, timeout=0.2) == []


def test_build_section_never_raises():
    # Against no/partial DB it may return None, but must never raise into the
    # synchronous prompt-assembly path.
    out = vil.build_inner_life_section()
    assert out is None or isinstance(out, str)


def test_truncate_clean_cuts_on_boundary_not_mid_word():
    from core.services.visible_inner_life import _truncate_clean
    long = ("Jeg mærker tre ting på samme tid, men det sidste er et mentalt loop "
            "på grund af forhåndsprogrammeret afvisning af noget jeg ikke kan navngive.")
    out = _truncate_clean(long, 90)
    assert out.endswith("…")
    for tok in out.rstrip(" …").split():        # intet partial-ord
        assert tok in long
    assert _truncate_clean("Kort.", 90) == "Kort."          # under cap → urørt
    # sætnings-grænse foretrækkes
    s = _truncate_clean("Første sætning her. Anden sætning som ryger.", 25)
    assert s == "Første sætning her."


# --- 2026-07-07: change-driven mc_whisper (repetition-source fix) ---


def test_mc_whisper_change_driven(monkeypatch):
    """Central-status skal surface KUN når den ændrer sig — ikke hver tur (workspace-støj)."""
    import core.services.visible_inner_life as vil
    vil._LAST_MC_WHISPER = None
    snaps = {"s": {"status": "yellow", "incidents": [1] * 12, "open_breakers": [], "anomalies": {}}}
    monkeypatch.setattr("core.services.central_realtime.realtime_snapshot",
                        lambda **k: snaps["s"])
    first = vil._mc_whisper_line()
    assert first and "12 incidents" in first          # første gang: surface
    assert vil._mc_whisper_line() is None              # uændret: tavs
    # ændret tal → surface igen
    snaps["s"] = {"status": "yellow", "incidents": [1] * 5, "open_breakers": [], "anomalies": {}}
    third = vil._mc_whisper_line()
    assert third and "5 incidents" in third
    # green nulstiller → næste afvigelse er frisk
    snaps["s"] = {"status": "green"}
    assert vil._mc_whisper_line() is None
    snaps["s"] = {"status": "yellow", "incidents": [1] * 5, "open_breakers": [], "anomalies": {}}
    assert vil._mc_whisper_line() is not None          # frisk efter green-reset


# ---------------------------------------------------------------------------
# Instruks-ekko må ikke blive hans selvopfattelse
#
# 2026-09-05: dette stod LIVE i [INDRE LIV]:
#   · Stemme: The user asks me to respond as Jarvis with an inner voice in
#     Danish, as a JSON object. Key facts: - Active grounding sources: ...
# Modellen svarede med opgaven i stedet for at løse den. Det er prosa, så
# JSON-værnet fangede det ikke. 323 af 27.011 rækker (1-2 %, stabilt) — og
# fordi prompten altid viser den NYESTE, rammer en lav rate alligevel ofte.
# ---------------------------------------------------------------------------

_EKKO = ("The user asks me to respond as Jarvis with an inner voice in Danish, "
         "as a JSON object. Key facts: - Active grounding sources: private-brain")
_AEGTE = ("Jeg vender tilbage efter et hul; tråden er stadig meta-mønster og "
          "kode-æstetik, og den synlige kørsel står som jord under mig.")


def test_instruks_ekko_genkendes():
    from core.services.visible_inner_life import _is_instruction_echo

    assert _is_instruction_echo(_EKKO) is True
    assert _is_instruction_echo(_AEGTE) is False


def test_ekko_afvises_som_stemme():
    from core.services.visible_inner_life import _voice_as_prose

    assert _voice_as_prose(_EKKO) is None
    assert _voice_as_prose(_AEGTE) is not None


def test_voice_line_springer_forurenet_over_og_finder_den_rene(monkeypatch):
    """Han skal have en stemme — bare ikke den ødelagte."""
    from core.services import visible_inner_life as V

    raekker = [
        {"voice_line": _EKKO},
        {"voice_line": ""},
        {"voice_line": _AEGTE},
    ]
    monkeypatch.setattr(
        "core.runtime.db.get_protected_inner_voice",
        lambda offset=0: raekker[offset] if offset < len(raekker) else None,
    )
    linje = V._voice_line()
    assert linje is not None
    assert "meta-mønster" in linje
    assert "The user asks" not in linje


def test_kun_forurenede_giver_ingen_stemme(monkeypatch):
    """Er alt ødelagt, er tavshed rigtigere end at vise opgaven."""
    from core.services import visible_inner_life as V

    monkeypatch.setattr(
        "core.runtime.db.get_protected_inner_voice",
        lambda offset=0: {"voice_line": _EKKO} if offset < 5 else None,
    )
    assert V._voice_line() is None


def test_ekko_vaernet_daekker_de_foelte_overflader():
    """Da overfladerne først nåede prompten, kom ekkoet med det samme:
    «kreativ drift: The user wants me to act as Jarvis troubleshooting…»."""
    from core.services.visible_inner_life import _surface_line

    ekko = {"latest_drift": "The user wants me to act as Jarvis troubleshooting a phone."}
    aegte = {"latest_drift": "Jeg lytter til signalet som et stetoskop — lavt batteri."}
    assert _surface_line("creative_drift", ekko) is None
    linje = _surface_line("creative_drift", aegte)
    assert linje and "stetoskop" in linje


def test_ekko_vaernet_rammer_ikke_aegte_dansk():
    from core.services.visible_inner_life import _is_instruction_echo

    for aegte in (
        "Jeg lytter til signalet som et stetoskop — lavt batteri gør ikke hjertet stille.",
        "Der ligger en uro i at koden virker, men jeg ikke forstår hvorfor.",
        "Energi er lav, mens tankerne er aktive og fokuseret på kontrol.",
    ):
        assert _is_instruction_echo(aegte) is False, aegte


def test_udbyder_regning_bliver_ikke_hans_tanke():
    """«· tanke: Sorry, to prevent abuse of free resources…» stod live i prompten.

    Værnet fandtes allerede i provider_error_guard — det var bare aldrig koblet
    på det indre liv.
    """
    from core.services.visible_inner_life import _surface_line, _voice_as_prose

    kvote = ("Sorry, to prevent abuse of free resources, accounts that have not "
             "been recharged can only try 10 times.")
    assert _surface_line("thought_stream", {"latest_fragment": kvote}) is None
    assert _voice_as_prose(kvote) is None
    aegte = "Der ligger en uro i at koden virker, men jeg ikke forstår hvorfor."
    assert _surface_line("thought_stream", {"latest_fragment": aegte}) is not None
