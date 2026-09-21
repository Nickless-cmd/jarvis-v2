# tests/test_notifikations_emittere.py
from __future__ import annotations


def test_godkendelse_giver_en_raekke_OG_et_push(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e
    from core.services import notification_router

    sendt = []
    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: sendt.append((a, kw)) or {"ok": True})

    e.paa_godkendelse("a-1", user_id="bjorn", session_id="s-1", vaerktoej="bash_session")

    raekker = n.aabne("bjorn", er_owner=True)
    assert len(raekker) == 1
    assert raekker[0]["ref"] == "a-1"
    assert sendt, "en godkendelse skal ogsaa naa telefonen"


def test_faerdigt_svar_giver_en_raekke_men_INTET_push(isolated_runtime, monkeypatch) -> None:
    """Standarden er at kun det der haster afbryder."""
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e
    from core.services import notification_router

    sendt = []
    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: sendt.append(a) or {"ok": True})

    e.paa_koersel_faerdig("r-1", user_id="bjorn", session_id="s-1", titel="Kæledyret")
    assert len(n.aabne("bjorn", er_owner=True)) == 1
    assert sendt == []


def test_eget_valg_kan_taende_for_pushet(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikations_emittere as e
    from core.services import notifikations_valg as v
    from core.services import notification_router

    sendt = []
    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: sendt.append(a) or {"ok": True})
    v.saet("bjorn", "run_done", "push")

    e.paa_koersel_faerdig("r-1", user_id="bjorn", session_id="s-1", titel="Kæledyret")
    assert sendt, "har man selv taendt for den slags, skal den pushe"


def test_systemraekke_havner_hos_owner(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(e, "_owner_id", lambda: "bjorn")
    e.system("release", "Ny version 0.6.70 er klar")
    raekker = n.aabne("bjorn", er_owner=True)
    assert len(raekker) == 1
    assert raekker[0]["slags"] == "release"


def test_push_der_fejler_maa_ikke_tabe_raekken(isolated_runtime, monkeypatch) -> None:
    """Feeden er den paalidelige del. Telefonen er den upaalidelige."""
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e
    from core.services import notification_router

    def sprang(*a, **kw):
        raise RuntimeError("ingen forbindelse")
    monkeypatch.setattr(notification_router, "route_proactive_notification", sprang)

    e.paa_godkendelse("a-1", user_id="bjorn", session_id="s-1", vaerktoej="bash_session")
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_faerdig_koersel_der_koerer_igen_lukker_raekken(isolated_runtime, monkeypatch) -> None:
    """Startede den forfra, er «svar klar» ikke sandt laengere."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import notifikations_emittere as e
    from core.services import notification_router
    from core.services.visible_runs_sections import run_finalization

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    e.paa_koersel_faerdig("r-1", user_id="bjorn", session_id="s-1", titel="X")
    monkeypatch.setattr(run_finalization, "status_for_run", lambda rid: "running")

    assert h.feed("bjorn", er_owner=True) == []
    assert n.aabne("bjorn", er_owner=True) == []
