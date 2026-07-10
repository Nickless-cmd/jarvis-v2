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

from core.services.central_agent_smith_escalation import (
    pattern_key,
    step_escalation,
    top_line,
)

logger = _logging.getLogger(__name__)
_STATE_KEY = "agent_smith_state"
_ESCALATION_KEY = "agent_smith_escalation"
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


def _load_escalation_state() -> dict[str, Any]:
    """Eskalerings-tilstandsmaskinens persistente state. Self-safe → tom."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        st = get_runtime_state_value(_ESCALATION_KEY, {})
        return st if isinstance(st, dict) else {}
    except Exception:
        return {}


def _save_escalation_state(state: dict[str, Any]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_ESCALATION_KEY, state)
    except Exception:
        pass


def _detected_patterns(a: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Byg {pattern_key: {kind,label,metric}} fra assess() — fraser + beslutnings-signaturer."""
    out: dict[str, dict[str, Any]] = {}
    for p in (a.get("repeated_phrases") or []):
        label = str(p.get("phrase") or "").strip()
        if label:
            out[pattern_key("phrase", label)] = {"kind": "phrase", "label": label,
                                                 "metric": float(p.get("in_messages") or 0)}
    for p in (a.get("decision_patterns") or []):
        label = str(p.get("signature") or "").strip()
        if label:
            out[pattern_key("seq", label)] = {"kind": "seq", "label": label,
                                             "metric": float(p.get("in_runs") or 0)}
    return out


def _execute_mint(key: str, label: str, kind: str, metric: float) -> str | None:
    """Trin 2/BIND: auto-mint en bindende behavioral_decision (Jarvis' egen idé, automatisk).
    Dedup + observe er indbygget i behavioral_decisions.create_decision. Self-safe → None."""
    try:
        from core.services.behavioral_decisions import create_decision
        if kind == "phrase":
            directive = (f'Stop med at gentage frasen "{label}" — Agent Smith har målt den '
                         f'{int(metric)}× i dit nylige output. Bryd mønstret aktivt, ikke bare i ord.')
            cue = f'Før du skriver "{label}" igen — stop og vælg en anden formulering eller handling.'
        else:
            directive = (f'Stop med at falde tilbage på samme træk "{label}" — Agent Smith har set '
                         f'det {int(metric)}× på stribe. Vælg en anden tilgang.')
            cue = f'Før du igen vælger "{label}" — stop og spørg: er der en anden vej?'
        dec = create_decision(
            directive=directive,
            rationale="Auto-mintet af Agent Smith (Trin 2/Bind): gentaget mønster bestod efter kommentar.",
            trigger_cue=cue, priority=85, source_type="agent_smith",
            source_record_id=key, created_by="agent_smith")
        return dec.get("decision_id")
    except Exception:
        return None


def _execute_revoke(decision_id: str) -> None:
    """De-eskalering: pensionér et Smith-mintet direktiv når mønsteret er løst (compliance)."""
    try:
        from core.services.behavioral_decisions import revoke_decision
        revoke_decision(decision_id, reason="Agent Smith: mønster løst (compliance)")
    except Exception:
        pass


def _execute_observe(act: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "metacognition", "nerve": "agent_smith",
                           "kind": "escalation", "event": act.get("event"),
                           "pattern_key": act.get("pattern_key"), "rung": act.get("rung"),
                           "label": act.get("label"), "reason": act.get("reason")})
    except Exception:
        pass


def run_escalation_tick(assessment: dict[str, Any] | None = None) -> dict[str, Any]:
    """Kør eskalerings-stigen over de aktuelt detekterede mønstre: mål compliance,
    klatre/de-eskalér, auto-mint/pensionér direktiver, observ hver overgang. Self-safe."""
    try:
        a = assessment or assess()
        detected = _detected_patterns(a)
        state = _load_escalation_state()
        new_state, actions = step_escalation(state, detected, datetime.now(UTC).isoformat())
        for act in actions:
            t = act.get("type")
            if t == "mint":
                did = _execute_mint(act["pattern_key"], act.get("label", ""),
                                    act.get("kind", "phrase"), float(act.get("metric") or 0))
                pat = new_state.get("patterns", {}).get(act["pattern_key"])
                if did and isinstance(pat, dict):
                    pat["decision_id"] = did
            elif t == "revoke":
                _execute_revoke(act["decision_id"])
            elif t == "observe":
                _execute_observe(act)
        _save_escalation_state(new_state)
        return {"actions": len(actions), "line": top_line(actions),
                "tracked": len(new_state.get("patterns", {})),
                "resolved_total": len(new_state.get("resolved", []))}
    except Exception:
        return {"actions": 0, "line": "", "tracked": 0, "resolved_total": 0}


def record_agent_smith(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn: assess → kør eskalerings-stigen → cache til kv (så prompt-halen læser
    billigt, ikke gen-beregner i ~7s-assemblyen) + egress-fri central().observe. Self-safe."""
    a = assess()
    esc = run_escalation_tick(a)
    rung_line = str(esc.get("line") or "")
    line = rung_line or a["felt"]
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_STATE_KEY, {"score": a["score"], "line": line,
                                             "rung_line": rung_line,
                                             "verdict": bool(a["verdict"] or rung_line),
                                             "ts": datetime.now(UTC).isoformat()})
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({"cluster": "metacognition", "nerve": "agent_smith", "kind": "self_similarity",
                           "score": a["score"], "verdict": a["verdict"],
                           "top_phrase": (a["repeated_phrases"] or [{}])[0].get("phrase", "")})
    except Exception:
        pass
    return {"status": "ok", "score": a["score"], "verdict": a["verdict"], "escalation": esc}


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
        if not isinstance(st, dict):
            return None
        # Eskaleret linje (bind/confront/resolved) surfacer UANSET score — den er allerede
        # en governance-hændelse. Ellers falder vi tilbage på score-gaten (ren kommentar).
        rung_line = str(st.get("rung_line") or "").strip()
        if rung_line:
            return f"[AGENT SMITH]\n{rung_line}"
        if float(st.get("score") or 0.0) >= _VOICE_THRESHOLD:
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
        # Eskalerings-stigen (read-only — ingen mint/tick på en GET-route)
        try:
            st = _load_escalation_state()
            _keep = ("label", "kind", "rung", "decision_id", "first_seen", "last_metric", "baseline")
            a["escalation"] = {
                "tracked": [{"key": k, **{f: p.get(f) for f in _keep}}
                            for k, p in (st.get("patterns") or {}).items()],
                "resolved": (st.get("resolved") or [])[-10:],
                "rungs": {"1": "kommentér", "2": "bind (auto-direktiv)", "3": "konfrontér (real-time)"},
            }
        except Exception:
            a["escalation"] = {"tracked": [], "resolved": []}
        return a
    except Exception:
        return {"status": "unavailable", "voice_enabled": voice_on}
