from core.tools.pause_and_ask_tools import _exec_pause_and_ask


def test_pause_and_ask_marks_when_several_options_may_be_combined():
    result = _exec_pause_and_ask({
        "question": "Hvilke flader?",
        "options": ["Desk", "Mobil"],
        "allow_multiple": True,
    })

    assert result["allow_multiple"] is True


def test_pause_and_ask_defaults_to_one_choice():
    result = _exec_pause_and_ask({"question": "Hvad nu?"})

    assert result["allow_multiple"] is False
