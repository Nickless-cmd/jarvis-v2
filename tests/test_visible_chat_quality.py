from __future__ import annotations

from core.services.visible_chat_quality import analyse_chat_response, observe_chat_response
from core.tools.tool_scoping import tool_scope


def test_quality_guard_measures_but_does_not_rewrite() -> None:
    wall = "Dette er en lang tanke. " * 35
    text = wall + "\n\nKonklusion: det samme igen?"
    signals = analyse_chat_response(text)
    assert {s["kind"] for s in signals} >= {
        "prose_wall", "mechanical_closure", "closing_question",
    }
    assert text == wall + "\n\nKonklusion: det samme igen?"


def test_quality_observer_is_chat_only(monkeypatch) -> None:
    observed: list[dict] = []

    class FakeCentral:
        def observe(self, payload):
            observed.append(payload)

    monkeypatch.setattr("core.services.central_core.central", lambda: FakeCentral())
    text = "En lang tanke. " * 50
    with tool_scope("code"):
        assert observe_chat_response(text, run_id="code") == []
    assert observed == []
    with tool_scope("chat"):
        assert observe_chat_response(text, run_id="chat")
    assert observed[0]["run_id"] == "chat"


def test_quality_guard_spots_surface_collisions_and_missing_prose() -> None:
    text = """| A | B |
|---|---|
| 1 | 2 |

```jarvis-ui
{"type":"comparison","title":"X","columns":["A","B"],"rows":[]}
```"""
    kinds = {s["kind"] for s in analyse_chat_response(text)}
    assert "competing_data_surfaces" in kinds
    assert "surface_without_standalone_text" in kinds


def test_kvalitetsvagten_ser_manglende_hierarki() -> None:
    """Målt 25/10-2026: 90 % af mine prosa-afsnit var på ≤3 sætninger, men kun
    5 % af svarene havde en overskrift og 5 % en liste. Mange korte afsnit uden
    ét eneste hierarkisk grep er ikke «roligt» — det er en mur af tekstøer.

    Signalet er diagnostik: det må pege på manglen uden at ændre teksten.
    """
    mur = "\n\n".join(f"Afsnit {i} med én enkelt pointe." for i in range(7))
    kinds = {s["kind"] for s in analyse_chat_response(mur)}
    assert "missing_hierarchy" in kinds

    # Et struktureret svar af samme længde må ikke rammes.
    struktureret = (
        "## Overskrift\n\nKort afsnit et.\n\nKort afsnit to.\n\n"
        "- punkt et\n- punkt to\n- punkt tre\n\nAfslutning her."
    )
    assert "missing_hierarchy" not in {s["kind"] for s in analyse_chat_response(struktureret)}

    # Et kort svar må ikke tvinges til at have hierarki.
    kort = "Ja, den er rettet.\n\nFejlen sad i guarden."
    assert "missing_hierarchy" not in {s["kind"] for s in analyse_chat_response(kort)}
