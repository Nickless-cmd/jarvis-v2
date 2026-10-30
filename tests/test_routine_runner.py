"""Værktøjssættet et rutine-run byder modellen.

MÅLT 25/10-2026: med alle 111 tilladte værktøjer valgte ollama-modellen
``recall`` og ``note_list`` — men ALDRIG ``madopskrift`` — og svarede derefter
«jeg har ikke adgang til et madopskrift-værktøj». Med det samme værktøj i et
sæt på 1–2 kaldte den det tre gange med rigtige danske søgeord.

Bredden var problemet, ikke værktøjet. Testene her værner om at sættet forbliver
smalt, at det indeholder de værktøjer en rutine faktisk løser opgaver med, og
at en rutines egen politik kan indsnævre — men aldrig udvide — adgangen.
"""

from __future__ import annotations

import hashlib

from core.services.routine_types import AccessScope, RoutineExecutionContext


def _kontekst(**ændringer) -> RoutineExecutionContext:
    værdier = {
        "run_id": "run_test",
        "routine_id": "routine_test",
        "routine_version": 1,
        "owner_user_id": "owner_test",
        "access_scope": AccessScope.USER_PRIVATE,
        "instruction_ref": "routine:test",
        "instruction_hash": hashlib.sha256(b"opgave").hexdigest(),
        "trigger_inputs": {},
        "workspace_name": "test",
        "workspace_kind": "",
        "workspace_root": "",
        "capability_scope": "chat",
        "permission_policy": {},
        "approval_policy": {},
        "provider": "",
        "model": "",
        "lease_generation": 1,
    }
    værdier.update(ændringer)
    return RoutineExecutionContext(**værdier)


def _navne(payload) -> set[str]:
    return {
        str((definition.get("function") or {}).get("name") or "")
        for definition in payload
    }


def test_routine_runner_public_api():
    from core.services.routine_runner import RoutineRunner

    assert callable(RoutineRunner.run_once)
    assert callable(RoutineRunner.cancel)


def test_kerne_saettet_er_smalt_nok_til_at_modellen_kan_overskue_det():
    """Et skema på 111 funktioner druknede det relevante værktøj."""
    from core.services.routine_runner import _rutine_tools_payload

    navne = _navne(_rutine_tools_payload(_kontekst()))

    assert navne, "en chat-rutine skal have værktøjer"
    assert len(navne) <= 30, (
        f"kerne-sættet er {len(navne)} værktøjer — bredden var netop fejlen"
    )


def test_kerne_saettet_indeholder_det_rutinen_faktisk_skal_bruge():
    from core.services.routine_runner import _rutine_tools_payload

    navne = _navne(_rutine_tools_payload(_kontekst()))

    for forventet in ("madopskrift", "web_search", "recall", "notify_user"):
        assert forventet in navne, f"{forventet} mangler i kerne-sættet"


def test_system_rutiner_forbliver_vaerktoejs_fri():
    """Heartbeat/dream er rammer, ikke opgaver — de skal ikke nå ud i verden."""
    from core.services.routine_runner import _rutine_tools_payload

    assert _rutine_tools_payload(_kontekst(capability_scope="system")) == []


def test_rutinens_egen_politik_indsnaevrer_saettet():
    from core.services.routine_runner import _rutine_tools_payload

    navne = _navne(_rutine_tools_payload(
        _kontekst(permission_policy={"tools": ["madopskrift"]})
    ))

    assert navne == {"madopskrift"}


def test_rutinens_politik_kan_ikke_udvide_adgangen():
    """En politik må indsnævre, aldrig udvide — ellers er gaten meningsløs."""
    from core.services.routine_runner import _rutine_tools_payload

    navne = _navne(_rutine_tools_payload(
        _kontekst(permission_policy={"tools": ["madopskrift", "operator_bash"]})
    ))

    assert navne == {"madopskrift"}
    assert "operator_bash" not in navne


def test_ukendte_vaerktoejsnavne_ignoreres_stille():
    from core.services.routine_runner import _rutine_tools_payload

    navne = _navne(_rutine_tools_payload(
        _kontekst(permission_policy={"tools": ["findes_ikke", "web_search"]})
    ))

    assert navne == {"web_search"}


def test_tom_politik_giver_kerne_saettet_ikke_tomt_saet():
    """``tools: []`` er et gyldigt valg om nul værktøjer — men fravær er ikke."""
    from core.services.routine_runner import _rutine_tools_payload

    assert _rutine_tools_payload(_kontekst(permission_policy={"tools": []})) == []

    kerne = _navne(_rutine_tools_payload(_kontekst(permission_policy={})))
    assert "madopskrift" in kerne


def test_rundebudget_laeses_fra_policy_og_afgraenses():
    from core.services.routine_runner import _rutine_max_rounds

    assert _rutine_max_rounds(_kontekst()) == 8
    assert _rutine_max_rounds(_kontekst(permission_policy={"max_rounds": 20})) == 20
    assert _rutine_max_rounds(_kontekst(permission_policy={"max_rounds": 1000})) == 64
    assert _rutine_max_rounds(_kontekst(permission_policy={"max_rounds": True})) == 8


def test_en_sanse_rutine_kan_faktisk_sanse_og_arkivere():
    """Natrutinen skal kunne SE, LYTTE og SKRIVE i arkivet — ikke kun læse det.

    MÅLT 28/10-2026 (``run_f43a8b354a864f0d846beec34930b73f``): kørslen svarede
    «Sanseværktøjerne var ikke i denne kørsels capability scope» og skrev INTET
    i fire døgn, mens den meldte ``succeeded`` hver nat.

    Rod-årsagen var ikke ``ORIGIN_TOOLS``: ``_rutine_tools_payload`` falder
    tilbage til ``_RUTINE_KERNE_TOOLS & tilladte`` når rutinen ikke har en
    ``tools``-policy (natrutinens er kun ``{"max_rounds": 20}``). Stod navnet
    ikke i den håndholdte liste, nåede det aldrig modellen — uanset politik.

    Testen fælder begge halvdele: at værktøjet er TILLADT af politikken, og at
    det faktisk er med i det skema rutinen byder modellen.
    """
    from core.services.routine_runner import _rutine_tools_payload
    from core.tools.autonomous_tool_policy import allowed_tools_for_origin

    navne = _navne(_rutine_tools_payload(_kontekst(permission_policy={"max_rounds": 20})))
    politik = allowed_tools_for_origin("routine")

    for værktøj in (
        "look_around", "mic_listen",
        "record_sensory_memory", "recall_sensory_memories",
    ):
        assert værktøj in politik, (
            f"{værktøj} afvises af politikken for origin 'routine' — et "
            f"rutine-run kan ikke sanse"
        )
        assert værktøj in navne, (
            f"{værktøj} er tilladt men står ikke i rutinens kerne-sæt, så det "
            f"når aldrig modellen (28/10-2026: natrutinen skrev intet i fire døgn)"
        )
