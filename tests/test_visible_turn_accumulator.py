"""Turblok-akkumulatoren — nu direkte testbar.

Udskilt fra `visible_runs.py` 2026-09-09. Før var den fem løse variabler og
fire lukninger inde i `_stream_visible_run`, og
`tests/test_turn_accumulator_wiring.py` måtte teste kontrakten indirekte:
«kan ikke importeres direkte uden at mocke hele streamet».

Det kan den nu. Testene her rammer selve objektet; wiring-testen bliver stående
som dækning af den rene blok-bygger den fodrer.
"""
from __future__ import annotations

from core.services.visible_turn_accumulator import TurnAccumulator, coerce_tool_input


class _FakeResultat:
    def __init__(self, tool_call_id: str, content: str) -> None:
        self.tool_call_id = tool_call_id
        self.content = content


# ── tekst-segmenter: hele grunden til at objektet findes ─────────────────

def test_tekst_i_traek_samles_i_ET_segment():
    a = TurnAccumulator()
    a.add_text("Jeg ")
    a.add_text("kigger.")
    assert a.text_segments == ["Jeg kigger."]


def test_et_vaerktoejskald_LUKKER_segmentet():
    """Uden lukningen smelter fortællingen før og efter et kald sammen til én,
    og turen kan ikke længere genfortælles som den blev til."""
    a = TurnAccumulator()
    a.add_text("Først kigger jeg.")
    a.close_segment()
    a.add_text("Så retter jeg.")
    assert a.text_segments == ["Først kigger jeg.", "Så retter jeg."]


def test_tom_tekst_aabner_ikke_et_segment():
    a = TurnAccumulator()
    a.add_text("")
    assert a.text_segments == []


# ── rækkefølge ───────────────────────────────────────────────────────────

def test_raekkefoelgen_registreres_som_den_kom():
    a = TurnAccumulator()
    a.note_text(); a.note_tool(); a.note_text()
    assert a.interleave == ["text", "tool", "text"]


# ── værktøjskald: to former, samme resultat ──────────────────────────────

def test_openai_formen_faar_sine_argumenter_PARSET():
    """`function.arguments` kommer som en JSON-STRENG. Uden parsing gemmer
    content_json en rå streng som klienten renderer garbled — og som er en
    dobbelt-sandhed mod resten, der er dicts."""
    a = TurnAccumulator()
    a.add_tools([{"id": "c1", "function": {"name": "bash", "arguments": '{"command": "ls"}'}}], [])
    assert a.tool_calls == [{"id": "c1", "name": "bash", "input": {"command": "ls"}}]


def test_den_flade_form_virker_ogsaa():
    a = TurnAccumulator()
    a.add_tools([{"id": "c2", "name": "read_file", "input": {"path": "x.py"}}], [])
    assert a.tool_calls[0]["name"] == "read_file"
    assert a.tool_calls[0]["input"] == {"path": "x.py"}


def test_manglende_navn_bliver_til_tool():
    a = TurnAccumulator()
    a.add_tools([{"id": "c3"}], [])
    assert a.tool_calls[0]["name"] == "tool"


def test_resultater_laeses_af_attributter():
    a = TurnAccumulator()
    a.add_tools([], [_FakeResultat("c1", "output")])
    assert a.tool_results == [
        {"tool_use_id": "c1", "status": "done", "content": "output", "is_error": False},
    ]


def test_en_fejl_i_opsamlingen_forplanter_sig_ALDRIG_til_streamet():
    """En kosmetisk detalje må ikke kunne afbryde et svar der ellers virkede."""
    class Sprængfarlig:
        @property
        def tool_call_id(self):  # pragma: no cover — kaldes via getattr
            raise RuntimeError("bum")
    a = TurnAccumulator()
    a.add_tools([], [Sprængfarlig()])          # må ikke kaste
    assert a.tool_results == []


# ── argument-normalisering ───────────────────────────────────────────────

def test_coerce_haandterer_dict_streng_og_vroevl():
    assert coerce_tool_input({"a": 1}) == {"a": 1}
    assert coerce_tool_input('{"a": 1}') == {"a": 1}
    assert coerce_tool_input("ikke json") == {}
    assert coerce_tool_input('"en streng"') == {}   # gyldig JSON, men ikke et objekt
    assert coerce_tool_input(None) == {}


# ── udtag ────────────────────────────────────────────────────────────────

def test_blokke_bygges_i_den_registrerede_raekkefoelge():
    a = TurnAccumulator()
    a.add_text("Jeg kigger i filen.")
    a.note_text()
    a.close_segment()
    a.add_tools([{"id": "c1", "name": "read_file", "input": {"path": "x.py"}}],
                [_FakeResultat("c1", "indhold")])
    a.note_tool()
    blokke = a.build_blocks("Færdig.")
    typer = [b.get("type") for b in blokke]
    assert "tool_use" in typer and "text" in typer
    assert typer.index("text") < typer.index("tool_use")


def test_en_tom_tur_giver_falsy_blokke():
    """Kaldstedet bruger `... or None`; en tom liste skal derfor være falsy og
    ikke en tom struktur der persisteres."""
    assert not TurnAccumulator().build_blocks("")
