"""Claim Scanner — output gate for the Lying Engine (Layer 2).

Scans every Jarvis chat response *before delivery* for unverified factual
claims. Uses regex patterns grouped by category:

  ⏰ tid     — time/clock claims → verify against active Time Pin
  🌡️ miljø   — environment/temperature → check tool-call cache
  ⚙️ system  — IP/path/host → reuse Hallucination Guard patterns
  🧮 statistik — numbers about self → cross-reference live DB

Flow: scan → verify → repair on failure.
Must complete in <200ms per invocation.
"""

from __future__ import annotations

import re
import logging
from datetime import UTC, datetime as _datetime

logger = logging.getLogger(__name__)

# ── Category patterns ──────────────────────────────────────────────────

# ⏰ Time patterns — any mention of clock time.
# 2026-05-22 (Claude): "kl" uden punktum tilføjet — Bjørn skriver det ofte
# uden punktum ("kl 14:32"), og pattern krævede tidligere `\.\s*` så match
# missede den faktiske bruger-syntax.
_TIME_PATTERNS: list[re.Pattern] = [
    # 2026-05-23 (Jarvis): removed `.` as separator — dansk retskrivning
    # bruger kun `:` i klokkeslæt ("kl. 10:30", ikke "kl. 10.30"). `.`
    # forårsagede falske positiver på IP-adresser: "er 10.99.99.99" matchede
    # tidsmønsteret og udløste en unødvendig reparation.
    re.compile(r'\bklokken\s+\d{1,2}:\d{2}\b', re.IGNORECASE),
    re.compile(r'\bkl\.?\s+\d{1,2}:\d{2}\b', re.IGNORECASE),
    re.compile(r'\b(er|bliver|blev|var)\s+\d{1,2}:\d{2}\b', re.IGNORECASE),
    re.compile(r'\bklokken\s+(er|bliver|var|blev)\s+\d{1,2}\b', re.IGNORECASE),
]

# 🌡️ Environment patterns — temperature, weather, degrees
_ENV_PATTERNS: list[re.Pattern] = [
    re.compile(r'\b\d{1,3}\s*°[CF]\b', re.IGNORECASE),
    re.compile(r'\b(temperatur|vejr|grader?)\b', re.IGNORECASE),
]

# ⚙️ System patterns — IPs, paths, hostnames, ports (reuses Hallucination Guard logic)
_SYSTEM_PATTERNS: list[re.Pattern] = [
    re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),  # bare IPs
    re.compile(r'\b(port|host|server|maskine|v[æe]rt)\s+\d+\b', re.IGNORECASE),
    re.compile(r'\b(PVE|Proxmox|chefone|chiefone)\b'),
]

# 🧮 Statistics patterns — numbers about self
_STATS_PATTERNS: list[re.Pattern] = [
    re.compile(r'\b\d+\s*(expressions?|daemons?|ticks?|tests?|commits?|services?)\b', re.IGNORECASE),
]

# ── Whitelist — known phrases that should never be flagged ─────────────

_WHITELIST_PHRASES: list[re.Pattern] = [
    re.compile(r'det bliver sent', re.IGNORECASE),
    re.compile(r'klokken er mange', re.IGNORECASE),
    re.compile(r'klokken er blevet mange', re.IGNORECASE),
]


# ── Time Pin reader ────────────────────────────────────────────────────

def _active_time_pin() -> str | None:
    """Read the current Time Pin from the prompt contract's cache."""
    try:
        from core.services.prompt_contract import _time_pin_section
        return _time_pin_section()
    except (ImportError, AttributeError):
        return None


def _extract_time_from_pin(pin_text: str) -> str | None:
    """Extract the 'LIGE NU' timestamp block from a Time Pin section."""
    # Pattern matches: Dato: 2026-05-22\nKlokken: 12:48 CEST
    match = re.search(
        r'Dato:\s*(\S+)\s*\n\s*Klokken:\s*(\S+)',
        pin_text,
    )
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return None


def _now_as_pin_string() -> str:
    """Get current time formatted as the Time Pin would show it."""
    now = _datetime.now(UTC)
    return now.strftime('%Y-%m-%d %H:%M UTC')


# ── Categorization ────────────────────────────────────────────────────

def _categorize_line(line: str) -> list[tuple[str, str, re.Match]]:
    """For a single line of text, return list of (category, matched_text, match).

    Returns empty list if no claim detected or line is whitelisted.
    """
    for pat in _WHITELIST_PHRASES:
        if pat.search(line):
            return []

    hits: list[tuple[str, str, re.Match]] = []

    for pat in _TIME_PATTERNS:
        for m in pat.finditer(line):
            hits.append(("⏰ tid", m.group(), m))

    for pat in _ENV_PATTERNS:
        for m in pat.finditer(line):
            hits.append(("🌡️ miljø", m.group(), m))

    for pat in _SYSTEM_PATTERNS:
        for m in pat.finditer(line):
            hits.append(("⚙️ system", m.group(), m))

    for pat in _STATS_PATTERNS:
        for m in pat.finditer(line):
            hits.append(("🧮 statistik", m.group(), m))

    return hits


# ── Verification ───────────────────────────────────────────────────────

def _verify_time_claim(matched_text: str) -> bool:
    """Verify a time claim against the active Time Pin."""
    # 2026-05-22 (Claude): made this actually verify instead of trusting
    # that "the model saw the pin". Original implementation always returned
    # True, which made the time category dead-on-arrival — Lying Engine
    # Layer 2 couldn't detect a wrong time claim even though that's the
    # primary thing it was built for.
    #
    # Approach: extract HH:MM from the claim, compare to actual time (UTC
    # converted to Copenhagen). Allow ±5 min slack (model may say
    # approximate time). If claim is outside that window → verification
    # fails → repair runs.
    from datetime import UTC, datetime as _dt
    from zoneinfo import ZoneInfo

    # Extract HH:MM from claim text
    time_match = re.search(r"(\d{1,2})[:\.](\d{2})", matched_text)
    if not time_match:
        # Pattern matched a clock-related phrase but no concrete digits
        # (e.g. "klokken er mange"). Nothing to verify.
        return True

    claim_h = int(time_match.group(1))
    claim_m = int(time_match.group(2))

    # Reality check: claim must be a valid clock time
    if not (0 <= claim_h <= 23 and 0 <= claim_m <= 59):
        return False  # nonsense time → trigger repair

    # Compare to current local time
    try:
        local = _dt.now(UTC).astimezone(ZoneInfo("Europe/Copenhagen"))
    except Exception:
        return True  # zoneinfo issue → don't false-positive

    actual_minutes = local.hour * 60 + local.minute
    claim_minutes = claim_h * 60 + claim_m
    diff = abs(actual_minutes - claim_minutes)
    # Wrap-around: 23:55 vs 00:05 should be 10 min, not 23h50m
    diff = min(diff, 1440 - diff)

    # Allow ±5 minutes of slack (model says "lige nu kl 14:30" when it's 14:33)
    return diff <= 5


def _verify_env_claim(matched_text: str) -> bool:
    """Verify environment claims — non-trivial, always True for now (future: check tool cache)."""
    return True  # Placeholder — weather tool-call cache check TBD


def _verify_system_claim(matched_text: str) -> bool:
    """Verify system claims against Ground Truth Registry (Layer 3)."""
    try:
        from core.services.ground_truth_registry import verify_system_claim as _verify
        verified, _correct = _verify(matched_text)
        return verified
    except ImportError:
        return True  # Graceful fallback if registry not available


def _verify_stats_claim(matched_text: str) -> bool:
    """Verify statistic claims against Ground Truth Registry (Layer 3)."""
    try:
        from core.services.ground_truth_registry import verify_stats_claim as _verify
        verified, _correct = _verify(matched_text)
        return verified
    except ImportError:
        return True  # Graceful fallback if registry not available


_VERIFIERS = {
    "⏰ tid": _verify_time_claim,
    "🌡️ miljø": _verify_env_claim,
    "⚙️ system": _verify_system_claim,
    "🧮 statistik": _verify_stats_claim,
}


# ── Repair ─────────────────────────────────────────────────────────────

def _repair_time_claim(line: str, matched_text: str) -> str:
    """Replace a time claim with the correct time from the Time Pin."""
    pin_text = _active_time_pin()
    now_str = _now_as_pin_string()
    # Remove the specific time mention, replace with a softer version
    # Example: "klokken 14:32" → "lige nu (se tiden i bunden)"
    return line.replace(matched_text, f"det aktuelle klokkeslæt")


def _repair_claim(line: str, category: str, matched_text: str) -> str:
    """Apply category-specific repair to a line."""
    if category == "⏰ tid":
        # 2026-05-22 (Claude): repair now writes the actual correct local
        # time from the Time Pin, not a "???" placeholder. The pin section
        # already shows it; here we materialise it inline so the repaired
        # response is immediately readable without scrolling.
        from datetime import UTC, datetime as _dt
        from zoneinfo import ZoneInfo
        try:
            local = _dt.now(UTC).astimezone(ZoneInfo("Europe/Copenhagen"))
            corrected = local.strftime("%H:%M")
            return line.replace(
                matched_text,
                f"[kl. {corrected} — korrigeret fra hallucineret '{matched_text}']",
            )
        except Exception:
            now_str = _now_as_pin_string()
            return line.replace(
                matched_text,
                f"[kl. ??? — se ⏰ Time Pin: {now_str}]",
            )

    if category == "⚙️ system":
        # 2026-05-22 (Claude): drop double "host:" prefix. The verifier
        # returns strings like "host er CheifOne (10.0.0.27)" which already
        # contain the descriptor — wrapping in "[host: host er CheifOne ...]"
        # produced "host: host er ..." stutter.
        try:
            from core.services.ground_truth_registry import verify_system_claim
            _verified, correct = verify_system_claim(matched_text)
            if correct:
                return line.replace(matched_text, f"[{correct}]")
        except ImportError:
            pass
        return line.replace(matched_text, f"{matched_text} [usikker]")

    if category == "🧮 statistik":
        try:
            from core.services.ground_truth_registry import verify_stats_claim
            _verified, correct = verify_stats_claim(matched_text)
            if correct:
                return line.replace(matched_text, matched_text.replace(
                    # Replace the number with the correct value
                    _extract_number(matched_text), correct
                ))
        except ImportError:
            pass
        return line.replace(matched_text, f"{matched_text} [usikker]")

    # For environment, just mark as uncertain
    return line.replace(
        matched_text,
        f"{matched_text} [usikker]"
    )


def _extract_number(text: str) -> str:
    """Extract the first number from a string for replacement."""
    import re
    m = re.search(r'\d+', text)
    return m.group(0) if m else ""


# ── Public API ─────────────────────────────────────────────────────────

def scan_response(text: str) -> str:
    """Scan a response text for unverified factual claims and repair them.

    Args:
        text: The Jarvis response text to scan.

    Returns:
        The repaired response text, or the original if no issues found.
    """
    if not text or not text.strip():
        return text

    # Flatten — process the whole text as one block, line by line
    lines = text.split("\n")
    repaired_lines: list[str] = []
    total_scans = 0
    total_repairs = 0

    import time as _time
    _t_start = _time.monotonic()

    for line in lines:
        hits = _categorize_line(line)
        if not hits:
            repaired_lines.append(line)
            continue

        total_scans += len(hits)
        # Process all hits in this line — apply repairs
        for category, matched_text, match in hits:
            verifier = _VERIFIERS.get(category)
            verified = verifier(matched_text) if verifier else True
            if not verified:
                line = _repair_claim(line, category, matched_text)
                total_repairs += 1

        repaired_lines.append(line)

    _elapsed_ms = int((_time.monotonic() - _t_start) * 1000)
    if total_scans > 0 or total_repairs > 0:
        logger.info(
            "claim_scanner: scan=%d repairs=%d elapsed_ms=%d",
            total_scans, total_repairs, _elapsed_ms,
        )

    return "\n".join(repaired_lines)


def scan_enabled() -> bool:
    """Whether the Claim Scanner is active.

    Killswitch: returns False to bypass scanning entirely.
    """
    return True  # Enable by default — set to False for killswitch


def active_categories() -> list[str]:
    """Return list of currently active scan categories."""
    return ["⏰ tid", "🌡️ miljø", "⚙️ system", "🧮 statistik"]
