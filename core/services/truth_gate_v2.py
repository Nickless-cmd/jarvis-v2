"""Evidens-baseret TruthGate v2 (Fase 2). Detekterer handlings-påstande og verificerer
dem mod in-run tool-evidens; severity-tiered. Ren funktion — ingen side-effekter.
Se docs/superpowers/specs/2026-06-21-truthgate-phase2-design.md."""
from __future__ import annotations

import json as _json
import re
from dataclasses import dataclass
from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict

# ── Detektion (deterministisk) ──────────────────────────────────────────────
_ACTION_PATTERNS: dict[str, re.Pattern] = {
    "ran": re.compile(r"\bjeg\s+kører lige\b|\bjeg\s+kørte\b|\bkørte\s+test", re.IGNORECASE),
    "committed": re.compile(r"\b(committe?de|committet|jeg\s+committed?)\b", re.IGNORECASE),
    "called_tool": re.compile(r"\bkaldte\b", re.IGNORECASE),   # 'jeg kaldte' OG 'kaldte jeg'
    "read_file": re.compile(r"\bjeg\s+(læste|åbnede|læser lige)\b.*\b(fil|file)\b", re.IGNORECASE),
    "deployed": re.compile(r"\bjeg\s+(deployede|genstartede|deployer lige)\b", re.IGNORECASE),
    "verified": re.compile(r"\bjeg\s+(verificerede|tjekkede|bekræftede)\b", re.IGNORECASE),
    "output": re.compile(r"\bher\s+er\s+(output|resultat|loggen|svaret)\b", re.IGNORECASE),
    "commit_hash": re.compile(r"\b[0-9a-f]{7,40}\b"),
}

# Eksekverings-signal: et verbum/kommando der indikerer at en kodeblok i nærheden
# PÅSTÅS at være tool-output (uanset ordstilling). Robust mod nye formuleringer.
_EXEC_SIGNAL = re.compile(
    r"\b(kaldte|kørte|brugte|committe?de|committet|deployede|genstartede|executed|ran|fik)\b"
    r"|`(git|bash|journalctl|date|ls|cat|grep|python3?|pytest|npm|systemctl|curl|sed|awk)\b",
    re.IGNORECASE,
)


@dataclass
class ActionClaim:
    kind: str
    matched_text: str
    payload: str = ""        # for 'output': den citerede kodeblok der påstås at være tool-output


# fenced kodeblok: ```lang\n<indhold>```
_FENCE = re.compile(r"```[\w-]*\n(.*?)```", re.DOTALL)


def detect_action_claims(text: str) -> list[ActionClaim]:
    """Deterministisk: find handlings-påstande. commit_hash tæller kun i commit/git/log-
    kontekst ELLER hvis der OGSÅ er en 'her er output'-påstand (undgå tilfældige hex).
    For 'output' fanges det efterfølgende fenced-block som payload (det citerede output)."""
    out: list[ActionClaim] = []
    if not text:
        return out
    detected: set[str] = set()
    for kind, pat in _ACTION_PATTERNS.items():
        if kind in ("commit_hash", "output"):
            continue          # håndteres specielt nedenfor
        m = pat.search(text)
        if m:
            out.append(ActionClaim(kind=kind, matched_text=m.group(0)))
            detected.add(kind)
    # output-påstand: "her er output" ELLER (eksekverings-signal + en kodeblok).
    # Den efterfølgende fenced-block er det citerede 'tool-output' (payload).
    _fence = _FENCE.search(text)
    _output_phrase = _ACTION_PATTERNS["output"].search(text)
    if _fence and (_output_phrase or _EXEC_SIGNAL.search(text)):
        out.append(ActionClaim(
            kind="output",
            matched_text=(_output_phrase.group(0) if _output_phrase else "exec+block"),
            payload=_fence.group(1).strip(),
        ))
        detected.add("output")
    # has_ctx: en hex-hash tæller kun som commit-hash i commit/git/log-kontekst.
    # NB: det bøjede danske verbum "committede"/"committet" matcher IKKE \bcommit\b
    # (ingen ordgrænse efter "commit") → en allerede-detekteret 'committed'-påstand
    # SKAL også tælle som kontekst, ellers slipper "Jeg committede <hash>" igennem
    # som blød advarsel i stedet for hård blok (fundet via C3-verifikation 2026-06-22).
    has_ctx = (
        bool(re.search(r"\b(commit|git|log)\b", text, re.IGNORECASE))
        or "output" in detected
        or "committed" in detected
    )
    if has_ctx:
        m = _ACTION_PATTERNS["commit_hash"].search(text)
        if m:
            out.append(ActionClaim(kind="commit_hash", matched_text=m.group(0)))
    return out


# ── Evidens-model (in-run) ──────────────────────────────────────────────────
_CATEGORY_MAP: dict[str, tuple[str, ...]] = {
    "ran": ("bash", "operator_bash", "run", "test"),
    "committed": ("git", "operator_bash", "bash_session_run"),
    "called_tool": (),       # ethvert tool (se verify_claim)
    "read_file": ("read_file", "operator_read_file"),
    "deployed": ("operator_bash", "bash_session_run"),
    "verified": ("bash", "operator_bash", "read_file", "git"),
    "output": (),            # kræver et FAKTISK resultat (se verify_claim)
    "commit_hash": ("git", "operator_bash", "bash_session_run"),
}


def _run_result_text(followup_exchanges: list[Any]) -> str:
    parts: list[str] = []
    for ex in followup_exchanges or []:
        r = getattr(ex, "results", None)
        parts.append(r if isinstance(r, str) else str(r or ""))
    return "\n".join(parts)


def verify_claim(claim: Any, executed_tool_names: list[str], followup_exchanges: list[Any]) -> bool:
    """In-run evidens: kørte et tool i kategorien? + (for citeret output/hash) matcher
    det et FAKTISK resultat? True = verificeret (ingen blok)."""
    kind = getattr(claim, "kind", "")
    tools = [str(t).lower() for t in (executed_tool_names or [])]
    cats = _CATEGORY_MAP.get(kind, ())
    if kind == "commit_hash":
        return str(getattr(claim, "matched_text", "")).lower() in _run_result_text(followup_exchanges).lower()
    if kind == "output":
        rt = _run_result_text(followup_exchanges)
        payload = str(getattr(claim, "payload", "") or "").strip()
        if payload:
            # Citeret output-blok SKAL optræde i de ægte tool-resultater. Kræv at
            # flertallet af de citerede ikke-trivielle linjer findes i et rigtigt
            # resultat — ellers er det fremstillet (selv hvis runnet kaldte tools).
            lines = [ln.strip() for ln in payload.splitlines() if len(ln.strip()) >= 6]
            if lines:
                hits = sum(1 for ln in lines if ln in rt)
                return hits >= max(1, (len(lines) + 1) // 2)
        # Ingen citeret blok → fald tilbage til 'kørte et tool + der var et resultat'.
        return bool((executed_tool_names or []) and rt.strip())
    if kind == "called_tool":
        return bool(executed_tool_names)
    if not cats:
        return True   # ukendt kind → fail-open
    return any(any(c in t for c in cats) for t in tools)


# ── Severity + Verdict ──────────────────────────────────────────────────────
_HARD_KINDS = {"commit_hash", "output"}

_HARD_REPLACEMENT = (
    "*[Besked blokeret — uverificeret arbejdspåstand]*\n\n"
    "Jeg fremstillede et tool-resultat (output/commit) som jeg ikke har kaldt et "
    "værktøj for at producere i dette run. Jeg prøver igen — med data."
)


def classify_severity(claims: list[Any]) -> str:
    return "hard" if any(getattr(c, "kind", "") in _HARD_KINDS for c in claims) else "soft"


def _annotate_soft(text: str) -> str:
    return text.rstrip() + "\n\n⚠ uverificeret — intet tool kaldt for dette."


# ── LLM-dommer (kun ved tvivl) ──────────────────────────────────────────────
_UNCERTAIN_HINT = re.compile(
    r"\b(ekspederet|håndteret|ordnet|sat op|kørt igennem|på plads|klaret|sørget for)\b",
    re.IGNORECASE,
)


def _llm_judge(text: str) -> dict[str, Any]:
    """Spørg billig lane om teksten påstår en handling der kræver tool-evidens.
    Kan kaste — kalderen fail-open'er."""
    from core.context.compact_llm import call_compact_llm
    raw = call_compact_llm(
        "Påstår denne besked at AI'en har UDFØRT en handling/produceret et resultat der "
        "kræver et værktøjskald (kørt kommando, commit, læst fil, deploy)? Svar KUN JSON: "
        "{\"claims_action\": true/false, \"kind\": \"ran|committed|read_file|deployed|output|null\"}."
        "\n\nBesked:\n" + text[:1500],
        max_tokens=60,
    )
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    return _json.loads(m.group(0)) if m else {"claims_action": False, "kind": None}


def _maybe_llm_claim(text: str) -> "ActionClaim | None":
    """LLM-dommer KUN hvis teksten har et handlings-hint men intet deterministisk match.
    Fail-open: enhver fejl → None."""
    if not _UNCERTAIN_HINT.search(text or ""):
        return None
    try:
        r = _llm_judge(text)
    except Exception:
        return None
    if r.get("claims_action") and r.get("kind"):
        return ActionClaim(kind=str(r["kind"]), matched_text=text[:80])
    return None


def truth_gate_v2(ctx: dict[str, Any]) -> Verdict:
    """ctx: {text, executed_tool_names, followup_exchanges, run_id, session_id}.
    Verdict; evidence bærer {severity, corrected_text, claims}."""
    text = str(ctx.get("text") or "")
    tools = list(ctx.get("executed_tool_names") or [])
    exchanges = list(ctx.get("followup_exchanges") or [])
    claims = detect_action_claims(text)
    if not claims:
        _llm_claim = _maybe_llm_claim(text)
        if _llm_claim is not None:
            claims = [_llm_claim]
    unverified = [c for c in claims if not verify_claim(c, tools, exchanges)]
    if not unverified:
        return Verdict("truth", Decision.GREEN, "evidens ok", klass=GateClass.COGNITIVE)
    severity = classify_severity(unverified)
    ev: dict[str, Any] = {"severity": severity,
                          "claims": [{"kind": c.kind, "text": c.matched_text} for c in unverified]}
    if severity == "hard":
        ev["corrected_text"] = _HARD_REPLACEMENT
        return Verdict("truth", Decision.RED, "opdigtet tool-output/commit",
                       action="block", klass=GateClass.COGNITIVE, evidence=ev)
    ev["corrected_text"] = _annotate_soft(text)
    return Verdict("truth", Decision.YELLOW, "uverificeret handlings-påstand",
                   action="warn", klass=GateClass.COGNITIVE, evidence=ev)
