"""Kold genoptagelse — Fase 6.

Jeg paastod foerst at den IKKE fandtes, ud fra en grep der filtrerede den
afgoerende linje vaek. Den findes: `_execute_agent_task_impl` laeser traadens
beskeder fra DB'en og laegger dem i prompten under «Conversation so far». Det
er praecis det der goer genoptagelsen KOLD — historikken ligger i databasen,
ikke i processens hukommelse, saa den overlever at processen doer.

Egenskaben var bare utestet. Disse tests laaser den fast:

  * en genoptaget agent ser hvad den allerede har gjort,
  * historikken kommer fra DB'en (ny proces, samme resultat),
  * og de nyeste beskeder overlever loftet.

MAALT 10/9-2026: loftet paa 40 bider ikke i praksis — den travleste AEGTE agent
har 12 beskeder. (Den ene raekke over 40 har tom `agent_id` og er ikke en agent.)
"""
from __future__ import annotations


def _tal(db, aid, tekst, retning="agent->runtime"):
    from uuid import uuid4
    db.create_agent_message(
        message_id=f"m-{uuid4().hex}",
        thread_id=f"agent-thread-{aid}",
        agent_id=aid, direction=retning, role="assistant",
        kind="message", content=tekst,
    )


def test_genoptaget_agent_ser_sit_eget_arbejde(isolated_runtime, monkeypatch):
    """Det der goer genoptagelsen brugbar: barnet begynder ikke forfra."""
    import core.runtime.db_agent_runtime as db
    import core.services.agent_runtime_spawn as sp

    aid = "a-koldt"
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="find sandheden")
    _tal(db, aid, "Jeg har allerede laest core/tools/ og fandt tre kandidater.")
    _tal(db, aid, "Den tredje ser forkert ud.")
    db.update_agent_registry_entry(aid, status="queued")

    set_prompt: list[str] = []

    class _Facade:
        @staticmethod
        def execute_with_role_or_fallback(*a, **kw):
            set_prompt.append(str(kw.get("message") or ""))
            return {"status": "completed", "text": "ok", "input_tokens": 1,
                    "output_tokens": 1, "cost_usd": 0.0, "provider": "p", "model": "m"}

    monkeypatch.setattr(sp, "_facade", lambda: _Facade)
    monkeypatch.setattr(sp, "_run_agent_tool_loop", None, raising=False)
    sp._execute_agent_task_impl(agent_id=aid)

    assert set_prompt, "udbyderen blev aldrig kaldt — testen maalte ingenting"
    p = set_prompt[0]
    assert "Conversation so far" in p
    assert "tre kandidater" in p, (
        "barnet fik ikke sin egen historik med — det ville begynde forfra")
    assert "Den tredje ser forkert ud" in p
    assert "find sandheden" in p, "maalet skal stadig med"


def test_historikken_kommer_fra_DB_ikke_fra_hukommelsen(isolated_runtime):
    """Kernen i ordet KOLD. En helt frisk proces — der aldrig har set agenten —
    skal kunne bygge den samme historik. Kan den det, overlever genoptagelsen
    at processen doer."""
    import os
    import subprocess
    import sys

    import core.runtime.db_agent_runtime as db
    from core.runtime import db_core

    aid = "a-frisk"
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
    _tal(db, aid, "et spor jeg allerede har fulgt")

    # HOME udledes af DB-stien, ikke af env: modul-konstanter bindes ved import,
    # saa env-varen alene flytter ikke barnets database.
    hjem = str(db_core.DB_PATH).split("/.jarvis-v2/")[0]
    ud = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "from core.services.agent_runtime_spawn import _build_agent_prompt\n"
         "from core.runtime.db_agent_runtime import (get_agent_registry_entry,\n"
         "                                           list_agent_messages)\n"
         "a = get_agent_registry_entry(%r)\n"
         "m = list_agent_messages(agent_id=%r, limit=40)\n"
         "print(_build_agent_prompt(agent=a, messages=m, execution_mode='solo-task'))"
         % (os.getcwd(), aid, aid)],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "HOME": hjem},
    )
    assert ud.returncode == 0, ud.stderr[-800:]
    assert "et spor jeg allerede har fulgt" in ud.stdout, (
        "en frisk proces kunne ikke genskabe historikken fra DB'en — saa er "
        "genoptagelsen ikke kold")


def test_loftet_beholder_de_NYESTE_beskeder(isolated_runtime):
    """Naar loftet en dag bider, skal det vaere halen der overlever — ikke
    hovedet. Det nyeste er det agenten skal svare paa."""
    import core.runtime.db_agent_runtime as db

    aid = "a-loft"
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
    for i in range(45):
        _tal(db, aid, f"besked-{i:02d}")

    # Som prompt-byggeren spoerger: halen.
    m = db.list_agent_messages(agent_id=aid, limit=40, tail=True)
    assert len(m) == 40
    tekster = [str(x.get("content") or "") for x in m]
    assert "besked-44" in tekster, "den nyeste besked faldt ud af vinduet"
    assert "besked-00" not in tekster
    assert tekster == sorted(tekster), (
        "halen skal stadig leveres aeldst-foerst — ellers laeser barnet "
        "samtalen baglaens")

    # Standarden er UAENDRET: visnings-kaldere vil stadig have hovedet.
    hoved = [str(x.get("content") or "")
             for x in db.list_agent_messages(agent_id=aid, limit=40)]
    assert "besked-00" in hoved and "besked-44" not in hoved


def test_UDFOEREREN_giver_barnet_halen_ikke_hovedet(isolated_runtime, monkeypatch):
    """Koblingen, ikke bare DB-funktionen.

    Min foerste hale-test bestod ogsaa UDEN at udfoereren bad om halen — den
    kaldte `list_agent_messages` direkte. Den beviste altsaa at muligheden
    fandtes, ikke at nogen brugte den. Denne gaar gennem udfoereren og laeser
    den prompt barnet faktisk faar.
    """
    import core.runtime.db_agent_runtime as db
    import core.services.agent_runtime_spawn as sp

    aid = "a-hale"
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
    for i in range(45):
        _tal(db, aid, f"besked-{i:02d}")
    db.update_agent_registry_entry(aid, status="queued")

    set_prompt: list[str] = []

    class _Facade:
        @staticmethod
        def execute_with_role_or_fallback(*a, **kw):
            set_prompt.append(str(kw.get("message") or ""))
            return {"status": "completed", "text": "ok", "input_tokens": 1,
                    "output_tokens": 1, "cost_usd": 0.0, "provider": "p", "model": "m"}

    monkeypatch.setattr(sp, "_facade", lambda: _Facade)
    monkeypatch.setattr(sp, "_run_agent_tool_loop", None, raising=False)
    sp._execute_agent_task_impl(agent_id=aid)

    assert set_prompt, "udbyderen blev aldrig kaldt — testen maalte ingenting"
    p = set_prompt[0]
    assert "besked-44" in p, (
        "barnet fik de AELDSTE 40 og svarede paa forgangen kontekst")
    assert "besked-00" not in p
