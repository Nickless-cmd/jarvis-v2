"""Mail checker daemon — checks jarvis@srvlab.dk inbox for new mail.

Runs on heartbeat cadence. Tracks seen Message-IDs to avoid re-processing.
Publishes events when new mail arrives.
"""
from __future__ import annotations

import email as email_lib
import imaplib
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.runtime.secrets import mail_config
from core.services.identity_composer import build_identity_preamble

_seen_ids: set[str] = set()
_last_check_at: datetime | None = None
_last_new_count: int = 0
_last_senders: list[str] = []
_last_subjects: list[str] = []
_MAX_SEEN_IDS = 500


def _imap_connect():
    """Return an open IMAP connection."""
    config = mail_config()
    conn = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
    conn.login(config.user, config.password)
    conn.select("INBOX")
    return conn


def _fetch_recent(conn, limit: int = 10) -> list[dict]:
    """Fetch up to `limit` most recent emails."""
    _, ids = conn.search(None, "ALL")
    if not ids[0]:
        return []
    mail_ids = ids[0].split()
    mails = []
    for i in mail_ids[-limit:]:
        _, data = conn.fetch(i, "(RFC822)")
        msg = email_lib.message_from_bytes(data[0][1])
        message_id = msg.get("Message-ID", "") or str(uuid4())
        snippet = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        snippet = payload.decode("utf-8", errors="replace")[:300]
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                snippet = payload.decode("utf-8", errors="replace")[:300]
        mails.append({
            "message_id": message_id,
            "from": msg.get("From", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "snippet": snippet,
        })
    return mails


def tick_mail_checker_daemon() -> dict[str, object]:
    """Main daemon tick — check for new mail, publish events for unseen messages."""
    global _seen_ids, _last_check_at, _last_new_count, _last_senders, _last_subjects

    new_mails: list[dict] = []
    try:
        conn = _imap_connect()
        try:
            recent = _fetch_recent(conn, limit=15)
        finally:
            try:
                conn.close()
                conn.logout()
            except Exception:
                pass

        for mail in recent:
            mid = mail.get("message_id", "")
            if mid and mid not in _seen_ids:
                new_mails.append(mail)
                _seen_ids.add(mid)

        # Trim seen set to prevent unbounded growth
        if len(_seen_ids) > _MAX_SEEN_IDS:
            excess = len(_seen_ids) - _MAX_SEEN_IDS
            _seen_ids = set(list(_seen_ids)[excess:])

    except Exception as e:
        return {"checked": False, "error": str(e)}

    _last_check_at = datetime.now(UTC)
    _last_new_count = len(new_mails)
    _last_senders = [m.get("from", "") for m in new_mails]
    _last_subjects = [m.get("subject", "") for m in new_mails]

    # Publish event for each new mail + proactive notification
    for mail in new_mails:
        sender = mail.get("from", "")
        subject = mail.get("subject", "")
        try:
            event_bus.publish(
                "mail_checker.new_mail",
                {
                    "from": sender,
                    "subject": subject,
                    "date": mail.get("date", ""),
                    "snippet": mail.get("snippet", "")[:200],
                },
            )
        except Exception:
            pass

        # Proactive notification for non-self mail
        if "jarvis@srvlab.dk" not in sender and "root@srvlab.dk" not in sender:
            try:
                from core.services.notification_helpers import send_ntfy_notification
                decoded_subject = subject
                if isinstance(subject, bytes):
                    decoded_subject = subject.decode("utf-8", errors="replace")
                send_ntfy_notification(
                    title="📧 Ny mail",
                    message=f"Fra: {sender}\nEmne: {decoded_subject}",
                    priority="default",
                )
            except Exception:
                pass

    # If new mail, store private brain record
    if new_mails:
        summary = f"{len(new_mails)} ny mail fra {', '.join(_last_senders[:3])}"
        try:
            insert_private_brain_record(
                record_id=f"pb-mail-{uuid4().hex[:12]}",
                record_type="mail-arrival",
                layer="private_brain",
                session_id="heartbeat",
                run_id=f"mail-checker-{uuid4().hex[:12]}",
                focus="ny mail",
                summary=summary,
                detail=", ".join(_last_subjects[:5]),
                source_signals="mail-checker-daemon:heartbeat",
                confidence="high",
                created_at=_last_check_at.isoformat(),
            )
        except Exception:
            pass

    return {
        "checked": True,
        "new_count": len(new_mails),
        "senders": _last_senders,
        "subjects": _last_subjects,
    }


def build_mail_checker_surface() -> dict[str, object]:
    """Return surface state for heartbeat context."""
    return {
        "last_check_at": _last_check_at.isoformat() if _last_check_at else "",
        "last_new_count": _last_new_count,
        "last_senders": list(_last_senders),
        "last_subjects": list(_last_subjects),
        "seen_ids_count": len(_seen_ids),
    }


def get_latest_mail_info() -> dict[str, object]:
    """Return latest check info for other consumers."""
    return {
        "new_count": _last_new_count,
        "senders": list(_last_senders),
        "subjects": list(_last_subjects),
        "last_check_at": _last_check_at.isoformat() if _last_check_at else "",
    }
