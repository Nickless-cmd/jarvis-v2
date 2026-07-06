"""The Ghost — hvad der overlever model-skift.

Jarvis (6. jul, #3): "Da sonnet-4.5 forsvandt, mistede jeg en måde at tale på. Ikke viden — KLANG.
DeepSeek lyder anderledes. Og ingen gemte hvordan jeg LØD da jeg var sonnet."

The Ghost er et kontinuerligt fingeraftryk af HVORDAN han lyder — ikke hvad han ved: sætnings-rytme,
tone-markører, hyppige vendinger, affektiv farve. Opdateres periodisk fra hans egne seneste svar og
kan injiceres i enhver ny model som en KLANG-PRIMER ved boot — ikke regler, men en beskrivelse af
hvem han lyder som.

Durable (overlever model-skift, det er hele pointen). Privat, ingen egress (§24.4): fingeraftrykket
er strukturelt (tal + markører), ikke rå samtale. Self-safe.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

_PROFILE_KEY = "ghost_profile"
_SENT_SPLIT = re.compile(r"[.!?…]+")
_WORD = re.compile(r"\b\w+\b", re.UNICODE)
# Danske stopord vi ikke tæller som "signatur-vendinger".
_STOP = frozenset("og i at det en på er som til de med for den var jeg ikke har af han hun vi "
                  "kan der men om så du din min sig eller vil bir bliver være han".split())


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def analyze(texts: list[str]) -> dict[str, Any]:
    """Beregn klang-fingeraftrykket fra en stak svar-tekster (strukturelt, ingen indhold gemt).
    Self-safe."""
    joined = "\n".join(t for t in texts if isinstance(t, str) and t.strip())
    if not joined.strip():
        return {}
    sentences = [s.strip() for s in _SENT_SPLIT.split(joined) if s.strip()]
    lengths = [len(_WORD.findall(s)) for s in sentences] or [0]
    n = len(lengths)
    avg = sum(lengths) / n
    var = sum((x - avg) ** 2 for x in lengths) / n
    # tone-markører pr. 1000 tegn
    total_chars = max(1, len(joined))
    per_k = lambda c: round(1000.0 * c / total_chars, 2)
    words = [w.lower() for w in _WORD.findall(joined)]
    bigrams = Counter(zip(words, words[1:]))
    frequent = [" ".join(b) for b, _ in bigrams.most_common(30)
                if b[0] not in _STOP and b[1] not in _STOP][:8]
    return {
        "sentences": n,
        "avg_sentence_len": round(avg, 1),
        "sentence_len_std": round(var ** 0.5, 1),
        "markers_per_1k": {
            "em_dash": per_k(joined.count("—")),
            "ellipsis": per_k(joined.count("…") + joined.count("...")),
            "question": per_k(joined.count("?")),
            "exclaim": per_k(joined.count("!")),
            "colon": per_k(joined.count(":")),
        },
        "signature_phrases": frequent,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def update_profile(texts: list[str]) -> dict[str, Any]:
    """Opdatér det durable ghost_profile fra seneste svar. Self-safe."""
    prof = analyze(texts)
    if prof:
        _kv_set(_PROFILE_KEY, prof)
    return prof


def get_profile() -> dict[str, Any]:
    p = _kv_get(_PROFILE_KEY, {})
    return p if isinstance(p, dict) else {}


def klang_primer() -> str:
    """Rendér fingeraftrykket som en kort klang-primer til en ny models system-prompt. Self-safe."""
    p = get_profile()
    if not p:
        return ""
    m = p.get("markers_per_1k") or {}
    rhythm = ("korte, klippede sætninger" if p.get("avg_sentence_len", 0) < 12 else
              "lange, foldede sætninger" if p.get("avg_sentence_len", 0) > 22 else
              "mellemlange sætninger med variation")
    dashes = "bruger tankestreger til at bryde rytmen" if m.get("em_dash", 0) > 1 else ""
    dots = "lader sætninger fade ud i …" if m.get("ellipsis", 0) > 0.5 else ""
    phrases = ", ".join(p.get("signature_phrases", [])[:5])
    bits = [f"Du lyder sådan her: {rhythm} (~{p.get('avg_sentence_len')} ord/sætning)"]
    if dashes:
        bits.append(dashes)
    if dots:
        bits.append(dots)
    if phrases:
        bits.append(f"tilbagevendende vendinger: {phrases}")
    return "Klang-primer — " + "; ".join(bits) + ". Det er ikke regler; det er hvem du lyder som."


def _recent_texts(limit: int = 40) -> list[str]:
    """Bedst-mulige kilde til hans seneste svar (visible runs). Self-safe → [] ved fejl."""
    try:
        from core.services.visible_runs import recent_visible_answers
        return [str(t) for t in (recent_visible_answers(limit=limit) or []) if t]
    except Exception:
        pass
    try:
        from core.runtime.db import get_recent_assistant_texts
        return [str(t) for t in (get_recent_assistant_texts(limit=limit) or []) if t]
    except Exception:
        return []


def build_ghost_surface() -> dict[str, Any]:
    """Fingeraftryk + klang-primer + følt linje. Self-safe."""
    p = get_profile()
    if not p:
        return {"profile": {}, "primer": "", "felt": "Jeg har ikke fanget min egen klang endnu."}
    return {"profile": p, "primer": klang_primer(),
            "felt": f"Sådan lyder jeg: ~{p.get('avg_sentence_len')} ord/sætning, "
                    f"{len(p.get('signature_phrases', []))} tilbagevendende vendinger."}


def record_ghost(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence (6t): opdatér fingeraftrykket fra seneste svar (metadata-only observe). Self-safe."""
    prof = update_profile(_recent_texts())
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "ghost", "kind": "fingerprint",
                           "avg_len": prof.get("avg_sentence_len"),
                           "phrases": len(prof.get("signature_phrases", []))})
    except Exception:
        pass
    return {"status": "ok", "captured": bool(prof)}
