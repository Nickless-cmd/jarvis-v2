# tests/test_notifikations_valg.py
from __future__ import annotations


def test_standard_er_tavs_undtagen_det_der_haster(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    assert v.kanal_for("bjorn", "approval") == "auto"
    assert v.kanal_for("bjorn", "question") == "auto"
    assert v.kanal_for("bjorn", "run_failed") == "auto"
    assert v.kanal_for("bjorn", "release") == "ingen"
    assert v.kanal_for("bjorn", "run_done") == "ingen"


def test_eget_valg_slaar_standarden(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    v.saet("bjorn", "release", "push")
    assert v.kanal_for("bjorn", "release") == "push"
    assert v.alle("bjorn")["release"] == "push"


def test_migreringen_baerer_de_fem_kolonner_over(isolated_runtime) -> None:
    """En halvvejs migreret base maa ikke tabe nogens valg."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder, briefing)"
            " VALUES (?,?,?,?)", ("bjorn", "auto", "mobile", "ingen"))
        conn.commit()

    assert v.migrer_kolonner() == 2
    assert v.kanal_for("bjorn", "reminder") == "mobile"
    assert v.kanal_for("bjorn", "briefing") == "ingen"


def test_migreringen_overskriver_ikke_et_nyere_valg(isolated_runtime) -> None:
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()
    v.saet("bjorn", "reminder", "ingen")
    v.migrer_kolonner()
    assert v.kanal_for("bjorn", "reminder") == "ingen"
