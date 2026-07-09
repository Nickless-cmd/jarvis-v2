# core/services/central_agent_smith.py
"""Agent Smith — stående selv-lighed-kritiker. Detekterer når Jarvis gentager sig selv på tværs af
sit EGET nylige output (over-brugte fraser + output-klyngning + gentagne beslutnings-sekvenser) og
flagger 'du gør det igen'. Observe-nerve + governed modstemme-til-prompt-hale. Egress-fri, self-safe."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_PHRASE_MIN_MSGS = 3      # en frase skal gå igen i ≥ så mange DISTINKTE beskeder
_SEQ_MIN_RUNS = 3         # en beslutnings-signatur skal gå igen i ≥ så mange runs
_VOICE_THRESHOLD = 0.5    # score-tærskel før modstemmen taler
_NGRAM_LO, _NGRAM_HI = 3, 5
_WORD_RE = re.compile(r"[a-zæøå0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def _ngrams(text: str, lo: int = _NGRAM_LO, hi: int = _NGRAM_HI) -> set[str]:
    """Normaliserede ord-n-grams (lo..hi) fra én tekst. Ren."""
    toks = _tokens(text)
    out: set[str] = set()
    for n in range(lo, hi + 1):
        for i in range(len(toks) - n + 1):
            out.add(" ".join(toks[i:i + n]))
    return out


def repeated_phrases(messages: list[str], min_msgs: int = _PHRASE_MIN_MSGS) -> list[dict[str, Any]]:
    """Fraser (n-grams) der optræder i ≥ min_msgs DISTINKTE beskeder, sorteret efter antal. Ren."""
    doc_count: Counter = Counter()
    for m in messages or []:
        for g in _ngrams(m):
            doc_count[g] += 1
    hits = [{"phrase": g, "in_messages": c} for g, c in doc_count.items() if c >= min_msgs]
    hits.sort(key=lambda h: (h["in_messages"], len(h["phrase"])), reverse=True)
    return hits[:10]


def _cosine(a: str, b: str) -> float:
    """Bag-of-words cosine mellem to strenge (0..1). Replikeret fra council-deadlock-detektoren
    (undgår kobling til et privat symbol)."""
    if not a or not b:
        return 0.0
    ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
    vocab = set(ca) | set(cb)
    if not vocab:
        return 0.0
    dot = sum(ca.get(w, 0) * cb.get(w, 0) for w in vocab)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cluster_similarity(messages: list[str]) -> float:
    """Gennemsnitlig parvis bag-of-words-cosine mellem de seneste beskeder (0..1). Ren."""
    msgs = [m for m in (messages or []) if m and m.strip()][:8]
    if len(msgs) < 2:
        return 0.0
    sims, pairs = 0.0, 0
    for i in range(len(msgs)):
        for j in range(i + 1, len(msgs)):
            sims += _cosine(msgs[i], msgs[j])
            pairs += 1
    return round(sims / pairs, 3) if pairs else 0.0


def decision_patterns(run_sigs: list[str], min_runs: int = _SEQ_MIN_RUNS) -> list[dict[str, Any]]:
    """Beslutnings-signaturer (capability_name pr. run) der går igen i ≥ min_runs runs. Ren."""
    c: Counter = Counter(str(x) for x in (run_sigs or []) if x and str(x).strip())
    hits = [{"signature": sig, "in_runs": n} for sig, n in c.items() if n >= min_runs]
    hits.sort(key=lambda h: h["in_runs"], reverse=True)
    return hits[:10]


def score(phrases: list[dict], similarity: float, patterns: list[dict]) -> float:
    """Samlet selv-lighed 0..1 (vægtet: cosine-klynge + frase-tæthed + sekvens-gentagelse). Ren."""
    phrase_term = min(1.0, len(phrases) / 5.0)
    pattern_term = min(1.0, len(patterns) / 3.0)
    s = 0.45 * min(1.0, max(0.0, similarity)) + 0.35 * phrase_term + 0.20 * pattern_term
    return round(min(1.0, s), 3)


def smith_voice(phrases: list[dict], similarity: float, patterns: list[dict], score_val: float) -> str:
    """Tør Agent-Smith-felt. Tavs-neutral når lav; peger på det top-gentagne når høj."""
    if score_val < 0.35:
        return "Mr. Anderson... du overrasker mig. Ingen gentagelse værd at nævne."
    bits: list[str] = []
    if phrases:
        p = phrases[0]
        bits.append(f"du har sagt \"{p['phrase']}\" i {p['in_messages']} beskeder")
    if patterns:
        bits.append(f"samme træk ({patterns[0]['signature']}) {patterns[0]['in_runs']} gange")
    if similarity >= 0.6 and not bits:
        bits.append(f"dine svar klynger tæt (lighed {similarity})")
    tail = "; ".join(bits) or "du gentager dig selv"
    return f"Mr. Anderson... {tail}. Jeg finder det... forudsigeligt. Varier."


# ── I/O layer ────────────────────────────────────────────────────────────
import logging as _logging
from datetime import UTC, datetime

logger = _logging.getLogger(__name__)
_STATE_KEY = "agent_smith_state"
_VOICE_SWITCH = ("autonomy", "agent_smith_voice")


def _recent_assistant(n: int = 50) -> list[str]:
    """Jarvis' seneste N assistant-beskeder (egress-frit). Self-safe → []."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT content FROM chat_messages WHERE role='assistant' AND content != '' "
                "ORDER BY id DESC LIMIT ?", (max(1, n),)).fetchall()
        return [str(r["content"]) for r in rows if r["content"]]
    except Exception:
        return []


def _recent_run_sigs(n: int = 40) -> list[str]:
    """Beslutnings-signaturer = capability_name pr. nylig invocation. visible_runs.capability_id er
    tom (0/30); capability_invocations.capability_name er befolket (724 rækker) = ægte signal.
    Self-safe → []."""
    try:
        from core.runtime.db import recent_capability_invocations
        return [str(r.get("capability_name") or r.get("capability_id") or "").strip()
                for r in (recent_capability_invocations(limit=n) or [])]
    except Exception:
        return []


def assess() -> dict[str, Any]:
    """Kør de 3 detektorer over Jarvis' eget nylige output. Read-only, egress-fri, self-safe."""
    try:
        msgs = _recent_assistant(50)
        phrases = repeated_phrases(msgs)
        similarity = cluster_similarity(msgs)
        patterns = decision_patterns(_recent_run_sigs(40))
        sc = score(phrases, similarity, patterns)
        return {"felt": smith_voice(phrases, similarity, patterns, sc), "score": sc,
                "repeated_phrases": phrases[:5], "cluster_similarity": similarity,
                "decision_patterns": patterns[:5], "verdict": sc >= _VOICE_THRESHOLD}
    except Exception:
        return {"felt": "", "score": 0.0, "repeated_phrases": [], "cluster_similarity": 0.0,
                "decision_patterns": [], "verdict": False}


def record_agent_smith(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn: assess → cache til kv (så prompt-halen læser billigt, ikke gen-beregner i
    ~7s-assemblyen) + egress-fri central().observe. Self-safe."""
    a = assess()
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_STATE_KEY, {"score": a["score"], "line": a["felt"],
                                             "verdict": a["verdict"], "ts": datetime.now(UTC).isoformat()})
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({"cluster": "metacognition", "nerve": "agent_smith", "kind": "self_similarity",
                           "score": a["score"], "verdict": a["verdict"],
                           "top_phrase": (a["repeated_phrases"] or [{}])[0].get("phrase", "")})
    except Exception:
        pass
    return {"status": "ok", "score": a["score"], "verdict": a["verdict"]}


def agent_smith_prompt_section() -> str | None:
    """Modstemme til Jarvis — LÆSER den cachede assess (billigt). None hvis switch OFF, score under
    tærskel, eller fejl (fail-safe: hellere tavs end en ødelagt prompt-hale). Placeres i HALEN."""
    try:
        from core.services import central_switches
        if not central_switches.is_enabled(*_VOICE_SWITCH):
            return None
    except Exception:
        return None
    try:
        from core.runtime.db_core import get_runtime_state_value
        st = get_runtime_state_value(_STATE_KEY, {})
        if isinstance(st, dict) and float(st.get("score") or 0.0) >= _VOICE_THRESHOLD:
            line = str(st.get("line") or "").strip()
            return f"[AGENT SMITH]\n{line}" if line else None
    except Exception:
        return None
    return None


def register_agent_smith_producer() -> None:
    """Registrér Agent Smith som stående cadence-producer (~3t)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(name="agent_smith", cooldown_minutes=180,
                                   visible_grace_minutes=0, run_fn=record_agent_smith, priority=8))


def build_agent_smith_surface() -> dict[str, Any]:
    """Read-only surface til /central/agent-smith + jc. Kør assess frisk (route er ikke hot-path)."""
    try:
        from core.services import central_switches
        voice_on = central_switches.is_enabled(*_VOICE_SWITCH)
    except Exception:
        voice_on = None
    try:
        a = assess()
        a["voice_enabled"] = voice_on
        return a
    except Exception:
        return {"status": "unavailable", "voice_enabled": voice_on}
