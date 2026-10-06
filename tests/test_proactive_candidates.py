from __future__ import annotations

import sqlite3

import pytest

from core.services import proactive_candidates as PC

BJOERN = "1246415163603816499"
MICHELLE = "1313522677369143429"


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "pc.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(PC, "connect", _connect)
    # Ingen bruger i konteksten som udgangspunkt: en test der vil måle
    # kontekst-opslaget sætter den selv. Uden dette ville testene arve den
    # kørende proces' kontekst og måle noget andet end de tror.
    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: "", raising=False,
    )
    monkeypatch.setattr(
        "core.identity.workspace_context.current_session_id", lambda: "", raising=False,
    )
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
    PC.add_candidate(source="c", text="webserveren svarer ikke paa port 80", priority="medium")
    assert [c["priority"] for c in PC.list_pending()] == ["critical", "medium", "low"]


def test_relevant_for_and_since_last_line(db):
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen",
                     priority="medium", user_id=BJOERN)
    PC.add_candidate(source="scheduled_task", text="Påmindelse om tandlægetid på torsdag",
                     priority="medium", user_id=BJOERN)
    line = PC.build_since_last_line("hvad skrev Michelle om iOS-testen?", session_id="s1", user_id=BJOERN)
    assert line.startswith("Siden sidst") and "Michelle" in line
    assert PC.build_since_last_line("hvad er vejret?", session_id="s1", user_id=BJOERN) == ""
    assert PC.build_since_last_line("hej", session_id="s1", user_id=BJOERN) == ""


def test_mentioned_when_answer_overlaps(db):
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen",
                     priority="medium", user_id=BJOERN)
    PC.build_since_last_line("hvad skrev Michelle om iOS-testen?", session_id="s2", user_id=BJOERN)
    n = PC.mark_mentioned_if_overlap(
        session_id="s2",
        answer_text="Michelle skrev om iOS-testen — hun spørger til beta-versionen.",
        run_id="r1",
    )
    assert n == 1
    assert PC.counts().get("mentioned") == 1
    assert PC.mark_mentioned_if_overlap(session_id="s2", answer_text="igen") == 0


def test_not_mentioned_when_answer_unrelated(db):
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="medium")
    PC.build_since_last_line("hvad skrev Michelle om iOS-testen?", session_id="s3", user_id=BJOERN)
    assert PC.mark_mentioned_if_overlap(session_id="s3", answer_text="Vejret bliver fint i morgen.") == 0
    assert PC.counts().get("pending") == 1


def test_bridge_candidates_shape_and_mark_surfaced(db):
    # Kilden var `wakeup_dispatcher` indtil 3/10-2026, hvor telemetri-værnet
    # begyndte at afvise den ved indgangen. Testen skal bruge en ÆGTE kilde,
    # ellers måler den ingenting.
    PC.add_candidate(source="mail_checker", text="Self-wakeup fyrede: morgenbrief-verifikation mangler",
                     priority="high", user_id=BJOERN)
    items = PC.bridge_candidates(BJOERN)
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


# ── bruger-dimensionen (bygget 6/10-2026, Bjørn) ────────────────────────
#
# Køen var GLOBAL: 312 rækker, ingen `user_id`-kolonne. Leverings-vejen
# matchede på TEKST-overlap, ikke på ejerskab — «Alarm: Bjørn skal til møde
# med Line» var en kandidat for enhver der skrev ordet «møde». Fem brugere
# deler runtime'en, og hver har sit eget workspace.


def test_en_anden_brugers_kandidat_vises_ikke(db):
    """Kernen i fixet: overlap er ikke ejerskab.

    Bjørns jobcenter-aftale matcher Michelles besked på ALLE tre ord — den
    gamle matchning ville have vist den til hende. Nu kræver visningen at
    brugeren ER den samme.
    """
    tekst = "Alarm: Bjørn skal til møde med Line på Jobcenteret i dag"
    PC.add_candidate(source="scheduled_task", user_id=BJOERN, text=tekst)
    # Michelles besked deler {møde, line, dag} med kandidaten — fuld dækning.
    assert PC.relevant_for("møde med Line i dag?", user_id=MICHELLE) == []
    assert PC.build_since_last_line("møde med Line i dag?", session_id="m1", user_id=MICHELLE) == ""
    # ... og den vises for den den tilhører.
    line = PC.build_since_last_line("møde med Line i dag?", session_id="b1", user_id=BJOERN)
    assert "Jobcenteret" in line


def test_interne_kandidater_vises_aldrig(db):
    """`''` = intern. Telemetri hører i Centralen, ikke i en samtale."""
    PC.add_candidate(source="autonomous_run",
                     text="run efterlod 5 ucommittede filer i arbejdstræet", user_id="")
    c = PC.list_pending()[0]
    assert c["user_id"] == ""
    # Teksten dækker beskeden 100 % — den er bare ikke til nogen.
    assert PC.relevant_for("hvad med de ucommittede filer i arbejdstræet?", user_id=BJOERN) == []
    assert PC.build_since_last_line("hvad med de ucommittede filer i arbejdstræet?",
                                    session_id="x", user_id="") == ""


def test_uden_bruger_vises_intet(db):
    """Ingen bruger = ingen visning. «Hvem som helst» er ikke en modtager."""
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", user_id=BJOERN)
    assert PC.relevant_for("hvad skrev Michelle om iOS-testen?", user_id="") == []
    assert PC.build_since_last_line("hvad skrev Michelle om iOS-testen?",
                                    session_id="x", user_id="") == ""
    assert PC.bridge_candidates("") == []


def test_ejeren_afgoeres_ved_indgangen(db, monkeypatch):
    """Eksplicit → current_user_id() → session-ejer → '' (intern)."""
    # 1) eksplicit vinder
    a = PC.add_candidate(source="mail_checker", text="mail fra Michelle om iOS", user_id=MICHELLE)
    assert a["status"] == "added"
    assert [c["user_id"] for c in PC.list_pending() if c["candidate_id"] == a["candidate_id"]] == [MICHELLE]

    # 2) current_user_id() når intet gives
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: BJOERN, raising=False)
    b = PC.add_candidate(source="mail_checker", text="vejret i Svendborg i morgen tidlig")
    assert b["status"] == "added"
    assert [c["user_id"] for c in PC.list_pending() if c["candidate_id"] == b["candidate_id"]] == [BJOERN]

    # 3) session-ejeren når current_user_id() er tom — owner har OFTE tom
    #    current_user_id() inde i run-generatoren, så dette led er ikke pynt.
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "", raising=False)
    monkeypatch.setattr(
        "core.services.chat_sessions.get_session_owner",
        lambda sid: MICHELLE if sid == "sess-m" else "", raising=False,
    )
    monkeypatch.setattr("core.identity.workspace_context.current_session_id", lambda: "sess-m", raising=False)
    c = PC.add_candidate(source="scheduled_task", text="påmindelse om tandlægetid på torsdag")
    assert c["status"] == "added"
    assert [x["user_id"] for x in PC.list_pending() if x["candidate_id"] == c["candidate_id"]] == [MICHELLE]


def test_session_id_parameter_taeller_naar_contextvar_er_tom(db, monkeypatch):
    """Prompt-byggeren kender sessionen som PARAMETER. Er contextvar'en tom,
    skal den parameter stadig kunne afgøre ejeren — ellers ville kandidaten
    blive «intern» midt i en samtale den hører til."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "", raising=False)
    monkeypatch.setattr("core.identity.workspace_context.current_session_id", lambda: "", raising=False)
    monkeypatch.setattr(
        "core.services.chat_sessions.get_session_owner",
        lambda sid: BJOERN if sid == "sess-b" else "", raising=False,
    )
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", user_id=BJOERN)
    assert PC.build_since_last_line("hvad skrev Michelle om iOS-testen?",
                                    session_id="sess-b", user_id=None).startswith("Siden sidst")


def test_interne_kilder_tvinger_tom_uanset_kontekst(db, monkeypatch):
    """Et autonomt run kan have en session — men dets telemetri er ikke en
    besked til den der ejer sessionen."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: BJOERN, raising=False)
    r = PC.add_candidate(source="run_closure_gate", text="run efterlod 3 ucommittede filer i repoet")
    assert r["status"] == "added"
    assert [c["user_id"] for c in PC.list_pending() if c["candidate_id"] == r["candidate_id"]] == [""]


def test_migrering_tilfoejer_kolonnen_paa_en_gammel_db(db):
    """En DB skabt før 6/10 har ingen `user_id`. `ensure_table` skal lægge den
    til — og kolonnen skal ligge SIDST, så `_row`s tuple-gren læser rigtigt."""
    with PC.connect() as conn:
        conn.execute(
            """
            CREATE TABLE proactive_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL,
                norm_text TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                surfaced_at TEXT NOT NULL DEFAULT '',
                mentioned_run_id TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            "INSERT INTO proactive_candidates (candidate_id, source, kind, text, norm_text, priority, "
            "status, created_at, updated_at) VALUES ('pc-gammel','mail_checker','','gammel raekke uden ejer',"
            "'gammel raekke uden ejer','medium','pending','2026-10-01T00:00:00+00:00','2026-10-01T00:00:00+00:00')"
        )
        conn.commit()
    r = PC.list_pending()
    assert len(r) == 1 and r[0]["user_id"] == ""  # migreret, ikke gættet
    # Og en ny række kan sætte den.
    PC.add_candidate(source="mail_checker", text="helt anden tekst om tandlaege", user_id=BJOERN)
    assert {c["user_id"] for c in PC.list_pending()} == {"", BJOERN}


def test_per_user_overflade_taeller_interne_for_sig(db):
    PC.add_candidate(source="mail_checker", text="Bjørns egen besked her", user_id=BJOERN)
    PC.add_candidate(source="autonomous_run", text="intern telemetri om et run", user_id="")
    assert PC.counts_per_user() == {"(intern)": 1, BJOERN: 1}


def test_add_candidate_tager_sessionen_naar_konteksten_er_tom(db, monkeypatch):
    """Run-slut-vejen: `current_user_id()` er tom, men kalderen har sessionen.

    `repeated_requests.surface_matured` kaldes fra
    `end_of_run_memory_consolidation` og giver nu sin `session_id` videre.
    Uden den blev regel-forslaget mærket «internt» og aldrig vist.
    """
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "", raising=False)
    monkeypatch.setattr("core.identity.workspace_context.current_session_id", lambda: "", raising=False)
    monkeypatch.setattr(
        "core.services.chat_sessions.get_session_owner",
        lambda sid: BJOERN if sid == "sess-run" else "", raising=False,
    )
    r = PC.add_candidate(source="repeated_requests", kind="rule_proposal:request",
                         text="Skal natrutinen være en fast regel?", session_id="sess-run")
    assert r["status"] == "added"
    assert [c["user_id"] for c in PC.list_pending() if c["candidate_id"] == r["candidate_id"]] == [BJOERN]
    # ... og uden sessionen ville den være intern — det er den sikre default.
    # (Anden kind: ellers fanger kærne-dubletten den som samme spørgsmål.)
    r2 = PC.add_candidate(source="repeated_requests", kind="rule_proposal:correction",
                          text="Skal tandlægetiden ligge fast om torsdagen?")
    assert r2["status"] == "added"
    assert [c["user_id"] for c in PC.list_pending() if c["candidate_id"] == r2["candidate_id"]] == [""]
