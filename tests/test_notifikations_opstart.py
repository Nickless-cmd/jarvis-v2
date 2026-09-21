from __future__ import annotations

import inspect


def test_opstartsarbejdet_goer_begge_dele(isolated_runtime, monkeypatch) -> None:
    """KALDER opstartsfunktionen rigtigt og bekraefter EFFEKTEN af begge
    handlinger — ikke bare at de er kaldt. En kilde-vagt der greber efter
    navnet ville vaere groen ogsaa hvis kaldet stod i en gren der aldrig
    naas — og praecis dét hul lod `migrer_kolonner()` ligge ukaldt gennem
    en hel gennemgang (fundet 21/9-2026). Samme hul stod aabent for
    `ryd_gamle()`: en gennemgang fjernede kaldet og alle fire tests i denne
    fil forblev groenne (bevist ved mutation 21/9-2026)."""
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import connect
    from core.services import notifikations_opstart, notifikations_valg, notifikationer

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()

    aaben = notifikationer.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Aaben")
    gammel = notifikationer.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Gammel")
    notifikationer.luk(gammel, "seen")
    for_laenge_siden = (datetime.now(UTC) - timedelta(days=9)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET klaret=? WHERE id=?", (for_laenge_siden, gammel))
        conn.commit()

    notifikations_opstart.koer_ved_opstart()

    # migreringen: det gamle kolonne-valg kan laeses fra den nye tabel
    assert notifikations_valg.kanal_for("bjorn", "reminder") == "mobile"

    # oprydningen: den klarede, gamle raekke er vaek — den aabne staar
    with connect() as conn:
        tilbage = [r[0] for r in conn.execute("SELECT id FROM notifikationer").fetchall()]
    assert tilbage == [aaben]


def test_opstartsarbejdet_vaelter_aldrig_ved_migreringsfejl(isolated_runtime, monkeypatch) -> None:
    """En feed der ikke kan migrere er stadig bedre end en API der ikke starter."""
    from core.services import notifikations_opstart, notifikations_valg

    def sprang() -> int:
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(notifikations_valg, "migrer_kolonner", sprang)

    notifikations_opstart.koer_ved_opstart()   # maa ikke kaste


def test_opstartsarbejdet_vaelter_aldrig_ved_oprydningsfejl(isolated_runtime, monkeypatch) -> None:
    """Samme garanti den anden vej: en fejlende `ryd_gamle` maa heller ikke
    vaelte opstarten."""
    from core.services import notifikations_opstart, notifikationer

    def sprang() -> int:
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(notifikationer, "ryd_gamle", sprang)

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
