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
    """En utilgaengelig ejer maa ikke se ud som en klaret opgave.

    Denne udgave monkeypatcher `approval_runtime.state` DIREKTE til at kaste.
    Det sker aldrig i produktion siden `state()` selv fangede internt (roden
    til den fejl denne test skulle finde, men ikke gjorde). Den staar her som
    en grov konsistens-check paa hydreringens EGEN `except`-net, uafhaengigt
    af hvad der ligger under `state()`. `test_db_utilgaengelig_...` nedenfor
    er den der maaler den AEGTE soem.
    """
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


def test_db_utilgaengelig_ved_hydrering_lukker_IKKE_raekken(isolated_runtime, monkeypatch) -> None:
    """Den AEGTE soem: DB-opslaget bag `approval_runtime.state()` fejler.

    `state()` har IKKE laengere sit eget `except Exception: return None` —
    fjernet fordi det gjorde en DB-fejl til den SAMME vaerdi som «kortet
    findes ikke», og lukkede raekken tavst (se
    docs/superpowers/specs/2026-09-21-notifikations-feed-design.md).

    Kortet laegges KUN i det DB-baarne lag (`_set_visible_approval_state`),
    ikke i `_PENDING_APPROVALS` — det tvinger `state()` til rent faktisk at
    ramme `_get_visible_approval_state()` -> `get_runtime_state_value()`,
    ligesom naar en anden proces har oprettet kortet.

    Monkeypatchen sidder paa `get_runtime_state_value` i modulet der rent
    faktisk KALDER navnet —
    `core.services.visible_runs_sections.run_control_state` — ikke i
    `core.runtime.db_core`, hvor navnet oprindeligt bor: en `from X import Y`
    kopierer referencen ved import, saa en monkeypatch paa `db_core` selv IKKE
    naar det kald der reelt sker (maalt: patchede `db_core` og saa kortet
    stadig blive fundet upaavirket).
    """
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    import core.services.visible_runs as VR
    from core.services.visible_runs_sections import run_control_state as rcs

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gemt titel")
    VR._set_visible_approval_state("a-1", {"status": "pending", "tool_name": "bash_session"})
    assert "a-1" not in VR._PENDING_APPROVALS

    def sprang(*_a, **_kw):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(rcs, "get_runtime_state_value", sprang)

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
