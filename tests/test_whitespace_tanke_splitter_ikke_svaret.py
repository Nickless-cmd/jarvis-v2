"""Ren whitespace som reasoning-delta må ikke rive svaret i to tekstblokke.

MÅLT 28/10-2026. Bjørn viste et skærmbillede hvor en besked stod som

    (In
    gen nye fund — releasen var allerede verificeret …

Altså ordet «Ingen» revet over. Det var ikke markdown: `content_json` havde
to tekstblokke, `"(In"` (3 tegn) og `"gen nye fund …"` (88) — tilsammen præcis
de 91 tegn `content` indeholdt. Ingen data tabt, men opdelt.

Rod-årsag: DeepSeek sender «\\n\\n» som reasoning-delta. `add_thinking` åbnede
et TOMT tanke-segment, hvilket satte `_segment_open = False` og dermed lukkede
tekst-segmentet midt i sætningen. `_build_turn_blocks` filtrerer den tomme
tanke væk (ingen blok), men 'think'-mærket i interleave bliver tilbage og
adskiller de to tekstblokke.

Målt over 4.000 gemte beskeder: 162 ramt — 107 i auto-sessioner, 55 i
almindelige. Det blev SET i wakeup- og autonome runs fordi de vises som
genindlæst `content_json`; en almindelig tur streames live og samles i
klientens egen akkumulator.

Testene er adfærdstests på blok-udtaget — ikke grep i kilden. Den første
test er modprøven: en ÆGTE tanke midt i teksten SKAL stadig give to blokke,
ellers ville et bart «return» i `add_thinking` bestå alt andet her.
"""

from __future__ import annotations

import pytest

from core.services.visible_turn_accumulator import TurnAccumulator


def _text_blokke(ta: TurnAccumulator) -> list[str]:
    blokke = ta.build_blocks(text="".join(ta.text_segments))
    return [b["text"] for b in blokke if b.get("type") == "text"]


def _typer(ta: TurnAccumulator) -> list[str]:
    return [b.get("type") for b in ta.build_blocks(text="".join(ta.text_segments))]


def test_whitespace_tanke_splitter_ikke_svaret() -> None:
    """«\\n\\n» som reasoning-delta må ikke dele en sætning i to blokke."""
    ta = TurnAccumulator()
    ta.note_text()
    ta.add_text("(In")
    ta.add_thinking("\n\n")          # ren luft — ikke en tanke
    ta.note_text()
    ta.add_text("gen nye fund — alt er verificeret.)")

    assert _text_blokke(ta) == ["(Ingen nye fund — alt er verificeret.)"]


def test_whitespace_tanke_efterlader_ingen_tom_tankeblok() -> None:
    """Den tomme tanke må heller ikke stå tilbage som en blok uden indhold."""
    ta = TurnAccumulator()
    ta.note_text()
    ta.add_text("J")
    ta.add_thinking("   ")
    ta.note_text()
    ta.add_text("eg tjekker CI-status.")

    assert _typer(ta) == ["text"]
    assert _text_blokke(ta) == ["Jeg tjekker CI-status."]


def test_rigtig_tanke_midt_i_teksten_giver_stadig_to_blokke() -> None:
    """MODPRØVE: en ægte tanke SKAL stadig skabe to tekstblokke.

    Uden denne test ville et bart `return ""` i `add_thinking` bestå alle de
    andre — og så ville tænkning midt i en tur forsvinde som synlig struktur.
    """
    ta = TurnAccumulator()
    ta.note_text()
    ta.add_text("Første del. ")
    ta.add_thinking("jeg skal lige tjekke loggen")
    ta.note_text()
    ta.add_text("Anden del.")

    assert _typer(ta) == ["text", "thinking", "text"]
    assert _text_blokke(ta) == ["Første del.", "Anden del."]


def test_whitespace_inde_i_en_aaaben_tanke_bevares() -> None:
    """Luft midt i en tanke er indhold og må ikke kastes væk."""
    ta = TurnAccumulator()
    ta.add_thinking("første linje")
    ta.add_thinking("\n\n")
    ta.add_thinking("anden linje")

    blokke = ta.build_blocks(text="")
    tanker = [b["text"] for b in blokke if b.get("type") == "thinking"]
    assert tanker == ["første linje\n\nanden linje"]


def test_whitespace_foer_tekst_giver_ingen_tom_tankeblok() -> None:
    """En strøm der ÅBNER med luft skal give én tekstblok, ikke to."""
    ta = TurnAccumulator()
    ta.add_thinking("\n")
    ta.note_text()
    ta.add_text("Svaret begynder her.")

    assert _typer(ta) == ["text"]
    assert _text_blokke(ta) == ["Svaret begynder her."]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
