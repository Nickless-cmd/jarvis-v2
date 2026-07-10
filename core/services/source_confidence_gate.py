"""Source-confidence gate (epistemisk gate, 2026-07-10).

Født af en ægte fejl i dag: Jarvis (og Claude) påstod at et tool "CCDN" fandtes,
baseret på en web-artikel — ukritisk, som var det first-hand viden. TruthGate v2
fanger HANDLINGS-påstande ("jeg kørte X"), ikke EKSISTENS/FAKTA-påstande fra
upålidelige kilder. Denne gate lukker det epistemiske hul: den skelner
**first-hand evidens** (set i kode/filer via inspektions-tools) fra **second-hand
rygte** (læst via web-søgning), og advarer når en eksistens/navne-påstand kun er
second-hand-kildet.

Ren detektor (testbar). Tænkt kørt SHADOW via central().decide over turens output
+ dens tool-provenance (_turn_tool_calls). Aktiv korrektion (injicér 'markér som
ifølge X / verificér') er et senere skridt efter shadow-observation.
"""
from __future__ import annotations

import re
from typing import Any

# First-hand = direkte inspektion af faktisk kilde (kode/filer/DB på egen maskine).
_FIRST_HAND = {
    "read_file", "grep", "glob", "list_dir", "cat", "db_query", "bash",
    "operator_read_file", "operator_grep", "operator_glob", "operator_list_dir",
    "git_log", "git_diff", "git_status", "git_blame", "search", "find_files",
    "search_memory", "get_flag", "read_memory_topic",
}
# Second-hand = eksternt rygte (web). Kan være sandt, men er IKKE first-hand.
_SECOND_HAND = {"web_search", "web_fetch", "web_scrape", "operator_webfetch", "wolfram_query"}

# Eksistens/navne-påstande (da+en) — "der findes et X", "det hedder Y", "X er et tool".
_EXISTENCE_RE = re.compile(
    r"\b(findes|hedder|kaldes|der\s+er\s+et|det\s+er\s+et|eksisterer|"
    r"there\s+is\s+a|is\s+a\s+(tool|module|feature|system|flag|file)|is\s+called|exists?)\b",
    re.IGNORECASE,
)


def _tool_names(tools_used: list) -> set[str]:
    out: set[str] = set()
    for t in tools_used or []:
        n = t.get("name") if isinstance(t, dict) else str(t)
        if n:
            out.add(str(n).strip())
    return out


def assess_source_confidence(*, output_text: str, tools_used: list | None = None) -> dict[str, Any]:
    """Vurdér epistemisk kilde-konfidens for en tur.

    Returnerer {confidence: high|medium|low, provenance, has_existence_claim,
    caution: str|None}. Caution sættes kun når en eksistens/navne-påstand er
    KUN second-hand-kildet (web uden first-hand inspektion) — det farlige tilfælde.
    """
    names = _tool_names(tools_used)
    first = bool(names & _FIRST_HAND)
    second = bool(names & _SECOND_HAND)
    has_claim = bool(_EXISTENCE_RE.search(str(output_text or "")))

    if first:
        provenance = "first-hand" if not second else "mixed"
    elif second:
        provenance = "second-hand"
    else:
        provenance = "unsourced"

    caution = None
    confidence = "high"
    if provenance == "first-hand":
        confidence = "high"
    elif provenance == "mixed":
        confidence = "high"
    elif provenance == "second-hand":
        confidence = "low" if has_claim else "medium"
        if has_claim:
            caution = ("Eksistens/navne-påstand er KUN web-kildet (second-hand). "
                       "Markér som 'ifølge <kilde>' og verificér mod første-hånds-kilde "
                       "(kode/filer) før du påstår at noget FINDES eller HEDDER noget bestemt.")
    else:  # unsourced
        confidence = "low" if has_claim else "medium"
        if has_claim:
            caution = ("Eksistens/navne-påstand uden nogen kilde i turen. Verificér "
                       "(grep/read_file) før du påstår eksistens.")

    return {"confidence": confidence, "provenance": provenance,
            "has_existence_claim": has_claim, "caution": caution}


def build_source_confidence_surface(*, output_text: str = "", tools_used: list | None = None) -> dict[str, Any]:
    """Central-CLI: jc raw /central/source-confidence (senest vurderede tur, hvis givet)."""
    a = assess_source_confidence(output_text=output_text, tools_used=tools_used or [])
    return {
        "active": bool(a["caution"]),
        "mode": "source-confidence",
        "summary": {"confidence": a["confidence"], "provenance": a["provenance"]},
        "assessment": a,
    }
