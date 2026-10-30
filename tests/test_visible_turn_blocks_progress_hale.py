"""Den gemte besked skal SLUTTE i sit svar — ikke i 41 progress-blokke.

MÅLT 30/10-2026 (Bjørn): «dine 2 ture er kollideret og knækket den ende».
I `chat_messages` id 236638 (185 blokke) lå det endelige svar på index 143 og
derefter 41 `progress`-blokke på index 144-184. Klienten tegner dem som
efter-arbejde, så turen ser ud som om den fortsatte efter den var slut.

Årsagen er ikke `_mark_text_phases` — den gjorde sit arbejde korrekt og satte
`phase='final_answer'` på index 143. Årsagen er at `_build_turn_blocks` lagde
hele det flade spor BAGEST med `blocks.extend(...)`, efter svaret.

Sporet er en flad duplikat af tool-kaldene (de findes allerede i kernen som
`tool_use`/`tool_result`). Det skal stadig med — men det skal ligge FØR svaret,
så beskeden slutter i tekst. Det er samme regel som `_flyt_afslutning_til_sidst`
bruger på live-vejen.
"""

from __future__ import annotations

from core.services.visible_turn_blocks import _build_turn_blocks


def _tur(**kw):
    base = dict(
        text="Svaret til Bjørn.",
        tool_calls=[{"id": "t1", "name": "bash", "input": {"command": "ls"}}],
        tool_results=[
            {"tool_use_id": "t1", "status": "done", "content": "ok", "is_error": False}
        ],
    )
    base.update(kw)
    return _build_turn_blocks(**base)


def test_beskeden_slutter_i_svaret_ikke_i_progress() -> None:
    """Den sidste blok skal være teksten — ikke et progress-spor."""
    blokke = _tur()
    assert blokke, "turen gav ingen blokke"
    assert blokke[-1]["type"] == "text", (
        f"den gemte besked slutter i {blokke[-1]['type']!r} — "
        f"det er «knækket i enden»"
    )
    assert blokke[-1].get("phase") == "final_answer"


def test_progress_sporet_er_bevaret_men_ligger_foer_svaret() -> None:
    """Sporet må ikke droppes — det skal bare ligge foran svaret."""
    blokke = _tur()
    typer = [b["type"] for b in blokke]
    assert "progress" in typer, "progress-sporet forsvandt — det skal stadig med"

    sidste_progress = max(i for i, t in enumerate(typer) if t == "progress")
    sidste_tekst = max(i for i, t in enumerate(typer) if t == "text")
    assert sidste_progress < sidste_tekst, (
        "der ligger stadig progress-blokke efter svaret"
    )


def test_flere_vaerktoejskald_giver_samme_regel() -> None:
    """Mange kald er netop den form Bjørn så (41 sporblokke)."""
    calls = [{"id": f"t{i}", "name": "bash", "input": {}} for i in range(6)]
    results = [
        {"tool_use_id": f"t{i}", "status": "done", "content": "ok", "is_error": False}
        for i in range(6)
    ]
    blokke = _tur(tool_calls=calls, tool_results=results)
    assert blokke[-1]["type"] == "text"
    assert sum(1 for b in blokke if b["type"] == "progress") >= 6


def test_tur_uden_tekst_faar_ikke_opfundet_et_svar() -> None:
    """Uden tekst findes intet svar — sporet må ikke opfinde en slutblok."""
    blokke = _tur(text="")
    assert all(b["type"] != "text" for b in blokke), (
        "en ren værktøjs-tur fik en tekstblok den ikke havde"
    )
