from __future__ import annotations

import sqlite3

import pytest

from core.services import proactive_candidates as PC


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "pc.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(PC, "connect", _connect)
    PC._SHOWN.clear()
    return path


def test_add_dedupes_within_24h_and_normalizes_priority(db):
    a = PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="normal")
    b = PC.add_candidate(source="mail_checker", text="ny  mail fra michelle om ios-testen", priority="high")
    assert a["status"] == "added" and b["status"] == "duplicate"
    assert PC.list_pending()[0]["priority"] == "medium"
    assert PC.add_candidate(source="x", text="kort")["status"] == "skipped"


def test_list_orders_by_priority_then_recency(db):
    PC.add_candidate(source="a", text="lav prioritet besked her", priority="low")
    PC.add_candidate(source="b", text="kritisk: mailserveren svarer ikke", priority="critical")
    PC.add_candidate(source="c", text="run-closure: 3 ucommittede filer i repoet", priority="medium")
    assert [c["priority"] for c in PC.list_pending()] == ["critical", "medium", "low"]


def test_relevant_for_and_since_last_line(db):
    PC.add_candidate(source="run_closure_gate", text="autonomt run efterlod 3 ucommittede filer i repoet — auto-commit blokeret", priority="medium")
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="medium")
    line = PC.build_since_last_line("er der stadig ucommittede filer i repoet?", session_id="s1")
    assert line.startswith("Siden sidst") and "ucommittede" in line
    assert PC.build_since_last_line("hvad er vejret?", session_id="s1") == ""
    assert PC.build_since_last_line("hej", session_id="s1") == ""


def test_mentioned_when_answer_overlaps(db):
    PC.add_candidate(source="run_closure_gate", text="autonomt run efterlod 3 ucommittede filer i repoet", priority="medium")
    PC.build_since_last_line("hvad med de ucommittede filer i repoet?", session_id="s2")
    n = PC.mark_mentioned_if_overlap(session_id="s2", answer_text="Ja — det autonome run efterlod 3 ucommittede filer i repoet, jeg committer dem nu.", run_id="r1")
    assert n == 1
    assert PC.counts().get("mentioned") == 1
    assert PC.mark_mentioned_if_overlap(session_id="s2", answer_text="igen") == 0


def test_not_mentioned_when_answer_unrelated(db):
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="medium")
    PC.build_since_last_line("hvad sagde Michelle om iOS testen?", session_id="s3")
    assert PC.mark_mentioned_if_overlap(session_id="s3", answer_text="Vejret bliver fint i morgen.") == 0
    assert PC.counts().get("pending") == 1


def test_bridge_candidates_shape_and_mark_surfaced(db):
    # Kilden var `wakeup_dispatcher` indtil 3/10-2026, hvor telemetri-værnet
    # begyndte at afvise den ved indgangen. Testen skal bruge en ÆGTE kilde,
    # ellers måler den ingenting.
    PC.add_candidate(source="mail_checker", text="Self-wakeup fyrede: morgenbrief-verifikation mangler", priority="high")
    items = PC.bridge_candidates()
    assert items and items[0]["source"] == "proactive_candidates" and items[0]["priority"] == "high"
    assert PC.mark([items[0]["source_id"]], "surfaced") == 1
    assert PC.list_pending() == []


def test_expire_stale(db):
    PC.add_candidate(source="a", text="gammel besked der aldrig blev leveret", priority="low")
    assert PC.expire_stale(days=0) == 1


# ── de tre støj-fixes (3/10-2026) ───────────────────────────────────────


def test_telemetri_afvises_ved_indgangen(db):
    """Self-wakeups og heartbeat-pings er EVENTS, ikke beskeder til Bjørn.

    Målt 3/10: 243 af 311 rækker (78 %) i køen var netop disse to kilder.
    """
    a = PC.add_candidate(source="wakeup_dispatcher", text="Self-wakeup fyrede: resume afbrudt kørsel", priority="high")
    b = PC.add_candidate(source="heartbeat", text="Heartbeat-ping leveret til webchat-session", priority="high")
    assert a["status"] == "skipped" and a["reason"] == "telemetry"
    assert b["status"] == "skipped" and b["reason"] == "telemetry"
    assert PC.counts().get("pending") is None  # intet nåede ind


def test_heartbeat_ping_kind_afvises_uanset_kilde(db):
    assert PC.add_candidate(source="hvad_som_helst", kind="heartbeat_ping",
                            text="en ping formet som en besked")["reason"] == "telemetry"


def test_aegte_kilde_slipper_igennem(db):
    assert PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                            text="Skal natrutinen være en fast regel?")["status"] == "added"
    assert PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle")["status"] == "added"


def test_route_for_og_indgangen_er_enige(db):
    """Ruten og indgangsværnet må ikke sige hver sit om samme kilde."""
    from core.services.outbound_nudges import route_for
    for src, knd in (("wakeup_dispatcher", "other"), ("heartbeat", "heartbeat_ping")):
        assert route_for(source=src, kind=knd) == "telemetry"
        assert PC.er_telemetri(src, knd) is True
    assert route_for(source="mail_checker", kind="other") == "bridge"


def test_samme_kerne_i_ny_ordlyd_er_dublet(db):
    """Skabelonen ændrer sig (tal, ordvalg) — kærnen er den samme.

    Målt 3/10: «natlig sanseregistrering» blev stillet 6 gange, morgenbriefen 5.
    """
    a = PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                         text="Du har bedt om det samme 3 gange fordelt på 2 samtaler: «natlig sanseregistrering». Skal det være en fast regel?")
    b = PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                         text="Du har bedt om det samme 6 gange fordelt på 4 samtaler: «natlig sanseregistrering». Skal det være en fast regel, så du ikke skal bede om det?")
    assert a["status"] == "added"
    assert b["status"] == "duplicate" and b["candidate_id"] == a["candidate_id"]


def test_forskellige_kaerner_er_ikke_dubletter(db):
    PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                     text="Du har bedt om det samme 3 gange: «natlig sanseregistrering». Fast regel?")
    b = PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                         text="Du har bedt om det samme 3 gange: «tjek ucommittede filer i repoet». Fast regel?")
    assert b["status"] == "added"


def test_kind_loft_stopper_det_fjerde(db):
    """Sikkerhedsnettet når ord-sammenligningen ikke rækker (dansk↔engelsk)."""
    for k in ("natlig sanseregistrering", "ucommittede filer i repoet", "middagsmedicin påmindelse"):
        assert PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                                text=f"Du har bedt om det samme 3 gange: «{k}». Fast regel?")["status"] == "added"
    fjerde = PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                              text="Du har bedt om det samme 3 gange: «morgenbrief til Mikkel». Fast regel?")
    assert fjerde["status"] == "skipped" and fjerde["reason"] == "kind-cap"


def test_expire_stale_lukker_surfaced_og_mentioned(db):
    """Et spørgsmål der ER stillet og ikke besvaret må ikke hænge for evigt.

    Målt 3/10: 155 `surfaced` + 118 `mentioned`, den ældste 29 dage gammel,
    og det gamle `expire_stale` ramte kun `pending`.
    """
    a = PC.add_candidate(source="mail_checker", text="en besked der blev vist men aldrig besvaret")
    PC.mark([a["candidate_id"]], "surfaced")
    with PC.connect() as conn:
        conn.execute("UPDATE proactive_candidates SET created_at='2026-08-01T00:00:00+00:00'")
        conn.commit()
    assert PC.expire_stale() == 1
    assert PC.counts().get("expired") == 1
    assert PC.counts().get("surfaced") is None
