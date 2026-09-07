"""Failover må ikke tabe opgaven (Bjørn 7/9-2026).

`execute_with_role_or_fallback` har fire fallback-veje, og alle fire gav
puljen `message or ""`. Agentens værktøjs-løkke kalder med `messages=[...]` og
sender aldrig `message` — så hver failover sendte en TOM prompt. Modellen fik
intet at svare på og svarede «Hello! How can I assist you today?», som blev
gemt som agentens fund og afleveret af explore som research.

Kæden bagved: cerebras kørte på 0,0 % success (credits-exhausted, 814 kald på
syv døgn). Primæren kastede hver gang → failover → tom prompt.
"""
from core.services.non_visible_lane_execution import _prompt_fra_messages as f


def test_opgaven_overlever_naar_kun_messages_er_givet():
    assert f([{"role": "user", "content": "Hvor er explore defineret?"}]) \
        == "Hvor er explore defineret?"


def test_den_SIDSTE_brugerbesked_vinder():
    """Værktøjs-løkken tilføjer runder; opgaven er den seneste brugertur."""
    assert f([
        {"role": "user", "content": "første"},
        {"role": "assistant", "content": "tænker"},
        {"role": "user", "content": "anden"},
    ]) == "anden"


def test_assistent_og_tool_ture_bruges_ikke_som_opgave():
    assert f([{"role": "assistant", "content": "svar"},
              {"role": "tool", "content": "resultat"}]) == ""


def test_indholdslister_flades_ud():
    assert f([{"role": "user", "content": [
        {"type": "text", "text": "linje 1"}, {"type": "text", "text": "linje 2"},
    ]}]) == "linje 1\nlinje 2"


def test_tomt_input_giver_tom_streng_ikke_en_fejl():
    for v in (None, [], [{}], [{"role": "user"}], [{"role": "user", "content": "   "}]):
        assert f(v) == ""


def test_uegnede_elementer_springes_over_uden_at_kaste():
    assert f(["ikke en dict", {"role": "user", "content": "det rigtige"}]) == "det rigtige"
