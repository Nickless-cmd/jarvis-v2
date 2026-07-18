"""Persistence + terminal outcome for visible runs (fail/cancel forbliver i main).

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``.
Ren KODE-FLYTNING — ingen logik-ændring. Funktionerne re-eksporteres tilbage til
``visible_runs`` i bunden af den fil, så bare kald i ``_stream_visible_run`` +
eksisterende call-sites/monkeypatches virker.

Facade-seam: main-residente callables der monkeypatches i tests eller er delt
sandhed (``append_chat_message``, ``_assert_presentation_invariant``,
``PresentationInvariantError``, ``_bounded_error``, ``_get_visible_run_control``,
``get_visible_run_controller``, ``_update_cognitive_systems_async``,
``_EMPTY_RUN_FALLBACK``) refereres via ``_vr.X`` INDE i funktions-kroppe (lazy) →
patch ses på kald-tidspunkt, ingen import-cyklus. ``time.sleep`` patches i tests via
``vr.time.sleep`` — samme modul-objekt her, så ingen seam nødvendig.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import core.services.visible_runs as _vr

from core.eventbus.bus import event_bus
from core.memory.private_layer_pipeline import write_private_terminal_layers
from core.runtime.db import connect
from core.services.markdown_structure import normalize_markdown_structure

logger = logging.getLogger(__name__)


def _preview_text(text: str, limit: int = 320) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _mark_mid_word_truncation(text: str) -> str:
    """Append "…" if the assistant text ends abruptly mid-word.

    Reasoning models (deepseek-v4-flash et al.) sometimes interleave text
    and tool_calls — emitting a tool_call mid-sentence and then never
    resuming the prose after the tool result lands. The user is left
    staring at half a word ("Jeg skrev et journa"). Detecting this in
    a robust way is hard, but the cheap heuristic of "ends with an
    alphanumeric character and is long enough to not be a single-word
    reply" catches the common case and gives the user a visible signal
    that something cut off, instead of silently lying about completeness.
    """
    if not text:
        return text
    stripped = text.rstrip()
    if not stripped:
        return text
    # Look at the LAST line only — multi-paragraph replies often end with
    # a short final sentence, but if that sentence itself is mid-word we
    # still want to flag it.
    last_line = stripped.splitlines()[-1].strip()
    if not last_line:
        return text
    # Short terse replies ("ja", "nej", "okay", "Done", "OK") are legit
    # without punctuation. Use word-count, not char-count: 3+ words ending
    # alphanumerically is almost always a cut-off sentence.
    if len(last_line.split()) < 3:
        return text
    last = last_line[-1]
    # Anything terminal-like is fine: punctuation, brackets, quotes,
    # emoji ranges, code-block fences, list-item dashes ending a line.
    if not last.isalnum():
        return text
    # Mid-word — annotate. The "…" stays inside the chat-display invariant
    # (no internal markers) and looks natural to the reader.
    return stripped + "…"


def _persist_session_assistant_message(
    run: "_vr.VisibleRun",
    text: str,
    *,
    reasoning_content: str = "",
    blocks: list[dict] | None = None,
) -> None:
    if not run.session_id:
        return
    normalized = str(text or "").strip()
    if not normalized:
        return
    # ── Leak/dump-guard (2026-06-23) ────────────────────────────────────────
    # Model echoer et råt (kæmpe) tool-result som svar i stedet for at opsummere
    # (Bjørns 27KB-dumps). Observe-only → synlig i Centralen, raffineres med data.
    # Markør-leaks ([tool_result:/[bash]:) fanges separat af presentation_invariant.
    if len(normalized) > 8000:
        try:
            from core.services import followup_observer as _fo_leak
            _fo_leak.note_leak(
                run.run_id, provider=run.provider, model=run.model,
                chars=len(normalized), reason="svar > 8000 tegn (sandsynlig dump)")
        except Exception:
            pass
    normalized = _mark_mid_word_truncation(normalized)
    # 2026-06-11 (Bjørn frustration crisis fix D2): når LLM emitter
    # tool-result markers eller tool-calls som prose, raisede
    # _assert_presentation_invariant — exception blev caught af caller,
    # men da raise sker FØR append_chat_message + event_bus.publish er
    # konsekvensen at run markeres completed i DB mens beskeden ALDRIG
    # når Discord/webchat subscriber. Bjørn ser kun "💭 modtaget" og
    # tror Jarvis er hængt. Vi sanitizer i stedet og persister en
    # honest fejl-besked så user får besked, og leaket fortsat logges
    # som warning for dev-visibility.
    try:
        _vr._assert_presentation_invariant(normalized)
    except _vr.PresentationInvariantError as _leak_exc:
        logger.warning(
            "presentation-invariant-leak run_id=%s session=%s sanitized: %s",
            run.run_id, run.session_id, str(_leak_exc)[:200],
        )
        # Loop-cluster: tool-marker/tool-call-as-prose-leak SYNLIG i Centralen
        # (var kun en log-warning → usynlig). Det er en ægte svar-kvalitets-anomali
        # (Bjørns frustrations-krise). Self-safe.
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "loop", "nerve": "presentation_invariant",
                "run_id": str(run.run_id or ""), "session_id": str(run.session_id or ""),
                "leak": str(_leak_exc)[:160], "provider": str(run.provider or ""),
                "model": str(run.model or ""),
            })
        except Exception:
            pass
        normalized = (
            "⚠ Jeg endte med at gentage tool-resultater som prose i mit svar "
            "i stedet for at faktisk kalde værktøjet. Det er en fejl jeg ikke "
            "skulle have lavet. Spørg mig igen, så svarer jeg ordentligt."
        )
    # Rekonstruér blokstruktur fra Jarvis' inline-markører (` - `/`**X:**`).
    # Han emitterer inkonsistent newlines (~50% af svar er én lang linje);
    # dette gør beskeden konsistent renderbar på ALLE kanaler + i gemt historik.
    # Ren CPU-funktion → ingen --workers 1 frys-risiko. Se markdown_structure.py.
    normalized = normalize_markdown_structure(normalized)

    # Cross-user deling-guard (§4.4, TOTP Fase 4.2): hvis det udgående svar nævner
    # en ANDEN bruger end samtalepartneren, flag det. Detektion + eventbus-signal
    # nu (observérbart); det blokerende approval-kort er desk-UI i Fase 6. Best-
    # effort: en fejl her må ALDRIG spærre svaret.
    try:
        from core.identity.workspace_context import current_user_id as _cuid
        _cur = str(_cuid() or "")
        if _cur:
            # ── Privacy-cluster 🔒 GENNEM Den Intelligente Central (SECURITY, fail-closed) ──
            # YELLOW = nævner en anden bruger → kræver bekræftelse. RED = fail-closed
            # (gate-exception) → flag ALLIGEVEL (ved tvivl lækker vi aldrig i stilhed —
            # modsat det gamle except:pass). Security-nerve: kan ikke slås fra, kun isoleres.
            from core.services.central_core import central as _central_priv
            from core.services.gate_privacy import privacy_gate as _privacy_gate
            from core.services.gate_kernel import Decision as _PvDec, GateClass as _PvGK
            _pvv = _central_priv().decide(
                "cross_user_share", {"text": normalized, "current_user_id": _cur},
                _privacy_gate, cluster="privacy", klass=_PvGK.SECURITY)
            if _pvv.decision in (_PvDec.YELLOW, _PvDec.RED):
                _share = _pvv.evidence or {}
                # Event-publicering i SIN EGEN try/except: et publish-problem (fx ukendt
                # event-familie, som tidligere væltede HELE guarden og sprang record_pending
                # over → tavst cross-user-læk) må ALDRIG forhindre at den pending share-
                # beslutning registreres. Observabilitet er sekundært til approval-kortet.
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish("cross_user_share.flagged", {
                        "session_id": run.session_id,
                        "current_user_id": _cur,
                        "mentioned_users": _share.get("mentioned_users"),
                        "prompt": _share.get("prompt"),
                    })
                except Exception:
                    pass
                # Registrér en pending share-beslutning → dukker op som kort i
                # Cowork-køen (Fase 6 #1). Bevidst IKKE i den live stream-sti.
                try:
                    from datetime import UTC, datetime
                    from uuid import uuid4
                    from core.services.share_guard_store import record_pending
                    record_pending(
                        decision_id=f"share-{uuid4().hex[:12]}",
                        session_id=run.session_id or "",
                        current_user_id=_cur,
                        mentioned_users=list(_share.get("mentioned_users") or []),
                        text_preview=normalized[:240],
                        created_at=datetime.now(UTC).isoformat(),
                    )
                except Exception:
                    pass
    except Exception as _share_exc:
        # Audit-remediation 2026-06-23: en fejl her spærrer ALDRIG svaret (Bjørns
        # availability-valg) — MEN den kollapsede privacy-guard er et potentielt
        # tavst cross-user-læk. Gør den LYD (severe incident) i stedet for except:pass.
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="privacy", nerve="cross_user_share", kind="fail_open",
                severity="severe", run_id=str(run.run_id or ""), session_id=str(run.session_id or ""),
                message=f"cross_user_share-guard kastede → svaret sendt UDEN deling-tjek: "
                        f"{type(_share_exc).__name__}: {_share_exc}"[:300],
            )
        except Exception:
            pass

    # Struktureret content_json (spec 2026-07-09): persistér den kanoniske blok-
    # array når kill-switchen er ON, så tool-kort overlever reload uden reconcile.
    # Flag OFF eller ingen blokke → content_json=None → uændret tekst-kun adfærd.
    content_json = None
    if blocks:
        try:
            from core.services.structured_content_flag import structured_content_v2_enabled
            if structured_content_v2_enabled():
                import json as _json
                content_json = _json.dumps(blocks, ensure_ascii=False)
        except Exception:
            content_json = None

    message = _append_chat_message_with_retry(
        session_id=run.session_id,
        role="assistant",
        content=normalized,
        reasoning_content=str(reasoning_content or ""),
        content_json=content_json,
    )
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("channel.chat_message_appended", {
            "session_id": run.session_id,
            "message": message,
            "source": "visible-run",
        })
    except Exception:
        pass


def _append_chat_message_with_retry(
    *,
    session_id: str,
    role: str,
    content: str,
    reasoning_content: str = "",
    content_json: str | None = None,
    _backoffs: tuple[float, ...] = (0.2, 0.5),
) -> dict[str, object]:
    """H5 persist-retry (spec §11.2 P5): persistering må ALDRIG tabes tavst pga.
    et FORBIGÅENDE DB-blip. "Vist live, væk ved reload" er data-integritet, ikke
    bare en nerve. ``connect()`` har sqlite's default-busy_timeout (~5s), så dette
    er primært en bælte-og-seler mod ikke-lock-transienter (kortvarig I/O-glitch
    under WAL-checkpoint mv.); for ægte locks dækker busy_timeout det meste.

    Vi retry'er KUN forbigående sqlite-fejl (database is locked/busy). Permanente
    fejl (ValueError "chat session not found", IntegrityError, disk full) propageres
    UÆNDRET ved første forsøg — retry på dem ville bare spilde tid. Den endelige
    fejl (efter udtømte retries, eller en ikke-transient fejl) propageres til
    caller, som fyrer ``persist_failed``-nerven (backstop). Selv-sikker: kaster
    aldrig en NY fejl-type ud over hvad ``append_chat_message`` selv ville kaste."""
    import sqlite3

    attempt = 0
    while True:
        try:
            return _vr.append_chat_message(
                session_id=session_id,
                role=role,
                content=content,
                reasoning_content=reasoning_content,
                content_json=content_json,
            )
        except sqlite3.OperationalError as exc:
            text = str(exc).lower()
            transient = ("database is locked" in text) or ("database is busy" in text)
            if not transient or attempt >= len(_backoffs):
                # Ikke-transient ELLER retries udtømte → lad caller fyre
                # persist_failed-nerven (final-failure backstop).
                raise
            time.sleep(_backoffs[attempt])
            attempt += 1


def _survival_or_fallback() -> str:
    """OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen svigter, lad Jarvis TALE fra
    Centralens durable selv (model-frit) i stedet for en tom stub. Falder tilbage til den
    generiske stub hvis Centralen intet selv har. Self-safe → aldrig tomt."""
    try:
        from core.services.central_self_state import survival_voice
        v = (survival_voice() or "").strip()
        if v:
            return v
    except Exception:
        pass
    return _vr._EMPTY_RUN_FALLBACK


def _session_last_role(session_id: str) -> str:
    """Sidste persisterede besked-rolle for en session (idempotens for invarianten)."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT role FROM chat_messages WHERE session_id = ? "
                "ORDER BY id DESC LIMIT 1", (str(session_id or ""),)).fetchone()
        if not row:
            return ""
        return str((row[0] if not isinstance(row, dict) else row.get("role")) or "")
    except Exception:
        return ""


def _guarantee_visible_outcome(run: "_vr.VisibleRun") -> None:
    """LIVSCYKLUS-INVARIANT (Bjørn 29. jun, #1): en completed INTERAKTIV run må ALDRIG
    ende uden synligt output. Når et run lukker 'completed' uden at have persisteret et
    assistant-svar (tavs cut — uanset hvilket lag der svigtede: tom first-pass,
    kortslutning, tom followup-runde), persistér en ærlig fallback så brugeren ALDRIG
    ser tomhed. Det dræber HELE den tavse-cut-klasse ved konvergens-punktet, uafhængigt
    af rod-årsag (#2 gjorde den synlig — dette gør den ufarlig).

    Idempotent: springer over hvis sidste besked allerede er assistant (bruger fik svar).
    Autonome runs må gerne ende tomt. ALDRIG kaste ind i run-finaliseringen."""
    try:
        if run.autonomous or not run.session_id:
            return
        _last_role = _session_last_role(run.session_id)
        if _last_role == "assistant":
            return
        _persist_session_assistant_message(run, _survival_or_fallback())
    except Exception:
        pass


def set_last_visible_run_outcome(
    run: "_vr.VisibleRun",
    *,
    status: str,
    error: str | None = None,
    text_preview: str | None = None,
) -> None:
    finished_at = datetime.now(UTC).isoformat()
    outcome = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "status": status,
        "finished_at": finished_at,
    }
    if error:
        outcome["error"] = error
    if text_preview:
        outcome["text_preview"] = text_preview
    # State-global _LAST_VISIBLE_RUN_OUTCOME bor i main (visible_runs) og læses af
    # get_last_visible_run_outcome dér. Skriv via _vr så det er SAMME objekt.
    _vr._LAST_VISIBLE_RUN_OUTCOME = outcome
    # ── Tur-integritets-verifikator (2026-06-23, Bjørn: ÉT runtime-checkpoint) ──
    # ALLE terminale stier (tool/no-tool/agentisk/non-agentisk) lander her med
    # status+preview. Et 'completed' run UDEN noget ægte svar = empty completion,
    # uanset sti/provider/model. Den agentiske guard fangede KUN den agentiske gren
    # → GLM's tekstløse-uden-tools cut smuttede udenom (verificeret 23. jun). Nu
    # fanget CENTRALT, det ene sted alle stier konvergerer. Self-safe; fyrer aldrig
    # på fejl/interrupted (egen håndtering) eller når preview faktisk har indhold.
    try:
        _ti_prev = str(text_preview or "").strip()
        if _ti_prev in ("[tool calls only]", "[Completed]", "[tool calls only]."):
            _ti_prev = ""
        if status == "completed" and not _ti_prev:
            from core.services import followup_observer as _fo_ti
            _fo_ti.note_empty_completion(
                run.run_id, provider=run.provider, model=run.model,
                session_id=run.session_id or "", path="unified_checkpoint")
            # #1 LIVSCYKLUS-INVARIANT: aldrig tavs tomhed — persistér fallback hvis
            # brugeren ikke fik et svar (idempotent + self-safe).
            _guarantee_visible_outcome(run)
    except Exception:
        pass
    # 2026-07-18 (hang-fix, målt): _persist_visible_run_outcome gør 3 DB-INSERTs under ÉT
    # write-lock. Under WAL-contention (2,7GB events-tabel + samtidige daemon/heartbeat/
    # inner-voice-writes) blokerede det 1-15s SYNKRONT lige efter svaret, FØR stream-luk →
    # "jarvis→tool→svar→hänger" (turn-trace: finalize-enter→after-outcome = 15,16s). Den
    # load-bearing del (in-memory _LAST_VISIBLE_RUN_OUTCOME + empty-completion-guard) er
    # ALLEREDE kørt synkront ovenfor; DB-projektionen (MC-dashboard/visible_runs) behøver
    # ikke blokere svaret. Kør den i en daemon-tråd så streamen lukker med det samme.
    import threading as _t_outcome
    _t_outcome.Thread(
        target=_persist_visible_run_outcome,
        args=(run,),
        kwargs=dict(status=status, finished_at=finished_at,
                    text_preview=text_preview, error=error),
        name=f"outcome-persist-{str(run.run_id)[:10]}", daemon=True,
    ).start()


def _persist_visible_run_outcome(
    run: "_vr.VisibleRun",
    *,
    status: str,
    finished_at: str,
    text_preview: str | None = None,
    error: str | None = None,
) -> None:
    controller = _vr.get_visible_run_controller(run.run_id)
    shared = _vr._get_visible_run_control(run.run_id)
    started_at = controller.started_at if controller else shared.get("started_at")
    capability_id = controller.last_capability_id if controller else shared.get("capability_id")
    user_message_preview = controller.user_message_preview if controller else shared.get("current_user_message_preview")
    bounded_error = _vr._bounded_error(error) if error else None
    work_preview = text_preview or bounded_error
    work_id = f"visible-work:{run.run_id}"
    note_id = f"visible-work-note:{run.run_id}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO visible_runs (
                run_id, lane, provider, model, status,
                started_at, finished_at, text_preview, error, capability_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                status=excluded.status,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                text_preview=excluded.text_preview,
                error=excluded.error,
                capability_id=excluded.capability_id
            """,
            (
                run.run_id,
                run.lane,
                run.provider,
                run.model,
                status,
                started_at,
                finished_at,
                text_preview,
                bounded_error,
                capability_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO visible_work_units (
                work_id, run_id, status, lane, provider, model,
                started_at, finished_at, user_message_preview, capability_id, work_preview
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                work_id=excluded.work_id,
                status=excluded.status,
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                user_message_preview=excluded.user_message_preview,
                capability_id=excluded.capability_id,
                work_preview=excluded.work_preview
            """,
            (
                work_id,
                run.run_id,
                status,
                run.lane,
                run.provider,
                run.model,
                started_at,
                finished_at,
                user_message_preview,
                capability_id,
                work_preview,
            ),
        )
        conn.execute(
            """
            INSERT INTO visible_work_notes (
                note_id, work_id, run_id, status, lane, provider, model,
                user_message_preview, capability_id, work_preview,
                projection_source, created_at, finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                work_id=excluded.work_id,
                status=excluded.status,
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                user_message_preview=excluded.user_message_preview,
                capability_id=excluded.capability_id,
                work_preview=excluded.work_preview,
                projection_source=excluded.projection_source,
                created_at=excluded.created_at,
                finished_at=excluded.finished_at
            """,
            (
                note_id,
                work_id,
                run.run_id,
                status,
                run.lane,
                run.provider,
                run.model,
                user_message_preview,
                capability_id,
                work_preview,
                "visible-selected-work-item",
                started_at or finished_at,
                finished_at,
            ),
        )
        conn.commit()
    write_private_terminal_layers(
        run_id=run.run_id,
        work_id=work_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        user_message_preview=user_message_preview,
        work_preview=work_preview,
        capability_id=capability_id,
    )

    # --- Cognitive Architecture: fire-and-forget post-run updates ---
    _vr._update_cognitive_systems_async(
        run_id=run.run_id,
        user_message=user_message_preview or "",
        assistant_response=work_preview or "",
        outcome_status=status,
    )
