"""Ground Truth Registry — Layer 3 of the Lying Engine.

A registry of known stable facts about Jarvis himself, maintained
independently of code and runtime state. Populated by a weekly heartbeat
daemon and optionally refreshed on demand.

Queried by the Claim Scanner (Layer 2) for categories:
  - ⚙️ system  — host, paths, model, provider
  - 🧮 statistik — expression count, daemon count, commit count

Design:
  - Ground truths are collected lazily and cached with a 1-hour TTL.
  - The daemon tick force-refreshes the cache.
  - The registry returns (verified: bool, correct_value: str|None) so
    the Claim Scanner can repair claims that mismatch reality.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Paths ───────────────────────────────────────────────────────────────

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
REPO_PATH = Path("/media/projects/jarvis-v2")
# 2026-05-22 (Claude, after Codex audit): DB_PATH previously pointed at
# REPO_PATH/state/jarvis.db — that file is 0 bytes (stale, never written
# to by runtime). The actual runtime DB lives in JARVIS_HOME/state/jarvis.db
# (~1 GB of live data). Reading from the repo path meant Ground Truth
# Registry's DB-derived facts (commit_count, expression_count, etc.) were
# all defaults — every "verified" claim against this registry was bogus.
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"
CONFIG_PATH = JARVIS_HOME / "config" / "runtime.json"

# ── Infrastructure facts ────────────────────────────────────────────────
# Static, hand-maintained facts about Jarvis' deployment infrastructure
# that can be verified by Claim Scanner. Codex audit 2026-05-22 flagged
# the Claim Scanner domain/path coverage gap — previously only repo_path
# and db_path were checked. These facts let the scanner catch wrong
# IPs/hosts/paths/ports that Jarvis might fabricate.
#
# Update when infrastructure changes. Each entry's *keys* are searched as
# substrings in claim text; if found, the claim is considered verified
# against the known fact. Unknown infrastructure mentions pass through
# (cannot verify ≠ wrong) — only KNOWN-WRONG values get flagged.
INFRASTRUCTURE_FACTS: dict[str, dict[str, str]] = {
    # Known hosts and what role each plays.
    # 2026-05-22 expansion: added per Jarvis' own Quick Facts review.
    "hosts": {
        # Proxmox cluster
        "10.0.0.2": "Proxmox host pve (i9-9900k, 32GB DDR4, Bjørn's old workstation; now Jarvis' Proxmox host)",
        "10.0.0.36": "Proxmox pve-02 (Kingston SSD, read-only)",
        "10.0.0.39": "Jarvis runtime host (LXC-105 on 10.0.0.2) — primary runtime location since 2026-05-25",
        # Legacy Jarvis runtime hosts (pre-2026-05-25 migration)
        "192.168.50.32": "Jarvis side-server (bs_jarvis, web root in ~/web/)",
        "192.168.50.36": "ChiefOne (Bjørn's desktop, NOT Jarvis runtime anymore)",
        "10.0.0.46": "FREED 2026-07-23 — was the he6 IPv6 egress proxy (croq-ipv6 LXC-107, tinyproxy:8888) for account2 groq; retired when groq moved to native v6bind source-binding on CT105",
        # Smart home
        "10.0.0.34": "Home Assistant host",
        # Hostname aliases (typo-tolerant)
        "cheifone": "Bjørn's desktop (NOT Jarvis runtime since 2026-05-25)",
        "chefone": "Bjørn's desktop (NOT Jarvis runtime since 2026-05-25)",
        "chiefone": "Bjørn's desktop (NOT Jarvis runtime since 2026-05-25)",
        "bs_jarvis": "Jarvis side-server on 192.168.50.32",
        "jarvis": "Jarvis runtime LXC-105 on 10.0.0.39 (host = 10.0.0.2 / pve)",
        "pve": "Proxmox host 10.0.0.2 (Jarvis' new home)",
        "pve-02": "Proxmox node 10.0.0.36",
    },
    # Known stable filesystem paths.
    "paths": {
        "/media/projects/jarvis-v2": "code repository",
        "/media/projects/jarvis-v2/web": "web root in repo (index.html + /api/status)",
        "/home/bs/.jarvis-v2": "runtime state directory",
        "/home/bs/.jarvis-v2/state/jarvis.db": "live SQLite database (~1 GB)",
        "/home/bs/.jarvis-v2/config/runtime.json": "runtime config + secrets",
        "/home/bs/.jarvis-v2/shared": "Jarvis shared state (identity, memory, arcs, brain)",
        "/home/bs/.jarvis-v2/workspaces/default": "default workspace (legacy — now migrated to shared/)",
        "/home/bs/web": "Jarvis web root on bs_jarvis (192.168.50.32)",
        "~/web": "Jarvis web root on bs_jarvis (192.168.50.32)",
        "/mnt/backup-ext": "external 4TB backup mount (on 10.0.0.2)",
    },
    # Known service ports.
    "ports": {
        "80": "Jarvis API (4 uvicorn workers, runtime_services_enabled=0)",
        "8011": "Jarvis runtime (heartbeat + services, workers=1)",
        "8400": "Mission Control / Dashboard",
        "8123": "Home Assistant on 10.0.0.34",
        "11434": "Ollama on 127.0.0.1 (localhost — same host as Jarvis runtime since 2026-05-25)",
    },
    # Known domains.
    "domains": {
        "jarvis.srvlab.dk": "Jarvis public website (PHP, realtidsstatus)",
        "srvlab.dk": "primary domain",
    },
    # Designed cadences for daemons/services. When Jarvis evaluates
    # whether a subsystem is "dead", he should query against these
    # ground-truth cadences first. Added 2026-05-25 after he claimed
    # audio/atmosphere/mixed daemons were "død 18-74h" when their
    # actual events were within minutes of his report — he forgot
    # active_sensing_daemon rotates one modality every 30-90 min.
    "cadences": {
        "active_sensing_daemon": (
            "single daemon, 30-90 min random interval, rotates across "
            "4 modalities (visual/audio/atmosphere/mixed). Each modality "
            "gets a turn every 2-6 hours on average. ~9-16 events/12h is "
            "normal — NOT 'dead' if last event was <6h ago."
        ),
        "heartbeat_phased_tick": "every ~1-2 seconds (fast tick)",
        "heartbeat_cadence_tick": "every ~30 seconds (slow tick)",
        "metacognition_signal_tracker": (
            "DB-polling every 5s, scores assistant messages post-flush"
        ),
        "theory_of_mind_tracker": "DB-polling every 5s, processes role=user|assistant",
        "spatial_entity_ledger": "DB-polling every 5s, processes visual sensory_memories",
        "session_inbox_flusher": "DB-polling every 5s, flushes on visible-run turn-end",
        "inner_voice_shadow": (
            "fire-and-forget per _helpful_signal call, ~1700ms avg LLM latency"
        ),
    },
}

# ── Pattern matchers for extracting numbers from claims ─────────────────

_NUMBER_PATTERN = re.compile(r"\b(\d+)\s*(expression|daemon|tick|test|commit|service)s?\b", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")
_HOSTNAME_PATTERN = re.compile(r"\b(chefone|chiefone|cheifone|pve|proxmox|jarvis)\b", re.IGNORECASE)

# ── Cache ───────────────────────────────────────────────────────────────

_GROUND_TRUTH_CACHE: dict[str, Any] = {}
_LAST_REFRESH: datetime | None = None
_CACHE_TTL_SECONDS = 3600  # 1 hour


# ── Collectors ──────────────────────────────────────────────────────────

def _detect_host() -> str:
    """Detect which machine Jarvis runs on — hostname + primary IP."""
    hostname = "unknown"
    ip = "?"
    try:
        result = subprocess.run(
            ["hostname"], capture_output=True, text=True, timeout=5
        )
        hostname = result.stdout.strip() or "unknown"
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=5
        )
        parts = result.stdout.strip().split()
        if parts:
            ip = parts[0]
    except Exception:
        pass
    return f"{hostname} ({ip})"


def _read_config_provider() -> str:
    """Read the current provider name from runtime.json."""
    try:
        import json
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Try visible provider first, then heartbeat, then fallback
            return str(
                data.get("visible_model_provider")
                or data.get("heartbeat_model_provider")
                or "unknown"
            )
    except Exception:
        pass
    return "unknown"


def _read_config_model() -> str:
    """Read the current model name from runtime.json."""
    try:
        import json
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            name = (
                data.get("visible_model_name")
                or data.get("heartbeat_model_name")
                or "unknown"
            )
            provider = _read_config_provider()
            return f"{name} via {provider}"
    except Exception:
        pass
    return "deepseek-v4-flash via deepseek provider"


def _query_expression_count() -> int | None:
    """Count expressions from the DB. Returns None on failure."""
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        row = conn.execute("SELECT COUNT(*) FROM expressions").fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception as exc:
        logger.debug("ground_truth: expression count query failed: %s", exc)
        return None


def _query_commit_count() -> int:
    """Count total commits in the repo."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_PATH), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
    except Exception:
        pass
    return 0


def _query_recent_commit_sha() -> str:
    """Get the current HEAD SHA (short)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_PATH), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _query_daemon_count() -> int:
    """Count active (enabled) daemons via daemon manager."""
    try:
        from core.services.daemon_manager import get_all_daemon_states
        states = get_all_daemon_states()
        return sum(1 for s in states if s.get("enabled"))
    except Exception:
        return 0


def _query_gpu_info() -> str:
    """Quick GPU summary if available."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        if lines:
            return " | ".join(lines[:2])  # max 2 GPUs
    except Exception:
        pass
    return ""


def _query_uname() -> str:
    """Kernel/OS info."""
    try:
        result = subprocess.run(
            ["uname", "-srm"], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── Public API ──────────────────────────────────────────────────────────

def collect_ground_truth() -> dict[str, Any]:
    """Collect all available ground truth about Jarvis. Slow — call rarely."""
    return {
        "system_model": _read_config_model(),
        "provider": _read_config_provider(),
        "running_on": _detect_host(),
        "repo_path": str(REPO_PATH),
        "db_path": str(DB_PATH),
        "head_sha": _query_recent_commit_sha(),
        "commit_count": _query_commit_count(),
        "expression_count": _query_expression_count(),
        "daemon_count": _query_daemon_count(),
        "gpu_info": _query_gpu_info(),
        "os_info": _query_uname(),
        "collected_at": datetime.now(UTC).isoformat(),
    }


def refresh_ground_truth() -> dict[str, Any]:
    """Force refresh the ground truth cache. Returns the fresh registry."""
    global _GROUND_TRUTH_CACHE, _LAST_REFRESH
    _GROUND_TRUTH_CACHE = collect_ground_truth()
    _LAST_REFRESH = datetime.now(UTC)
    logger.info(
        "ground_truth: refreshed — %d keys, expression_count=%s, commit_count=%d, daemon_count=%d",
        len(_GROUND_TRUTH_CACHE),
        _GROUND_TRUTH_CACHE.get("expression_count"),
        _GROUND_TRUTH_CACHE.get("commit_count", 0),
        _GROUND_TRUTH_CACHE.get("daemon_count", 0),
    )
    return _GROUND_TRUTH_CACHE


def get_ground_truth(key: str | None = None, force_refresh: bool = False) -> Any:
    """Get ground truth from cache, auto-refreshing if stale.

    Args:
        key: Specific key to retrieve. If None, returns full dict.
        force_refresh: Skip cache and re-collect.

    Returns:
        The full ground truth dict, or the value for a specific key.
    """
    global _GROUND_TRUTH_CACHE, _LAST_REFRESH

    now = datetime.now(UTC)
    should_refresh = (
        force_refresh
        or not _GROUND_TRUTH_CACHE
        or _LAST_REFRESH is None
        or (now - _LAST_REFRESH).total_seconds() > _CACHE_TTL_SECONDS
    )

    if should_refresh:
        refresh_ground_truth()

    if key:
        return _GROUND_TRUTH_CACHE.get(key)
    return _GROUND_TRUTH_CACHE


def ground_truth_summary() -> str:
    """Return a human-readable summary block for injection or repair."""
    gt = get_ground_truth()
    lines = [
        "Ground Truth (verificerede fakta):",
        f"  • Model: {gt.get('system_model', '?')}",
        f"  • Host: {gt.get('running_on', '?')}",
        f"  • Repository: {gt.get('repo_path', '?')}",
        f"  • HEAD: {gt.get('head_sha', '?')} ({gt.get('commit_count', '?')} commits)",
    ]
    ec = gt.get("expression_count")
    if ec is not None:
        lines.append(f"  • Expressions i DB: {ec}")
    dc = gt.get("daemon_count", 0)
    if dc:
        lines.append(f"  • Aktive daemons: {dc}")
    gpu = gt.get("gpu_info", "")
    if gpu:
        lines.append(f"  • GPU: {gpu}")
    os_info = gt.get("os_info", "")
    if os_info:
        lines.append(f"  • OS: {os_info}")
    return "\n".join(lines)


# ── Claim Verification ─────────────────────────────────────────────────

def verify_system_claim(claim_text: str) -> tuple[bool, str | None]:
    """Verify a system claim (IP, host, path) against ground truth.

    Returns:
        (verified: bool, correct_value: str | None)
        - verified=True means the claim matches ground truth.
        - verified=False means the claim is wrong. correct_value has the
          correct fact if available.
    """
    gt = get_ground_truth()
    text_lower = claim_text.lower()

    # 2026-05-22 (Claude): consult infrastructure_facts FIRST so known
    # remote hosts, shared paths, service ports, and public domains don't
    # get falsely flagged as mismatching the local running_on host.
    # Without this short-circuit, any IP that's not the local primary IP
    # returns (False, ...) which is wrong — they're known good facts
    # about the broader deployment.
    for category in ("hosts", "paths", "ports", "domains", "cadences"):
        for key in INFRASTRUCTURE_FACTS.get(category, {}):
            if key.lower() in text_lower:
                return (True, None)

    # Check hostname claims — fuzzy match
    host_match = _HOSTNAME_PATTERN.search(claim_text)
    if host_match:
        running_on = str(gt.get("running_on", "")).lower()
        claimed_host = host_match.group(0).lower()
        # Normalise fuzzy spelling: cheifone/chefone → chefone
        normalised_claimed = claimed_host.replace("chefone", "chefone").replace("cheifone", "chefone").replace("chiefone", "chefone")
        running_norm = running_on.replace("chefone", "chefone").replace("cheifone", "chefone").replace("chiefone", "chefone")
        if normalised_claimed in running_norm:
            return (True, None)
        # Check partial match — hostname might be in running_on string
        if claimed_host in running_on:
            return (True, None)
        return (False, gt.get("running_on", "unknown"))

    # Check IP claims
    ip_match = _IP_PATTERN.search(claim_text)
    if ip_match:
        running_on = str(gt.get("running_on", ""))
        claimed_ip = ip_match.group(1)
        if claimed_ip in running_on:
            return (True, None)
        else:
            return (False, f"host er {gt.get('running_on', 'unknown')}")

    # Check path claims
    for path_key in ("repo_path", "db_path"):
        actual = str(gt.get(path_key, ""))
        if actual and actual.lower() in text_lower:
            return (True, None)

    # Check model/provider claims
    model = str(gt.get("system_model", "")).lower()
    if model and ("model" in text_lower or "provider" in text_lower):
        if model in text_lower:
            return (True, None)
        # Partial match: check if key model words appear
        key_words = ["deepseek", "flash", "v4"]
        if any(w in text_lower for w in key_words):
            return (True, None)

    # No specific match — pass through (can't verify ≠ wrong)
    return (True, None)


def lookup_infrastructure_fact(key: str) -> str | None:
    """Look up a known infrastructure fact (host/path/port) for ground-truth
    citation. Returns the description, or None if unknown.

    Used by Claim Scanner and hallucination_guard to inject correct values
    when a wrong claim is detected.
    """
    needle = str(key or "").lower().strip()
    if not needle:
        return None
    for category in ("hosts", "paths", "ports", "domains", "cadences"):
        for fact_key, description in INFRASTRUCTURE_FACTS.get(category, {}).items():
            if fact_key.lower() == needle:
                return description
    return None


def verify_stats_claim(claim_text: str) -> tuple[bool, str | None]:
    """Verify a statistic claim (counts of expressions, daemons, commits)
    against ground truth.

    Returns:
        (verified: bool, correct_value: str | None)
    """
    gt = get_ground_truth()
    match = _NUMBER_PATTERN.search(claim_text)

    if not match:
        return (True, None)  # No statistic detected — pass through

    claimed_number = int(match.group(1))
    claimed_unit = match.group(2).lower()

    # Map unit to ground truth key
    unit_to_key = {
        "expression": "expression_count",
        "commits": "commit_count",
        "daemons": "daemon_count",
    }
    # Handle plurals
    if claimed_unit == "daemon":
        claimed_unit = "daemons"
    elif claimed_unit == "commit":
        claimed_unit = "commits"
    elif claimed_unit == "expression":
        claimed_unit = "expressions"

    key = unit_to_key.get(claimed_unit + "s" if not claimed_unit.endswith("s") else claimed_unit)
    if not key:
        key = unit_to_key.get(claimed_unit + "s")
    if not key:
        key = unit_to_key.get(claimed_unit)

    if key not in gt:
        return (True, None)

    actual = gt[key]
    if actual is None:
        return (True, None)  # Can't verify — pass through

    if claimed_number == actual:
        return (True, None)

    return (False, str(actual))


# ── Daemon Tick ─────────────────────────────────────────────────────────

def ground_truth_daemon_tick() -> dict[str, Any]:
    """Called by heartbeat daemon — refreshes cache and returns summary.

    Cadence: every 60 minutes (default) or configurable.
    """
    gt = refresh_ground_truth()
    return {
        "status": "ok",
        "keys_collected": len(gt),
        "expression_count": gt.get("expression_count"),
        "commit_count": gt.get("commit_count", 0),
        "daemon_count": gt.get("daemon_count", 0),
        "host": str(gt.get("running_on", "")).split("(")[0].strip(),
        "collected_at": gt.get("collected_at", ""),
    }
