"""Kvitteringen for `send_message_to_agent` — Fase 6.

Foer koerte barnet INLINE, og foraelderens tur var frosset indtil det var
faerdigt. Det faeldede to kriterier: kvitteringen, og «foraelderen kan
fortsaette mens et accepteret barn koerer».

MAALT over 929 aegte agent-koersler foer bygningen:

    median   6,0 s      p90  36,8 s      max 430,5 s      over 60 s: 68

Det tal bestemte formen. En kvittering paa HVER besked ville vaere daarligere
for det almindelige tilfaelde — foraelderen skulle polle efter et
seks-sekunders job. Halen er problemet, ikke medianen. Derfor: vent kort,
kvittér derefter.
"""
from __future__ import annotations

import threading
import time


def _agent(db, aid="a"):
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
    db.update_agent_registry_entry(aid, status="queued")
    return aid


def test_hurtigt_barn_svarer_som_foer(isolated_runtime, monkeypatch):
    """Medianen er 6 s. Det almindelige tilfaelde maa IKKE blive til en
    kvittering — saa ville foraelderen polle efter et kort job."""
    import core.services.agent_message_receipt as mr

    aid = _agent(__import__("core.runtime.db_agent_runtime", fromlist=["x"]))
    monkeypatch.setattr(
        "core.services.agent_runtime.execute_agent_task",
        lambda **kw: {"status": "completed", "agent_id": aid, "messages": []})

    svar = mr.send_med_kvittering(agent_id=aid, content="hej",
                                  taalmodighed_s=5.0)
    assert svar.get("status") == "completed", (
        "et hurtigt barn blev til en kvittering — foraelderen skal have svaret")


def test_langsomt_barn_giver_kvittering_og_koerer_VIDERE(isolated_runtime, monkeypatch):
    """Kernen. Barnet maa ikke kasseres fordi foraelderen holdt op med at vente."""
    import core.runtime.db_agent_runtime as db
    import core.services.agent_message_receipt as mr

    aid = _agent(db, "a-langsom")
    naaede_frem = threading.Event()

    def _langsom(**kw):
        time.sleep(0.6)
        naaede_frem.set()
        return {"status": "completed", "agent_id": aid, "messages": []}

    monkeypatch.setattr("core.services.agent_runtime.execute_agent_task", _langsom)

    t0 = time.monotonic()
    svar = mr.send_med_kvittering(agent_id=aid, content="graev dybt",
                                  taalmodighed_s=0.15)
    brugt = time.monotonic() - t0

    assert svar.get("status") == "accepted", "foraelderen fik ikke en kvittering"
    assert svar.get("agent_id") == aid
    assert brugt < 0.5, f"foraelderen ventede alligevel ({brugt:.2f}s)"
    assert "hent_resultat" in svar, (
        "en kvittering der ikke siger hvordan man henter resultatet, "
        "forudsaetter at laeseren kender huset")
    assert aid in str(svar["hent_resultat"]), "afhentningen naevner ikke agenten"

    assert naaede_frem.wait(timeout=5), (
        "barnet blev kasseret da foraelderen holdt op med at vente — hele "
        "pointen var at det arbejder videre")


def test_beskeden_er_landet_FOER_der_kvitteres(isolated_runtime, monkeypatch):
    """En kvittering paa noget der ikke er accepteret ville vaere en loegn."""
    import core.runtime.db_agent_runtime as db
    import core.services.agent_message_receipt as mr

    aid = _agent(db, "a-landet")
    monkeypatch.setattr("core.services.agent_runtime.execute_agent_task",
                        lambda **kw: time.sleep(1) or {"status": "completed"})

    svar = mr.send_med_kvittering(agent_id=aid, content="min besked",
                                  taalmodighed_s=0.1)
    assert svar.get("status") == "accepted"
    tekster = [str(m.get("content") or "") for m in db.list_agent_messages(agent_id=aid)]
    assert "min besked" in tekster, "der blev kvitteret for en besked der ikke var landet"


def test_ukendt_agent_giver_fejl_ikke_kvittering(isolated_runtime):
    import core.services.agent_message_receipt as mr

    svar = mr.send_med_kvittering(agent_id="findes-ikke", content="hej",
                                  taalmodighed_s=0.1)
    assert svar.get("status") == "error"
    assert "accepted" not in str(svar.get("status"))


def test_barnet_baerer_foraelderens_kontekst_men_ikke_godkendelsen(isolated_runtime,
                                                                  monkeypatch):
    """Fase 5 besluttede hvad et barn arver: autonomi, workspace-tillid og
    vaerktoejs-scope bevares, ejer-godkendelsen ryddes. En almindelig traad
    mister ALLE fire — og to af tabene peger i den FARLIGE retning: tomt scope
    betyder «unbound legacy» (ser alt), og tabt autonomi fjerner
    sandkasse-kravet for bash."""
    import core.runtime.db_agent_runtime as db
    import core.services.agent_message_receipt as mr
    from core.services.run_autonomy_context import _autonom
    from core.services.workspace_trust import _trust_ctx
    from core.tools.owner_approval import _ejer_godkendt
    from core.tools.tool_scoping import _scope_var

    aid = _agent(db, "a-kontekst")
    set_i_barnet: dict = {}

    def _kig(**kw):
        set_i_barnet.update(
            autonom=_autonom.get(None), tillid=_trust_ctx.get(None),
            scope=_scope_var.get(None), godkendt=_ejer_godkendt.get(None),
        )
        return {"status": "completed", "messages": []}

    monkeypatch.setattr("core.services.agent_runtime.execute_agent_task", _kig)

    # NULSTIL BAGEFTER. ContextVars sat i en test overlever i den samme traad,
    # saa en senere test arver dem — foerste koersel af denne fil vaeltede
    # `test_child_authority`, som med rette gaar ud fra standarden.
    poletter = [(_autonom, _autonom.set(True)),
                (_trust_ctx, _trust_ctx.set({"tillid": "fuld"})),
                (_scope_var, _scope_var.set("agent")),
                (_ejer_godkendt, _ejer_godkendt.set(True))]
    try:
        mr.send_med_kvittering(agent_id=aid, content="hej", taalmodighed_s=5.0)
    finally:
        for var, polet in reversed(poletter):
            var.reset(polet)

    assert set_i_barnet.get("autonom") is True, "autonomien gik tabt i traaden"
    assert set_i_barnet.get("tillid") == {"tillid": "fuld"}, "tilliden gik tabt"
    assert set_i_barnet.get("scope") == "agent", (
        "vaerktoejs-scopet gik tabt — tomt scope betyder «ser alt»")
    assert set_i_barnet.get("godkendt") is False, (
        "barnet arvede foraelderens ejer-godkendelse: ET MENNESKE sagde ja til "
        "DEN handling, ikke til alt barnet maatte finde paa")
