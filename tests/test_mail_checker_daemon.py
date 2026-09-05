"""Tests for core/services/mail_checker_daemon.py — særligt støjværnet.

Regressionsværn for 2026-08-30: efter at mailkontoen var blevet misbrugt til en
udsendelse, landede 435 returmails i INBOX. Dæmonen læste dem som "ny mail" og
udløste en push-notifikation, et høj-prioritets nudge og et LLM-kald pr. stk. —
for fire dage gammel maskinstøj. Værnet skal fange alle tre akser: alder, art
og mængde.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import mail_checker_daemon as mcd


# --- ART: bounces og autosvar er maskinstøj -------------------------------

@pytest.mark.parametrize(
    ("sender", "subject"),
    [
        ("Mail Delivery System <MAILER-DAEMON@srvlab.dk>", "Undelivered Mail Returned to Sender"),
        ("Mail Delivery Subsystem <mailer-daemon@googlemail.com>", "Delivery Status Notification (Failure)"),
        ("postmaster@example.com", "Undeliverable: kvartalsrapport"),
        ("Elena <ebudesheim@wintersbros.com>", "Automatic reply: [EXTERNAL] Faktura"),
        ("someone@example.com", "Out of office"),
        ("care@freightwise.com", "Auto Response"),
    ],
)
def test_bounces_and_autoreplies_are_automated(sender: str, subject: str) -> None:
    assert mcd._is_automated(sender, subject) is True


@pytest.mark.parametrize(
    ("sender", "subject"),
    [
        ("Bjørn Slot <onkeladolf@gmail.com>", "hej jarvis!"),
        ("Bjørn Slot <admin@srvlab.dk>", "specs."),
        ("kunde@firma.dk", "Spørgsmål til tilbud"),
        ("", ""),
    ],
)
def test_human_mail_is_not_automated(sender: str, subject: str) -> None:
    assert mcd._is_automated(sender, subject) is False


# --- ALDER: gammel post er ikke "ny" --------------------------------------

def test_old_mail_is_stale() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    four_days_ago = "Wed, 26 Aug 2026 18:58:01 +0200"
    assert mcd._is_stale(four_days_ago, now=now) is True


def test_fresh_mail_is_not_stale() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    an_hour_ago = (now - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    assert mcd._is_stale(an_hour_ago, now=now) is False


def test_mail_just_inside_the_window_is_not_stale() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    edge = (now - timedelta(hours=mcd._MAX_AGE_HOURS - 1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    assert mcd._is_stale(edge, now=now) is False


@pytest.mark.parametrize("header", ["", "ikke en dato", "Mon, 99 Xxx 9999"])
def test_unparseable_date_counts_as_fresh(header: str) -> None:
    """Hellere notificere en gang for meget end tie om ægte post."""
    assert mcd._is_stale(header) is False


def test_naive_date_is_treated_as_utc_not_crash() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    assert mcd._is_stale("Wed, 26 Aug 2026 18:58:01", now=now) is True


# --- MÆNGDE: tærsklen findes og er lav nok til at fange et indbrud --------

def test_flood_threshold_is_configured_low() -> None:
    assert 0 < mcd._FLOOD_THRESHOLD <= 10


def test_age_window_is_a_day() -> None:
    assert mcd._MAX_AGE_HOURS == 24


# --- Selve hændelsen: 435 bounces må ikke give 435 notifikationer ---------

def test_the_real_backlog_is_entirely_silenced() -> None:
    """Præcis den bunke der udløste hændelsen: gamle MAILER-DAEMON-returmails."""
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    backlog = [
        {
            "from": "Mail Delivery System <MAILER-DAEMON@srvlab.dk>",
            "subject": "Undelivered Mail Returned to Sender",
            "date": "Wed, 26 Aug 2026 19:21:24 +0200",
        }
    ] * 435
    noisy = [
        m for m in backlog
        if not mcd._is_automated(m["from"], m["subject"]) and not mcd._is_stale(m["date"], now=now)
    ]
    assert noisy == [], "backloggen må ikke udløse en eneste notifikation"


def test_fresh_human_mail_still_gets_through() -> None:
    """Værnet må ikke gøre dæmonen døv for ægte post."""
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    mail = {
        "from": "Bjørn Slot <onkeladolf@gmail.com>",
        "subject": "kan du lige tjekke noget?",
        "date": (now - timedelta(minutes=5)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
    }
    assert mcd._is_automated(mail["from"], mail["subject"]) is False
    assert mcd._is_stale(mail["date"], now=now) is False


# --- Hele ticket: holder den rent faktisk mund? ---------------------------

class _Recorder:
    """Fanger alt hvad dæmonen ville sende ud."""

    def __init__(self) -> None:
        self.nudges: list[str] = []
        self.notifications: list[str] = []
        self.llm_calls: list[str] = []
        self.replies: list[str] = []


@pytest.fixture()
def sinks(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    rec = _Recorder()
    import core.services.ntfy_gateway as ntfy
    import core.services.outbound_nudges as nudges

    monkeypatch.setattr(nudges, "push_nudge",
                        lambda **kw: rec.nudges.append(kw.get("message", "")), raising=False)
    monkeypatch.setattr(ntfy, "send_notification",
                        lambda **kw: rec.notifications.append(kw.get("title", "")), raising=False)
    monkeypatch.setattr(mcd, "_evaluate_mail",
                        lambda sender, subject, snippet: rec.llm_calls.append(subject) or
                        {"should_respond": False, "urgency": "low", "draft_reply": "", "reason": "test"})
    monkeypatch.setattr(mcd, "_send_auto_reply",
                        lambda **kw: rec.replies.append(kw.get("to_addr", "")) or True)
    monkeypatch.setattr(mcd, "_imap_connect", lambda: object())
    monkeypatch.setattr(mcd, "_mark_as_seen", lambda uids: len(uids))
    monkeypatch.setattr(mcd, "insert_private_brain_record", lambda **kw: None)
    monkeypatch.setattr(mcd.event_bus, "publish", lambda *a, **kw: None)
    # Den delte tilstand (2026-09-05) gaar til den RIGTIGE runtime-state. Uden
    # disse to stubs ville testene skrive deres syntetiske message-ids ind i
    # produktionens seen-liste — og derefter se deres egen post som allerede læst.
    monkeypatch.setattr(mcd, "_load_mail_state", lambda: {})
    monkeypatch.setattr(mcd, "_save_mail_state", lambda **kw: None)
    mcd._seen_ids = set()
    mcd._auto_responded_ids = set()
    return rec


def _mail(n: int, sender: str, subject: str, date: str) -> dict:
    return {"message_id": f"<m{n}@t>", "imap_uid": str(n),
            "from": sender, "subject": subject, "date": date, "snippet": ""}


def test_tick_is_silent_for_the_bounce_backlog(monkeypatch: pytest.MonkeyPatch, sinks: _Recorder) -> None:
    backlog = [_mail(i, "Mail Delivery System <MAILER-DAEMON@srvlab.dk>",
                     "Undelivered Mail Returned to Sender",
                     "Wed, 26 Aug 2026 19:21:24 +0200") for i in range(15)]
    monkeypatch.setattr(mcd, "_fetch_recent", lambda conn, limit=15: backlog)

    out = mcd.tick_mail_checker_daemon()

    assert out["new_count"] == 15
    assert out["quiet_count"] == 15
    assert out["actionable_count"] == 0
    assert sinks.nudges == []
    assert sinks.notifications == []
    assert sinks.llm_calls == [], "en bounce må aldrig koste et LLM-kald"
    assert sinks.replies == []


def test_tick_notifies_once_for_a_flood(monkeypatch: pytest.MonkeyPatch, sinks: _Recorder) -> None:
    now = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")
    flood = [_mail(i, f"afsender{i}@example.com", f"emne {i}", now)
             for i in range(mcd._FLOOD_THRESHOLD + 3)]
    monkeypatch.setattr(mcd, "_fetch_recent", lambda conn, limit=15: flood)

    out = mcd.tick_mail_checker_daemon()

    assert out["flood_suppressed"] is True
    assert len(sinks.nudges) == 1, "ét samlet nudge, ikke ét pr. mail"
    assert len(sinks.notifications) == 1
    assert sinks.llm_calls == [], "et indbrud af post må ikke koste N LLM-kald"


def test_tick_still_reacts_to_a_single_real_mail(monkeypatch: pytest.MonkeyPatch, sinks: _Recorder) -> None:
    now = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")
    monkeypatch.setattr(mcd, "_fetch_recent",
                        lambda conn, limit=15: [_mail(1, "Bjørn <onkeladolf@gmail.com>",
                                                      "kan du tjekke noget?", now)])

    out = mcd.tick_mail_checker_daemon()

    assert out["actionable_count"] == 1
    assert out["flood_suppressed"] is False
    assert len(sinks.nudges) == 1
    assert len(sinks.notifications) == 1
    assert sinks.llm_calls == ["kan du tjekke noget?"]


# ---------------------------------------------------------------------------
# 2026-09-05: tilstanden laa i modul-globaler, og daemonen koerer i en ANDEN
# proces end den der bygger prompten. build_mail_checker_surface() i api'en
# svarede derfor altid last_check_at="" selvom tjekket koerte hvert andet minut.
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta


def _flade(monkeypatch, **felter):
    from core.services import mail_checker_daemon as M

    monkeypatch.setattr(M, "build_mail_checker_surface", lambda: felter)
    return M


def test_delt_tilstand_vinder_over_tomme_globaler(monkeypatch):
    """Netop det api-processen ikke kunne se foer."""
    from core.services import mail_checker_daemon as M

    monkeypatch.setattr(
        M, "_load_mail_state",
        lambda: {"last_check_at": "2026-09-05T10:00:00+00:00", "last_new_count": 2,
                 "last_senders": ["a@b.dk"], "last_subjects": ["Faktura"],
                 "seen_ids": ["x", "y"]},
    )
    ud = M.build_mail_checker_surface()
    assert ud["last_new_count"] == 2
    assert ud["seen_ids_count"] == 2


def test_ingen_ny_post_giver_tom_sektion(monkeypatch):
    M = _flade(monkeypatch, last_new_count=0, last_check_at=datetime.now(UTC).isoformat())
    assert M.mail_awareness_section() == ""


def test_ny_post_naevner_afsender_og_emne(monkeypatch):
    M = _flade(
        monkeypatch,
        last_new_count=2,
        last_check_at=datetime.now(UTC).isoformat(),
        last_senders=["revisor@firma.dk", "kirsten@example.com"],
        last_subjects=["Årsregnskab 2026", "Frokost på fredag?"],
    )
    ud = M.mail_awareness_section()
    assert "[NY POST]" in ud
    assert "revisor@firma.dk" in ud and "Årsregnskab 2026" in ud
    assert "kirsten@example.com" in ud


def test_gammelt_fund_staar_ikke_som_nyt(monkeypatch):
    """Et døgn gammelt tjek må ikke stå i prompten som om posten lige kom."""
    gammel = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    M = _flade(monkeypatch, last_new_count=3, last_check_at=gammel,
               last_senders=["a@b.dk"], last_subjects=["Gammelt"])
    assert M.mail_awareness_section() == ""


def test_sektionen_paaminder_ikke_om_at_tjekke(monkeypatch):
    """Minimum teater: kendsgerninger, ingen opfordring."""
    M = _flade(monkeypatch, last_new_count=1, last_check_at=datetime.now(UTC).isoformat(),
               last_senders=["a@b.dk"], last_subjects=["Emne"])
    ud = M.mail_awareness_section().lower()
    for nag in ("husk", "du bør", "glem ikke", "remember"):
        assert nag not in ud
