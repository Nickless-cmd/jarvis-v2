"""Et genereret billede skal stå dér hvor det blev lavet.

## Målingen

Bjørn 13/9-2026: «hans billeder kommer først efter streamen er slut i stedet
for inde i streamen hvor de faktisk bliver lavet».

Målt på en ægte besked: **50 blokke**, hvor begge billeder lå på plads 49 og
50 — efter fyrre `progress`-blokke. Begge iagttagelser kom af ét udtryk i
`_with_published_files`:

    return list(blocks) + as_blocks(poster)

## Ankeret fandtes i forvejen

`progress`-blokken for værktøjet bærer et `tool_use_id`:

    progress 39: {"type":"progress","tool_use_id":"call_00_WO06n96h…",
                  "message":"openrouter_image","status":"done"}

Kæden manglede kun ét led: executoren stemplede `_runtime_session_id`,
`_runtime_turn_id` og `_runtime_user_id`, men ikke kald-id'et.
"""
from __future__ import annotations

import core.services.visible_runs as _vr  # noqa: F401  (bryder cirkel-importen)
from core.services.visible_runs_outcomes import _indsaet_ved_deres_vaerktoej as indsæt


def _prog(tid: str, navn: str = "") -> dict:
    return {"type": "progress", "tool_use_id": tid, "message": navn, "status": "done"}


def _bil(navn: str, tid: str = "") -> dict:
    b = {"type": "image", "filename": navn}
    if tid:
        b["tool_use_id"] = tid
    return b


def test_billedet_staar_LIGE_EFTER_sit_vaerktoej():
    ud = indsæt([{"type": "text"}, _prog("c1", "openrouter_image"), {"type": "text"}],
                [_bil("a.png", "c1")])
    typer = [b["type"] for b in ud]
    assert typer == ["text", "progress", "image", "text"], typer


def test_flere_billeder_hver_ved_sit_vaerktoej():
    """To vaerktoejskald, to billeder — de maa ikke bytte plads."""
    ud = indsæt([_prog("c1", "openrouter_image"), {"type": "text"},
                 _prog("c2", "openrouter_image_edit")],
                [_bil("redigeret.png", "c2"), _bil("original.png", "c1")])
    navne = [b.get("filename") for b in ud if b["type"] == "image"]
    assert navne == ["original.png", "redigeret.png"], navne


def test_to_billeder_fra_SAMME_kald_bliver_sammen():
    ud = indsæt([_prog("c1"), {"type": "text"}],
                [_bil("en.png", "c1"), _bil("to.png", "c1")])
    assert [b["type"] for b in ud] == ["progress", "image", "image", "text"]


def test_et_billede_UDEN_anker_havner_bagerst():
    """Et gaet paa en placering ville vaere vaerre end bagerst: et billede ved
    den forkerte tekst laeses som hoerende til den."""
    ud = indsæt([{"type": "text"}, _prog("c1")], [_bil("hjemloes.png")])
    assert ud[-1]["filename"] == "hjemloes.png"


def test_et_billede_hvis_vaerktoej_MANGLER_forsvinder_ikke():
    """En manglende `progress`-blok maa ikke aede billedet."""
    ud = indsæt([{"type": "text"}], [_bil("a.png", "findes-ikke")])
    assert any(b.get("filename") == "a.png" for b in ud), "billedet forsvandt"


def test_ingen_filer_lader_blokkene_UROERT():
    b = [{"type": "text"}, _prog("c1")]
    assert indsæt(b, []) == b


def test_alle_blokke_overlever():
    """En omrokering der taber en blok er ikke en omrokering."""
    b = [{"type": "text"}, _prog("c1"), {"type": "thinking"}, _prog("c2")]
    ud = indsæt(b, [_bil("a.png", "c1"), _bil("b.png")])
    assert len(ud) == len(b) + 2
    for x in b:
        assert x in ud


# ------------------------------------------------- kaeden skal vaere hel

def test_executoren_stempler_kald_idet():
    """Uden det led kan en fil kun haenges bagpaa turen."""
    import pathlib
    kilde = pathlib.Path("core/services/simple_tool_executor.py").read_text()
    assert '_runtime_tool_use_id' in kilde, "executoren stempler ikke kald-id'et"


def test_billedvaerktoejet_SENDER_det_videre():
    import pathlib
    kilde = pathlib.Path("core/tools/openrouter_image_tools.py").read_text()
    assert 'tool_use_id=str(args.get("_runtime_tool_use_id")' in kilde


def test_den_udgivne_fil_BAERER_ankeret():
    from core.services.published_files import as_blocks
    ud = as_blocks([{"filename": "a.png", "mime_type": "image/png",
                     "attachment_id": "x", "tool_use_id": "c1"}])
    assert ud and ud[0].get("tool_use_id") == "c1"


def test_en_fil_uden_anker_faar_ikke_et_tomt_felt():
    """Et tomt `tool_use_id` ville matche en blok med tomt id — og et billede
    ved det forkerte vaerktoej er vaerre end et bagerst."""
    from core.services.published_files import as_blocks
    ud = as_blocks([{"filename": "a.png", "mime_type": "image/png",
                     "attachment_id": "x", "tool_use_id": ""}])
    assert "tool_use_id" not in ud[0]


def test_KALDEREN_bruger_den_nye_placering():
    """Uden denne vagt var mutationen «tilbage til `blocks + filer`» groen:
    testene ovenfor kalder hjaelperen DIREKTE og roerer aldrig kalderen.

    Samme hul som `user_id` og `work_ref` tidligere i dag — funktionen kan
    findes uden nogensinde at blive brugt.
    """
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path(
        "core/services/visible_runs_outcomes.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "_med_udgivne_filer"), None)
    assert fn is not None, "_med_udgivne_filer er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_indsaet_ved_deres_vaerktoej" in kaldt, \
        "filerne haenges stadig bagpaa hele turen"
