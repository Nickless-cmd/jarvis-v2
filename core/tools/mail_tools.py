"""Mail tools for Jarvis — jarvis@srvlab.dk

Provides send_mail and read_mail as native runtime tools.
Uses SMTP (port 587, STARTTLS) and IMAP (port 993, SSL).
"""

from __future__ import annotations

import email as email_lib
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from core.runtime.secrets import MailConfig, mail_config


# ---------------------------------------------------------------------------
# Executor functions
# ---------------------------------------------------------------------------


def _mail_config() -> MailConfig:
    return mail_config()

def _exec_send_mail(args: dict[str, Any]) -> dict[str, Any]:
    """Send an email from jarvis@srvlab.dk.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text or HTML).
        html: If true, body is sent as HTML.
    """
    to = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")
    html = args.get("html", False)

    if not to:
        return {"success": False, "error": "'to' is required"}
    if not subject:
        return {"success": False, "error": "'subject' is required"}
    if not body:
        return {"success": False, "error": "'body' is required"}

    try:
        config = _mail_config()
        if html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "html"))
        else:
            msg = MIMEText(body)

        msg["From"] = config.user
        msg["To"] = to
        msg["Subject"] = subject

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as s:
            s.starttls()
            s.login(config.user, config.password)
            s.send_message(msg)

        return {"success": True, "message": f"Mail sent to {to}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _exec_read_mail(args: dict[str, Any]) -> dict[str, Any]:
    """Read recent emails from jarvis@srvlab.dk inbox.

    Args:
        limit: Number of recent emails to fetch (default 10, max 50).
        folder: IMAP folder to read (default INBOX).
    """
    limit = min(int(args.get("limit", 10)), 50)
    folder = args.get("folder", "INBOX")

    try:
        config = _mail_config()
        with imaplib.IMAP4_SSL(config.imap_host, config.imap_port) as m:
            m.login(config.user, config.password)
            m.select(folder)
            _, ids = m.search(None, "ALL")

            if not ids[0]:
                return {"mails": [], "count": 0}

            mail_ids = ids[0].split()
            mails = []

            for i in mail_ids[-limit:]:
                _, data = m.fetch(i, "(RFC822)")
                msg = email_lib.message_from_bytes(data[0][1])

                # Get body snippet
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
                    "from": msg["From"],
                    "subject": msg["Subject"],
                    "date": msg["Date"],
                    "snippet": snippet,
                })

        return {"mails": mails, "count": len(mails)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Tool definitions (Ollama-compatible JSON schemas)
# ---------------------------------------------------------------------------

MAIL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "send_mail",
            "description": (
                "Send an email from jarvis@srvlab.dk. Supports plain text and HTML. "
                "Use this to reach out to people, send reports, notifications, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (plain text or HTML if html=true).",
                    },
                    "html": {
                        "type": "boolean",
                        "description": "If true, body is sent as HTML. Default false.",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_mail",
            "description": (
                "Read recent emails from jarvis@srvlab.dk inbox. "
                "Returns sender, subject, date, and body snippet for each email."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent emails to fetch (default 10, max 50).",
                    },
                    "folder": {
                        "type": "string",
                        "description": "IMAP folder to read (default INBOX).",
                    },
                },
            },
        },
    },
]
