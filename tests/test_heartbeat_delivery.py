"""Heartbeat-levering: udskillelsens kontrakt og vagten foran leveringen.

`heartbeat_delivery.py` blev skilt ud af `heartbeat_runtime.py` (7.432 linjer)
2/10-2026, fordi de to leveringsfunktioner skulle gennem daemon-vagten i
`notification_bridge`. Foer skrev de direkte med `append_chat_message` og kunne
derfor banke paa midt i en saetning.

Testene her daekker to ting som den oprindelige testfil ikke kan se:

1. **Udskillelsens bagudkompatibilitet.** `heartbeat_runtime` skal stadig
   udstille begge navne, og de skal vaere SAMME objekt som i det nye modul —
   ellers rammer en monkeypatch i én af dem ikke den anden. Praecis den fejl
   (`from X import Y` binder en kopi) kostede tre fejlsoegninger paa ét doegn.
2. **At vagten faktisk staar foran.** En kilde-vagt, fordi leveringen ellers
   kraever hele heartbeat-policy-maskineriet: ingen af de to funktioner maa
   kalde `append_chat_message`, og begge skal kalde
   `send_session_notification` med `push=False`.
"""
from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
import json
import pathlib

from core.services import heartbeat_delivery as hd
from core.services import heartbeat_runtime as hr

KILDE = pathlib.Path("core/services/heartbeat_delivery.py")
LEVERINGSFUNKTIONER = ("_deliver_heartbeat_proposal", "_deliver_heartbeat_ping_directly")


def _indsæt_ejersession(isolated_runtime, session_id: str, owner: str, minutter: int) -> None:
    tidspunkt = (datetime.now(UTC) - timedelta(minutes=minutter)).isoformat()
    with isolated_runtime.db.connect() as conn:
        conn.execute(
            """INSERT INTO chat_sessions
                   (session_id, title, created_at, updated_at, owner_user_id)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, session_id, tidspunkt, tidspunkt, owner),
        )
        if owner:
            conn.execute(
                """INSERT INTO chat_messages
                       (message_id, session_id, role, content, user_id, created_at)
                   VALUES (?, ?, 'user', 'hej', ?, ?)""",
                (f"msg-{session_id}", session_id, owner, tidspunkt),
            )


def _heartbeat_testvagter(monkeypatch, *, pinned: str = "") -> list[str]:
    sendt_til: list[str] = []
    monkeypatch.setattr("core.services.routine_trigger_adapters.cutover_allows", lambda *_a: False)
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "bjorn")
    monkeypatch.setattr("core.services.notification_bridge.get_pinned_session_id", lambda: pinned)
    monkeypatch.setattr("core.services.session_inbox.is_session_active", lambda *_a, **_k: False)
    monkeypatch.setattr(
        "core.services.chat_sessions.get_chat_session",
        lambda sid: {"id": sid} if sid else None,
    )
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification",
        lambda _text, **kw: sendt_til.append(kw["session_id"])
        or {"status": "ok", "message": {"id": "m1"}},
    )
    return sendt_til


def _funktion(navn: str) -> ast.FunctionDef:
    tree = ast.parse(KILDE.read_text())
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == navn:
            return n
    raise AssertionError(f"{navn} findes ikke i {KILDE}")


def test_re_eksporten_er_samme_objekt_ikke_en_kopi():
    """`heartbeat_runtime._deliver_...` skal VAERE funktionen fra det nye modul.

    Er de to forskellige objekter, vil en test der patcher det ene se det andet
    koere videre uaendret — og den slags fejl fejler tavst."""
    for navn in LEVERINGSFUNKTIONER:
        assert hasattr(hr, navn), f"{navn} er ikke re-eksporteret fra heartbeat_runtime"
        assert getattr(hr, navn) is getattr(hd, navn), navn


def test_ingen_af_leveringsfunktionerne_skriver_direkte_laengere():
    """Hele formaalet med flytningen. Et `append_chat_message` her ville
    omgaa daemon-vagten og kunne lande midt i Bjoerns saetning."""
    for navn in LEVERINGSFUNKTIONER:
        tekst = ast.unparse(_funktion(navn))
        assert "append_chat_message" not in tekst, (
            f"{navn} skriver stadig direkte i sessionen"
        )


def test_begge_leverer_gennem_vagten_uden_at_tilfoeje_push():
    """`push=False` er ikke pynt: ingen af de to sendte mobil-push foer, og
    flytningen maatte ikke give Bjoern to nye push-kilder."""
    for navn in LEVERINGSFUNKTIONER:
        fn = _funktion(navn)
        kald = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and (getattr(n.func, "attr", None) or getattr(n.func, "id", None))
            == "send_session_notification"
        ]
        assert len(kald) == 1, f"{navn} kalder vagten {len(kald)} gange, forventede én"
        kw = {k.arg: ast.unparse(k.value) for k in kald[0].keywords if k.arg}
        assert kw.get("push") == "False", f"{navn} ville tilfoeje en push: {kw}"
        assert "session_id" in kw, (
            f"{navn} sender ikke sin egen session med — vagten ville saa vaelge "
            "en ANDEN samtale end i dag"
        )


def test_status_laeses_med_hjaelperen_og_ikke_som_lighed_med_ok():
    """«queued» ER en succes. Et `status == "ok"` her ville genindfoere
    dobbelt-leveringen fra 23/9-2026, hvor morgenbriefen blev koeet og
    run'et laeste det som «webchat nede» og tog Discord-noedplanen."""
    for navn in LEVERINGSFUNKTIONER:
        tekst = ast.unparse(_funktion(navn))
        assert "delivery_succeeded" in tekst, f"{navn} tjekker ikke status via hjaelperen"
        assert '== \'ok\'' not in tekst, f"{navn} sammenligner status med 'ok'"


def test_ping_historikken_fejler_mod_tom_og_ikke_mod_en_undtagelse():
    """`_recent_ping_history` slaar op i heartbeat_runtime ved kaldetid (en
    modul-import ville vaere cirkulaer). Fejler opslaget, skal den give en tom
    historik — en undtagelse midt i en levering ville vaere vaerre end et
    manglende dublet-tjek."""
    import core.services.heartbeat_runtime as rigtig

    gammel = rigtig._recent_ping_history

    def _sprael(**_k):
        raise RuntimeError("DB nede")

    rigtig._recent_ping_history = _sprael
    try:
        assert hd._recent_ping_history(limit=3) == []
    finally:
        rigtig._recent_ping_history = gammel


def test_proposal_afviser_fremmed_pin_og_vaelger_ejerens_session(
    isolated_runtime, monkeypatch,
):
    _indsæt_ejersession(isolated_runtime, "chat-bjorn", "bjorn", 10)
    _indsæt_ejersession(isolated_runtime, "chat-mikkel", "mikkel", 1)
    sendt_til = _heartbeat_testvagter(monkeypatch, pinned="chat-mikkel")

    svar = hd._deliver_heartbeat_proposal(
        policy={"ping_channel": "webchat"},
        tick_id="tick-1",
        summary="Et konkret forslag",
        proposed_action="Et konkret forslag",
    )

    assert svar["status"] == "sent"
    assert sendt_til == ["chat-bjorn"]
    assert json.loads(svar["artifact"])["session_id"] == "chat-bjorn"


def test_ping_ignorerer_nyere_fremmed_session(isolated_runtime, monkeypatch):
    _indsæt_ejersession(isolated_runtime, "chat-bjorn", "bjorn", 10)
    _indsæt_ejersession(isolated_runtime, "chat-mikkel", "mikkel", 1)
    sendt_til = _heartbeat_testvagter(monkeypatch)
    monkeypatch.setattr(hd, "_recent_ping_history", lambda **_k: [])
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: type("Settings", (), {"nudge_system_enabled": False})(),
    )

    svar = hd._deliver_heartbeat_ping_directly(
        policy={"allow_ping": True, "kill_switch": "enabled", "ping_channel": "webchat"},
        tick_id="tick-2",
        ping_text="Jeg fandt noget konkret at følge op på.",
        summary="Et konkret ping",
    )

    assert svar["status"] == "sent"
    assert sendt_til == ["chat-bjorn"]
    assert json.loads(svar["artifact"])["session_id"] == "chat-bjorn"


def test_heartbeat_uden_ejerstemplet_session_skriver_intet(
    isolated_runtime, monkeypatch,
):
    _indsæt_ejersession(isolated_runtime, "chat-mikkel", "mikkel", 1)
    sendt_til = _heartbeat_testvagter(monkeypatch, pinned="chat-mikkel")
    monkeypatch.setattr(hd, "_recent_ping_history", lambda **_k: [])

    proposal = hd._deliver_heartbeat_proposal(
        policy={"ping_channel": "webchat"}, tick_id="tick-3",
        summary="Forslag", proposed_action="Forslag",
    )
    ping = hd._deliver_heartbeat_ping_directly(
        policy={"allow_ping": True, "kill_switch": "enabled", "ping_channel": "webchat"},
        tick_id="tick-4", ping_text="Et specifikt nyt ping.", summary="Ping",
    )

    assert proposal["blocked_reason"] == "missing-webchat-session"
    assert ping["blocked_reason"] == "missing-webchat-session"
    assert sendt_til == []
