"""Initiativ-sektionen skal ikke ligge i awareness-laget, men tail-anchored.

MAALT 23/11-2026 — og den foerste begrundelse for denne test var FORKERT, hvilket
er vaerd at skrive ned, fordi fejlen er laererig:

Jeg antog at `_awareness_add` betoed «i det cachede praefiks», og at sektionen
derfor kostede cachen hver gang koen aendrede sig. Det holder ikke:
awareness-laget flushes ind i `_dyn_tail` (`_dyn_tail.extend(_awareness_buffer)`),
altsaa EFTER `DYNAMIC_TAIL_SENTINEL` — samme hale som `_tail_add` skriver til.

Maalt i en bygget prompt, med en pending post:

    _awareness_add (HEAD)   sektion paa tegn 11.479, sentinel paa 7.166
    _tail_add      (ny)     sektion paa tegn 12.078, sentinel paa 7.166

Altsaa: begge i halen. En test der sammenligner praefiks-hashes kan derfor ikke
se forskellen — den passerer paa baade gammel og ny kode, og den blev derfor
fjernet igen. Det er praecis den «groenne vagt der ikke kan se det den vaerner
om»-klasse der har kostet mest i dette repo.

Den REELLE forskel er budgettet: awareness-laget har et loft paa
`_AWARENESS_BUDGET` (6.000 tegn), og alt undtagen pinnet identitet kan evictes.
`_tail_add` har ingen budget-konkurrence. En post han selv har rejst maa ikke
tabe en pladskamp til en diagnostik-linje.

Vagten her maaler derfor den observerbare forskel: hvilken vej sektionen gik.
`_tail_add` markerer i `derived_inputs` med «(tail-anchored)», `_awareness_add`
goer ikke. Den markoer er testens bevis — og den fejlede korrekt paa HEAD.
"""
from __future__ import annotations

from core.services.prompt_contract import build_visible_chat_prompt_assembly


def _derived() -> list[str]:
    assembly = build_visible_chat_prompt_assembly(
        provider="deepseek",
        model="deepseek-chat",
        user_message="hvordan staar det til",
        session_id=None,
    )
    return list(assembly.derived_inputs or [])


def test_initiativ_sektionen_er_tail_anchored(isolated_runtime) -> None:
    """Sektionen skal gaa gennem `_tail_add`, ikke awareness-laget.

    `_tail_add` tilfoejer «{label} (tail-anchored)» til derived_inputs;
    `_awareness_add` tilfoejer labelen raat. Forskellen er observerbar, og den
    er den eneste observerbare forskel — se modulets docstring.
    """
    from core.services import initiative_queue

    iid = initiative_queue.push_initiative(
        focus="Verifikations-post: skal gaa gennem _tail_add",
        source="jarvis-tool",
        priority="high",
    )
    assert iid, "posten blev ikke oprettet — testen ville maale en tom koe"

    derived = _derived()

    assert "own initiatives (tail-anchored)" in derived, (
        "initiativ-sektionen gik ikke gennem _tail_add — den ligger stadig i "
        f"awareness-laget og kan evictes af dets budget. derived_inputs={derived}"
    )
    assert "own initiatives" not in derived, (
        "sektionen optraeder UDEN tail-markoer — den er stadig i awareness-laget"
    )


def test_tom_koe_bygger_ingen_sektion(isolated_runtime) -> None:
    """Uden pending poster skal sektionen slet ikke optraede."""
    from core.services import initiative_queue

    assert initiative_queue.get_pending_initiatives() == []

    derived = _derived()

    assert "own initiatives" not in " ".join(derived), (
        "sektionen blev bygget paa en tom koe — den skal returnere None"
    )
