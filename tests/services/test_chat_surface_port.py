"""Porten fra læseopgave til flade — tærsklerne og begrundelserne.

Testene her fælder politikken. Portens egen mening om tærsklerne må ikke
opstå: den skal arve `surface_for_reading_task` ord for ord.
"""

from core.services.chat_response_policy import decide_surface, surface_for_reading_task


def test_compare_with_two_shared_axes_gets_comparison():
    dom = decide_surface("compare", item_count=3, shared_dimensions=2)
    assert dom["flade"] == "comparison"
    assert dom["vaerktoej"] is None
    assert dom["navn"] == "sammenligning"


def test_compare_with_one_shared_axis_is_prose_and_says_why():
    """To ting på én akse er en liste, ikke en sammenligning.

    Niveau 4's kriterium står ved magt. Porten skal sige HVORFOR den siger nej,
    så modellen kan rette sin vurdering i stedet for at gætte.
    """
    dom = decide_surface("compare", item_count=2, shared_dimensions=1)
    assert dom["flade"] is None
    assert dom["vaerktoej"] is None
    assert "to fælles akser" in dom["reason"]


def test_sequence_below_three_items_is_prose():
    dom = decide_surface("sequence", item_count=2)
    assert dom["flade"] is None
    assert "tre led" in dom["reason"]


def test_sequence_at_three_items_gets_timeline():
    assert decide_surface("sequence", item_count=3)["flade"] == "timeline"


def test_stats_outside_three_to_eight_is_prose():
    assert decide_surface("scan_numbers", item_count=2)["flade"] is None
    assert decide_surface("scan_numbers", item_count=9)["flade"] is None
    assert decide_surface("scan_numbers", item_count=4)["flade"] == "stats"


def test_numbers_routes_to_vis_graf_not_a_native_surface():
    """Tal hvis FORM er pointen hører i et tegne-værktøj, ikke i en tekstblok."""
    dom = decide_surface("numbers")
    assert dom["vaerktoej"] == "vis_graf"
    assert dom["flade"] is None


def test_flow_routes_to_mermaid():
    assert decide_surface("flow")["vaerktoej"] == "render_mermaid"


def test_interactive_routes_to_widget():
    assert decide_surface("interactive")["vaerktoej"] == "vis_widget"


def test_none_task_is_prose():
    """Step 0: de fleste svar er samtale og svarer sig selv i tekst."""
    dom = decide_surface("none")
    assert dom["flade"] is None
    assert dom["vaerktoej"] is None
    assert "ingen flade" in dom["reason"]


def test_already_rendered_wins_over_every_task():
    for task in ("compare", "numbers", "flow", "scan_numbers", "warn"):
        dom = decide_surface(
            task, item_count=5, shared_dimensions=3, already_rendered=True,
        )
        assert dom["flade"] is None
        assert dom["vaerktoej"] is None
        assert "allerede vist" in dom["reason"]


def test_unknown_task_never_crashes_and_returns_prose():
    dom = decide_surface("noget-opdigtet", item_count=7)
    assert dom["flade"] is None
    assert dom["vaerktoej"] is None


def test_port_and_policy_agree_on_every_native_surface():
    """Porten må ikke have sin egen mening om tærsklerne."""
    cases = [
        ("compare", 2, 2),
        ("compare", 1, 2),
        ("sequence", 3, 0),
        ("scan_numbers", 3, 0),
        ("choose", 2, 0),
        ("choose", 7, 0),
        ("locate", 1, 0),
        ("warn", 1, 0),
        ("warn", 2, 0),
    ]
    for task, count, axes in cases:
        expected = surface_for_reading_task(
            task, item_count=count, shared_dimensions=axes,
        )
        got = decide_surface(task, item_count=count, shared_dimensions=axes)
        assert got["flade"] == expected, f"{task}/{count}/{axes}"
