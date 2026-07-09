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
