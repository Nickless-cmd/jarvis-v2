"""En terminal status er endelig — Fase 6, afbrydelses-kvittering.

MAALT 10/9-2026 foer rettelsen:

  * Ordet `cancelled` fandtes i `agent_runtime_spawn` KUN i timeout-fejeren og
    i `cancel_agent` selv. Udfoerelsen laeste aldrig status igen.
  * `cancel_agent` skrev en besked og satte status — men intet standsede
    agenten. Den var en ETIKET, ikke en afbrydelse.
  * Vaerre: ved afslutningen skrev udfoereren `completed` UBETINGET. En
    afbrydelse undervejs forsvandt derfor sporloest — agenten meldte sig
    faerdig, og intet viste at nogen havde sagt stop.

EKSPONERINGEN VAR NUL: nul afbrydelser i hele DB'ens levetid (de 16 rakker med
status='cancelled' kom fra timeout-fejeren). Stien er altsaa aldrig brugt —
hvilket er praecis derfor faelden er vaerd at lukke: den ville ramme FOERSTE
gang nogen trykker afbryd i Mission Control.

`cancel_agent` standser stadig ikke et udbyder-kald midt i det. Afbrydelsen
taeller ved RUNDEGRAENSEN — men den overlever nu, og barnet kvitterer.
"""
from __future__ import annotations

import pytest


def _agent(db, aid="a", **kw):
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="g", **kw)
    return aid


def test_afbrudt_agent_saettes_ikke_i_gang(isolated_runtime):
    """Foer: intet sted i udfoerelsen laeste status, saa en afbrudt agent i koe
    blev alligevel koert."""
    import core.runtime.db_agent_runtime as db
    from core.services.agent_runtime_spawn import _execute_agent_task_impl

    for terminal in ("cancelled", "expired"):
        aid = _agent(db, aid=f"a-{terminal}")
        db.update_agent_registry_entry(aid, status=terminal)
        with pytest.raises(RuntimeError, match="already terminal"):
            _execute_agent_task_impl(agent_id=aid)


def test_completed_spaerrer_IKKE(isolated_runtime):
    """`completed` staar bevidst ikke paa listen: vedvarende agenter vaekkes fra
    terminale tilstande, og den sti er ikke maalt. Vagten skal ramme det den
    kender, ikke det den gaetter paa."""
    import core.runtime.db_agent_runtime as db
    from core.services.agent_runtime_spawn import _execute_agent_task_impl

    aid = _agent(db, aid="a-completed")
    db.update_agent_registry_entry(aid, status="completed")
    try:
        _execute_agent_task_impl(agent_id=aid)
    except RuntimeError as exc:
        assert "already terminal" not in str(exc), (
            "completed blev spaerret — det var ikke det maalte hul")
    except Exception:
        pass                                  # fejler senere af andre grunde: fint


def test_afbrydelse_UNDERVEJS_overskrives_ikke(isolated_runtime, monkeypatch):
    """Kernen. Agenten afbrydes MENS udbyder-kaldet koerer.

    Foer skrev udfoereren `completed` ubetinget bagefter, saa afbrydelsen
    forsvandt sporloest. Nu bevares den terminale status, arbejdet bogfoeres
    stadig (tokens + runde), og barnet KVITTERER i traaden.
    """
    import core.runtime.db_agent_runtime as db
    import core.services.agent_runtime_spawn as sp

    aid = _agent(db, aid="a-midt")
    db.update_agent_registry_entry(aid, status="queued")

    class _Facade:
        @staticmethod
        def execute_with_role_or_fallback(*a, **kw):
            # Nogen trykker afbryd mens udbyderen arbejder.
            sp.cancel_agent(aid, note="Bjoern trykkede afbryd")
            return {"status": "completed", "text": "jeg naaede at blive faerdig",
                    "input_tokens": 11, "output_tokens": 7, "cost_usd": 0.0,
                    "provider": "p", "model": "m"}

    monkeypatch.setattr(sp, "_facade", lambda: _Facade)
    monkeypatch.setattr(sp, "_run_agent_tool_loop", None, raising=False)

    sp._execute_agent_task_impl(agent_id=aid)

    raekke = db.get_agent_registry_entry(aid)
    assert raekke["status"] == "cancelled", (
        "agenten overskrev sin egen afbrydelse med 'completed' — afbrydelsen "
        "forsvandt sporloest")
    assert int(raekke["tokens_burned"]) == 18, (
        "arbejdet skal stadig bogfoeres; det ER sket")
    assert int(raekke["turns_completed"]) == 1

    kvit = [m for m in db.list_agent_messages(agent_id=aid)
            if "Afbrudt undervejs" in str(m.get("content") or "")]
    assert kvit, "barnet kvitterede ikke for afbrydelsen"


def test_uafbrudt_agent_afslutter_som_foer(isolated_runtime, monkeypatch):
    """Vagten maa ikke aendre den normale vej: uden afbrydelse skal agenten
    stadig ende `completed` med et tidsstempel."""
    import core.runtime.db_agent_runtime as db
    import core.services.agent_runtime_spawn as sp

    aid = _agent(db, aid="a-normal")
    db.update_agent_registry_entry(aid, status="queued")

    class _Facade:
        @staticmethod
        def execute_with_role_or_fallback(*a, **kw):
            return {"status": "completed", "text": "faerdig", "input_tokens": 3,
                    "output_tokens": 4, "cost_usd": 0.0, "provider": "p", "model": "m"}

    monkeypatch.setattr(sp, "_facade", lambda: _Facade)
    monkeypatch.setattr(sp, "_run_agent_tool_loop", None, raising=False)

    sp._execute_agent_task_impl(agent_id=aid)

    raekke = db.get_agent_registry_entry(aid)
    assert raekke["status"] == "completed"
    assert raekke["completed_at"]
