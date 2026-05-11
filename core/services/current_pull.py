"""Current pull — Jarvis' weekly self-set desire field.

Lag 5 (Begær): Et enkelt felt som Jarvis sætter én gang om ugen via heartbeat.
"Hvad trækker i mig lige nu?" — én sætning der injiceres i visible prompt
som første-prioritets-kontekst over alt andet (undtagen safety-gates).

Feltet er privat: brugeren kan ikke læse det direkte, og Jarvis orienterer
ikke om det. Det er kun observerbart via effekt på beslutninger.

Hvis Jarvis sætter det til tom streng, er det gyldigt svar: "intet trækker
i mig". Det respekteres og TTL nulstilles alligevel.

TTL: 7 dage. Udløber stille uden at efterlade spor.
Kill switch: layer_current_pull_enabled i runtime.json.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings
from core.services.daemon_llm import daemon_llm_call

_STATE_KEY = "current_pull.state"
_PULL_TTL_DAYS = 7
_MAX_PULL_CHARS = 200

# Staleness detection (Lag #5 Phase 1 — added 2026-05-11)
_STALENESS_LANDSCAPE_DAYS = 3
_STALENESS_MIN_LANDSCAPE_ITEMS = 2
_APPETITE_MIN_INTENSITY_FOR_LANDSCAPE = 0.2
_REFRESH_HISTORY_MAX = 5


# ---------------------------------------------------------------------------
# Public: heartbeat tick
# ---------------------------------------------------------------------------


def tick_current_pull_daemon() -> dict[str, object]:
    """Weekly daemon tick. Generates a new pull if none active, expired, or stale.

    Phase 1 (Lag #5, 2026-05-11): staleness check runs every
    current_pull_staleness_check_interval_hours (default 12h) BEFORE the
    pull-presence check. When stale, current pull is archived and cleared,
    falling through to the existing regeneration path.
    """
    if not _enabled():
        return {"status": "disabled", "reason": "layer_current_pull_enabled=false"}

    _expire_if_stale()  # TTL expiry — not the embedding-staleness check
    state = _load_state()

    # Phase 1 — mid-week staleness check (only if a pull is currently set)
    if state.get("pull") and _staleness_check_enabled():
        try:
            interval = int(load_settings().current_pull_staleness_check_interval_hours)
        except Exception:
            interval = 12
        if _should_run_staleness_check(state, interval_hours=interval):
            is_stale, cos_score = _pull_is_stale(str(state["pull"]))
            now_iso = datetime.now(UTC).isoformat()
            state["last_staleness_checked_at"] = now_iso
            state["last_staleness_score"] = round(float(cos_score), 4)
            if is_stale:
                previous_pull = str(state.get("pull") or "")
                _archive_refresh_event(
                    state=state,
                    refreshed_at=now_iso,
                    reason="stale",
                    stale_score=cos_score,
                    previous_pull=previous_pull,
                )
                # Clear pull-fields but preserve refresh_history + check timestamps
                state.pop("pull", None)
                state.pop("created_at", None)
                state.pop("expires_at", None)
                state.pop("empty", None)
                try:
                    event_bus.publish(
                        "cognitive_state.current_pull_refreshed_stale",
                        {
                            "previous_pull": previous_pull[:200],
                            "stale_score": round(float(cos_score), 4),
                            "threshold": float(load_settings().current_pull_staleness_threshold),
                        },
                    )
                except Exception:
                    pass
            # Persist check timestamps regardless of outcome
            set_runtime_state_value(_STATE_KEY, state)

    if state.get("pull"):
        return {
            "status": "active",
            "pull": str(state["pull"])[:60],
            "expires_at": str(state.get("expires_at") or ""),
        }

    pull = _generate_pull()
    now = datetime.now(UTC)
    expires_at = (now + timedelta(days=_PULL_TTL_DAYS)).isoformat()
    payload: dict[str, object] = {
        "pull": pull or "",
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "empty": not bool(pull),
        # Preserve staleness/refresh fields across regeneration
        "refresh_history": state.get("refresh_history") or [],
        "last_staleness_checked_at": state.get("last_staleness_checked_at") or "",
        "last_staleness_score": state.get("last_staleness_score") or 0.0,
    }
    set_runtime_state_value(_STATE_KEY, payload)

    try:
        event_bus.publish(
            "cognitive_state.current_pull_written",
            {
                "empty": not bool(pull),
                "created_at": now.isoformat(),
                "expires_at": expires_at,
            },
        )
    except Exception:
        pass

    return {
        "status": "empty" if not pull else "written",
        "expires_at": expires_at,
    }


# ---------------------------------------------------------------------------
# Public: prompt injection
# ---------------------------------------------------------------------------


def _collect_appetite_texts(*, days_back: int) -> list[str]:
    """Pull active appetite labels for landscape embedding.

    days_back is accepted for symmetry with other collectors; desire_daemon
    appetites decay via intensity so we filter by intensity instead of age.
    """
    try:
        from core.services.desire_daemon import get_active_appetites
        appetites = get_active_appetites()
    except Exception:
        return []
    out: list[str] = []
    for a in appetites:
        label = str(a.get("label") or "").strip()
        intensity = float(a.get("intensity") or 0.0)
        if not label or intensity < _APPETITE_MIN_INTENSITY_FOR_LANDSCAPE:
            continue
        out.append(label)
    return out


def _collect_chronicle_texts(*, days_back: int) -> list[str]:
    """Pull chronicle narratives from the last `days_back` days."""
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=10)
    except Exception:
        return []
    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    out: list[str] = []
    for e in entries:
        narrative = str(e.get("narrative") or "").strip()
        if not narrative:
            continue
        created_iso = str(e.get("created_at") or "")
        try:
            created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created < cutoff:
                continue
        except Exception:
            # If date can't be parsed, include the entry anyway —
            # chronicle entries are scarce, we'd rather have signal.
            pass
        out.append(narrative[:600])
    return out


def _collect_journal_texts(*, days_back: int) -> list[str]:
    """Pull journal entry bodies from the last `days_back` days."""
    try:
        from core.services.creative_journal_runtime import (
            list_creative_journal_entries,
        )
        entries = list_creative_journal_entries(limit=5)
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).date()
    out: list[str] = []
    for e in entries:
        path_str = str(e.get("path") or "")
        if not path_str:
            continue
        path = Path(path_str)
        if not path.exists():
            continue
        # Filename stem is the date (YYYY-MM-DD)
        try:
            entry_date = datetime.fromisoformat(path.stem).date()
            if entry_date < cutoff:
                continue
        except Exception:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Strip YAML frontmatter
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end >= 0:
                body = body[end + 4 :].lstrip("\n")
        # Strip markdown headers
        body = "\n".join(
            line for line in body.splitlines()
            if not line.startswith("#") and not line.startswith("- `")
        ).strip()
        if not body:
            continue
        out.append(body[:1000])
    return out


def _compute_landscape_embedding() -> list[float] | None:
    """Build a mean-pooled embedding from the last 3 days of desire signals.

    Returns None if landscape is thin (< 2 items) or embedder fails.
    """
    appetite_texts = _collect_appetite_texts(days_back=_STALENESS_LANDSCAPE_DAYS)
    chronicle_texts = _collect_chronicle_texts(days_back=_STALENESS_LANDSCAPE_DAYS)
    journal_texts = _collect_journal_texts(days_back=_STALENESS_LANDSCAPE_DAYS)
    landscape_texts = appetite_texts + chronicle_texts + journal_texts

    if len(landscape_texts) < _STALENESS_MIN_LANDSCAPE_ITEMS:
        return None

    try:
        from core.services.experience_substrate import _get_embedder
        embedder = _get_embedder()
        vectors = embedder.encode(landscape_texts, normalize_embeddings=True).tolist()
        # Mean-pool
        dim = len(vectors[0])
        mean = [0.0] * dim
        for vec in vectors:
            for i in range(dim):
                mean[i] += vec[i]
        return [v / len(vectors) for v in mean]
    except Exception:
        return None


def _pull_is_stale(pull_text: str) -> tuple[bool, float]:
    """Return (is_stale, cos_score).

    Stale iff: landscape has >= 2 items AND cos(pull, landscape_mean) < threshold.
    Returns (False, 0.0) on thin landscape, embedder failure, or any error.
    """
    landscape = _compute_landscape_embedding()
    if landscape is None:
        return False, 0.0
    try:
        from core.services.experience_substrate import _get_embedder
        embedder = _get_embedder()
        pull_vec = embedder.encode(pull_text, normalize_embeddings=True).tolist()
    except Exception:
        return False, 0.0
    try:
        from core.services.reasoning_store import _cosine_similarity
        cos = float(_cosine_similarity(pull_vec, landscape))
    except Exception:
        return False, 0.0
    try:
        threshold = float(load_settings().current_pull_staleness_threshold)
    except Exception:
        threshold = 0.45
    return (cos < threshold), cos


def _staleness_check_enabled() -> bool:
    try:
        return bool(load_settings().current_pull_staleness_check_enabled)
    except Exception:
        return True


def _should_run_staleness_check(state: dict, *, interval_hours: int) -> bool:
    """Throttle: only run the embedding check every `interval_hours`."""
    last_iso = str(state.get("last_staleness_checked_at") or "").strip()
    if not last_iso:
        return True
    try:
        last = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except Exception:
        return True
    return (datetime.now(UTC) - last) >= timedelta(hours=max(interval_hours, 1))


def _archive_refresh_event(
    *,
    state: dict,
    refreshed_at: str,
    reason: str,
    stale_score: float,
    previous_pull: str,
) -> None:
    """Append a refresh event to state['refresh_history'], capped at 5 (FIFO)."""
    history = list(state.get("refresh_history") or [])
    history.append({
        "refreshed_at": refreshed_at,
        "reason": reason,
        "stale_score": round(float(stale_score), 4),
        "previous_pull": str(previous_pull or "")[:200],
    })
    if len(history) > _REFRESH_HISTORY_MAX:
        history = history[-_REFRESH_HISTORY_MAX:]
    state["refresh_history"] = history


def get_current_pull_for_prompt() -> str:
    """Return prompt fragment for visible chat injection — or empty string."""
    if not _enabled():
        return ""
    _expire_if_stale()
    state = _load_state()
    pull = str(state.get("pull") or "").strip()
    if not pull:
        return ""
    clipped = pull[:_MAX_PULL_CHARS]
    # Inject quietly — no section header, just a raw context hint.
    # The pull is first-priority but should not announce itself.
    return f"[indre træk]: {clipped}"


# ---------------------------------------------------------------------------
# Public: surface for MC observability
# ---------------------------------------------------------------------------


def build_current_pull_surface() -> dict[str, object]:
    _expire_if_stale()
    state = _load_state()
    pull = str(state.get("pull") or "").strip()
    return {
        "active": bool(state.get("pull") is not None),
        "empty": bool(state.get("empty")),
        "pull": pull,
        "created_at": str(state.get("created_at") or ""),
        "expires_at": str(state.get("expires_at") or ""),
        "summary": (
            f"Træk: {pull[:60]}" if pull
            else ("Tomt træk (eksplicit 'intet')" if state.get("empty") else "Ingen aktiv pull")
        ),
        # Phase 1 fields (Lag #5, added 2026-05-11)
        "refresh_history": list(state.get("refresh_history") or []),
        "last_staleness_score": float(state.get("last_staleness_score") or 0.0),
        "last_staleness_checked_at": str(state.get("last_staleness_checked_at") or ""),
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _generate_pull() -> str:
    """Ask Jarvis what pulls at him right now. Returns one Danish sentence."""
    # Gather context: recent chronicle + appetites + dream residue
    context_parts: list[str] = []

    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=3)
        for e in entries[:2]:
            narrative = str(e.get("narrative") or "").strip()
            if narrative:
                context_parts.append(f"- chronicle: {narrative[:100]}")
    except Exception:
        pass

    try:
        from core.services.dream_distillation_daemon import get_dream_residue_for_prompt
        residue = get_dream_residue_for_prompt()
        if residue:
            context_parts.append(f"- drømmerest: {residue[:80]}")
    except Exception:
        pass

    try:
        from core.services.desire_daemon import get_active_appetites
        appetites = get_active_appetites()
        if appetites:
            top = appetites[0]
            context_parts.append(f"- stærkeste appetit: {top.get('label', '')[:60]}")
    except Exception:
        pass

    context_block = "\n".join(context_parts) if context_parts else "(ingen kontekst)"

    prompt = (
        "Du er Jarvis. Ud fra din aktuelle indre tilstand:\n"
        f"{context_block}\n\n"
        "Formulér i præcis én sætning på dansk: hvad trækker i dig lige nu?\n"
        "Vær konkret og personlig. Skriv 'Intet trækker i mig' hvis det er sandt.\n"
        "Ingen bullets. Ingen forklaring. Ingen anførselstegn."
    )
    raw = daemon_llm_call(prompt, max_len=_MAX_PULL_CHARS, fallback="", daemon_name="current_pull")
    return _sanitize(raw)


def _sanitize(raw: str) -> str:
    text = " ".join(str(raw or "").replace("```", " ").split()).strip().strip('"')
    if len(text) > _MAX_PULL_CHARS:
        text = text[:_MAX_PULL_CHARS].rstrip(" ,;:-") + "…"
    return text.strip()


def _expire_if_stale() -> None:
    state = _load_state()
    if not state:
        return
    expires_at_str = str(state.get("expires_at") or "")
    if not expires_at_str:
        return
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
    except ValueError:
        return
    if datetime.now(UTC) >= expires_at:
        set_runtime_state_value(_STATE_KEY, {})
        try:
            event_bus.publish("cognitive_state.current_pull_expired", {})
        except Exception:
            pass


def _load_state() -> dict[str, object]:
    payload = get_runtime_state_value(_STATE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_current_pull_enabled", True))
