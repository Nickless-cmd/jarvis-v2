from __future__ import annotations

from core.services.flade_deferred_turn import (
    DeferredTurnAddress,
    aflæs_approval_resultat,
    afslut_tool_resultat,
    kør_deferred_tool,
)


def adresse(revision: int = 4) -> DeferredTurnAddress:
    return DeferredTurnAddress(
        account_id="owner-1",
        conversation_id="chat-1",
        source_message_id="msg-1",
        widget_instance_id="widget-1",
        content_revision=revision,
    )


def test_gyldigt_tool_resultat_reviderer_samme_widget() -> None:
    udfald = afslut_tool_resultat(
        adresse(),
        {"status": "ok", "temperature": 12},
    )

    assert udfald == {
        "status": "delivered",
        "retryable": False,
        "result": {"status": "ok", "temperature": 12},
        "address": {
            "accountId": "owner-1",
            "conversationId": "chat-1",
            "sourceMessageId": "msg-1",
            "widgetInstanceId": "widget-1",
            "contentRevision": 5,
        },
    }


def test_tool_fejl_er_retryable_og_reviderer_ikke_adressen() -> None:
    udfald = afslut_tool_resultat(
        adresse(),
        {"status": "error", "error": "midlertidig netværksfejl"},
    )

    assert udfald["status"] == "failed"
    assert udfald["code"] == "tool_failed"
    assert udfald["retryable"] is True
    assert udfald["address"]["contentRevision"] == 4


def test_tomt_eller_uformeligt_resultat_er_ugyldigt_ikke_retryable() -> None:
    for raw in (None, {}, [], ""):
        udfald = afslut_tool_resultat(adresse(), raw)
        assert udfald["status"] == "failed"
        assert udfald["code"] == "invalid_tool_result"
        assert udfald["retryable"] is False


def test_kun_tool_fra_den_eksisterende_gate_kan_koeres() -> None:
    kald: list[tuple[str, dict]] = []

    udfald = kør_deferred_tool(
        adresse(),
        tool_name="bash",
        arguments={"command": "echo bypass"},
        allowed_tools={"weather"},
        execute=lambda navn, args: kald.append((navn, args)) or {"status": "ok"},
    )

    assert kald == []
    assert udfald["status"] == "failed"
    assert udfald["code"] == "component_unavailable"
    assert udfald["retryable"] is False


def test_approval_needed_bliver_et_approval_kort_ikke_en_succes() -> None:
    registreret: list[tuple[str, dict, dict]] = []
    udfald = kør_deferred_tool(
        adresse(),
        tool_name="weather",
        arguments={"location": "Svendborg"},
        allowed_tools={"weather"},
        execute=lambda _navn, _args: {
            "status": "approval_needed",
            "message": "Godkend kaldet",
        },
        register_approval=lambda navn, args, raw: registreret.append((navn, args, raw)) or "approval-1",
    )

    assert registreret[0][0:2] == ("weather", {"location": "Svendborg"})
    assert udfald == {
        "status": "approval_required",
        "retryable": False,
        "approvalId": "approval-1",
        "address": adresse().public(),
    }


def test_godkendt_kald_reviderer_fladen_med_det_faktiske_resultat() -> None:
    udfald = aflæs_approval_resultat(adresse(), {
        "status": "approved",
        "tool_status": "ok",
        "result_text": '{"temperature":12}',
    })
    assert udfald["status"] == "delivered"
    assert udfald["result"]["result"] == '{"temperature":12}'
    assert udfald["address"]["contentRevision"] == 5


def test_ventende_godkendelse_er_ikke_en_tool_fejl() -> None:
    udfald = aflæs_approval_resultat(adresse(), {"status": "pending"}, approval_id="approval-1")
    assert udfald == {
        "status": "approval_required",
        "retryable": False,
        "approvalId": "approval-1",
        "address": adresse().public(),
    }


def test_afvist_godkendelse_er_terminal_ikke_retryable() -> None:
    udfald = aflæs_approval_resultat(adresse(), {"status": "denied"}, approval_id="approval-1")
    assert udfald["status"] == "failed"
    assert udfald["code"] == "tool_failed"
    assert udfald["retryable"] is False
