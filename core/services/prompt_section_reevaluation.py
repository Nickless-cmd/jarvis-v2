"""Revurderings-løkke for slukkede prompt-sektioner.

**Problemet.** `prompt_observer.DIAGNOSTIC_NOISE_LABELS` slukker 24 awareness-kanaler.
Listen blev lavet 2026-06-22 på Jarvis' egen gennemgang af sin prompt, og de fleste
domme var rigtige *dengang*. Men en blacklist er en frossen dom uden udløbsdato: intet
i systemet spørger nogensinde igen, selv når indholdet bag en kanal er blevet bedre.
Målt 18. aug: `rules learned from arcs` — cut som "repeated retrospective noise" —
producerer i dag 653 tegn ægte lærte drift-regler som aldrig nåede frem.

**Hvorfor opsamlingen er gratis.** Kaldsmønsteret er
``_awareness_add(60, "rules learned from arcs", arc_rules_section())``: Python
evaluerer builderen FØR `_awareness_add` kaldes, så indholdet er allerede beregnet når
blacklisten forkaster det. Blacklisten sparer nul compute — den smider færdigt arbejde
væk. Vi kan derfor prøvetage det uden at køre noget ekstra.

**Hvad løkken gør — og ikke gør.** Den *foreslår*, den tænder ikke. Samme trust-gate som
`self_repair_engine` og `system_cartographer`: en maskine der selv må skrue op for hvad
Jarvis ser om sig selv, er en maskine der kan tale sig selv efter munden. Forslaget bærer
sin egen begrundelse, fordi den oprindelige klage over blacklisten netop var at *"INGEN
kunne se HVORFOR en sektion blev droppet"*.

Tærsklerne er kalibreret mod de seks kanaler der blev målt i hånden 18. aug (se
`tests/test_prompt_section_reevaluation.py`): løkken skal nå frem til samme dom som
mennesket gjorde. Et falsk positiv koster et blik, ikke en regression.
"""
from __future__ import annotations

import hashlib
import re
import time

_SAMPLE_PREFIX = "prompt_section_sample."
_SWEEP_KEY = "prompt_section_reeval.last_sweep"
_SAMPLE_TTL = 30 * 24 * 3600
_SWEEP_TTL = 90 * 24 * 3600

_SAMPLE_COOLDOWN_S = 3600.0  # højst én prøve pr. kanal i timen
_SWEEP_INTERVAL_S = 24 * 3600.0
_HEAD_CHARS = 400  # nok til at begrunde et forslag, for lidt til at være en kopi
_MAX_HASHES = 6

_MIN_SAMPLES = 3  # skal ses over flere builds før den kan foreslås
CANDIDATE_SCORE = 0.6

# En sektion der melder at den intet fandt, er ikke information.
_PLACEHOLDERS = ("<ingen", "<none", "<tom", "ingen data", "n/a", "ikke fundet")
# "Ny samtale ×5", "NEJ ×14" — tællinger, ikke bevidsthed (blacklistens egen begrundelse).
_COUNT_LINE = re.compile(r"[×x]\s*\d+\s*$")

_last_sample_at: dict[str, float] = {}
_last_hash: dict[str, str] = {}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]


def substance(text: str) -> dict[str, object]:
    """Scorer om indholdet er værd at læse. ``{score: 0..1, reasons: [...]}``.

    Heuristikkerne er ikke gættede — hver enkelt svarer til en dom vi traf i hånden:
    tomhed, pladsholdere ("<ingen edges fundet>"), selvindlysende gentagelse
    (``agentic_round_start ← agentic_round_start``) og rene tællinger ("×14").
    """
    body = str(text or "").strip()
    reasons: list[str] = []
    if not body:
        return {"score": 0.0, "reasons": ["tom"], "chars": 0, "lines": 0}

    lines = _lines(body)
    low = body.lower()
    score = 1.0

    if any(p in low for p in _PLACEHOLDERS):
        score -= 0.7
        reasons.append("pladsholder: melder selv at den intet fandt")

    # Krop uden overskrift: første linje er næsten altid en label.
    payload = lines[1:] if len(lines) > 1 else lines
    if payload:
        dup_ratio = 1.0 - (len(set(payload)) / len(payload))
        if dup_ratio >= 0.2:
            score -= 0.5
            reasons.append(f"gentagelse: {dup_ratio:.0%} af linjerne er dubletter")
        count_ratio = sum(1 for ln in payload if _COUNT_LINE.search(ln)) / len(payload)
        if count_ratio >= 0.5:
            score -= 0.5
            reasons.append("tællinger frem for indhold")

    if len(body) < 40:
        score -= 0.4
        reasons.append("for kort til at bære betydning")

    score = max(0.0, min(1.0, score))
    if score >= CANDIDATE_SCORE and not reasons:
        reasons.append("substantielt indhold uden støj-mønstre")
    return {"score": round(score, 3), "reasons": reasons,
            "chars": len(body), "lines": len(lines)}


def observe_discarded(label: str, content: str | None) -> None:
    """Prøvetag indhold som blacklisten netop har forkastet. Gratis og selv-sikker.

    Rate-limitet pr. kanal (1/time) og skriver kun når indholdet faktisk har ændret sig,
    så det normale tilfælde koster ét dict-opslag og ingen DB-trafik. Kaster ALDRIG ind
    i en prompt-build.
    """
    try:
        label = str(label or "").strip()
        body = str(content or "").strip()
        if not label or not body:
            return
        now = time.time()
        if now - _last_sample_at.get(label, 0.0) < _SAMPLE_COOLDOWN_S:
            return
        h = _digest(body)
        if _last_hash.get(label) == h:
            _last_sample_at[label] = now
            return
        _last_sample_at[label] = now
        _last_hash[label] = h

        from core.services import shared_cache

        key = _SAMPLE_PREFIX + label
        prev = shared_cache.get(key) or {}
        hashes = [x for x in list(prev.get("hashes") or []) if x != h][-(_MAX_HASHES - 1):]
        hashes.append(h)
        shared_cache.set(key, {
            "label": label,
            "head": body[:_HEAD_CHARS],
            "chars": len(body),
            "hashes": hashes,
            "samples": int(prev.get("samples") or 0) + 1,
            "first_seen": prev.get("first_seen") or now,
            "last_seen": now,
        }, ttl_seconds=_SAMPLE_TTL)
        # Kun på en faktisk skrivning (≤1/time/kanal) — aldrig pr. build.
        maybe_run_sweep()
    except Exception:
        pass


def _read_samples() -> list[dict[str, object]]:
    try:
        from core.runtime.db import connect
        import json

        now = time.time()
        with connect() as conn:
            rows = conn.execute(
                "SELECT cache_key, value_json FROM shared_cache "
                "WHERE cache_key LIKE ? AND expires_at > ?",
                (_SAMPLE_PREFIX + "%", now),
            ).fetchall()
        out = []
        for key, value_json in rows:
            try:
                v = json.loads(value_json)
            except Exception:
                continue
            if isinstance(v, dict) and v.get("head"):
                out.append(v)
        return out
    except Exception:
        return []


def evaluate() -> list[dict[str, object]]:
    """Vurdér alle prøvetagne, slukkede kanaler. Ren læsning — tænder intet."""
    results = []
    for s in _read_samples():
        label = str(s.get("label") or "")
        head = str(s.get("head") or "")
        verdict = substance(head)
        samples = int(s.get("samples") or 0)
        distinct = len(set(s.get("hashes") or []))
        reasons = list(verdict["reasons"])

        candidate = bool(verdict["score"] >= CANDIDATE_SCORE and samples >= _MIN_SAMPLES)
        if candidate and distinct <= 1 and samples >= _MIN_SAMPLES * 2:
            # Uændret over mange builds = et notat ingen læser, ikke et levende signal.
            candidate = False
            reasons.append("frosset: identisk indhold over alle prøver")
        if verdict["score"] >= CANDIDATE_SCORE and samples < _MIN_SAMPLES:
            reasons.append(f"afventer flere prøver ({samples}/{_MIN_SAMPLES})")

        results.append({
            "label": label, "score": verdict["score"], "chars": verdict["chars"],
            "samples": samples, "distinct": distinct,
            "candidate": candidate, "reasons": reasons, "head": head[:200],
        })
    results.sort(key=lambda r: (-float(r["score"]), str(r["label"])))
    return results


def _propose(candidates: list[dict[str, object]]) -> None:
    """Læg forslaget hvor Bjørn og Centralen kan se det — med sin egen begrundelse."""
    if not candidates:
        return
    try:
        from core.runtime.db_central_incidents import record_central_incident

        for c in candidates:
            record_central_incident(
                cluster="prompt", nerve="section_reevaluation", kind="reenable_proposed",
                severity="info", dedup=True,
                message=(
                    f"'{c['label']}' er slukket, men bærer nu {c['chars']} tegn "
                    f"({c['score']:.2f}): {'; '.join(c['reasons'])[:160]}. "
                    f"Tænd: central_switches.set_enabled('prompt_section', "
                    f"'{c['label']}', True)"
                ),
            )
    except Exception:
        pass


def maybe_run_sweep() -> dict[str, object]:
    """Kør vurderingen højst én gang i døgnet. Ren DB-læsning + aritmetik (~ms).

    Kaldes fra opsamlings-stien, så der ikke skal bygges endnu en blind timer-daemon
    (jf. de 25 LLM-blinde daemoner der allerede brænder tokens). Kører ingen buildere.
    """
    try:
        from core.services import shared_cache

        now = time.time()
        last = shared_cache.get(_SWEEP_KEY) or {}
        if now - float(last.get("at") or 0.0) < _SWEEP_INTERVAL_S:
            return {"ran": False, "reason": "cooldown"}
        shared_cache.set(_SWEEP_KEY, {"at": now}, ttl_seconds=_SWEEP_TTL)

        results = evaluate()
        candidates = [r for r in results if r["candidate"]]
        _propose(candidates)
        return {"ran": True, "evaluated": len(results),
                "candidates": [c["label"] for c in candidates]}
    except Exception:
        return {"ran": False, "reason": "error"}


def reevaluation_surface() -> dict[str, object]:
    """Overflade til Centralen/MC: hvilke slukkede kanaler fortjener et nyt blik?"""
    results = evaluate()
    candidates = [r for r in results if r["candidate"]]
    return {
        "active": bool(results),
        "evaluated": len(results),
        "candidates": candidates,
        "all": results,
        "summary": (
            f"{len(candidates)} af {len(results)} slukkede kanaler bærer nu indhold "
            f"der er værd at læse" if results else "Ingen prøver endnu"
        ),
    }
