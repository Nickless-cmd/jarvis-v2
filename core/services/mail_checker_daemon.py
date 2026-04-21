"""Mail checker daemon — checks jarvis@srvlab.dk inbox for new mail.

Runs on heartbeat cadence. Tracks seen Message-IDs to avoid re-processing.
Publishes events when new mail arrives. Autonomously evaluates and responds
to mails that require action.
"""
from __future__ import annotations

import email as email_lib
import imaplib
import json
import logging
import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.runtime.secrets import mail_config
from core.services.identity_composer import build_identity_preamble
from core.services.daemon_llm import daemon_llm_call

logger = logging.getLogger(__name__)

_seen_ids: set[str] = set()
_last_check_at: datetime | None = None
_last_new_count: int = 0
_last_senders: list[str] = []
_last_subjects: list[str] = []
_MAX_SEEN_IDS = 500

# Auto-responded Message-IDs to avoid duplicate replies
_auto_responded_ids: set[str] = set()
_MAX_RESPONDED_IDS = 200


def _evaluate_mail(sender: str, subject: str, snippet: str) -> dict:
    """Use LLM to evaluate whether a mail needs a response and draft one.

    Returns dict with keys: should_respond (bool), urgency (low/medium/high),
    draft_reply (str or empty), reason (str).
    """
    prompt = (
        f"Du er Jarvis, en AI-assistent der kun kan sende ren tekst-mail.\n"
        f"Du kan IKKE hente data, vedhæfte filer, tjekke kalender, udføre opgaver eller handle på Bjørns vegne.\n"
        f"Du skriver KUN kvitteringssvar for at lade afsenderen vide at mailen er modtaget, eller for at bekræfte noget Bjørn allerede ved.\n\n"
        f"Vurder denne mail:\n"
        f"Afsender: {sender}\n"
        f"Emne: {subject}\n"
        f"Indhold (uddrag): {snippet[:500]}\n\n"
        f"Svar KUN med et JSON-objekt (ingen preamble, ingen markdown-fences):\n"
        f'{{"should_respond": true/false, "urgency": "low/medium/high", '
        f'"reason": "hvorfor", "draft_reply": "dit udkast eller tom streng"}}\n\n'
        f"Regler for should_respond=false (vigtigst):\n"
        f"- Nyhedsbreve, spam, markedsføring, automatiske notifikationer, kvitteringer fra systemer.\n"
        f"- Mails fra jarvis@srvlab.dk, root@srvlab.dk, eller noreply/no-reply-adresser.\n"
        f"- Mails der beder om DATA du skulle hente (vejr, kalender, dokumenter, status).\n"
        f"- Mails der beder om at du UDFØRER en opgave (booke møde, sende fil, logge ind).\n"
        f"- Mails fra Bjørn selv (bs@srvlab.dk) — dem håndterer hovedsystemet.\n"
        f"- Er du i tvivl: should_respond=false.\n\n"
        f"Regler for draft_reply (hvis should_respond=true):\n"
        f"- Skriv KUN kvitteringssvar. Lov ALDRIG noget du ikke selv kan gøre som ren tekst.\n"
        f"- Forbudte formuleringer: 'jeg har sendt', 'vedhæftet', 'her er', 'jeg har tjekket', '[link]', '[data]'.\n"
        f"- Tilladte formuleringer: 'Tak for din mail', 'Bjørn vender tilbage', 'Jeg er tilgængelig', 'bekræftet', 'modtaget'.\n"
        f"- Maks 3-4 linjer. Dansk. Underskriv med 'Jarvis, Bjørns AI-assistent'."
    )
    raw = daemon_llm_call(
        prompt,
        max_len=1200,
        fallback="",
        daemon_name="mail_checker",
    )
    if not raw:
        return {"should_respond": False, "urgency": "low", "draft_reply": "", "reason": "LLM returned empty"}

    # Extract JSON object from LLM output (handles preamble text, markdown fences, trailing garbage)
    def _extract_json_obj(text: str) -> dict | None:
        # Find first '{' and match balanced braces
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    result = _extract_json_obj(raw)
    if result is None:
        logger.warning("mail_checker: could not extract JSON from LLM output: %s", raw[:200])
        return {"should_respond": False, "urgency": "low", "draft_reply": "", "reason": f"JSON extract failed: {raw[:100]}"}
    return {
        "should_respond": bool(result.get("should_respond", False)),
        "urgency": str(result.get("urgency", "low")),
        "draft_reply": str(result.get("draft_reply", "")),
        "reason": str(result.get("reason", "")),
    }


def _send_auto_reply(to_addr: str, subject: str, reply_body: str) -> bool:
    """Send an auto-reply email via SMTP. Returns True on success."""
    try:
        config = mail_config()
        msg = MIMEMultipart()
        msg["From"] = config.user
        msg["To"] = to_addr
        msg["Subject"] = f"Re: {subject}"
        msg["X-Auto-Response"] = "jarvis-auto"
        msg.attach(MIMEText(reply_body, "plain", "utf-8"))

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls()
            server.login(config.user, config.password)
            server.send_message(msg)
        logger.info("mail_checker: Auto-replied to %s re: %s", to_addr, subject)
        return True
    except Exception as e:
        logger.error("mail_checker: Failed to send auto-reply: %s", e)
        return False


def _extract_email_address(sender: str) -> str:
    """Extract bare email address from 'Name <email>' or plain email."""
    if "<" in sender and ">" in sender:
        return sender.split("<")[1].split(">")[0].strip()
    return sender.strip()


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
    global _seen_ids, _last_check_at, _last_new_count, _last_senders, _last_subjects, _auto_responded_ids

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

        # Proactive notification + auto-evaluate for non-self mail
        if "jarvis@srvlab.dk" not in sender and "root@srvlab.dk" not in sender:
            try:
                from core.services.ntfy_gateway import send_notification
                decoded_subject = subject
                if isinstance(subject, bytes):
                    decoded_subject = subject.decode("utf-8", errors="replace")
                send_notification(
                    message=f"Fra: {sender}\nEmne: {decoded_subject}",
                    title="Ny mail",
                    priority="default",
                    tags=["email"],
                )
            except Exception as e:
                logger.warning("mail_checker: ntfy notify failed: %s", e)

            mid = mail.get("message_id", "")
            if mid and mid not in _auto_responded_ids:
                try:
                    evaluation = _evaluate_mail(
                        sender=sender,
                        subject=subject,
                        snippet=mail.get("snippet", ""),
                    )
                    _auto_responded_ids.add(mid)
                    if len(_auto_responded_ids) > _MAX_RESPONDED_IDS:
                        excess = len(_auto_responded_ids) - _MAX_RESPONDED_IDS
                        _auto_responded_ids = set(list(_auto_responded_ids)[excess:])

                    if evaluation.get("should_respond") and evaluation.get("draft_reply"):
                        to_addr = _extract_email_address(sender)
                        reply_sent = _send_auto_reply(
                            to_addr=to_addr,
                            subject=subject,
                            reply_body=evaluation["draft_reply"],
                        )
                        if reply_sent:
                            logger.info(
                                "mail_checker: Auto-replied to %s (urgency=%s, reason=%s)",
                                to_addr, evaluation.get("urgency"), evaluation.get("reason"),
                            )
                            try:
                                from core.services.ntfy_gateway import send_notification
                                send_notification(
                                    message=f"Til: {to_addr}\nEmne: Re: {subject}\nÅrsag: {evaluation.get('reason', '')}",
                                    title="Auto-svar sendt",
                                    priority="low",
                                    tags=["incoming_envelope"],
                                )
                            except Exception:
                                pass
                except Exception as e:
                    logger.warning("mail_checker: Auto-evaluate failed for %s: %s", mid, e)

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
