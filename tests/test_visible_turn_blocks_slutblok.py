"""Persistens-laget skal have samme slutblok-regel som live-visningen.

Målt 30/10-2026, 24 timer efter ``b967bef32`` (slutblok-fixet, live fra
16:16:29Z): 9 af 169 completed ture (5,3 %, baseline 2,8 %) bærer stadig
mønstret i ``chat_messages``.

Årsagen er at fixet ramte SSE-vejen og ikke persistens-vejen.
``_mark_text_phases`` stempler efter POSITION: en tekstblok bliver kun
``final_answer`` hvis den ligger EFTER det sidste ``tool_use``. Men når
værktøjskaldet kom efter svaret — eller når turen slet ikke har noget
``tool_use`` efter svaret — findes der ingen blok med ``final_answer``, og
klientens reload-fallback ekskluderer eksplicit ``commentary``
(``chatFlowModel.ts:186``). Svaret renderer derfor i arbejdsområdet.

SSE-fixets regel er: **turens SIDSTE tekstblok ER svaret.** Den regel skal
gælde begge steder, ellers ser live-visningen og den gemte besked forskellige
ud — og det er præcis dét Bjørn ser som «et tomrun».
"""

from __future__ import annotations

from core.services.visible_turn_blocks import _mark_text_phases


def _typer(blocks: list[dict]) -> list[str]:
    return [b["type"] for b in blocks]


def test_sidste_tekstblok_efter_sidste_tool_er_svaret() -> None:
    """Den form der ALLEREDE virker — må ikke ændre sig."""
    blocks = _mark_text_phases([
        {"type": "text", "text": "jeg kigger"},
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "ok"},
        {"type": "text", "text": "svaret"},
    ])
    tekster = [b for b in blocks if b["type"] == "text"]
    assert tekster[0]["phase"] == "commentary"
    assert tekster[1]["phase"] == "final_answer"


def test_svar_fulgt_af_et_vaerktoejskald_er_stadig_svaret() -> None:
    """Den defekt der blev målt: svaret kom FØR det sidste kald.

    Mønstret er ``text -> tool_use -> progress``. Teksten er turens eneste
    svar, men positions-reglen stempler den ``commentary`` fordi der ligger et
    ``tool_use`` efter den. Klienten lægger den derfor i folden.
    """
    blocks = _mark_text_phases([
        {"type": "text", "text": "Sådan ligger det."},
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "ok"},
        {"type": "progress", "tool_use_id": "t1", "tool": "bash", "status": "done"},
    ])
    tekster = [b for b in blocks if b["type"] == "text"]
    assert len(tekster) == 1
    assert tekster[0]["phase"] == "final_answer", (
        "turens eneste svar blev stempllet commentary fordi et kald fulgte efter"
    )


def test_tur_der_slutter_med_tool_use_har_en_slutblok() -> None:
    """Selv når turen ender på et værktøjskald skal der findes ét svar."""
    blocks = _mark_text_phases([
        {"type": "text", "text": "Første observation."},
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "ok"},
        {"type": "text", "text": "Det var konklusionen."},
        {"type": "tool_use", "id": "t2", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "t2", "status": "done", "content": "ok"},
    ])
    faser = [b["phase"] for b in blocks if b["type"] == "text"]
    assert faser[0] == "commentary"
    assert faser[1] == "final_answer", "den sidste tekstblok er den brugeren læser"


def test_kun_kommentarer_giver_ingen_slutblok_naar_der_ikke_er_tekst() -> None:
    """En tur der kun kørte værktøjer skal ikke opfinde et svar."""
    blocks = _mark_text_phases([
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "ok"},
        {"type": "progress", "tool_use_id": "t1", "tool": "bash", "status": "done"},
    ])
    assert not [b for b in blocks if b["type"] == "text"]


def test_der_er_praecis_en_slutblok() -> None:
    """Invarianten: aldrig to ``final_answer`` — klienten vælger den første."""
    blocks = _mark_text_phases([
        {"type": "text", "text": "a"},
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
        {"type": "text", "text": "b"},
        {"type": "tool_use", "id": "t2", "name": "bash", "input": {}},
        {"type": "text", "text": "c"},
    ])
    faser = [b["phase"] for b in blocks if b["type"] == "text"]
    assert faser.count("final_answer") == 1
    assert faser[-1] == "final_answer"


def test_uden_tools_er_al_tekst_svaret() -> None:
    """Uændret: en tur uden værktøjskald er hele teksten svaret."""
    blocks = _mark_text_phases([
        {"type": "text", "text": "et rent svar"},
    ])
    assert blocks[0]["phase"] == "final_answer"
