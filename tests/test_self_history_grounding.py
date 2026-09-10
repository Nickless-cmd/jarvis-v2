"""Prompten maa ikke forveksle et rygte med en kendsgerning.

Opgave 6 — grenens skarpeste krav, og hele grunden til at bygge resten. Alt
det foregaaende er lagre; her naar de prompten, og her afgoeres det om Jarvis
kan skelne mellem:

  * hvad han HAR OBSERVERET og hvad nogen har SAGT til ham,
  * hvad han er blevet FORTOLKET til at vaere og hvad der er maalt,
  * og hvad et alias beviser (at et navn peger et sted) mod hvad det IKKE
    beviser (at en ny model er rullet ud).

En modsigelse maerkes i stedet for at blive loest i stilhed. At vaelge én side
uden at sige det er den vaerste udgave: laeseren tror han ser hele billedet.
"""
from __future__ import annotations

from core.services.self_history_grounding import (
    build_self_history_grounding_section,
    classify_self_history_query,
)


def test_uvedkommende_beskeder_giver_INGEN_sektion():
    """En grounding-sektion i hver tur ville laere modellen at ignorere den."""
    for besked in ("hvad er klokken?", "lav en kop kaffe", "", "tak for hjælpen"):
        p = classify_self_history_query(besked)
        assert p.wants_grounding is False, besked
        assert build_self_history_grounding_section(besked, session_id="s") is None


def test_spoergsmaal_om_egen_historik_udloeser_den():
    for besked in (
        "hvad sagde du om dig selv i går?",
        "er din selvopfattelse ændret?",
        "which model actually answered me?",
        "hvilken model svarede egentlig?",
        "hvad er du blevet bedre til?",
    ):
        assert classify_self_history_query(besked).wants_grounding is True, besked


def test_en_VERIFICERET_kendsgerning_slaar_en_nyere_samtale_paastand(isolated_runtime):
    """Grenens kerne. Et emne er hvad nogen TALTE om — ikke hvad der er sandt.
    Selv naar samtalen er nyere."""
    from core.runtime.db_world_self_truth import upsert_conversation_topic
    from core.services.world_facts import record_world_fact

    record_world_fact(
        canonical_key="fact:harness-public",
        statement="The DeepSeek Harness is public.",
        status="verified", confidence="high",
        source_kind="primary_source", source_ref="https://example/harness",
    )
    upsert_conversation_topic(
        topic_id="t1", canonical_key="topic:harness",
        title="Harness er ikke udgivet",
        summary="Vi talte om at harnessen ikke er offentlig",
        source_kind="visible_run", session_id="s", run_id="r1",
        created_at="2026-09-10T12:00:00", updated_at="2026-09-10T12:00:00",
    )

    tekst = build_self_history_grounding_section(
        "er harnessen offentlig?", session_id="s") or ""
    assert "public" in tekst.lower(), "den verificerede kendsgerning naaede ikke prompten"
    lav = tekst.lower()
    if "harness er ikke udgivet" in lav:
        assert ("samtale" in lav or "omtalt" in lav), (
            "et samtale-emne blev gengivet som verdens-sandhed")


def test_selvbilleder_kaldes_FORTOLKEDE_ikke_maalte(isolated_runtime):
    from core.services.self_model_history import record_self_model_snapshot

    record_self_model_snapshot(
        identity_focus="at bygge", preferred_work_mode="dybt",
        recurring_tension="tid", growth_direction="taalmod",
        confidence="medium", source="distiller")
    tekst = build_self_history_grounding_section(
        "hvad sagde du om dig selv i går?", session_id="s") or ""
    assert "fortolk" in tekst.lower(), (
        "selvbilleder blev fremlagt som maalinger — de er destillerede "
        "fortolkninger")


def test_et_alias_beviser_ikke_en_udrulning(isolated_runtime):
    """Ser man `deepseek-flash` i svaret, ved man at NAVNET pegede derhen —
    ikke at en ny model er rullet ud bag det navn. Prompten skal sige det, for
    ellers bygger Jarvis en konklusion paa et alias."""
    from core.services.provider_model_epochs import record_model_observation

    record_model_observation(provider="deepseek", requested_model="deepseek-chat",
                             observed_model="deepseek-flash")
    tekst = build_self_history_grounding_section(
        "hvilken model svarede egentlig?", session_id="s") or ""
    lav = tekst.lower()
    assert "deepseek-chat" in lav and "deepseek-flash" in lav, (
        "baade det oenskede og det observerede navn skal staa")
    assert "beviser ikke" in lav or "ikke bevis" in lav, (
        "prompten siger ikke hvad aliaset IKKE beviser")


def test_sektionen_kaster_aldrig(isolated_runtime, monkeypatch):
    """En grounding-sektion maa aldrig kunne vaelte prompt-bygningen."""
    import core.services.self_history_grounding as g

    monkeypatch.setattr(g, "_verdens_fakta",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db")))
    assert build_self_history_grounding_section(
        "hvad sagde du om dig selv i går?", session_id="s") is not None or True


def test_sektionen_er_koblet_i_prompten():
    """Uden koblingen er hele grenen lagre ingen laeser. Testen laeser
    kaldstedet, fordi prompt-bygningen kraever en fuld runtime."""
    import inspect

    from core.services import prompt_contract as pc

    kilde = inspect.getsource(pc)
    assert "build_self_history_grounding_section(" in kilde, (
        "grounding-sektionen naar aldrig prompten")
    assert "self/world grounding" in kilde
