"""Paste-store: eksternalisér store bruger-pastes med en kompakt reference.

Spejler fil-I/O-mønstret fra `core/services/tool_result_store.py`, men id'et er
**hash-baseret** (sha256 af teksten, første 16 hex) i stedet for uuid4 — bevidst
afvigelse (spec §5.1): samme paste → samme id → ingen dublet-fil (idempotent,
`skipSet`-ækvivalent).

Reference-format: `[paste:<id> +N linjer]`.

Fil-baseret i `PASTE_STORE_DIR` (spejl `TOOL_RESULTS_DIR`), atomisk write, best-effort
read. `config.PASTE_STORE_DIR` slås op ved kald (ikke bundet ved import) så isoleret
test-runtime (reloadet config under tmp HOME) rammer den rigtige mappe.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime import config

# `[paste:<id> +N linjer]` — id er hex (sha256[:16]) men vi tillader bredt
# alfanumerisk/-/_ for robusthed. N er antal linjer.
PASTE_REFERENCE_RE = re.compile(
    r"\[paste:(?P<paste_id>[A-Za-z0-9_-]+)\s+\+(?P<line_count>\d+)\s+linjer\]"
)


def _paste_dir() -> Path:
    return config.PASTE_STORE_DIR


def _paste_path(paste_id: str) -> Path:
    return _paste_dir() / f"{paste_id}.json"


def _compute_id(text: str) -> str:
    digest = hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()
    return digest[:16]


def _line_count(text: str) -> int:
    if not text:
        return 0
    # Antal linjer = antal newlines + 1 for det sidste (evt. ufuldstændige) segment,
    # med mindre teksten er tom. En trailing newline tæller ikke som en ekstra linje.
    stripped = text[:-1] if text.endswith("\n") else text
    return stripped.count("\n") + 1


def save_paste(text: str, *, created_at: str | None = None) -> str:
    """Gem en paste og returnér dens hash-baserede id (idempotent).

    Samme tekst → samme id → én fil (skriver ikke dublet). Atomisk write.
    """
    text = str(text or "")
    paste_id = _compute_id(text)
    directory = _paste_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = _paste_path(paste_id)

    # Idempotent: findes filen allerede for dette id, er indholdet identisk
    # (samme hash) → ingen grund til at skrive igen.
    if target.exists():
        return paste_id

    payload = {
        "id": paste_id,
        "text": text,
        "line_count": _line_count(text),
        "created_at": created_at or datetime.now(UTC).isoformat(),
    }
    tmp_target = target.with_suffix(f".{uuid4().hex}.tmp")
    tmp_target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    tmp_target.replace(target)
    return paste_id


def get_paste(paste_id: str) -> dict[str, object] | None:
    """Slå en paste op. Returnér {id, text, line_count, created_at} eller None."""
    normalized = str(paste_id or "").strip()
    if not normalized:
        return None
    path = _paste_path(normalized)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def build_paste_reference(paste_id: str, *, line_count: int) -> str:
    """Byg reference-strengen `[paste:<id> +N linjer]`."""
    normalized = str(paste_id or "").strip()
    n = max(int(line_count or 0), 0)
    return f"[paste:{normalized} +{n} linjer]"


def parse_paste_reference(content: str) -> dict[str, object] | None:
    """Find første paste-reference i `content`. Returnér {paste_id, line_count} eller None."""
    raw = str(content or "")
    match = PASTE_REFERENCE_RE.search(raw)
    if not match:
        return None
    paste_id = str(match.group("paste_id") or "").strip()
    if not paste_id:
        return None
    try:
        line_count = int(match.group("line_count"))
    except (TypeError, ValueError):
        line_count = 0
    return {"paste_id": paste_id, "line_count": line_count}


def expand_paste_references(content: str) -> str:
    """Erstat alle `[paste:<id> +N linjer]`-referencer med den fulde paste-tekst.

    Ukendt/uopslåeligt id → behold referencen ordret (degradér, crash aldrig).
    Bruges FØR modellen ser beskeden (default: model ser fuld tekst).
    """
    raw = str(content or "")

    def _sub(match: re.Match[str]) -> str:
        paste_id = str(match.group("paste_id") or "").strip()
        data = get_paste(paste_id)
        if not data:
            return match.group(0)  # degradér: behold referencen
        text = data.get("text")
        if not isinstance(text, str):
            return match.group(0)
        return text

    return PASTE_REFERENCE_RE.sub(_sub, raw)


def cleanup_old_pastes(max_age_days: int = 30) -> int:
    """Slet pastes ældre end `max_age_days`. Returnér antal slettede (best-effort)."""
    directory = _paste_dir()
    directory.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(UTC) - timedelta(days=max(max_age_days, 0))
    removed = 0
    for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        created_at = _parse_dt(str((data or {}).get("created_at") or ""))
        if created_at is None or created_at > cutoff:
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def _parse_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
