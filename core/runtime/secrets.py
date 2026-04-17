from __future__ import annotations

import json
import os
from dataclasses import dataclass

from core.runtime.config import SETTINGS_FILE


@dataclass(frozen=True, slots=True)
class MailConfig:
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    user: str
    password: str


def _backup_file():
    return SETTINGS_FILE.parent / "api_keys.backup.json"


def _missing_key_message(key: str) -> str:
    return (
        f"{key} mangler i {SETTINGS_FILE}. "
        f"Tilfoej den som top-level key - se {_backup_file()} for reference."
    )


def _parse_int(value: object, key: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{key} i {SETTINGS_FILE} skal vaere et heltal."
        ) from exc


def read_runtime_key(
    key: str,
    env_override: str | None = None,
    *,
    as_int: bool = False,
) -> str | int:
    """
    Read a top-level key from ~/.jarvis-v2/config/runtime.json.

    env_override wins when set to a non-empty environment variable.
    as_int returns an int and raises RuntimeError when parsing fails.
    """
    if env_override:
        env_value = os.environ.get(env_override)
        if env_value:
            return _parse_int(env_value, key) if as_int else env_value

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(_missing_key_message(key)) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Kunne ikke laese gyldig JSON fra {SETTINGS_FILE}. "
            f"Ret filen og tilfoej {key} som top-level key."
        ) from exc

    value = data.get(key)
    if value in ("", None):
        raise RuntimeError(_missing_key_message(key))

    return _parse_int(value, key) if as_int else str(value)


def mail_config() -> MailConfig:
    return MailConfig(
        smtp_host=str(
            read_runtime_key("mail_smtp_host", env_override="JARVIS_MAIL_SMTP_HOST")
        ),
        smtp_port=int(
            read_runtime_key(
                "mail_smtp_port",
                env_override="JARVIS_MAIL_SMTP_PORT",
                as_int=True,
            )
        ),
        imap_host=str(
            read_runtime_key("mail_imap_host", env_override="JARVIS_MAIL_IMAP_HOST")
        ),
        imap_port=int(
            read_runtime_key(
                "mail_imap_port",
                env_override="JARVIS_MAIL_IMAP_PORT",
                as_int=True,
            )
        ),
        user=str(read_runtime_key("mail_user", env_override="JARVIS_MAIL_USER")),
        password=str(
            read_runtime_key("mail_password", env_override="JARVIS_MAIL_PASSWORD")
        ),
    )
