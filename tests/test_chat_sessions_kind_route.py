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


# ── Tilladelses-arven ved oprettelse (3/10-2026) ─────────────────────────

def test_oprettelsen_arver_tilladelses_niveauet():
    """Bjoern: «composer arver ikk permissions». Uden koblingen her havde en
    ny samtale ingen vaerdi i `approval_mode`, serveren svarede `ask`, og
    desks PermissionContext overskrev hans «fuld adgang» i samme oejeblik
    samtalen blev valgt."""
    kilde = inspect.getsource(chat_rute.chat_create_session)
    assert "inherit_from" in kilde
    assert "arv_permission(" in kilde


def test_man_kan_ikke_arve_fra_en_samtale_man_ikke_har_adgang_til():
    """Arven maa ikke blive en genvej rundt om adgangskontrollen: et niveau
    fra en FREMMED samtale ville vaere privilegier uden en beslutning."""
    kilde = inspect.getsource(chat_rute.chat_create_session)
    i_arv = kilde.index("inherit_from")
    i_kraev = kilde.index("_kraev_adgang(_arv)")
    i_hent = kilde.index("arv_permission(")
    assert i_arv < i_kraev < i_hent, (
        "adgangstjekket skal ligge FOER arven laeses")


def test_inherit_from_er_tomt_som_standard():
    """En klient der fandtes foer feltet skal faa praecis det den altid har
    faaet: ingen arv, altsaa `ask`."""
    felter = chat_rute.ChatSessionCreateRequest.model_fields
    assert felter["inherit_from"].default == ""


# ── Boy-scout split: tillids-ruterne flyttede, URL'erne gjorde ikke ───────

def test_tillids_ruterne_svarer_stadig_paa_samme_URL():
    """`chat.py` stod paa 2.006 linjer, saa de tre `/chat/workspace-trust`-ruter
    blev udskilt. Flytningen maa ikke kunne fjerne dem fra app'en — en rute
    der forsvinder er en stille regression, og desk's workstation-vaelger
    bygger paa listen."""
    from apps.api.jarvis_api.app import app
    stier = {r.path for r in app.routes if "workspace-trust" in getattr(r, "path", "")}
    assert stier == {"/chat/workspace-trust", "/chat/workspace-trust/list"}
    metoder = {
        m for r in app.routes if getattr(r, "path", "") == "/chat/workspace-trust"
        for m in (getattr(r, "methods", None) or set())
    }
    assert {"GET", "POST"} <= metoder


def test_de_flyttede_navne_kan_stadig_importeres_fra_chat():
    """Bagudkompatibilitet, som Boy Scout-reglen kraever: re-eksportér
    symbolerne saa eksisterende imports ikke braekker."""
    for navn in ("WorkspaceTrustRequest", "get_workspace_trust",
                 "list_workspace_trust", "set_workspace_trust"):
        assert hasattr(chat_rute, navn), navn
