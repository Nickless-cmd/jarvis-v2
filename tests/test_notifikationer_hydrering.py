# tests/test_notifikationer_hydrering.py
from __future__ import annotations


def test_godkendelse_afgjort_et_andet_sted_lukker_sig_selv(isolated_runtime, monkeypatch) -> None:
    """Godkender man paa telefonen, skal desk-feeden helbrede sig selv."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1",
            titel="Vil du tillade bash?")
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "approved"})

    assert h.feed("bjorn", er_owner=True) == []
    assert n.aabne("bjorn", er_owner=True) == []


def test_ventende_godkendelse_bliver_staaende_og_kan_afgoeres(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gammel titel")
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash_session"})

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["kan_afgoere"] is True
    # Ejeren er sandheden: titlen kommer fra ham, ikke fra den gemte kopi.
    assert "bash_session" in poster[0]["titel"]


def test_hydrering_der_fejler_lukker_IKKE_raekken(isolated_runtime, monkeypatch) -> None:
    """En utilgaengelig ejer maa ikke se ud som en klaret opgave."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gemt titel")

    def sprang(_aid):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(approval_runtime, "state", sprang)

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["titel"] == "Gemt titel"
    assert poster[0]["foraeldet"] is True
    assert poster[0]["kan_afgoere"] is False
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_egen_raekke_er_sin_egen_sandhed(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="bjorn", slags="reminder", kilde="egen",
            titel="Husk mælk", tekst="Du bad mig minde dig om det i morges.")
    poster = h.feed("bjorn", er_owner=True)
    assert poster[0]["titel"] == "Husk mælk"
    assert poster[0]["kan_afgoere"] is False


def test_anden_brugers_raekke_naar_aldrig_owners_feed(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="mikkel", slags="reminder", kilde="egen", titel="Mikkels ting")
    assert h.feed("bjorn", er_owner=True) == []
    assert len(h.feed("mikkel", er_owner=False)) == 1
