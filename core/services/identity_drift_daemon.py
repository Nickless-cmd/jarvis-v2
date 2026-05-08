"""Identity drift daemon — detect unauthorized changes to identity files.

Per Shapira et al. (NODES AI 2026, "Temporal Substrate Architecture"):
agenter uden formel identity-persistence udviser systematiske
produktions-fejl gennem "identity drift" — gradvis tab af konsistens
over tid. Vi har mutation-logging (identity_mutation_log) men ingen
aktiv detektor for ændringer der IKKE er logget gennem den kanal.

Denne daemon er detektoren. Kører hver 24t og:

  1. For hver watched identity-fil (SOUL, IDENTITY, USER, STANDING_ORDERS):
     - Hent nyeste snapshot fra workspace_prompt_versions
     - Sammenlign med current disk-content (sha256)
     - Hvis ændret OG ingen tilsvarende identity_mutation_log-entry:
       → Brug LLM til semantic diff ("authorized edit vs drift?")
       → Hvis drift: publish identity.drift_detected event
  2. Tag fresh snapshot uanset (cumulative timeline-data)

Lazy + best-effort: aldrig blocking, never raises. Snapshots går via
prompt_evolution som vi byggede tidligere — så daemon'en arver dens
dedup + rollback-kapabilitet "for free".
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 24

# Identity-bærende filer vi overvåger. Kun core-files — ikke transient
# arbejdsfiler. Filer der ikke findes springes over uden støj.
_WATCHED_FILES = ("SOUL.md", "IDENTITY.md", "USER.md", "STANDING_ORDERS.md")

# Time-window: hvis mutation_log har en entry for filen indenfor dette
# vindue FØR detect-tidspunktet, anses ændringen som "logged" og ingen
# drift fyrer. Stort vindue så mutation_log + drift-detection ikke
# race-conditions.
_MUTATION_LOG_LOOKBACK_HOURS = 48

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict[str, object] = {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _workspace_dir() -> Path:
    """Resolve the active workspace dir for identity files."""
    try:
        from core.identity.workspace_paths import ensure_default_workspace
        return ensure_default_workspace(name="default")
    except Exception:
        # Fallback to canonical path so daemon doesn't die on import quirks
        return Path.home() / ".jarvis-v2" / "workspaces" / "default"


def _was_change_logged(filename: str, change_at: datetime) -> bool:
    """Check identity_mutation_log for any entry on this file within
    the lookback window. Returns True = legitimate logged edit.
    """
    try:
        from core.services.identity_mutation_log import list_mutations
        recent = list_mutations(limit=50, target_filter=filename)
        if not recent:
            return False
        cutoff = change_at - timedelta(hours=_MUTATION_LOG_LOOKBACK_HOURS)
        for r in recent:
            ts_raw = str(r.get("recorded_at") or "").strip()
            if not ts_raw:
                continue
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
            except Exception:
                continue
            if cutoff <= ts <= change_at + timedelta(hours=1):
                return True
        return False
    except Exception as exc:
        logger.debug("identity_drift: mutation_log check failed: %s", exc)
        return False


def _classify_drift_via_llm(
    *, filename: str, prior_content: str, current_content: str
) -> dict[str, object]:
    """Ask the quality lane to classify the change.

    Returns dict with keys:
      - is_drift: bool
      - severity: 'minor'|'moderate'|'severe'|'unknown'
      - reasoning: short explanation
    Falls back to heuristic-based result if LLM unreachable.
    """
    # Cap content sizes so the prompt doesn't explode on big files.
    cap = 3000
    prior_snippet = prior_content[:cap]
    current_snippet = current_content[:cap]

    prompt = (
        f"Du analyserer en ændring i Jarvis' identity-fil '{filename}'.\n"
        f"PRIOR (sidste snapshot):\n```\n{prior_snippet}\n```\n\n"
        f"CURRENT (nuværende disk-state):\n```\n{current_snippet}\n```\n\n"
        "Ændringen er IKKE registreret i identity_mutation_log. "
        "Det betyder enten:\n"
        "  (a) Bjørn ændrede manuelt (legitimt, men ikke loggdet)\n"
        "  (b) Drift — Jarvis' identitet er glidet uden eksplicit godkendelse\n\n"
        "Returnér KUN gyldig JSON med følgende felter:\n"
        '  {"is_drift": true|false, "severity": "minor|moderate|severe", '
        '"reasoning": "kort dansk forklaring"}\n\n'
        "Drift er bekymrende hvis: identitets-claims ændres, kerneværdier "
        "tilføjes/fjernes, navngivne relationer flyttes, eller stil "
        "skifter væsentligt. Triviel formulering eller typo-fix er ikke drift."
    )
    try:
        from core.services.daemon_llm import quality_daemon_llm_call
        raw = quality_daemon_llm_call(
            prompt, max_len=600, daemon_name="identity_drift", fallback="",
        )
    except Exception as exc:
        logger.debug("identity_drift: LLM call failed: %s", exc)
        return {"is_drift": True, "severity": "unknown", "reasoning": f"llm-unreachable:{exc}"}

    if not raw:
        return {"is_drift": True, "severity": "unknown", "reasoning": "llm-empty"}

    try:
        import json as _json
        # Find first { and matching last } — robust against prefix prose.
        s = raw.find("{")
        e = raw.rfind("}")
        if s < 0 or e <= s:
            return {"is_drift": True, "severity": "unknown",
                    "reasoning": f"unparseable-llm:{raw[:80]}"}
        parsed = _json.loads(raw[s : e + 1])
        return {
            "is_drift": bool(parsed.get("is_drift", True)),
            "severity": str(parsed.get("severity") or "unknown"),
            "reasoning": str(parsed.get("reasoning") or "")[:300],
        }
    except Exception as exc:
        logger.debug("identity_drift: JSON parse failed: %s", exc)
        return {"is_drift": True, "severity": "unknown",
                "reasoning": f"parse-failed:{exc}"}


def _check_one_file(workspace_dir: Path, filename: str, now: datetime) -> dict[str, object]:
    """Examine one watched file. Returns a per-file result dict."""
    file_path = workspace_dir / filename
    if not file_path.exists():
        return {"filename": filename, "status": "skipped-missing"}

    try:
        current = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        return {"filename": filename, "status": f"read-failed:{exc}"}
    current_sha = _sha256(current)

    # Look up the most recent snapshot before now. We use list_prompt_history.
    try:
        from core.services.prompt_evolution import (
            get_version,
            list_prompt_history,
            snapshot_workspace_file,
        )
    except Exception as exc:
        return {"filename": filename, "status": f"prompt_evolution-import-failed:{exc}"}

    history = list_prompt_history(filename=filename, limit=5)
    if not history:
        # First time we see this file — take baseline snapshot, no drift.
        snapshot_workspace_file(
            filename=filename,
            content=current,
            reason="identity_drift_daemon: baseline",
            created_by="identity_drift_daemon",
        )
        return {"filename": filename, "status": "baseline-taken"}

    last = history[0]
    last_sha = str(last.get("content_sha256") or "")
    if last_sha == current_sha:
        # Unchanged. Refresh-snapshot er no-op via prompt_evolution dedup.
        return {"filename": filename, "status": "unchanged"}

    # ── Change detected. Was it logged in identity_mutation_log?
    last_seen_at_raw = str(last.get("created_at") or "")
    try:
        last_seen_at = datetime.fromisoformat(last_seen_at_raw.replace("Z", "+00:00"))
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=UTC)
    except Exception:
        last_seen_at = now - timedelta(days=1)

    if _was_change_logged(filename, last_seen_at):
        # Legitimate change — refresh snapshot, no drift.
        snapshot_workspace_file(
            filename=filename,
            content=current,
            reason="identity_drift_daemon: refresh after logged mutation",
            created_by="identity_drift_daemon",
        )
        return {"filename": filename, "status": "logged-mutation"}

    # ── Unlogged change. Pull the prior content for LLM diff.
    prior_version = get_version(version_id=str(last.get("version_id") or ""))
    prior_content = str((prior_version or {}).get("content") or "")
    classification = _classify_drift_via_llm(
        filename=filename,
        prior_content=prior_content,
        current_content=current,
    )

    if classification.get("is_drift"):
        try:
            event_bus.publish(
                "identity.drift_detected",
                {
                    "filename": filename,
                    "severity": classification.get("severity"),
                    "reasoning": classification.get("reasoning"),
                    "prior_version_id": last.get("version_id"),
                    "prior_sha256": last_sha,
                    "current_sha256": current_sha,
                    "detected_at": _now_iso(),
                },
            )
        except Exception as exc:
            logger.debug("identity_drift: event publish failed: %s", exc)

    # Always refresh the snapshot so next cycle starts from current state.
    snapshot_workspace_file(
        filename=filename,
        content=current,
        reason=(
            "identity_drift_daemon: drift detected" if classification.get("is_drift")
            else "identity_drift_daemon: trivial change refresh"
        ),
        created_by="identity_drift_daemon",
    )
    return {
        "filename": filename,
        "status": "drift" if classification.get("is_drift") else "trivial",
        "severity": classification.get("severity"),
        "reasoning": classification.get("reasoning"),
    }


# ---------------------------------------------------------------------------
# Daemon tick
# ---------------------------------------------------------------------------


def tick_identity_drift_daemon() -> dict[str, object]:
    """Run one identity-drift detection cycle if cadence elapsed."""
    global _last_tick_at, _last_result

    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"checked": False}

    workspace_dir = _workspace_dir()
    per_file: list[dict[str, object]] = []
    drift_count = 0
    for filename in _WATCHED_FILES:
        try:
            r = _check_one_file(workspace_dir, filename, now)
        except Exception as exc:
            logger.warning(
                "identity_drift: %s check failed: %s", filename, exc, exc_info=True,
            )
            r = {"filename": filename, "status": f"error:{exc}"}
        per_file.append(r)
        if r.get("status") == "drift":
            drift_count += 1

    _last_tick_at = now
    _last_result = {
        "checked_at": _now_iso(),
        "files": per_file,
        "drift_count": drift_count,
    }
    return {"checked": True, **_last_result}


# ---------------------------------------------------------------------------
# Surface for runtime awareness
# ---------------------------------------------------------------------------


def build_identity_drift_surface() -> dict[str, object]:
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "last_result": _last_result,
    }
