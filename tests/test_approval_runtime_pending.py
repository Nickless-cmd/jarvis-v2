
# ── Kortet hører til en EJER, ikke til det vindue der er åbent (20/9-2026) ───
def test_pending_for_owner_finder_kort_paa_tvaers_af_samtaler(monkeypatch):
    """Session-udgaven lukkede kun det halve hul.

    Bjørn 20/9-2026: «der ligger en jeg ikke kan få lov at se som skal
    godkendes, den holder hans run». Målt i det øjeblik: fire kort ventede,
    alle i en samtale desk ikke selv streamede.
    """
    import core.services.approval_runtime as ar
    import core.services.visible_runs as vr

    # Kortene bor paa disken (24/9-2026); skriv dem hvor koden laeser dem.
    for _aid, _kort in {
        "a1": {"tool_name": "bash", "session_id": "s1", "owner_user_id": "bjorn",
               "created_at": "2026-09-20T18:39:54Z"},
        "a2": {"tool_name": "bash", "session_id": "s2", "owner_user_id": "bjorn",
               "created_at": "2026-09-20T18:41:23Z"},
        "a3": {"tool_name": "bash", "session_id": "s3", "owner_user_id": "en-anden",
               "created_at": "2026-09-20T18:42:00Z"},
    }.items():
        vr.saet_godkendelse(_aid, _kort)
    kort = ar.pending_for_owner("bjorn")
    assert kort["approval_id"] == "a2"        # nyeste først
    assert kort["session_id"] == "s2"         # og den siger HVOR det kom fra


def test_pending_for_owner_ser_ikke_en_andens_kort(monkeypatch):
    import core.services.approval_runtime as ar
    import core.services.visible_runs as vr

    vr.saet_godkendelse("a3", {"tool_name": "bash", "session_id": "s3",
                               "owner_user_id": "en-anden",
                               "created_at": "2026-09-20T18:42:00Z"})
    assert ar.pending_for_owner("bjorn") is None
    assert ar.pending_for_owner("") is None


def test_pending_for_owner_er_tom_naar_intet_venter(monkeypatch):
    import core.services.approval_runtime as ar
    import core.services.visible_runs as vr

    assert ar.pending_for_owner("bjorn") is None
