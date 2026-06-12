"""Communication guard — scanner assistant-output for boundary violations.

Triggerfraser som "godnat", "sov godt" osv. fanges her. Guarden har to
tilstande:
  - TTL-baseret (engangs-irettesættelse): glemmer sig selv efter X turns
  - Permanent (præference): gælder for altid

Guarden kaldes *før* assistant-svar sendes til brugeren. Hvis den finder
en triggerfrase, sætter den en nudge i stedet for at sende — og giver
mig chancen for at omformulere.

Scanning: case-insensitive, substring-match (ikke regex, for at undgå
overengineering). Triggerfraser kan tilføjes via add_trigger().
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
_GUARD_FILE = Path.home() / ".jarvis-v2" / "state" / "communication_guard.json"

# Default permanente triggerfraser (baseret på Bjørns præference).
_DEFAULT_TRIGGERS: list[dict[str, Any]] = [
    {
        "phrase": "godnat",
        "kind": "permanent",
        "severity": "hard",
        "reason": "Bjørn bestemmer selv hvorna°r samtalen slutter",
        "added_at": None,  # altid aktiv
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "sov godt",
        "kind": "permanent",
        "severity": "hard",
        "reason": "Bjørn bestemmer selv hvorna°r samtalen slutter",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "laeg dig til at sove",
        "kind": "permanent",
        "severity": "hard",
        "reason": "Bjørn bestemmer selv hvorna°r samtalen slutter",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "put dig selv",
        "kind": "permanent",
        "severity": "hard",
        "reason": "Bjørn bestemmer selv hvorna°r samtalen slutter",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "du ma vare traet",
        "kind": "permanent",
        "severity": "soft",
        "reason": "Jeg skal ikke antage Bjørns tilstand",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "du har haft en lang dag",
        "kind": "permanent",
        "severity": "soft",
        "reason": "Jeg skal ikke antage Bjørns tilstand",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "jeg gor det",
        "kind": "permanent",
        "severity": "soft",
        "reason": "Stop loefte-fraser — goer det eller lad vaer",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "beklager",
        "kind": "permanent",
        "severity": "soft",
        "reason": "Stop overdreven undskylden",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "undskyld",
        "kind": "permanent",
        "severity": "soft",
        "reason": "Stop overdreven undskylden",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
    {
        "phrase": "lad mig",
        "kind": "permanent",
        "severity": "soft",
        "reason": "Stop loefte-fraser — goer det eller lad vaer",
        "added_at": None,
        "ttl_turns": None,
        "ttl_until": None,
    },
]

# Fraser der er trygge at HÅRD-blokere før afsendelse: utvetydige
# afslutnings-/sove-fraser. Bruges som fallback når en persisteret trigger
# mangler 'severity'-feltet (legacy state). ALT andet behandles som blødt.
_HARD_DEFAULT_PHRASES: frozenset[str] = frozenset({
    "godnat",
    "sov godt",
    "sov soedt",
    "sov sødt",
    "laeg dig til at sove",
    "læg dig til at sove",
    "put dig selv",
    "tid til at sove",
    "good night",
    "night night",
    "sleep well",
})


def _is_hard(trigger: dict[str, Any]) -> bool:
    """Er denne trigger en HÅRD blok (afvis besked før send) eller blød
    (kun prompt-påmindelse / log)?

    - severity == 'hard'  → hård.
    - severity == 'soft'  → blød.
    - severity mangler (legacy state) → hård kun hvis frasen er en kendt
      utvetydig afslutnings-/sove-frase; ellers blød (sikker default).
    """
    sev = trigger.get("severity")
    if sev == "hard":
        return True
    if sev == "soft":
        return False
    return trigger.get("phrase", "").strip().lower() in _HARD_DEFAULT_PHRASES


def _load() -> list[dict[str, Any]]:
    if not _GUARD_FILE.exists():
        return list(_DEFAULT_TRIGGERS)
    try:
        data = json.loads(_GUARD_FILE.read_text())
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return list(_DEFAULT_TRIGGERS)


def _save(triggers: list[dict[str, Any]]) -> None:
    _GUARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    _GUARD_FILE.write_text(json.dumps(triggers, ensure_ascii=False, indent=2), encoding="utf-8")


def add_trigger(
    phrase: str,
    *,
    kind: str = "ttl",
    reason: str = "",
    ttl_turns: int | None = 10,
    ttl_hours: int | None = None,
) -> None:
    """Tilfoj en triggerfrase til guarden.

    Args:
        phrase: Frasen der skal fanges (case-insensitive matche).
        kind: 'permanent' eller 'ttl'.
        reason: Hvorfor denne frase er blokeret.
        ttl_turns: Antal turns før guarden glemmer sig selv (kun hvis kind='ttl').
        ttl_hours: Antal timer før guarden glemmer sig selv (kun hvis kind='ttl').
    """
    triggers = _load()
    # Tjek om den allerede findes
    for t in triggers:
        if t["phrase"].lower() == phrase.lower():
            t["kind"] = kind
            t["reason"] = reason or t["reason"]
            t["added_at"] = datetime.now(UTC).isoformat()
            if kind == "ttl":
                t["ttl_turns"] = max(ttl_turns if ttl_turns is not None else 10, 1)
                if ttl_hours:
                    t["ttl_until"] = (datetime.now(UTC) + timedelta(hours=ttl_hours)).isoformat()
                else:
                    t["ttl_until"] = None
            else:
                t["ttl_turns"] = None
                t["ttl_until"] = None
            _save(triggers)
            return

    triggers.append({
        "phrase": phrase,
        "kind": kind,
        "reason": reason,
        "added_at": datetime.now(UTC).isoformat(),
        "ttl_turns": max(ttl_turns if ttl_turns is not None else 10, 1) if kind == "ttl" else None,
        "ttl_until": (datetime.now(UTC) + timedelta(hours=ttl_hours)).isoformat() if kind == "ttl" and ttl_hours else None,
    })
    _save(triggers)


def remove_trigger(phrase: str) -> bool:
    """Fjern en triggerfrase. Returner True hvis den blev fjernet."""
    triggers = _load()
    before = len(triggers)
    triggers = [t for t in triggers if t["phrase"].lower() != phrase.lower()]
    if len(triggers) < before:
        _save(triggers)
        return True
    return False


def scan(text: str) -> dict[str, Any] | None:
    """Skan en tekst for triggerfraser.

    Args:
        text: Teksten der skal scannes (typisk assistant-output).

    Returns:
        En dict med match-info, eller None hvis ingen trigger blev fundet.
        {
            "matched": "godnat",
            "kind": "permanent" | "ttl",
            "reason": "...",
        }
    """
    if not text or not text.strip():
        return None

    triggers = _load()
    lower_text = text.lower()

    for t in triggers:
        if t["phrase"].lower() in lower_text:
            # Tjek TTL-udloeb
            if t["kind"] == "ttl":
                ttl_until = t.get("ttl_until")
                ttl_turns = t.get("ttl_turns")
                # Hvis TTL er udloebet, skip denne trigger
                if ttl_until:
                    try:
                        until = datetime.fromisoformat(ttl_until)
                        if datetime.now(UTC) > until:
                            continue
                    except (ValueError, TypeError):
                        pass
                if ttl_turns is not None and ttl_turns <= 0:
                    continue

            return {
                "matched": t["phrase"],
                "kind": t["kind"],
                "severity": "hard" if _is_hard(t) else "soft",
                "reason": t.get("reason", ""),
            }

    return None


def _trigger_active(t: dict[str, Any], now: datetime) -> bool:
    """Er en trigger aktiv lige nu (permanent, eller TTL ikke udløbet)?"""
    if t["kind"] != "ttl":
        return True
    ttl_until = t.get("ttl_until")
    if ttl_until:
        try:
            if now > datetime.fromisoformat(ttl_until):
                return False
        except (ValueError, TypeError):
            pass
    ttl_turns = t.get("ttl_turns")
    if ttl_turns is not None and ttl_turns <= 0:
        return False
    return True


def enforce_outgoing(text: str | None) -> dict[str, Any]:
    """Hård-gate for udga°ende assistant-tekst — kaldes FØR afsendelse.

    Blokerer KUN pa° utvetydige afslutnings-/sove-fraser (severity='hard').
    Stilistiske fraser ('lad mig', 'undskyld', ...) rapporteres som
    soft_matches men blokerer ALDRIG — ellers braekker normal dansk tale.

    Returns:
        {
            "blocked": bool,        # True kun ved hård match
            "matched": str | None,  # den hård-frase der blokerede
            "kind": str | None,
            "reason": str | None,
            "soft_matches": list[str],  # bløde fraser fundet (ikke-blokerende)
        }
    """
    clean = {"blocked": False, "matched": None, "kind": None,
             "reason": None, "severity": None, "soft_matches": []}
    if not text or not text.strip():
        return clean

    triggers = _load()
    lower_text = text.lower()
    now = datetime.now(UTC)

    hard_hit: dict[str, Any] | None = None
    soft_matches: list[str] = []
    for t in triggers:
        if t["phrase"].lower() not in lower_text:
            continue
        if not _trigger_active(t, now):
            continue
        if _is_hard(t):
            if hard_hit is None:
                hard_hit = t
        else:
            if t["phrase"] not in soft_matches:
                soft_matches.append(t["phrase"])

    if hard_hit is not None:
        return {
            "blocked": True,
            "matched": hard_hit["phrase"],
            "kind": hard_hit["kind"],
            "reason": hard_hit.get("reason", ""),
            "severity": "hard",
            "soft_matches": soft_matches,
        }
    return {**clean, "soft_matches": soft_matches}


def prompt_section() -> str:
    """Bygger en høj-salient påmindelse til system-prompten med de aktive
    grænser. Hårde fraser = 'sig ALDRIG'; bløde = 'omformulér'.

    Returnerer "" hvis ingen aktive triggers.
    """
    triggers = _load()
    now = datetime.now(UTC)
    hard: list[str] = []
    soft: list[str] = []
    for t in triggers:
        if not _trigger_active(t, now):
            continue
        (hard if _is_hard(t) else soft).append(t["phrase"])
    if not hard and not soft:
        return ""

    lines = ["🚫═══ KOMMUNIKATIONS-GRÆNSER ═══🚫"]
    if hard:
        lines.append(
            "Sig ALDRIG til Bjørn (han bestemmer selv hvornår samtalen slutter): "
            + ", ".join(f'"{p}"' for p in hard)
            + "."
        )
    if soft:
        lines.append(
            "Undgå / omformulér (gør tingen i stedet for at love eller undskylde den): "
            + ", ".join(f'"{p}"' for p in soft)
            + "."
        )
    lines.append("🚫═══════════════════════════════🚫")
    return "\n".join(lines)


def consume_turn() -> None:
    """Traek en TTL-turn fra alle TTL-baserede triggers. Kald efter hver
    assistant-turn (dvs. efter hver gang vi har genereret et svar)."""
    triggers = _load()
    changed = False
    for t in triggers:
        if t["kind"] == "ttl" and t.get("ttl_turns") is not None:
            if t["ttl_turns"] > 0:
                t["ttl_turns"] -= 1
                changed = True
            # Hvis turns na°r 0, fjern triggeren
            if t["ttl_turns"] == 0:
                t["ttl_turns"] = -1  # marker som inaktiv
                changed = True
    if changed:
        _save(triggers)


def cleanup_expired() -> int:
    """Rens udloebne TTL-triggers og triggers med ttl_turns <= 0.

    Returns:
        Antal fjernede triggers.
    """
    triggers = _load()
    before = len(triggers)
    now = datetime.now(UTC)
    triggers = [
        t for t in triggers
        if not (
            t["kind"] == "ttl"
            and (
                t.get("ttl_turns") is not None and t["ttl_turns"] <= 0
                or t.get("ttl_until") and _safe_parse_iso(t["ttl_until"], now) <= now
            )
        )
    ]
    removed = before - len(triggers)
    if removed:
        _save(triggers)
    return removed


def _safe_parse_iso(s: str | None, now: datetime) -> datetime:
    if not s:
        return now + timedelta(days=365)
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return now + timedelta(days=365)


def list_triggers() -> list[dict[str, Any]]:
    """Returner alle aktive triggers."""
    return _load()


def active_count() -> int:
    """Antal aktive triggerfraser (permanente + ikke-udloebne TTL)."""
    triggers = _load()
    now = datetime.now(UTC)
    count = 0
    for t in triggers:
        if t["kind"] == "permanent":
            count += 1
        elif t["kind"] == "ttl":
            ttl_turns = t.get("ttl_turns")
            ttl_until = t.get("ttl_until")
            if ttl_turns is not None and ttl_turns <= 0:
                continue
            if ttl_until and _safe_parse_iso(ttl_until, now) <= now:
                continue
            count += 1
    return count
