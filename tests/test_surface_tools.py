"""`vaelg_flade` som værktøj: svaret skal være handlingsbart og aldrig vælte turen."""

from core.tools.surface_tools import SURFACE_TOOL_DEFINITIONS, _exec_vaelg_flade


def test_tool_is_registered_with_its_own_schema():
    names = [d["function"]["name"] for d in SURFACE_TOOL_DEFINITIONS]
    assert names == ["vaelg_flade"]
    params = SURFACE_TOOL_DEFINITIONS[0]["function"]["parameters"]
    assert params["required"] == ["opgave"]
    assert "none" in params["properties"]["opgave"]["enum"]


def test_executor_returns_the_tool_choice_for_numbers():
    out = _exec_vaelg_flade({"opgave": "numbers"})
    assert out["status"] == "ok"
    assert out["vaerktoej"] == "vis_graf"
    assert out["flade"] is None
    assert "Nævn ikke dette kald" in out["text"]


def test_executor_returns_native_surface_for_comparison():
    out = _exec_vaelg_flade({"opgave": "compare", "antal": 3, "delte_akser": 2})
    assert out["status"] == "ok"
    assert out["flade"] == "comparison"
    assert "jarvis-ui" in out["text"]


def test_executor_says_prose_when_thresholds_fail():
    out = _exec_vaelg_flade({"opgave": "compare", "antal": 2, "delte_akser": 1})
    assert out["status"] == "ok"
    assert out["valg"] == "prosa"
    assert "to fælles akser" in out["text"]


def test_executor_survives_garbage_input():
    """En gal payload må give prosa, ikke en undtagelse."""
    out = _exec_vaelg_flade({"opgave": None, "antal": "ikke-et-tal", "delte_akser": -5})
    assert out["status"] == "ok"
    assert out["valg"] == "prosa"


def test_executor_handles_missing_args_entirely():
    out = _exec_vaelg_flade({})
    assert out["status"] == "ok"
    assert out["valg"] == "prosa"
