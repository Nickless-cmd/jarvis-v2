"""Agent runtime — council & swarm collective rounds.

Split out of ``agent_runtime`` (behavior-preserving). Owns the collective
lifecycle: creating council/swarm sessions, posting notes, running one
collective round to a conclusion (worker fanout, swarm coordinator merge,
controller-based council deliberation), deriving a landing initiative,
closing sessions, and the vote/confidence/conflict helpers those need.

Re-exported via ``core.services.agent_runtime`` for backward compatibility.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from core.services.agent_runtime_base import (
    COUNCIL_ROLE_ORDER,
    MAX_SWARM_WORKERS,
    SWARM_ROLE_ORDER,
    _ACTIVE_STATUSES,
    _facade,
    _now_iso,
    _role_needs_tools,
    add_council_member,
    create_agent_message,
    create_agent_run,
    create_council_session,
    get_agent_registry_entry,
    get_council_session,
    list_agent_messages,
    list_council_members,
    logger,
    update_agent_registry_entry,
    update_agent_run,
    update_council_member,
    update_council_session,
)
from core.services.agent_runtime_spawn import (
    _agent_thread_id,
    _council_thread_id,
    _format_messages,
    send_peer_message,
    spawn_agent_task,
)
from core.services.agent_runtime_surfaces import build_council_detail_surface


def _trim(text: str, limit: int = 400) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit]


def _parse_percent_confidence(text: str) -> str:
    lowered = str(text or "").lower()
    for marker in ("% sikker", "% confidence", "% confident"):
        if marker not in lowered:
            continue
        token = lowered.split(marker, 1)[0].rsplit(" ", 1)[-1]
        try:
            value = int(token)
        except Exception:
            return ""
        if value >= 75:
            return "high"
        if value >= 40:
            return "medium"
        return "low"
    return ""


def _extract_confidence(text: str) -> str:
    lowered = str(text or "").lower()
    percent = _parse_percent_confidence(text)
    if percent:
        return percent
    for label in ("high", "medium", "low"):
        if f"confidence: {label}" in lowered or f"confidence={label}" in lowered:
            return label
    if "tillid" in lowered and "lav" in lowered:
        return "low"
    if "tillid" in lowered and "moderat" in lowered:
        return "medium"
    if "tillid" in lowered and "h" in lowered:
        return "high"
    return "medium"


def _extract_vote(text: str) -> str:
    lowered = str(text or "").lower()
    for label in ("approve", "reject", "hold", "revise"):
        if f"vote: {label}" in lowered or f"vote={label}" in lowered:
            return label
    if 'stemmer "ja"' in lowered or "stemmer ja" in lowered:
        return "approve"
    if 'stemmer "nej"' in lowered or "stemmer nej" in lowered:
        return "reject"
    if "udskyd" in lowered:
        return "hold"
    return ""


def _format_peer_context(messages: list[dict[str, object]], *, target_agent_id: str = "", limit: int = 16) -> str:
    relevant: list[dict[str, object]] = []
    for message in messages:
        peer_agent_id = str(message.get("peer_agent_id") or "")
        agent_id = str(message.get("agent_id") or "")
        if target_agent_id and peer_agent_id not in {"", target_agent_id} and agent_id != target_agent_id:
            continue
        relevant.append(message)
    return _format_messages(relevant, limit=limit)


def _detect_swarm_conflicts(outputs: list[dict]) -> dict:
    """Detect disagreements across swarm/council outputs."""
    _DISSENT_WORDS = {"disagree", "against", "however", "risk", "caution", "contradict", "concern", "but"}
    votes = [str(o.get("vote") or "").strip().lower() for o in outputs if o.get("vote")]
    vote_counts: dict[str, int] = {}
    for v in votes:
        if v:
            vote_counts[v] = vote_counts.get(v, 0) + 1
    has_vote_split = len(set(v for v in votes if v)) > 1
    disagreements = []
    for out in outputs:
        text = (out.get("text") or "").lower()
        if any(w in text for w in _DISSENT_WORDS):
            disagreements.append({"role": out.get("role", "?"), "excerpt": (out.get("text") or "")[:120]})
    return {
        "has_disagreement": bool(disagreements) or has_vote_split,
        "disagreements": disagreements[:4],
        "vote_split": vote_counts,
    }


def _load_council_model_config() -> list[dict]:
    """Read ~/.jarvis-v2/config/council_models.json, return role_models list."""
    try:
        import json
        from core.runtime.config import CONFIG_DIR
        path = CONFIG_DIR / "council_models.json"
        if path.exists():
            return json.loads(path.read_text()).get("role_models") or []
    except Exception:
        pass
    return []


def create_council_session_runtime(
    *,
    topic: str,
    roles: list[str] | None = None,
    owner_agent_id: str = "jarvis",
    member_models: list[dict] | None = None,
) -> dict[str, object]:
    roles = roles or COUNCIL_ROLE_ORDER[:4]
    # Fall back to persisted config if caller didn't supply explicit overrides
    member_models = member_models if member_models is not None else _load_council_model_config()
    council_id = f"council-{uuid4().hex}"
    create_council_session(
        council_id=council_id,
        owner_agent_id=owner_agent_id,
        topic=topic,
        status="forming",
        summary=f"Council formed around: {topic}",
    )
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=f"council-thread-{council_id}",
        council_id=council_id,
        direction="jarvis->council",
        role="system",
        kind="council-brief",
        content=topic,
    )
    for role in roles:
        role_model = next((m for m in member_models if m.get("role") == role), {})
        agent = spawn_agent_task(
            role=role,
            goal=f"Council topic: {topic}",
            parent_agent_id=owner_agent_id,
            auto_execute=False,
            council_id=council_id,
            provider=str(role_model.get("provider") or ""),
            model=str(role_model.get("model") or ""),
        )
        update_agent_registry_entry(str(agent.get("agent_id") or ""), status="waiting")
        add_council_member(
            council_id=council_id,
            agent_id=str(agent.get("agent_id") or ""),
            role=role,
            position_summary="awaiting deliberation",
            confidence="pending",
        )
    update_council_session(council_id, status="deliberating")
    return build_council_detail_surface(council_id) or {}


def create_swarm_session_runtime(
    *,
    topic: str,
    roles: list[str] | None = None,
    owner_agent_id: str = "jarvis",
    member_models: list[dict] | None = None,
) -> dict[str, object]:
    roles = roles or SWARM_ROLE_ORDER[:4]
    member_models = member_models or []
    council_id = f"swarm-{uuid4().hex}"
    create_council_session(
        council_id=council_id,
        owner_agent_id=owner_agent_id,
        topic=topic,
        status="forming",
        mode="swarm",
        summary=f"Swarm formed around: {topic}",
    )
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=_council_thread_id(council_id),
        council_id=council_id,
        direction="jarvis->swarm",
        role="system",
        kind="swarm-brief",
        content=topic,
    )
    for role in roles:
        role_model = next((m for m in member_models if m.get("role") == role), {})
        agent = spawn_agent_task(
            role=role,
            goal=f"Swarm topic: {topic}",
            parent_agent_id=owner_agent_id,
            auto_execute=False,
            council_id=council_id,
            provider=str(role_model.get("provider") or ""),
            model=str(role_model.get("model") or ""),
        )
        update_agent_registry_entry(str(agent.get("agent_id") or ""), status="waiting")
        add_council_member(
            council_id=council_id,
            agent_id=str(agent.get("agent_id") or ""),
            role=role,
            position_summary="awaiting swarm dispatch",
            confidence="pending",
        )
    update_council_session(council_id, status="deliberating")
    return build_council_detail_surface(council_id) or {}


def post_council_message(
    *,
    council_id: str,
    content: str,
    kind: str = "jarvis-note",
    role: str = "user",
) -> dict[str, object]:
    session = get_council_session(council_id)
    if session is None:
        raise RuntimeError(f"unknown council: {council_id}")
    create_agent_message(
        message_id=f"agent-msg-{uuid4().hex}",
        thread_id=f"council-thread-{council_id}",
        council_id=council_id,
        direction="jarvis->council",
        role=role,
        kind=kind,
        content=str(content or "").strip(),
    )
    update_council_session(council_id, status="deliberating")
    return build_council_detail_surface(council_id) or session


def _derive_initiative(synthesis: str, *, topic: str = "") -> str:
    """Distil a short, actionable initiative string from a synthesis.

    Axis 5: the council/swarm conclusion must be able to LAND. This turns
    free-form synthesis prose into one compact action line a downstream
    consumer can push as an initiative. Heuristic + self-safe (never
    raises): prefer an explicit recommendation/next-step sentence; else
    fall back to the first substantive sentence; else "".
    """
    text = " ".join(str(synthesis or "").split())
    if not text:
        return ""
    import re as _re
    # Split into sentences, keep non-trivial ones.
    sentences = [s.strip() for s in _re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 12]
    if not sentences:
        return ""
    # Prefer a sentence that reads like an action / recommendation.
    action_markers = (
        "recommend", "should", "next step", "propose", "anbefal", "bør",
        "næste skridt", "foreslå", "action", "initiativ", "vi kan", "let's",
    )
    lowered_pairs = [(s, s.lower()) for s in sentences]
    for original, low in lowered_pairs:
        if any(marker in low for marker in action_markers):
            return original[:280]
    # No explicit action → take the first substantive sentence as the seed.
    return sentences[0][:280]


def _augment_council_surface(
    council_id: str, *, conclusion: str, initiative: str = "",
) -> dict[str, object]:
    """Build the collective-round return dict with conclusion + initiative.

    Wraps ``build_council_detail_surface`` and stamps the Axis 5 contract
    fields (``conclusion`` + ``initiative``) onto it. Self-safe: falls back
    to a minimal dict if the surface build fails.
    """
    # Resolve through the facade so ``monkeypatch.setattr(agent_runtime,
    # "build_council_detail_surface", ...)`` is honored across the split.
    surface = _facade().build_council_detail_surface(council_id) or {}
    if not isinstance(surface, dict):
        surface = {}
    surface["conclusion"] = str(conclusion or "")
    surface["initiative"] = str(initiative or "")
    return surface


def _run_collective_round(council_id: str, *, mode: str) -> dict[str, object]:
    """Run one collective (council or swarm) round to a conclusion.

    RETURN CONTRACT (Axis 5 — synthese der lander):
      Returns the council/swarm detail surface (from
      ``build_council_detail_surface``) augmented with a top-level
      ``initiative`` key:
        {
          ... surface fields (council_id, status, summary, members, ...),
          "conclusion": <str>,   # the synthesis text (mirrors summary)
          "initiative": <str>,   # a short, actionable next-step string
                                 # derived from the synthesis, or "" when
                                 # nothing actionable surfaced.
        }
      The ``initiative`` field replaces the old hardcoded None so a caller
      (e.g. the autonomous council daemon) can turn a conclusion into a real
      initiative (push_initiative / surface-to-owner) instead of a dead
      summary row. It is a plain string (possibly empty) — never None — so
      ``if result.get("initiative"):`` is the correct truthiness check.
    """
    from core.services.council_deliberation_controller import (
        DeliberationController,
        DeliberationResult,
    )

    session = get_council_session(council_id)
    if session is None:
        raise RuntimeError(f"unknown council: {council_id}")
    thread_id = _council_thread_id(council_id)
    messages = list_agent_messages(council_id=council_id, thread_id=thread_id, limit=160)
    members = list_council_members(council_id=council_id)
    update_council_session(council_id, status="deliberating")
    round_outputs: list[dict[str, str]] = []
    coordinator = members[-1] if mode == "swarm" and members else None
    workers = [
        m for m in members
        if coordinator is None or str(m.get("agent_id") or "") != str(coordinator.get("agent_id") or "")
    ]

    # ── Worker execution ───────────────────────────────────────────────
    def _run_one_worker(member: dict) -> dict[str, str] | None:
        agent_id = str(member.get("agent_id") or "")
        agent = get_agent_registry_entry(agent_id)
        if agent is None:
            return None
        member_role = str(member.get("role") or agent.get("role") or "member")
        update_agent_registry_entry(agent_id, status="active", last_error="")
        prompt = (
            f"System prompt:\n{agent.get('system_prompt') or ''}\n\n"
            f"{'Swarm' if mode == 'swarm' else 'Council'} topic: {session.get('topic') or ''}\n"
            f"Your role: {member_role}\n\n"
            f"{'Collective' if mode == 'swarm' else 'Council'} transcript so far:\n"
            f"{_format_messages(messages, limit=18)}\n\n"
            "Respond to the collective. Include compact sections for summary, recommendation, confidence, and vote."
        )
        run_id = f"agent-run-{uuid4().hex}"
        create_agent_run(
            run_id=run_id, agent_id=agent_id, status="starting",
            execution_mode=mode, provider=str(agent.get("provider") or ""),
            model=str(agent.get("model") or ""),
            input_summary=str(session.get("topic") or ""),
            input_payload_json=json.dumps({"prompt": prompt, "council_id": council_id, "mode": mode}),
            started_at=_now_iso(),
        )
        try:
            result = _facade().execute_with_role_or_fallback(
                message=prompt,
                provider=str(agent.get("provider") or ""),
                model=str(agent.get("model") or ""),
                requires_tools=_role_needs_tools(str(agent.get("role") or "")),
                lane="council",
            )
            text = str(result.get("text") or "").strip()
            create_agent_message(
                message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
                run_id=run_id, council_id=council_id, agent_id=agent_id,
                direction="agent->council" if mode == "council" else "agent->swarm",
                role="assistant",
                kind="council-position" if mode == "council" else "swarm-work",
                content=text,
            )
            if mode == "swarm" and coordinator is not None:
                send_peer_message(
                    from_agent_id=agent_id,
                    to_agent_id=str(coordinator.get("agent_id") or ""),
                    content=f"{member_role}: {_trim(text, 220)}",
                    kind="swarm-hand-off",
                )
            update_agent_run(
                run_id, status="completed", output_summary=_trim(text),
                output_payload_json=json.dumps(result), finished_at=_now_iso(),
                input_tokens=int(result.get("input_tokens") or 0),
                output_tokens=int(result.get("output_tokens") or 0),
                cost_usd=float(result.get("cost_usd") or 0.0),
                provider_status=str(result.get("status") or "completed"),
            )
            update_agent_registry_entry(
                agent_id, status="waiting",
                tokens_burned_delta=int(result.get("input_tokens") or 0) + int(result.get("output_tokens") or 0),
                completed_at=_now_iso(),
            )
            update_council_member(
                council_id=council_id, agent_id=agent_id,
                position_summary=_trim(text),
                vote=_extract_vote(text), confidence=_extract_confidence(text),
            )
            return {"role": member_role, "agent_id": agent_id, "text": text, "vote": _extract_vote(text)}
        except Exception as exc:
            err = str(exc)
            create_agent_message(
                message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
                run_id=run_id, council_id=council_id, agent_id=agent_id,
                direction="agent->council" if mode == "council" else "agent->swarm",
                role="assistant",
                kind="council-failure" if mode == "council" else "swarm-failure",
                content=err,
            )
            update_agent_run(run_id, status="failed", finished_at=_now_iso(), failure_reason=err, provider_status="failed")
            update_agent_registry_entry(agent_id, status="failed", failure_increment=1, last_error=err)
            update_council_member(council_id=council_id, agent_id=agent_id, position_summary=f"failed: {_trim(err)}", confidence="low")
            return None

    # Swarm: parallel fanout; Council: sequential (preserves deliberation order)
    if mode == "swarm" and len(workers) > 1:
        with ThreadPoolExecutor(max_workers=min(len(workers), MAX_SWARM_WORKERS)) as pool:
            futures = [pool.submit(_run_one_worker, m) for m in workers]
            for fut in as_completed(futures):
                try:
                    out = fut.result()
                    if out:
                        round_outputs.append(out)
                except Exception as exc:
                    logger.warning("swarm worker thread failed: %s", exc)
    else:
        for member in workers:
            out = _run_one_worker(member)
            if out:
                round_outputs.append(out)

    # ── Swarm coordinator merge ────────────────────────────────────────
    if mode == "swarm" and coordinator is not None:
        coordinator_id = str(coordinator.get("agent_id") or "")
        coordinator_agent = get_agent_registry_entry(coordinator_id)
        if coordinator_agent is not None:
            peer_messages = list_agent_messages(council_id=council_id, thread_id=thread_id, limit=200)
            handoffs = _format_peer_context(peer_messages, target_agent_id=coordinator_id, limit=22)
            conflicts = _detect_swarm_conflicts(round_outputs)
            conflict_note = ""
            if conflicts["has_disagreement"]:
                conflict_note = (
                    "\n\nNote: Workers show disagreement. Capture dissent explicitly in your synthesis."
                    f" Conflicting signals: {json.dumps(conflicts['vote_split'])}"
                )
            update_agent_registry_entry(coordinator_id, status="active", last_error="")
            prompt = (
                f"System prompt:\n{coordinator_agent.get('system_prompt') or ''}\n\n"
                f"Swarm topic: {session.get('topic') or ''}\n"
                "Your role: swarm coordinator / synthesizer\n\n"
                "Worker handoffs:\n"
                f"{handoffs}{conflict_note}\n\n"
                "Produce the merged swarm result back to Jarvis. Include summary, findings, "
                "recommendation, confidence, blockers, and any dissenting_opinions."
            )
            run_id = f"agent-run-{uuid4().hex}"
            create_agent_run(
                run_id=run_id, agent_id=coordinator_id, status="starting",
                execution_mode="swarm",
                provider=str(coordinator_agent.get("provider") or ""),
                model=str(coordinator_agent.get("model") or ""),
                input_summary=str(session.get("topic") or ""),
                input_payload_json=json.dumps({
                    "prompt": prompt, "council_id": council_id, "mode": "swarm",
                    "coordinator": True, "conflicts": conflicts,
                }),
                started_at=_now_iso(),
            )
            result = _facade().execute_with_role_or_fallback(
                message=prompt,
                provider=str(coordinator_agent.get("provider") or ""),
                model=str(coordinator_agent.get("model") or ""),
                requires_tools=_role_needs_tools(str(coordinator_agent.get("role") or "")),
                lane="council",
            )
            synthesis = str(result.get("text") or "").strip()
            create_agent_message(
                message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
                run_id=run_id, council_id=council_id, agent_id=coordinator_id,
                direction="swarm->jarvis", role="assistant", kind="swarm-synthesis",
                content=synthesis,
            )
            update_agent_run(
                run_id, status="completed", output_summary=_trim(synthesis),
                output_payload_json=json.dumps(result), finished_at=_now_iso(),
                input_tokens=int(result.get("input_tokens") or 0),
                output_tokens=int(result.get("output_tokens") or 0),
                cost_usd=float(result.get("cost_usd") or 0.0),
                provider_status=str(result.get("status") or "completed"),
            )
            update_agent_registry_entry(
                coordinator_id, status="waiting",
                tokens_burned_delta=int(result.get("input_tokens") or 0) + int(result.get("output_tokens") or 0),
                completed_at=_now_iso(),
            )
            update_council_member(
                council_id=council_id, agent_id=coordinator_id,
                position_summary=_trim(synthesis),
                vote=_extract_vote(synthesis), confidence=_extract_confidence(synthesis),
            )
            summary_with_meta = _trim(synthesis, 600)
            if conflicts["has_disagreement"]:
                summary_with_meta += f" [conflicts: {json.dumps(conflicts['vote_split'])}]"
            update_council_session(council_id, status="reporting", summary=summary_with_meta)
            # Axis 5: swarm synthesis also lands as an initiative.
            initiative = _derive_initiative(synthesis, topic=str(session.get("topic") or ""))
            return _augment_council_surface(
                council_id, conclusion=synthesis, initiative=initiative,
            )

    # ── Council deliberation (controller-based) ────────────────────────
    if mode == "council":
        member_map = {str(m.get("role") or "member"): m for m in workers}

        class _RuntimeController(DeliberationController):
            def _run_round(self_inner) -> list[str]:
                outputs = []
                for role in self_inner.active_members:
                    member = member_map.get(role)
                    if member is None:
                        continue
                    out = _run_one_worker(member)
                    if out:
                        outputs.append(f"{out['role']}: {out['text'][:300]}")
                return outputs or [f"(no output from {', '.join(self_inner.active_members)})"]

            def _synthesize(self_inner, *, forced: bool = False) -> str:
                transcript = "\n".join(self_inner._transcript_lines[-12:])
                forced_note = (
                    "\n\nNote: Rådet er gået i stå. Konkluder på baggrund af hvad der foreligger."
                    if forced else ""
                )
                prompt = (
                    f"Council topic: {str(session.get('topic') or '')}\n"
                    f"Your role: synthesizer\n\n"
                    f"Council transcript:\n{transcript}{forced_note}\n\n"
                    "Produce a council conclusion in 2-4 sentences."
                )
                synth_member = member_map.get("synthesizer") or {}
                result = _facade().execute_with_role_or_fallback(
                    message=prompt,
                    provider=str(synth_member.get("provider") or ""),
                    model=str(synth_member.get("model") or ""),
                    requires_tools=_role_needs_tools("synthesizer"),
                    lane="council",
                )
                return str(result.get("text") or "").strip()

        ctrl = _RuntimeController(
            topic=str(session.get("topic") or ""),
            members=[str(m.get("role") or "member") for m in workers],
            max_rounds=8,
        )
        dr: DeliberationResult = ctrl.run()
        refreshed_members = list_council_members(council_id=council_id)
        synthesis = _build_council_role_prefixed_summary(refreshed_members)

        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
            council_id=council_id, direction="council->jarvis",
            role="assistant", kind="council-synthesis", content=synthesis,
        )
        update_council_session(council_id, status="reporting", summary=synthesis)
        # Axis 5: derive an actionable initiative from the synthesis so the
        # conclusion can LAND (no longer hardcoded None → dead output).
        initiative = _derive_initiative(synthesis, topic=str(session.get("topic") or ""))
        # Persist to council memory
        try:
            from core.services.council_memory_service import append_council_conclusion
            append_council_conclusion(
                topic=str(session.get("topic") or ""),
                score=0.0,
                members=[str(m.get("role") or "") for m in members],
                signals=[],
                transcript=dr.transcript[:1200],
                conclusion=synthesis[:600],
                initiative=(initiative or None),
            )
        except Exception:
            pass
        return _augment_council_surface(council_id, conclusion=synthesis, initiative=initiative)

    # ── Council synthesis (fallback for non-council modes) ─────────────
    if round_outputs:
        conflicts = _detect_swarm_conflicts(round_outputs)
        synthesis = " | ".join(f"{item['role']}: {_trim(item['text'], 180)}" for item in round_outputs[:5])
        if conflicts["has_disagreement"]:
            synthesis += f" [dissent: {json.dumps(conflicts['vote_split'])}]"
        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
            council_id=council_id, direction="council->jarvis",
            role="assistant", kind="council-synthesis", content=synthesis,
        )
        update_council_session(council_id, status="reporting", summary=synthesis)
        initiative = _derive_initiative(synthesis, topic=str(session.get("topic") or ""))
        return _augment_council_surface(council_id, conclusion=synthesis, initiative=initiative)
    update_council_session(council_id, status="reporting", summary=f"No {mode} outputs produced.")
    return _augment_council_surface(council_id, conclusion="", initiative="")


def _close_council_agents(council_id: str) -> None:
    """Mark all council member agents as completed to release spawn slots.

    Council agents are left in 'waiting' status after _run_collective_round.
    Without this cleanup they count toward MAX_CONCURRENT_AGENTS and block
    future councils from spawning.
    """
    try:
        members = list_council_members(council_id=council_id)
        for member in members:
            agent_id = str(member.get("agent_id") or "")
            if not agent_id:
                continue
            agent = get_agent_registry_entry(agent_id)
            if agent is None:
                continue
            if str(agent.get("status") or "") in _ACTIVE_STATUSES:
                update_agent_registry_entry(agent_id, status="completed", completed_at=_now_iso())
        update_council_session(council_id, status="closed", finished_at=_now_iso())
    except Exception as exc:
        logger.warning("_close_council_agents: cleanup failed for %s: %s", council_id, exc)


def _build_council_role_prefixed_summary(members: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for member in members:
        role = str(member.get("role") or "member").strip() or "member"
        position = str(member.get("position_summary") or "").strip()
        if not position or position == "awaiting deliberation":
            continue
        parts.append(f"{role}: {position}")
    return "\n".join(parts) if parts else "no council positions recorded"


def run_council_round(council_id: str) -> dict[str, object]:
    """Run one council round and ALWAYS close the session afterwards.

    Axis 5-lifecycle fix: the close was previously only reached on the happy
    path — an exception in _run_collective_round left the session
    'deliberating' forever and its member agents in 'waiting', accumulating
    against MAX_CONCURRENT_AGENTS and blocking future councils. try/finally
    guarantees _close_council_agents runs even on failure.
    """
    # Resolve through the facade so tests patching agent_runtime._run_collective_round
    # / ._close_council_agents are honored across the split (behavior-preserving).
    try:
        return _facade()._run_collective_round(council_id, mode="council")
    finally:
        _facade()._close_council_agents(council_id)


def run_swarm_round(council_id: str) -> dict[str, object]:
    """Run one swarm round and ALWAYS close the session afterwards.

    Same try/finally close guarantee as run_council_round — see its
    docstring for the hang the Axis 5-lifecycle fix removes.
    """
    try:
        return _facade()._run_collective_round(council_id, mode="swarm")
    finally:
        _facade()._close_council_agents(council_id)
