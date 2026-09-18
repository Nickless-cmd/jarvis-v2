"""Kartografen skal kunne lukke sine egne opgaver igen.

## Hvad der var galt (målt 18/9-2026)

Ti reparations-opgaver stod `blocked`, den ældste fra 8. maj — fire en halv
måned. Seks af dem pegede på filer som scanningen ikke flager længere. System
Cartographer kunne rejse en opgave, men aldrig lukke den; præcis samme hul som
Agency Cartographer havde samme dag.

En kø hvor over halvdelen er løst, er en kø man holder op med at kigge i — og
så forsvinder de fire ægte sammen med resten.

## Hvad lukningen PÅSTÅR

Ikke at filen er repareret. Kun at scanningen ikke flager den længere;
kriterierne kan også have ændret sig. Den forskel står i `result_summary`.
"""
from __future__ import annotations

import core.services.system_cartographer as sc


def _opsaet(monkeypatch, opgaver: list[dict]) -> list[dict]:
    from core.services import runtime_tasks

    opdateringer: list[dict] = []
    monkeypatch.setattr(runtime_tasks, "list_tasks",
                        lambda status, kind, limit=50: [
                            o for o in opgaver
                            if o["status"] == status and o["kind"] == kind])
    monkeypatch.setattr(runtime_tasks, "update_task",
                        lambda tid, **kw: opdateringer.append({"id": tid, **kw}))
    return opdateringer


def test_en_opgave_hvis_fil_ikke_laengere_flages_lukkes(monkeypatch):
    opdateringer = _opsaet(monkeypatch, [
        {"task_id": "t-gammel", "status": "blocked", "kind": "observability_bridge_repair",
         "scope": "core/services/narrative_summary_daemon.py"},
    ])
    ud = sc._luk_opgaver_scanningen_ikke_flager({
        "darkEdges": [{"path": "core/services/identity_sketch.py", "service": "identity_sketch"}],
        "theaterAudit": {"findings": [{"file": "core/services/inner_voice_shadow.py"}]},
    })
    assert ud == ["t-gammel"]
    assert opdateringer[0]["status"] == "succeeded"
    # Lukningen paastaar ikke at filen er repareret.
    assert "ikke laengere" in opdateringer[0]["result_summary"]
    assert "repareret" in opdateringer[0]["result_summary"]


def test_en_opgave_der_STADIG_flages_roeres_ikke(monkeypatch):
    opdateringer = _opsaet(monkeypatch, [
        {"task_id": "t-aegte", "status": "blocked", "kind": "observability_bridge_repair",
         "scope": "core/services/identity_sketch.py"},
    ])
    ud = sc._luk_opgaver_scanningen_ikke_flager({
        "darkEdges": [{"path": "core/services/identity_sketch.py", "service": "identity_sketch"}],
        "theaterAudit": {"findings": []},
    })
    assert ud == [] and opdateringer == []


def test_en_TOM_scanning_lukker_intet(monkeypatch):
    """En scanning der ikke naaede at koere, maa ikke lukke noget. Ellers
    ville tavshed blive kaldt et svar — og hele koeen ville forsvinde paa én
    daarlig koersel."""
    opdateringer = _opsaet(monkeypatch, [
        {"task_id": "t", "status": "blocked", "kind": "observability_bridge_repair",
         "scope": "core/services/hvadsomhelst.py"},
    ])
    ud = sc._luk_opgaver_scanningen_ikke_flager({"darkEdges": [], "theaterAudit": {"findings": []}})
    assert ud == [] and opdateringer == []


def test_en_ren_laesning_af_fladen_aendrer_INTET():
    """`auto_enqueue=False` er en laesning. Den maa hverken rejse eller lukke."""
    flade = sc.build_system_cartographer_surface()
    assert flade.get("resolvedTasks") == []
