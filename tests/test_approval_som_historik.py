"""Godkendelsen skal kunne findes igen — målt 31/10-2026.

## Fejlen der blev lukket

Et godkendelses-kort levede KUN i klientens `pendingApproval`. Efter en reload
var det væk, og en afgjort godkendelse blev aldrig til noget man kunne scrolle
tilbage til. Bjørns formulering: «approval cards må ikk kunne dø et run».

## To invariants, og den anden er den farlige

1. **Anmodningen og afgørelsen SKAL skrives** som rækker i samtalens historik.
   Formen er append-only: to hændelser, ikke én række der opdateres. En UPDATE
   ville bryde ledgerens invariant, hvor rækken er en projektion af en hændelse
   der allerede er skrevet.

2. **`approval_request` må ALDRIG nå prompten.** Det er UI-historik, ikke noget
   nogen sagde. `transcript_sections` havde kun grene for `user` og `tool` —
   alt andet faldt i `else`-grenen og blev læst som ASSISTANT-tekst. Uden
   filteret ville modellen læse sit eget godkendelses-kort som sin egen sætning.

Den anden er den farlige: en manglende persistering er et savnet kort, men en
lækket `approval_request` er en fordrejning af hvad jeg tror jeg har sagt.
"""
from __future__ import annotations

import json

import pytest

from core.services import approval_runtime as AR


@pytest.fixture
def kort():
    return {
        "tool_name": "exec_command",
        "arguments": {"command": "rm -rf /tmp/x"},
        "result": {"classification": "destructive", "command": "rm -rf /tmp/x"},
        "run_id": "r1",
        "session_id": "s-historik",
        "created_at": "2026-10-31T12:00:00+00:00",
        "owner_user_id": "bjorn",
    }


def _opret_session(session_id: str) -> None:
    """En godkendelse opstaar ALTID i en koerende samtale — sa sessionen
    findes i produktion. Testen skal derfor oprette den, ikke gaette."""
    from datetime import UTC, datetime
    from core.runtime.db import connect
    nu = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions "
            "(session_id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (session_id, "t", nu, nu),
        )
        conn.commit()


def _blok(raekke: dict) -> dict:
    """Raekkens foerste blok — formen er en liste, saa `_content_json_for_row`
    returnerer den som den er (et objekt ville blive kastet vaek)."""
    return json.loads(raekke["content_json"])[0]


def _raekker(session_id: str) -> list[dict]:
    from core.runtime.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT message_id, role, content, content_json FROM chat_messages "
            "WHERE session_id = ? AND role = 'approval_request' ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── 1. anmodningen skrives ────────────────────────────────────────────────

def test_anmodningen_skrives_som_en_raekke(isolated_runtime, kort):
    _opret_session("s-historik")
    mid = AR.persist_approval_message(
        approval_id="approval-abc", kort=kort, status="pending",
    )
    assert mid, "anmodningen blev ikke persisteret"

    rows = _raekker("s-historik")
    assert len(rows) == 1
    data = _blok(rows[0])
    assert data["approval_id"] == "approval-abc"
    assert data["status"] == "pending"
    assert data["tool"] == "exec_command"
    # Kommandoen skal stå i historikken — ellers kan man ikke se HVAD man
    # godkendte da man ser tilbage.
    assert "rm -rf /tmp/x" in data["action"]
    assert "rm -rf /tmp/x" in rows[0]["content"]


# ── 2. afgørelsen er en NY hændelse, ikke en opdatering ────────────────────

def test_afgoerelsen_er_en_ny_haendelse(isolated_runtime, kort):
    _opret_session("s-historik")
    AR.persist_approval_message(
        approval_id="approval-abc", kort=kort, status="pending",
    )
    AR.persist_approval_message(
        approval_id="approval-abc", kort=kort, status="approved",
        decided_by="bjorn",
    )

    rows = _raekker("s-historik")
    assert len(rows) == 2, "afgørelsen må ikke overskrive anmodningen"

    statusser = [_blok(r)["status"] for r in rows]
    assert statusser == ["pending", "approved"]

    # Samme approval_id binder dem sammen — det er dét klienten grupperer på.
    ids = {_blok(r)["approval_id"] for r in rows}
    assert ids == {"approval-abc"}

    sidste = _blok(rows[-1])
    assert sidste["decided_by"] == "bjorn"
    assert sidste["decided_at"], "afgørelsen mangler tidsstempel"


def test_alle_fire_statusser_kan_skrives(isolated_runtime, kort):
    _opret_session("s-historik")
    for st in ("pending", "approved", "denied", "expired"):
        assert AR.persist_approval_message(
            approval_id=f"approval-{st}", kort=kort, status=st,
        ), f"{st} blev ikke skrevet"
    assert len(_raekker("s-historik")) == 4


# ── 3. self-safe: en fejl må ikke vælte godkendelses-flowet ───────────────

def test_persistering_der_kaster_vaelter_ikke_flowet(isolated_runtime, kort, monkeypatch):
    import core.services.chat_sessions as CS

    def _kaster(*a, **k):
        raise RuntimeError("DB nede")

    monkeypatch.setattr(CS, "append_chat_message", _kaster)

    # Returnerer None — men KASTER IKKE. Et kort der ikke kan gemmes er
    # dårligt; et kort der ikke kan VISES fordi skrivningen kastede, er værre.
    assert AR.persist_approval_message(
        approval_id="approval-x", kort=kort, status="pending",
    ) is None


def test_kort_uden_session_skrives_ikke(isolated_runtime, kort):
    kort["session_id"] = ""
    assert AR.persist_approval_message(
        approval_id="approval-x", kort=kort, status="pending",
    ) is None


# ── 4. DEN FARLIGE: approval_request må ikke nå prompten ──────────────────

def test_approval_request_naar_ALDRIG_prompten(isolated_runtime):
    from core.services.chat_sessions import append_chat_message
    from core.services.prompt_sections.transcript_sections import (
        _build_structured_transcript_messages as bygg,
    )

    sid = "s-prompt"
    _opret_session(sid)
    append_chat_message(session_id=sid, role="user", content="kør kommandoen")
    append_chat_message(
        session_id=sid, role="approval_request",
        content="Godkendelse afventer: exec_command — rm -rf /tmp/x",
        content_json=json.dumps([{"type": "approval", "approval_id": "a1",
                                  "tool": "exec_command", "action": "rm -rf /tmp/x",
                                  "status": "pending"}]),
    )
    append_chat_message(session_id=sid, role="assistant", content="Jeg venter.")

    besked = bygg(sid, limit=50, include=True, bivirkninger=False)

    alt = " ".join(m.get("content") or "" for m in besked)
    assert "Godkendelse afventer" not in alt, (
        "godkendelses-kortet lækkede ind i prompten som samtaletekst"
    )
    assert "approval_request" not in alt
    # Og de ægte beskeder skal stadig være der.
    assert any("kør kommandoen" in (m.get("content") or "") for m in besked)


# ── 5. data skal overleve vejen til klienten ──────────────────────────────

def test_blokken_naar_klienten_som_struktur(isolated_runtime, kort):
    """`_content_json_for_row` kaster et OBJECT vaek og rekonstruerer fra tekst.
    Formen SKAL vaere en liste, ellers mister klienten approval_id og status —
    og saa kan den hverken gruppere eller vise hvad der blev afgjort."""
    _opret_session("s-historik")
    AR.persist_approval_message(
        approval_id="approval-klient", kort=kort, status="denied",
        decided_by="bjorn",
    )
    from core.services.chat_sessions import get_chat_session

    session = get_chat_session("s-historik")
    raekke = next(
        m for m in session["messages"] if m["role"] == "approval_request"
    )
    blokke = raekke["content_json"]
    assert isinstance(blokke, list) and blokke, "blokken forsvandt"
    blok = blokke[0]
    assert blok["type"] == "approval"
    assert blok["approval_id"] == "approval-klient"
    assert blok["status"] == "denied"
    assert blok["decided_by"] == "bjorn"
