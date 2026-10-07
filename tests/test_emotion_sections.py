"""emotion_sections: udskilt fra prompt_contract, samme navne og samme adfaerd."""
from __future__ import annotations

import pytest

NAMES = ("_emotion_concept_tone_section", "_emotion_signal_section")


@pytest.mark.parametrize("name", NAMES)
def test_functions_are_reexported_from_prompt_contract(name):
    from core.services import prompt_contract
    from core.services.prompt_sections import emotion_sections

    assert getattr(prompt_contract, name) is getattr(emotion_sections, name)


@pytest.mark.parametrize("name", NAMES)
def test_sections_never_raise_and_return_text_or_none(isolated_runtime, name):
    from core.services.prompt_sections import emotion_sections

    out = getattr(emotion_sections, name)()
    assert out is None or isinstance(out, str)
