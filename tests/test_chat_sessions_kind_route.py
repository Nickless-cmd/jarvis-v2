"""Naar ruten videregiver `kind` — og naar den IKKE goer."""
import inspect

from apps.api.jarvis_api.routes import chat as chat_rute


def test_listningen_videregiver_kind():
    kilde = inspect.getsource(chat_rute.chat_sessions)
    assert "kind=(kind or None)" in kilde


def test_UDELADT_kind_betyder_alt_ikke_chat():
    # Enhver klient der fandtes foer kolonnen skal faa praecis det den altid
    # har faaet. `kind=""` -> None -> intet filter.
    sig = inspect.signature(chat_rute.chat_sessions)
    assert sig.parameters["kind"].default == ""


def test_oprettelsen_videregiver_kind():
    kilde = inspect.getsource(chat_rute.chat_create_session)
    assert 'kind=request.kind or "chat"' in kilde


def test_kind_er_IKKE_det_samme_som_workspace_kind():
    # De to staar ved siden af hinanden og betyder noget helt forskelligt.
    felter = chat_rute.ChatSessionCreateRequest.model_fields
    assert "kind" in felter and "workspace_kind" in felter
    assert felter["kind"].default == "chat"
    assert felter["workspace_kind"].default == ""
