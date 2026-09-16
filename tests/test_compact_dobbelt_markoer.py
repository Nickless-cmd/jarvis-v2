"""Dobbelt-komprimering (16/9-2026).

Hver komprimering skrev TO markoerer 10-17 s fra hinanden: foerst en
«self-heal» der skrev den gamle markoer om, saa selve komprimeringen. I
hullet saa en prompt-bygning kun et resume paa 300 ord og intet efter det.
Se core/context/session_compact.py.
"""
import core.context.compact_ground_truth as gt
import core.context.session_compact as sc


def _tomme_sider(monkeypatch, gemte):
    monkeypatch.setattr(sc, "_get_all_session_messages", lambda sid: [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"besked {i} " * 20}
        for i in range(40)
    ])
    monkeypatch.setattr(sc, "_store_marker", lambda sid, txt, git_sha="": gemte.append(txt) or f"compact-{len(gemte)}")
    monkeypatch.setattr("core.services.identity_sketch.update_identity_sketch", lambda **k: None)
    monkeypatch.setattr(gt, "validate_compact_marker", lambda *a, **k: {"verified_false": 0})


def test_komprimering_skriver_kun_een_markoer_og_heler_ikke_foerst(monkeypatch):
    gemte: list[str] = []
    _tomme_sider(monkeypatch, gemte)
    monkeypatch.setattr(gt, "resolve_stale_markers_on_load",
                        lambda sid: (_ for _ in ()).throw(AssertionError("self-heal foer komprimering")))
    monkeypatch.setattr(gt, "auto_regenerate_compact_marker",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("omskrivning under komprimering")))
    afloest = []
    monkeypatch.setattr(gt, "mark_failures_superseded", lambda sid, new_marker_id: afloest.append(new_marker_id) or 1)
    r = sc.compact_session_history("s1", keep_recent=4, summarise_fn=lambda msgs: "resume")
    assert r is not None
    assert len(gemte) == 1
    assert afloest == ["compact-1"], "gamle fejl skal lukkes som afloest af den nye markoer"


def test_omskrivning_springer_over_naar_der_er_beskeder_efter_markoeren(monkeypatch):
    monkeypatch.setattr("core.services.chat_sessions.chat_session_messages_since_last_compact",
                        lambda sid, max_total=4000: [{"id": 9, "role": "user", "content": "ny"}])
    # Alt andet staar klar til en omskrivning — KUN vagten maa stoppe den.
    monkeypatch.setattr("core.services.chat_sessions.get_compact_marker_with_sha", lambda sid: ("gammelt", "abc"))
    monkeypatch.setattr(gt, "collect_compact_ground_truth", lambda sid: {})
    monkeypatch.setattr(gt, "format_ground_truth_block", lambda g: "")
    monkeypatch.setattr(gt, "validate_compact_marker", lambda *a, **k: {"passed": False, "verified_false": 2})
    monkeypatch.setattr("core.services.chat_sessions.store_compact_marker",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("ny markoer oven paa beskeder")))
    monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM-kald spildt")))
    assert gt.auto_regenerate_compact_marker("s1") is None


def test_omskrivning_bevarer_den_ordrette_hale(monkeypatch):
    hale = "[user] den seneste besked ordret"
    gammel = "gammelt resume" + gt._HALE_OVERSKRIFT + hale
    monkeypatch.setattr("core.services.chat_sessions.chat_session_messages_since_last_compact",
                        lambda sid, max_total=4000: [])
    monkeypatch.setattr("core.services.chat_sessions.get_compact_marker_with_sha", lambda sid: (gammel, "abc"))
    monkeypatch.setattr(gt, "collect_compact_ground_truth", lambda sid: {})
    monkeypatch.setattr(gt, "format_ground_truth_block", lambda g: "")
    monkeypatch.setattr(gt, "validate_compact_marker", lambda *a, **k: {"passed": False, "verified_false": 2})
    monkeypatch.setattr(gt, "get_current_git_sha", lambda: "def")
    monkeypatch.setattr("core.context.compact_llm.call_compact_llm", lambda *a, **k: "rettet resume")
    gemt = []
    monkeypatch.setattr("core.services.chat_sessions.store_compact_marker",
                        lambda sid, txt, git_sha="": gemt.append(txt) or "compact-ny")
    assert gt.auto_regenerate_compact_marker("s1") == "compact-ny"
    assert gemt[0].startswith("rettet resume")
    assert gemt[0].endswith(hale)


# ── Valideringens commit-tjek (16/9-2026) ────────────────────────────────
_COMMITS = "5e93f4ba3 feat(desk): saved rail viser kapitler — alle ingen virke brugerens\nabc fix: skill_flade_event i visible_runs.py"


def _tjek(ctx):
    return gt._check_claim_against_ground_truth(
        {"pattern": "mangler", "context": ctx, "claim_type": "x"},
        {"key_files": {}, "recent_commits": _COMMITS},
    )


def test_almindelige_ord_doemmer_ikke_et_resume_falsk():
    # Produktionens aegte eksempler: alle 104 «fejl» saa saadan ud.
    for ctx in (
        "et i denne samtale, hæftningen bevist virke  Det eneste der mangler er dit blik",
        "De noter er alle overflade-resuméer — jeg mangler selve fundet",
        "r placeret i brugerens boble, manglende download- og zoom-funktionalit",
        "Det jeg mangler: ingen LLM involveret",
    ):
        assert _tjek(ctx)["verified_false"] is False, ctx


def test_identifikator_som_commits_roerer_doemmes_stadig():
    r = _tjek("resumeet siger at `skill_flade_event` mangler")
    assert r["verified_false"] is True
    assert r["confidence"] == "medium"
    assert _tjek("visible_runs.py mangler koblingen")["verified_false"] is True


def test_identifikator_skal_matche_helt_ord():
    # «skill_flade» er ikke «skill_flade_event».
    assert _tjek("skill_flade mangler")["verified_false"] is False


def test_versionsnumre_er_ikke_identifikatorer():
    assert gt._identifikatorer("desk 0.3.94 og 15.09") == []
