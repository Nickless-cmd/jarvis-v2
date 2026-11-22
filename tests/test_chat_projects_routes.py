"""Projekt-ruterne: Desk-kontrakten, ejerskabet og CI-rutens lukkede fejl.

Målt 22/11-2026: ``core.services.project_context`` og ``file_mention_resolver`` blev
leveret uden en eneste kalder — mekanismer der så ud som om de virkede. Testene her
låser at ruterne faktisk binder dem, og at en andens samtale er 404 (ikke 403, så et
gæt ikke kan bekræftes).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import chat_projects as R

A, B = "ejer-a", "ejer-b"
S1, S2 = "sess-a-1", "sess-a-2"


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.services.chat_sessions as chat_sessions

    ejere = {S1: A, S2: A, "sess-b-1": B}
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: ejere.get(sid))

    def som(uid):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)

    som(A)

    class H:
        som_ = staticmethod(som)

        def http(self, fn, *a, **kw):
            with pytest.raises(HTTPException) as e:
                fn(*a, **kw)
            return e.value.status_code

    yield H()


def test_ny_ejer_har_ingen_projekter(rt) -> None:
    assert R.list_projekter() == {"projects": []}


def test_opret_og_list_projekt_i_desk_kontrakten(rt) -> None:
    svar = R.opret_projekt(R.OpretProjektBody(name="Vinter", session_id=S1))
    projekt = svar["project"]
    assert projekt["name"] == "Vinter"
    assert projekt["id"].startswith("project-")
    assert projekt["files"] == []

    liste = R.list_projekter()["projects"]
    assert [p["id"] for p in liste] == [projekt["id"]]


def test_projekt_er_usynligt_for_en_anden_ejer(rt) -> None:
    projekt = R.opret_projekt(R.OpretProjektBody(name="Mit", session_id=S1))["project"]
    rt.som_(B)
    assert R.list_projekter() == {"projects": []}


def test_binding_og_unbind_af_session(rt) -> None:
    projekt = R.opret_projekt(R.OpretProjektBody(name="Bundet", session_id=S1))["project"]
    assert R.hent_session_projekt(S1) == {"project_id": projekt["id"]}

    R.bind_session_projekt(S2, R.BindProjektBody(project_id=projekt["id"]))
    assert R.hent_session_projekt(S2) == {"project_id": projekt["id"]}

    R.bind_session_projekt(S2, R.BindProjektBody(project_id=None))
    assert R.hent_session_projekt(S2) == {"project_id": None}


def test_fremmed_session_er_404(rt) -> None:
    assert rt.http(R.hent_session_projekt, "sess-b-1") == 404
    assert rt.http(R.hent_session_projekt, "findes-ikke") == 404


def test_bind_til_ukendt_projekt_er_404(rt) -> None:
    assert rt.http(R.bind_session_projekt, S1, R.BindProjektBody(project_id="project-nope")) == 404


def test_ci_status_feiler_lukket_uden_arbejdstrae(rt) -> None:
    svar = R.git_ci_status(root="/findes/ikke", branch="main")
    assert svar["ok"] is False
    assert svar["state"] == "none"
    assert svar["checks"] == []
    assert svar["error"] == "ukendt_arbejdstrae"


def test_ci_status_uden_github_remote_giver_ikke_falsk_groen(rt, tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    svar = R.git_ci_status(root=str(tmp_path), branch="main")
    assert svar["ok"] is False
    assert svar["state"] == "none"
    assert svar["error"] in {"remote_er_ikke_github", "ukendt_sha", "ingen_branch"}
