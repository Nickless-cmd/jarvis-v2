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
