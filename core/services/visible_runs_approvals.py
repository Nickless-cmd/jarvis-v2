"""Pending tool-approval resolution for visible runs.

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``.
Ren KODE-FLYTNING — ingen logik-ændring. ``resolve_pending_approval`` re-eksporteres
tilbage til ``visible_runs`` i bunden af den fil, så eksisterende imports
(``apps/api/.../chat.py``, ``cowork.py``) og test-kald mod ``visible_runs.X`` virker.

Main-residente symboler der (a) er delt state (``_PENDING_APPROVALS``,
``_persist_pending_approvals`` — brugt af ``_stream_visible_run``) eller (b)
monkeypatches i tests (``append_chat_message``, ``_get_visible_approval_state``,
``_set_visible_approval_state``) refereres via ``_vr.X`` INDE i funktions-kroppen
(lazy) → samme objekt-identitet + patches ses på kald-tidspunkt.
"""

from __future__ import annotations

import threading

import logging
from datetime import UTC, datetime

import core.services.visible_runs as _vr

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


# Laasen daekker «laes tilstanden OG skriv at den er taget». Uden den er der et
# vindue hvor to svarere begge ser «pending».
_OVERTAGELSES_LAAS = threading.Lock()


def _er_udloebet(pending: dict) -> str:
    """Er godkendelsen for gammel til at maatte bruges? Returnerer grunden.

    Tom streng = den er frisk nok. Kan alderen IKKE afgoeres, siges det — men
    kaldet spaerres ikke: en manglende tidsstempel er husets fejl, ikke
    brugerens, og at afvise paa den ville laase ham ude af sine egne kort.
    """
    from datetime import UTC, datetime

    from core.runtime.db_approval_bridge import DEFAULT_TTL_S

    raa = str(pending.get("created_at") or "").strip()
    if not raa:
        return ""
    try:
        t = datetime.fromisoformat(raa)
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
    except Exception:
        return ""
    alder = (datetime.now(UTC) - t).total_seconds()
    if alder <= DEFAULT_TTL_S:
        return ""
    if alder < 7200:
        return f"{int(alder // 60)} minutter gammel"
    if alder < 172800:
        return f"{alder / 3600:.1f} timer gammel"
    return f"{alder / 86400:.1f} dage gammel"


def resolve_pending_approval(approval_id: str, *, approved: bool,
                             answered_by: str | None = None) -> dict:
    """Resolve a pending tool approval.

    Resolves a pending approval in shared runtime state so a blocked streaming
    generator can resume even if the approve/deny request lands on another worker.
    """
    from core.tools.simple_tools import execute_tool_force, format_tool_result_for_model

    # ── OVERTAGELSEN (Fase 4) ───────────────────────────────────────────
    # «a decision is consumed at most once by atomic claim.»
    #
    # MAALT 9/9-2026: to samtidige svar paa samme kort udfoerte kommandoen TO
    # GANGE. Hullet var vinduet mellem at tage kortet og at skrive at det var
    # taget: traad A poppede det fra hukommelsen, traad B fandt None dér og
    # faldt tilbage til den DELTE tilstand, som stadig sagde «pending» — for A
    # naaede ikke at skrive «approved» foer efter kaldet var koert.
    #
    # Baade selve fundet og fixet: taenk paa den DELTE tilstand som CAS-punktet.
    # Kortet markeres «resolving» FOER udbyder-graensen krydses, under en laas
    # der ogsaa daekker oplaesningen — saa den anden svarer ser en tilstand der
    # ikke er «pending», og bliver afvist af vagten der allerede fandtes.
    with _OVERTAGELSES_LAAS:
        pending = _vr._PENDING_APPROVALS.pop(approval_id, None)
        if pending is not None:
            _vr._persist_pending_approvals()
        shared_pending = _vr._get_visible_approval_state(approval_id)
        if not pending and shared_pending:
            pending = shared_pending
        if not pending:
            return {"error": "Approval not found or expired", "status": "error"}
        if str(pending.get("status") or "pending") not in {"", "pending"}:
            return {"error": "Approval already resolved", "status": "error"}
        # Marker den som taget MENS laasen holdes. En anden proces laeser samme
        # delte tilstand og ser nu at kortet er i brug.
        try:
            _vr._set_visible_approval_state(
                approval_id, {**pending, "approval_id": approval_id,
                              "status": "resolving"})
        except Exception:
            # Kan vi ikke markere den, kan vi heller ikke garantere
            # engangs-forbruget. Det siges hoejt frem for at koere videre og
            # haabe.
            logger.warning("Fase 4: kunne ikke markere %s som overtaget — "
                           "engangs-forbruget kan IKKE garanteres",
                           approval_id, exc_info=True)

    # ── HVEM SVARER (Fase 4) ────────────────────────────────────────────
    # «duplicate, late, and cross-user answers cannot authorize execution».
    # Endepunktet tog ingen bruger og lavede intet ejerskabstjek: enhver
    # autentificeret kalder kunne godkende ET HVILKET SOM HELST kort ved at
    # kende dets id. Identiteten fandtes hele tiden i auth-middleware'ens
    # ContextVar — den naaede bare aldrig hertil.
    #
    # Et kort UDEN ejer slipper igennem: de 26 der laa paa produktionen har
    # ingen, og en manglende identitet er husets fejl, ikke brugerens.
    _ejer = str(pending.get("owner_user_id") or "").strip()
    _svarer = str(answered_by or "").strip()
    if _ejer and _svarer and _ejer != _svarer:
        logger.warning("Fase 4: afviser KRYDSBRUGER-svar paa %s — ejer=%r svarer=%r",
                       approval_id, _ejer, _svarer)
        _vr._PENDING_APPROVALS[approval_id] = pending      # kortet er IKKE brugt
        _vr._persist_pending_approvals()
        return {
            "status": "error",
            "tool": pending.get("tool_name") or "",
            "error": "Den godkendelse tilhoerer en anden bruger.",
            "result_text": "[Godkendelsen tilhoerer en anden bruger]",
            "chat_persisted": False,
        }

    # ── UDLOEB (Fase 4) ──────────────────────────────────────────────────
    # Der var INTET aldersstjek. Ordet «expired» stod kun i fejlbeskeden
    # ovenfor. Maalt 9/9-2026: 26 ventende godkendelser laa i
    # `state/pending_approvals.json`, alle `bash`, den aeldste fra 29. august
    # — elleve dage. De blev genindlaest i hukommelsen ved HVER procesopstart,
    # saa en genstart genoplivede dem i stedet for at fejle lukket.
    #
    # Et ja i dag ville altsaa have koert en kommando fra i forgaars med de
    # argumenter der blev fanget dengang. Spec'ens ord: «duplicate, late, and
    # cross-user answers cannot authorize execution».
    #
    # Samme TTL som broen bruger — ét tal, ikke to.
    _for_gammel = _er_udloebet(pending)
    if _for_gammel:
        logger.warning("Fase 4: afviser UDLOEBET godkendelse %s (%s) — %s",
                       approval_id, pending.get("tool_name"), _for_gammel)
        _vr._PENDING_APPROVALS.pop(approval_id, None)
        _vr._persist_pending_approvals()
        return {
            "status": "error",
            "tool": pending.get("tool_name") or "",
            "error": (f"Godkendelsen er udloebet ({_for_gammel}). "
                      "Bed om handlingen igen, saa laver jeg et nyt kort."),
            "result_text": f"[Godkendelsen er udloebet: {_for_gammel}]",
            "chat_persisted": False,
        }

    # ── Permission-classifier GOLD outcome (harness Part E) ──
    # The owner just approved/denied a surfaced mutating action → the real signal.
    # Compare against the earlier stashed prediction. Fail-open, never blocks.
    try:
        from core.services import permission_classifier as _pc
        _pc_stashed = _pc.pop_prediction(approval_id)
        if _pc_stashed:
            _pc.record_prediction_outcome(
                _pc_stashed["tool"],
                predicted=_pc_stashed["predicted"],
                actual="approve" if approved else "deny",
                is_owner_gold=True,
            )
    except Exception:
        pass

    # Skygge: fortæl broen hvad mennesket klikkede. Ændrer intet.
    try:
        from core.services.approval_bridge_shadow import note_decided
        note_decided(approval_id, approved=bool(approved))
    except Exception:
        pass

    if not approved:
        _vr._set_visible_approval_state(
            approval_id,
            {
                **pending,
                "approval_id": approval_id,
                "status": "denied",
                "approved": False,
                "resolved_at": datetime.now(UTC).isoformat(),
            },
        )
        event_bus.publish("tool.approval_resolved", {
            "approval_id": approval_id,
            "tool": pending["tool_name"],
            "approved": False,
            "status": "denied",
        })
        # Fire-and-forget: approval denial is both a rupture (relational) and
        # a regret (cognitive — Jarvis predicted user would approve, but didn't).
        _tool_name = pending.get("tool_name") or ""
        _session_id = str(pending.get("session_id") or "")
        try:
            from core.services.rupture_repair import (
                _ensure_tables as _rupture_ensure,
                _rupture_key,
                _upsert_rupture,
            )
            from core.runtime.db import connect as _connect
            _rupture_ensure()
            topic = f"approval:{_tool_name}"
            rkey = _rupture_key(source_kind="approval_rejected", topic=topic)
            from datetime import UTC as _UTC, datetime as _dt
            _now = _dt.now(_UTC).isoformat().replace("+00:00", "Z")
            with _connect() as _conn:
                _upsert_rupture(
                    _conn,
                    rupture_key=rkey,
                    topic=topic,
                    source_kind="approval_rejected",
                    reason=f"User denied approval for tool {_tool_name}",
                    evidence={"approval_id": approval_id, "tool": _tool_name},
                    tension_level=0.7,
                    linked_run_id=str(pending.get("run_id") or ""),
                    linked_session_id=_session_id,
                    linked_incident_id="",
                    status="open",
                    last_seen_at=_now,
                )
                _conn.commit()
        except Exception:
            pass
        try:
            from core.services.regret_engine import open_or_update_regret
            open_or_update_regret(
                decision_id=f"approval:{approval_id}",
                context={"tool": _tool_name, "approval_id": approval_id},
                expected_outcome="approved",
                actual_outcome="rejected",
                lesson=f"Bruger afviste tool-call til {_tool_name}",
                confidence_before=0.7,
                confidence_after=0.1,
                linked_run_id=str(pending.get("run_id") or ""),
                linked_session_id=_session_id,
            )
        except Exception:
            pass
        return {"status": "denied", "tool": pending["tool_name"]}

    # owner_approved: et menneske har set PRAECIS dette kald og klikket Godkend.
    # Uden det rammer en destruktiv kommando sin egen gate igen og svarer
    # approval_needed paa ny — i ring. Autonome runs kalder samme funktion UDEN
    # flaget og skal blive ved med at blive stoppet.
    # Skygge: ville broen have tilladt PRÆCIS dette kald?
    #
    # Her, lige før udbyder-grænsen krydses, er stedet spec'en peger på. Broens
    # svar afgør ingenting endnu — men den forsøger den ægte overtagelse med de
    # ægte argumenter, og dét er den eneste måde at opdage om digesten
    # overlever den virkelige vej: fra værktøjets svar, gennem en dict i
    # hukommelsen, gennem delt tilstand mellem processer, og tilbage.
    # K5: overtagelsen OG `dispatching` committer i ÉN sætning, HER — lige før
    # udbyder-grænsen krydses. Bevist på tværs af rigtige processer, ikke kun
    # tråde (`test_EN_vinder_ogsaa_paa_tvaers_af_PROCESSER`).
    #
    # Så længe broen kører i skygge, afgør svaret ingenting. Når den HÅNDHÆVER,
    # er et nej et nej — og «broen kunne ikke afgøre det» er også et nej, for
    # en godkendelse man ikke kan bevise er ikke en godkendelse.
    try:
        from core.services.approval_bridge_shadow import note_claim
        bro_tillod, bro_grund = note_claim(
            approval_id, tool_name=pending["tool_name"],
            arguments=pending["arguments"], legacy_allowed=True)
    except Exception:
        bro_tillod, bro_grund = True, "skyggen kastede"

    # K7: er PRAECIS dette kald allerede afsendt én gang uden at nogen saa
    # udfaldet? Saa maa det ikke ske af sig selv igen. Naar broen HAANDHAEVER
    # er det et nej; i skygge siges det kun hoejt.
    try:
        from core.services.retry_admissibility import may_auto_retry
        _k7 = may_auto_retry(pending["tool_name"], pending["arguments"])
    except Exception:
        _k7 = None
    if _k7 is not None and not _k7.tilladt and _k7.tidligere:
        logger.warning("K7: %s — %s", pending["tool_name"], _k7.grund)
        bro_tillod, bro_grund = False, _k7.grund

    if not bro_tillod:
        try:
            from core.tools.approval_rollout_gate import bridge_active
            haandhaever = bridge_active()
        except Exception:
            haandhaever = False
        if haandhaever:
            logger.warning("K5: afviser %s (%s) — broen sagde nej: %s",
                           approval_id, pending["tool_name"], bro_grund[:200])
            try:
                from core.services.approval_bridge_shadow import note_settled
                note_settled(approval_id, ok=False)
            except Exception:
                pass
            return {
                "status": "error",
                "tool": pending["tool_name"],
                "error": ("Godkendelsen kunne ikke overtages: " + bro_grund),
                "result_text": ("[Godkendelsen kunne ikke overtages: "
                                + bro_grund + "]"),
                "chat_persisted": False,
                "approval_id": approval_id,
            }

    try:
        result = execute_tool_force(
            pending["tool_name"], pending["arguments"], owner_approved=True,
        )
    except Exception:
        # Skyggen aabnede posten foer kaldet; den skal lukkes ogsaa naar det
        # gik galt, ellers staar den som «udfald ukendt» for evigt.
        try:
            from core.services.approval_bridge_shadow import note_settled
            note_settled(approval_id, ok=False)
        except Exception:
            pass
        raise
    try:
        from core.services.approval_bridge_shadow import note_settled
        note_settled(approval_id, ok=not (isinstance(result, dict)
                                          and result.get("status") == "error"))
    except Exception:
        pass
    result_text = format_tool_result_for_model(pending["tool_name"], result)

    # 2026-05-24 (Claude): persist tool result as role=tool in chat
    # transcript here too. Previously this was only done inside the
    # streaming run's tool-loop (visible_runs.py line ~1095). When the
    # streaming run timed out or disconnected before the user clicked
    # Approve, the tool would execute on approval but the result never
    # reached chat_messages — leaving Jarvis blind to it on the next
    # turn. Now we append from here AND set a dedupe marker so the
    # streaming path can skip its own append when it sees we already
    # persisted (avoiding duplicate role=tool messages when the stream
    # is still active and racing with resolve_pending_approval).
    chat_persisted = False
    session_id = str(pending.get("session_id") or "")
    if session_id:
        try:
            # Use the module-level import so monkeypatching in tests works.
            _vr.append_chat_message(
                session_id=session_id,
                role="tool",
                content=result_text,
                tool_name=str(pending.get("tool_name") or ""),
                tool_arguments=dict(pending.get("arguments") or {}),
            )
            chat_persisted = True
        except Exception:
            logger.exception(
                "resolve_pending_approval: chat persistence failed for %s",
                approval_id,
            )

    event_bus.publish("tool.approval_resolved", {
        "approval_id": approval_id,
        "tool": pending["tool_name"],
        "approved": True,
        "status": result.get("status", "ok"),
    })
    _vr._set_visible_approval_state(
        approval_id,
        {
            **pending,
            "approval_id": approval_id,
            "status": "approved",
            "approved": True,
            "resolved_at": datetime.now(UTC).isoformat(),
            "tool_status": result.get("status", "ok"),
            "result_text": result_text,
            "chat_persisted": chat_persisted,
        },
    )

    return {
        "status": result.get("status", "ok"),
        "tool": pending["tool_name"],
        "result_text": result_text,
        "chat_persisted": chat_persisted,
    }
