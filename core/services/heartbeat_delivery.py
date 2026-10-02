"""Heartbeat-levering: de to veje et hjerteslag naar webchatten ad.

## Hvorfor filen findes

Boy Scout, 2/10-2026. `heartbeat_runtime.py` var paa 7.432 linjer, og de to
funktioner herunder skulle aendres: de skrev direkte med `append_chat_message`
og var derfor HELT uden daemon-vagten i `notification_bridge`, saa et hjerteslag
kunne banke paa midt i en saetning. De laa side om side (4388-4762) og goer samme
slags arbejde — levere ét afgraenset stykke tekst til Bjoerns webchat-session —
saa de er den naturlige enhed at skille ud.

`_deliver_heartbeat_proposal` leverer ét forslag; `_deliver_heartbeat_ping_directly`
leverer et ping, med nudge-systemet som foerste forsoeg og direkte levering som
fallback.

## Bagudkompatibilitet

`heartbeat_runtime` re-eksporterer begge navne, saa baade dens egne kaldesteder
og `tests/test_heartbeat_bridge_triggers.py` (der naar dem som
`heartbeat_runtime._deliver_...`) virker uaendret. En test der patcher dem paa
`heartbeat_runtime` rammer ogsaa de interne kaldere, fordi de slaar navnet op
som modul-global dér.

`_recent_ping_history` hentes ved kaldetid fra `heartbeat_runtime` — en import
paa modulniveau ville vaere cirkulaer, da `heartbeat_runtime` importerer herfra.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def _recent_ping_history(*, limit: int = 8) -> Any:
    """Slaa op i `heartbeat_runtime` ved kaldetid — en modul-import ville vaere
    cirkulaer. Fejler opslaget, er et tomt historik-svar det sikre: vagten mod
    gentagelser falder saa mod «ingen kendt historik», ikke mod en undtagelse
    midt i en levering."""
    try:
        from core.services.heartbeat_runtime import (
            _recent_ping_history as _rigtig,
        )
        return _rigtig(limit=limit)
    except Exception:
        logger.warning("heartbeat_delivery: kunne ikke laese ping-historik", exc_info=True)
        return []


def _deliver_heartbeat_proposal(
    *,
    policy: dict[str, object],
    tick_id: str,
    summary: str,
    proposed_action: str,
) -> dict[str, str]:
    message_text = proposed_action.strip() or summary.strip()
    if not message_text:
        return {
            "status": "blocked",
            "summary": "Heartbeat propose decision had no user-facing text to deliver.",
            "action_type": "",
            "artifact": "",
            "blocked_reason": "missing-proposal-text",
        }

    ping_channel = str(policy.get("ping_channel") or "none").strip() or "none"
    trigger_entry: dict | None = None
    if ping_channel != "webchat":
        workspace_str = str(policy.get("workspace") or "").strip()
        if workspace_str:
            from core.runtime import heartbeat_triggers as _triggers

            trigger_entry = _triggers.consume_trigger(Path(workspace_str))
        if trigger_entry is None:
            return {
                "status": "recorded",
                "summary": message_text,
                "action_type": "",
                "artifact": "",
                "blocked_reason": "",
            }

    # Same banned-patterns as _deliver_heartbeat_ping_directly —
    # internal system summaries must never reach the user as webchat messages.
    _proposal_banned_patterns = (
        "bounded liveness pressure",
        "open-loop continuity is still live",
        "heartbeat appears to have",
        "liveness pressure because",
        "open-loop continuity is still",
        "relation continuity is still",
        "witness continuity is still",
        "bounded autonomy pressure",
        "should i review",
        "should i look at",
        "is there anything specific you would like",
        "vil du have jeg dykker ned",
        "vil du have jeg kigger",
        "skal jeg kigge",
        "skal jeg dykke ned",
        "er der noget specifikt",
        "er der noget bestemt du vil",
    )
    lowered_proposal = message_text.lower()
    if any(p in lowered_proposal for p in _proposal_banned_patterns):
        return {
            "status": "blocked",
            "summary": message_text,
            "action_type": "webchat-heartbeat-proposal",
            "artifact": "",
            "blocked_reason": "system-internal-text-rejected",
        }

    from core.services.chat_sessions import (
        get_chat_session,
        list_chat_sessions,
    )
    from core.services.notification_bridge import get_pinned_session_id

    # Prefer the pinned session (the one the user is actively viewing),
    # fall back to most recent session.
    session_id = get_pinned_session_id()
    if not session_id or get_chat_session(session_id) is None:
        sessions = list_chat_sessions()
        session_id = str((sessions[0] or {}).get("id") or "").strip() if sessions else ""
    if not session_id or get_chat_session(session_id) is None:
        event_bus.publish(
            "heartbeat.propose_blocked",
            {
                "tick_id": tick_id,
                "blocked_reason": "missing-webchat-session",
            },
        )
        return {
            "status": "blocked",
            "summary": "No webchat session is available for bounded propose delivery.",
            "action_type": "webchat-heartbeat-proposal",
            "artifact": "",
            "blocked_reason": "missing-webchat-session",
        }

    # 2/10-2026: ÉT aktivitets-tjek. Her stod en haandrullet variant der laeste
    # hele sessionens beskeder, kiggede paa den seneste med role="user" og
    # droppede forslaget hvis den var under 5 minutter gammel. Den overlappede
    # `is_session_active` — samme formaal, samme 5-minutters vindue — men
    # maalte noget andet og kunne drive fra den. De er nu det samme tjek.
    #
    # Tre ting blev bedre ved at bruge den faelles:
    #   * den laeser events-tabellen og er cross-process; den gamle laeste en
    #     session-snapshot i DENNE proces,
    #   * vinduet kommer fra `_SESSION_ACTIVE_WINDOW_SECONDS` i stedet for et
    #     haardkodet 5, saa der kun er ét tal at aendre,
    #   * den taeller ENHVER besked, ogsaa Jarvis' egne. Det tjener formaalet
    #     bedre end den gamle: et forslag lige efter at en tur afsluttede ser
    #     praecis ud som den «dobbelt-besvarelse» tjekket skulle forhindre.
    #
    # Handlingen er DROP, ikke koe, og det er med vilje: et forslag er
    # periodisk og bliver lavet igen ved naeste tik. Et gammelt forslag der
    # lander efter Bjoerns tur er stoej han ikke bad om, mens et friskt kommer
    # af sig selv. Koe-vejen i vagten er derfor uopnaaelig HERFRA — det gaelder
    # kun denne ene sti, og de oevrige kilder koees som foer.
    from core.services.session_inbox import is_session_active
    if is_session_active(session_id):
        return {
            "status": "blocked",
            "summary": message_text,
            "action_type": "webchat-heartbeat-proposal",
            "artifact": "",
            # Navnet var «recent-user-activity», men tjekket taeller nu enhver
            # besked. Ingen laeser strengen (verificeret), saa den kan vaere
            # praecis frem for arvet.
            "blocked_reason": "recent-session-activity",
        }

    # 2/10-2026: gennem daemon-vagten i stedet for direkte skrivning. Er
    # sessionen aktiv, koees beskeden og flushes efter Bjoerns tur — et
    # hjerteslag skal ikke banke paa midt i en saetning. `push=False`: denne
    # vej sendte ikke mobil-push foer, og flytningen maa ikke tilfoeje en.
    from core.services.notification_bridge import (
        delivery_succeeded,
        send_session_notification,
    )
    levering = send_session_notification(
        message_text,
        source="heartbeat-propose-bridge",
        session_id=session_id,
        push=False,
    )
    # "queued" ER en succes. Kalderen tjekker `status == "sent"` praecist, saa
    # koeningen maa IKKE aendre status — den staar i summary og artifact i
    # stedet. Et "queued" laest som fejl kostede en dobbelt-levering 23/9.
    if not delivery_succeeded(levering):
        return {
            "status": "blocked",
            "summary": "Heartbeat kunne ikke levere forslaget til webchat.",
            "action_type": "webchat-heartbeat-proposal",
            "artifact": "",
            "blocked_reason": f"notification-{levering.get('status') or 'error'}",
        }
    koeet = str(levering.get("status") or "") == "queued"
    message_id = str((levering.get("message") or {}).get("id") or "")
    event_bus.publish(
        "heartbeat.propose_delivered",
        {
            "tick_id": tick_id,
            "session_id": session_id,
            "message_id": message_id,
            "queued": koeet,
            "summary": summary,
        },
    )
    return {
        "status": "sent",
        "summary": (
            "Heartbeat queued one bounded proposal — flushes after Bjoerns tur."
            if koeet else
            "Heartbeat delivered one bounded proposal to webchat."
        ),
        "action_type": "webchat-heartbeat-proposal",
        "artifact": json.dumps(
            {
                "session_id": session_id,
                "message_id": message_id,
                "delivery_channel": "webchat-queued" if koeet else "webchat",
            },
            ensure_ascii=False,
            default=str,
        ),
        "blocked_reason": "",
    }


def _deliver_heartbeat_ping_directly(
    *,
    policy: dict[str, object],
    tick_id: str,
    ping_text: str,
    summary: str,
) -> dict[str, str]:
    """Deliver an LLM-authored ping straight to webchat.

    Bypasses the strict 3-gate execution pilot. Used when the heartbeat LLM
    actually wrote a ping_text — Jarvis must always be able to deliver an
    asked question whether it came from a thought, curiosity, or boredom.
    """
    message_text = ping_text.strip() or summary.strip()
    if not message_text:
        return {
            "status": "blocked",
            "summary": "Heartbeat ping decision had no user-facing text to deliver.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "missing-ping-text",
        }

    # Anti-spam guard: reject generic templated pings even when the LLM
    # ignored the prompt instruction. These are the patterns Jarvis was
    # caught spamming ("Should I review the recent...", etc.). If we
    # detect any of them, we block delivery and let the next tick try
    # again with fresh context.
    banned_patterns = (
        "should i review",
        "should i look at",
        "is there anything specific you would like",
        "is there anything you would like me to review",
        "vil du have jeg dykker ned",
        "vil du have jeg kigger",
        "skal jeg kigge",
        "skal jeg dykke ned",
        "er der noget specifikt",
        "er der noget bestemt du vil",
        # Runtime leak patterns — liveness summaries must never reach the user
        "bounded liveness pressure",
        "open-loop continuity is still live",
        "heartbeat appears to have",
        "liveness pressure because",
        "open-loop continuity is still",
        "relation continuity is still",
        "witness continuity is still",
        "bounded autonomy pressure",
    )
    lowered_message = message_text.lower()
    if any(pattern in lowered_message for pattern in banned_patterns):
        return {
            "status": "blocked",
            "summary": message_text,
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "generic-templated-ping-rejected",
        }

    # Repetition guard: reject if this exact text (or a near-duplicate)
    # is already in recent assistant history. We compare against the
    # last 8 assistant messages.
    try:
        recent = _recent_ping_history(limit=8)
        normalized_message = " ".join(lowered_message.split())
        for prior in recent:
            normalized_prior = " ".join(prior.lower().split())
            if not normalized_prior:
                continue
            if normalized_message == normalized_prior:
                return {
                    "status": "blocked",
                    "summary": message_text,
                    "action_type": "webchat-heartbeat-ping",
                    "artifact": "",
                    "blocked_reason": "duplicate-of-recent-message",
                }
    except Exception:
        # Fejler ÅBENT som ovenfor: uden historik kan vi ikke se en dublet, og
        # saa sendes pinget. Logges, saa en gentagelse paa skaermen kan spores
        # til et fejlet opslag i stedet for at se ud som en bevidst gentagelse.
        logger.warning(
            "heartbeat_delivery: kunne ikke laese ping-historik — "
            "sender uden dublet-tjek", exc_info=True,
        )

    if not bool(policy.get("allow_ping")):
        return {
            "status": "blocked",
            "summary": "Heartbeat policy blocks ping delivery.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "ping-not-allowed",
        }

    kill_switch_state = str(policy.get("kill_switch") or "enabled")
    if kill_switch_state != "enabled":
        return {
            "status": "blocked",
            "summary": "Heartbeat kill switch blocks proactive webchat delivery.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "kill-switch-disabled",
        }

    ping_channel = str(policy.get("ping_channel") or "none").strip() or "none"
    trigger_entry: dict | None = None
    if ping_channel != "webchat":
        workspace_str = str(policy.get("workspace") or "").strip()
        if workspace_str:
            from core.runtime import heartbeat_triggers as _triggers

            trigger_entry = _triggers.consume_trigger(Path(workspace_str))
        if trigger_entry is None:
            return {
                "status": "recorded",
                "summary": message_text,
                "action_type": "webchat-heartbeat-ping",
                "artifact": "",
                "blocked_reason": "",
            }

    from core.services.chat_sessions import (
        get_chat_session,
        list_chat_sessions,
    )

    sessions = list_chat_sessions()
    session_id = str((sessions[0] or {}).get("id") or "").strip() if sessions else ""
    if not session_id or get_chat_session(session_id) is None:
        event_bus.publish(
            "heartbeat.ping_blocked",
            {
                "tick_id": tick_id,
                "blocked_reason": "missing-webchat-session",
            },
        )
        return {
            "status": "blocked",
            "summary": "No webchat session is available for bounded ping delivery.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "missing-webchat-session",
        }

    # Route through nudge ledger instead of direct send to webchat
    # (2026-05-13). Same spejlsal-fix as Discord path: Jarvis sees the
    # pending nudge in awareness and decides whether to surface, with
    # full context. Killswitch falls back to direct send.
    try:
        from core.services.outbound_nudges import push_nudge
        from core.runtime.settings import load_settings as _ls
        if _ls().nudge_system_enabled:
            push_result = push_nudge(
                source="heartbeat",
                kind="heartbeat_ping",
                message=message_text,
                importance="normal",
                parent_session_id=session_id,
            )
            event_bus.publish("heartbeat.ping_delivered", {
                "tick_id": tick_id,
                "session_id": session_id,
                "channel": "webchat-nudge",
                "nudge_id": push_result.get("nudge_id"),
                "ping_text": message_text[:200],
            })
            return {
                "status": "queued",
                "summary": "Heartbeat ping queued as nudge for Jarvis review.",
                "action_type": "webchat-heartbeat-ping-nudge",
                "artifact": json.dumps({
                    "session_id": session_id,
                    "nudge_id": push_result.get("nudge_id"),
                    "delivery_channel": "nudge-ledger",
                    "ping_text": message_text[:200],
                }, ensure_ascii=False, default=str),
                "blocked_reason": "",
            }
    except Exception as _nudge_exc:
        logger.debug("heartbeat webchat: nudge push failed, fallback to direct: %s", _nudge_exc)

    # Fallback: direct send (killswitch off or nudge failed)
    # 2/10-2026: gennem daemon-vagten i stedet for direkte skrivning. Er
    # sessionen aktiv, koees beskeden og flushes efter Bjoerns tur — et
    # hjerteslag skal ikke banke paa midt i en saetning. `push=False`: denne
    # vej sendte ikke mobil-push foer, og flytningen maa ikke tilfoeje en.
    from core.services.notification_bridge import (
        delivery_succeeded,
        send_session_notification,
    )
    levering = send_session_notification(
        message_text,
        source="heartbeat-ping-bridge",
        session_id=session_id,
        push=False,
    )
    # "queued" ER en succes. Kalderen tjekker `status == "sent"` praecist, saa
    # koeningen maa IKKE aendre status — den staar i summary og artifact i
    # stedet. Et "queued" laest som fejl kostede en dobbelt-levering 23/9.
    if not delivery_succeeded(levering):
        return {
            "status": "blocked",
            "summary": "Heartbeat kunne ikke levere pinget til webchat.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": f"notification-{levering.get('status') or 'error'}",
        }
    koeet = str(levering.get("status") or "") == "queued"
    message_id = str((levering.get("message") or {}).get("id") or "")
    event_bus.publish(
        "heartbeat.ping_delivered",
        {
            "tick_id": tick_id,
            "session_id": session_id,
            "message_id": message_id,
            "queued": koeet,
            "channel": "webchat-direct",
            "summary": summary,
            "ping_text": message_text[:200],
        },
    )
    return {
        "status": "sent",
        "summary": (
            "Heartbeat queued one bounded ping — flushes after Bjoerns tur."
            if koeet else
            "Heartbeat delivered one bounded ping to webchat (direct, nudge bypassed)."
        ),
        "action_type": "webchat-heartbeat-ping",
        "artifact": json.dumps(
            {
                "session_id": session_id,
                "message_id": message_id,
                "delivery_channel": "webchat-queued" if koeet else "webchat",
                "ping_text": message_text[:200],
            },
            ensure_ascii=False,
            default=str,
        ),
        "blocked_reason": "",
    }
