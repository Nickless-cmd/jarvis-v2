"""Rule-engine conclusions — symbolic reasoning surfaced to the LLM.

Bygger bro mellem rule_engine (forward-chaining symbolsk inferens) og
visible-lane prompten. Engine producerer allerede skarpe conclusions
("strong appetite drives focus", "release marker fyret") — denne sektion
formaterer top-N og injecter dem som awareness-line.

Det er det første "neuro-symbolic" lag der faktisk når Jarvis. Han har
haft engine + 36 regler siden commit 8860301 — denne fil får output'et
ud af engine'en og ind i hans bevidsthed.

Design:
  - Læser conclusions fra evaluate_rules(snapshot) — best-effort
  - Top-5 sorteret (engine sorterer allerede på priority_delta + urgency)
  - Kompakt format: "[urgency:domain +Δ] suggestion (rule_name)"
  - Returnerer "" hvis engine fejler eller intet fyrer (ingen noise)
  - Cap'er per-line for at undgå prompt-bloat

Awareness-prioritet: 28 (mellem) — symbolsk reasoning er værd at tjekke,
men ikke kritisk identity. Dropper først hvis budget overflows.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Hvor mange conclusions vi viser. 5 er nok til at give Jarvis et bredt
# billede uden at fylde prompten. Engine returnerer allerede sorteret
# efter priority_delta DESC, urgency DESC.
_TOP_N = 5

# Per-suggestion cap så en lang regel ikke fylder hele sektionen.
_SUGGESTION_MAX_CHARS = 140


def _format_conclusion(c) -> str:
    """One line per conclusion: '[urgency:domain ±Δ] suggestion (rule)'."""
    urgency = (c.urgency or "low").upper()[:4]
    domain = c.target_domain or "?"
    delta = c.priority_delta
    sign = "+" if delta >= 0 else ""
    suggestion = (c.suggestion or "").strip()
    if len(suggestion) > _SUGGESTION_MAX_CHARS:
        suggestion = suggestion[: _SUGGESTION_MAX_CHARS - 1].rstrip() + "…"
    rule_name = c.rule_name or "?"
    return f"  [{urgency:>4}:{domain:<10} {sign}{delta:>3}] {suggestion} ({rule_name})"


def rule_conclusions_section() -> str:
    """Build the rule-engine conclusions section for prompt injection.

    Returns empty string if:
      - Engine fails to import or evaluate
      - No rules fired against current signal state
      - Top-5 conclusions all have priority_delta=0

    Best-effort throughout — never breaks prompt assembly.
    """
    try:
        from core.services.rule_engine import evaluate_rules
        from core.services.signal_surface_router import list_all_surfaces
    except Exception as exc:
        logger.debug("rule_conclusions: import failed: %s", exc)
        return ""

    try:
        signals = list_all_surfaces()
        result = evaluate_rules(signals)
    except Exception as exc:
        logger.debug("rule_conclusions: evaluate failed: %s", exc)
        return ""

    if not result.conclusions:
        return ""

    top = result.conclusions[:_TOP_N]
    # Skip the section entirely if all top conclusions are no-op deltas.
    if all(abs(c.priority_delta) < 5 for c in top):
        return ""

    lines = ["🧠 Symbolsk ræsonnering — top-5 regel-konklusioner lige nu:"]
    for c in top:
        lines.append(_format_conclusion(c))
    lines.append(
        "(Disse er forslag fra forward-chaining over signal-stakken. "
        "De er ikke ordrer — du beslutter."
    )
    return "\n".join(lines)
