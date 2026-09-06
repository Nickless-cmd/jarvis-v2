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
from typing import Any
import re
import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
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

# --- Støjværn -------------------------------------------------------------
# Dæmonen læser INBOX med SEARCH UNSEEN. Den har ingen anelse om ALDER eller
# ART, så enhver ulæst mail er "ny mail" der udløser push-notifikation,
# høj-prioritets nudge OG et LLM-kald.
#
# 2026-08-26 blev kontoen misbrugt til en udsendelse. Returmailsene landede i
# INBOX: 435 ulæste bounces. Dæmonen begyndte at behandle dem 15 ad gangen som
# "ny mail" — dvs. ~435 notifikationer og ~435 LLM-kald fordelt over to døgn,
# for post der var fire dage gammel og udelukkende bestod af MAILER-DAEMON.
#
# Tre værn, i den rækkefølge de rammer:
#   1. ALDER   — post ældre end _MAX_AGE_HOURS er ikke "ny". Markeres læst, ellers tavs.
#   2. ART     — bounces og autosvar er maskinstøj: hverken notifikation eller LLM.
#   3. MÆNGDE  — flere end _FLOOD_THRESHOLD ægte nye mails i ét tick er et
#                unormalt indbrud af post. Så ét samlet varsel i stedet for N,
#                og ingen LLM-vurdering i det tick.
# Alle tre markerer stadig posten som læst, så backloggen ikke bygger sig op igen.
_MAX_AGE_HOURS = 24
_FLOOD_THRESHOLD = 5

_AUTOMATED_RE = re.compile(
    r"mailer.?daemon|postmaster@|delivery (status|subsystem)|undeliver"
    r"|returned mail|automatic reply|out of office|auto.?response|auto.?reply",
    re.IGNORECASE,
)


def _is_automated(sender: str, subject: str) -> bool:
    """True for bounces og autosvar — maskinstøj, ikke post der skal svares på."""
    return bool(_AUTOMATED_RE.search(sender or "") or _AUTOMATED_RE.search(subject or ""))


def _is_stale(date_header: str, now: datetime | None = None) -> bool:
    """True hvis mailen er ældre end _MAX_AGE_HOURS.

    Et ulæselig/manglende Date-felt regnes som FRISK — vi vil hellere notificere
    en gang for meget end tie om ægte post.
    """
    if not date_header:
        return False
    try:
        sent = parsedate_to_datetime(date_header)
    except (TypeError, ValueError):
        return False
    if sent is None:
        return False
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=UTC)
    age = (now or datetime.now(UTC)) - sent
    return age.total_seconds() > _MAX_AGE_HOURS * 3600


def _evaluate_mail(sender: str, subject: str, snippet: str) -> dict:
    """Use LLM to evaluate whether a mail needs a response and draft one.

    Returns dict with keys: should_respond (bool), urgency (low/medium/high),
    draft_reply (str or empty), reason (str).
    """
    prompt = (
        f"RESPOND WITH JSON ONLY. NO TEXT BEFORE OR AFTER THE JSON OBJECT.\n"
        f"DO NOT WRITE ANY SENTENCES. DO NOT EXPLAIN. OUTPUT EXACTLY THIS FORMAT:\n"
        f'{{"should_respond": false, "urgency": "low", "reason": "spam", "draft_reply": ""}}\n\n'
        f"You are Jarvis, Bjorn's AI assistant. Evaluate this email:\n"
        f"Sender: {sender}\n"
        f"Subject: {subject}\n"
        f"Snippet: {snippet[:500]}\n\n"
        f"should_respond=false for: newsletters, spam, marketing, system notifications, "
        f"mails from jarvis@srvlab.dk or root@srvlab.dk, mails asking you to fetch data "
        f"(weather, calendar, documents), mails asking you to perform tasks, "
        f"mails from Bjorn himself (bs@srvlab.dk). When in doubt: false.\n\n"
        f"should_respond=true ONLY for: real humans who need a simple acknowledgment receipt.\n"
        f"If true, draft_reply must be a short Danish acknowledgment (2-3 lines max), "
        f"signed 'Jarvis, Bjorns AI-assistent'. Never promise data, files, or actions.\n\n"
        f"OUTPUT ONE JSON OBJECT. NOTHING ELSE:"
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
    """Fetch up to `limit` most recent UNSEEN emails.

    Uses BODY.PEEK so fetching does NOT mark mails as \\Seen — we only do that
    explicitly via _mark_as_seen after Jarvis has processed each mail.
    """
    _, ids = conn.search(None, "UNSEEN")
    if not ids[0]:
        return []
    mail_ids = ids[0].split()
    mails = []
    for i in mail_ids[-limit:]:
        _, data = conn.fetch(i, "(BODY.PEEK[])")
        if not data or not data[0]:
            continue
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
            "imap_uid": i.decode("ascii") if isinstance(i, bytes) else str(i),
            "from": msg.get("From", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "snippet": snippet,
        })
    return mails


def _mark_as_seen(imap_uids: list[str]) -> int:
    """Mark the given IMAP message IDs as \\Seen. Returns count successfully marked."""
    if not imap_uids:
        return 0
    marked = 0
    try:
        conn = _imap_connect()
        try:
            for uid in imap_uids:
                try:
                    conn.store(uid, "+FLAGS", "\\Seen")
                    marked += 1
                except Exception as e:
                    logger.warning("mail_checker: failed to mark %s as seen: %s", uid, e)
        finally:
            try:
                conn.close()
                conn.logout()
            except Exception:
                pass
    except Exception as e:
        logger.warning("mail_checker: IMAP reconnect for mark-seen failed: %s", e)
    return marked



# ── Tilstand paa tvaers af processer ──────────────────────────────────────
#
# 2026-09-05: `_last_check_at` m.fl. var modul-globaler. Daemonen koerer i
# jarvis-runtime, men prompten bygges i jarvis-api — to processer, hver sit sæt
# globaler. `build_mail_checker_surface()` i api'en svarede derfor ALTID
# `last_check_at: ""` selvom tjekket koerte hvert andet minut. Ingen kunne se at
# posten var tjekket, og intet downstream kunne bruge resultatet.
#
# `_seen_ids` havde samme problem med en ekstra tand: den nulstilledes ved hver
# genstart, saa al post saa ny ud igen.
#
# Tilstanden ligger nu i runtime-state, som begge processer deler.

_MAIL_STATE_KEY = "mail_checker.state"


def _load_mail_state() -> dict[str, Any]:
    """Laes delt tilstand. Self-safe: tom dict ved enhver fejl."""
    try:
        from core.runtime.db import get_runtime_state_value
        data = get_runtime_state_value(_MAIL_STATE_KEY)
        return dict(data) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_mail_state(*, check_at: str, new_count: int, senders: list[str],
                     subjects: list[str], seen_ids: set[str]) -> None:
    """Skriv delt tilstand. Self-safe: en fejl her maa ikke vaelte tick'et."""
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_MAIL_STATE_KEY, {
            "last_check_at": check_at,
            "last_new_count": int(new_count),
            "last_senders": list(senders)[:10],
            "last_subjects": list(subjects)[:10],
            "seen_ids": list(seen_ids)[-_MAX_SEEN_IDS:],
        })
    except Exception as exc:
        logger.debug("mail_checker: kunne ikke gemme delt tilstand: %s", exc)


def tick_mail_checker_daemon() -> dict[str, object]:
    """Main daemon tick — check for new mail, publish events for unseen messages."""
    global _seen_ids, _last_check_at, _last_new_count, _last_senders, _last_subjects, _auto_responded_ids

    # Hent den DELTE seen-liste, saa en genstart ikke faar al post til at se ny ud
    # og saa to processer ikke danner hver sin sandhed.
    _delt = _load_mail_state()
    _gemt_seen = _delt.get("seen_ids")
    if isinstance(_gemt_seen, list) and _gemt_seen:
        _seen_ids = set(_seen_ids) | {str(x) for x in _gemt_seen}

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
    _save_mail_state(
        check_at=_last_check_at.isoformat(), new_count=_last_new_count,
        senders=_last_senders, subjects=_last_subjects, seen_ids=_seen_ids,
    )

    # Del posten op FØR vi larmer: kun frisk, menneskelig post fortjener en
    # notifikation, et nudge og et LLM-kald. Resten markeres blot læst.
    actionable: list[dict] = []
    quiet: list[dict] = []
    for mail in new_mails:
        is_quiet = _is_automated(
            mail.get("from", ""), mail.get("subject", "")
        ) or _is_stale(mail.get("date", ""))
        mail["quiet"] = is_quiet
        (quiet if is_quiet else actionable).append(mail)

    flooded = len(actionable) > _FLOOD_THRESHOLD
    if quiet:
        logger.info(
            "mail_checker: %d ny(e) mail(s) tavse (bounce/autosvar eller ældre end %dt)",
            len(quiet), _MAX_AGE_HOURS,
        )
    if flooded:
        # Et indbrud af post er én begivenhed, ikke N. Ét varsel, ingen LLM.
        logger.warning(
            "mail_checker: %d nye mails i ét tick (grænse %d) — samlet varsel, "
            "ingen per-mail vurdering", len(actionable), _FLOOD_THRESHOLD,
        )
        try:
            from core.services.outbound_nudges import push_nudge
            push_nudge(
                source="mail_checker",
                kind="other",
                message=f"{len(actionable)} nye mails på én gang — usædvanligt meget post",
                importance="high",
            )
        except Exception:
            pass
        try:
            from core.services.ntfy_gateway import send_notification
            send_notification(
                message=f"{len(actionable)} nye mails på én gang. Tjek indbakken.",
                title="Usædvanlig meget post",
                priority="default",
                tags=["email"],
            )
        except Exception as e:
            logger.warning("mail_checker: ntfy notify failed: %s", e)

    # Publish event for each new mail + proactive notification
    for mail in new_mails:
        sender = mail.get("from", "")
        subject = mail.get("subject", "")
        noisy_ok = not mail.get("quiet") and not flooded
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

        # Push nudge so Jarvis sees new mail in awareness prompt
        if noisy_ok:
            try:
                from core.services.outbound_nudges import push_nudge
                push_nudge(
                    source="mail_checker",
                    kind="other",
                    message=f"Ny mail fra {sender}: {subject}",
                    importance="high",
                )
            except Exception:
                pass

        # Proactive notification + auto-evaluate for non-self mail
        if noisy_ok and "jarvis@srvlab.dk" not in sender and "root@srvlab.dk" not in sender:
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

    # Mark processed mails as \Seen on the IMAP server so the user's mail
    # client reflects that Jarvis has already read and handled them.
    processed_uids = [str(m.get("imap_uid")) for m in new_mails if m.get("imap_uid")]
    marked = _mark_as_seen(processed_uids) if processed_uids else 0

    return {
        "checked": True,
        "new_count": len(new_mails),
        "senders": _last_senders,
        "subjects": _last_subjects,
        "marked_seen": marked,
        # Støjværnets arbejde, så det kan ses i registry/diagnostik
        "actionable_count": len(actionable),
        "quiet_count": len(quiet),
        "flood_suppressed": flooded,
    }


def build_mail_checker_surface() -> dict[str, object]:
    """Return surface state for heartbeat context.

    Laeser DELT tilstand foerst: daemonen koerer i en anden proces end den der
    bygger prompten, saa modul-globalerne her er tomme i api-processen.
    """
    delt = _load_mail_state()
    if delt.get("last_check_at"):
        return {
            "last_check_at": str(delt.get("last_check_at") or ""),
            "last_new_count": int(delt.get("last_new_count") or 0),
            "last_senders": list(delt.get("last_senders") or []),
            "last_subjects": list(delt.get("last_subjects") or []),
            "seen_ids_count": len(delt.get("seen_ids") or []),
        }
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


# Hvor gammelt et tjek maa vaere foer det ikke laengere er "nu". Uden dette ville
# et doegn gammelt fund staa i prompten som om posten lige var kommet.
_MAIL_FRESH_HOURS = 12


def mail_awareness_section() -> str:
    """Ny post som en KENDSGERNING i prompten. "" naar der intet er.

    Beslutningen «tjek mails ved ny session og orientér Bjørn» stod paa 0,03 i
    adherence — et ritual han skulle huske. Daemonen tjekker i forvejen hvert
    andet minut i cluster_infra; det der manglede var at resultatet naaede ham.
    Nu staar det der naar der ER noget, og tier naar der ikke er.

    Ingen opfordring, ingen paamindelse. Kun hvem der har skrevet og om hvad.
    """
    try:
        flade = build_mail_checker_surface()
    except Exception:
        return ""

    antal = int(flade.get("last_new_count") or 0)
    if antal <= 0:
        return ""

    tjekket = str(flade.get("last_check_at") or "")
    if not tjekket:
        return ""
    try:
        da = datetime.fromisoformat(tjekket.replace("Z", "+00:00")).astimezone(UTC)
        timer = (datetime.now(UTC) - da).total_seconds() / 3600.0
    except Exception:
        return ""
    if timer > _MAIL_FRESH_HOURS:
        return ""

    afsendere = [str(x) for x in (flade.get("last_senders") or [])]
    emner = [str(x) for x in (flade.get("last_subjects") or [])]
    linjer = ["[NY POST] %d ny%s siden sidste tjek (%s):" % (
        antal, "" if antal == 1 else "e", _mail_time_label(timer))]
    for i in range(min(len(afsendere), len(emner), 5)):
        afsender = afsendere[i].strip() or "(ukendt afsender)"
        emne = emner[i].strip() or "(intet emne)"
        linjer.append("  • %s — %s" % (afsender[:60], emne[:80]))
    if antal > 5:
        linjer.append("  … og %d mere" % (antal - 5))
    return "\n".join(linjer)


def _mail_time_label(timer: float) -> str:
    if timer < 1:
        return "inden for den seneste time"
    if timer < 2:
        return "for en time siden"
    return "for %d timer siden" % int(timer)
