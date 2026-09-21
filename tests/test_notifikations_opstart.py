from __future__ import annotations

import inspect


def test_opstartsarbejdet_goer_begge_dele(isolated_runtime, monkeypatch) -> None:
    """KALDER opstartsfunktionen rigtigt. En kilde-vagt der greber efter navnet
    ville vaere groen ogsaa hvis kaldet stod i en gren der aldrig naas — og
    praecis dét hul lod `migrer_kolonner()` ligge ukaldt gennem en hel
    gennemgang (fundet 21/9-2026)."""
    from core.runtime.db import connect
    from core.services import notifikations_opstart, notifikations_valg

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()

    notifikations_opstart.koer_ved_opstart()

    assert notifikations_valg.kanal_for("bjorn", "reminder") == "mobile"


def test_opstartsarbejdet_vaelter_aldrig_opstarten(isolated_runtime, monkeypatch) -> None:
    """En feed der ikke kan rydde op er stadig bedre end en API der ikke starter."""
    from core.services import notifikations_opstart, notifikations_valg

    def sprang() -> int:
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(notifikations_valg, "migrer_kolonner", sprang)

    notifikations_opstart.koer_ved_opstart()   # maa ikke kaste


def test_app_kalder_opstartsarbejdet() -> None:
    """Vagt over selve ledningen. Funktionens ADFAERD er daekket ovenfor; det
    her er det ene der ikke kan koeres i en test uden at starte hele API'ets
    lifespan med alle dens daemoner."""
    import apps.api.jarvis_api.app as m
    assert "koer_ved_opstart" in inspect.getsource(m)


def test_migreringen_er_idempotent(isolated_runtime) -> None:
    """Den koerer ved HVER opstart — anden gang maa den ikke goere noget."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()

    assert v.migrer_kolonner() == 1
    assert v.migrer_kolonner() == 0
