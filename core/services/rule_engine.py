"""Rule Engine — forward-chaining symbolic inference over signal surfaces.

Evaluates production rules against current signal state, collects conclusions
with full reasoning traces. Advisory only — never blocks or enforces.

Design:
  - Forward-chaining: all rules evaluated each cycle
  - Non-limiting: outputs are prioritized suggestions + traces
  - Inspectable: every conclusion carries a human-readable trace string
  - Composable: feeds into R1+R2+R3 advisory ecosystem
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import logging

logger = logging.getLogger(__name__)


# ── Core data types ────────────────────────────────────────────────────


@dataclass
class RuleConclusion:
    """One conclusion from one rule firing."""

    rule_name: str
    suggestion: str
    priority_delta: int  # -100 to +100, how much this should shift focus
    trace: str  # human-readable reasoning, e.g. "curiosity(0.83) + scan_found_novel=True → scan_agi"
    target_domain: str  # 'action', 'focus', 'attention', 'strategy', 'pause', 'reflect'
    urgency: str  # 'low', 'medium', 'high', 'critical'


EMPTY_CONCLUSION: RuleConclusion = RuleConclusion(
    rule_name="",
    suggestion="",
    priority_delta=0,
    trace="",
    target_domain="",
    urgency="low",
)


@dataclass
class Rule:
    """One production rule in the engine."""

    name: str
    description: str
    domain: str
    priority: int  # higher = evaluated first
    condition: Callable[[dict[str, Any]], bool]
    action: Callable[[dict[str, Any]], RuleConclusion]


@dataclass
class RuleCycleResult:
    """Result of one full evaluation cycle."""

    conclusions: list[RuleConclusion] = field(default_factory=list)
    rules_evaluated: int = 0
    rules_fired: int = 0
    errors: list[str] = field(default_factory=list)


# ── Engine ─────────────────────────────────────────────────────────────


class RuleEngine:
    """Forward-chaining rule engine.

    Register rules via add_rule() or register_rules().
    Call evaluate(signals) to run all rules against current state.
    """

    def __init__(self) -> None:
        self._rules: list[Rule] = []
        self._sorted: bool = False

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)
        self._sorted = False

    def register_rules(self, rules: list[Rule]) -> None:
        self._rules.extend(rules)
        self._sorted = False

    def clear_rules(self) -> None:
        self._rules.clear()
        self._sorted = False

    @property
    def rules(self) -> list[Rule]:
        if not self._sorted:
            self._rules.sort(key=lambda r: r.priority, reverse=True)
            self._sorted = True
        return list(self._rules)

    def evaluate(self, signals: dict[str, Any]) -> RuleCycleResult:
        """Evaluate all rules against current signal state.

        signals: snapshot from list_all_surfaces() or a merged dict.
        Returns sorted conclusions (highest priority_delta first).
        """
        result = RuleCycleResult()
        result.rules_evaluated = len(self._rules)

        sorted_rules = self.rules  # already sorted

        for rule in sorted_rules:
            try:
                if rule.condition(signals):
                    conclusion = rule.action(signals)
                    if conclusion and conclusion != EMPTY_CONCLUSION:
                        conclusion.rule_name = rule.name
                        result.conclusions.append(conclusion)
                        result.rules_fired += 1
            except Exception as exc:
                msg = f"Rule '{rule.name}' failed: {exc}"
                logger.warning(msg)
                result.errors.append(msg)

        # Sort conclusions: priority_delta descending, then urgency weight
        urgency_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        def _sort_key(c: RuleConclusion) -> tuple:
            return (-c.priority_delta, -urgency_order.get(c.urgency, 0))

        result.conclusions.sort(key=_sort_key)
        return result

    def get_rule(self, name: str) -> Rule | None:
        for r in self._rules:
            if r.name == name:
                return r
        return None

    def rules_by_domain(self, domain: str) -> list[Rule]:
        return [r for r in self._rules if r.domain == domain]


# ── Signal helpers ─────────────────────────────────────────────────────


def _get(signals: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely dig into nested signal dicts."""
    current = signals
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, {})
        else:
            return default
    return current if current is not None else default


def signal_value(
    signals: dict[str, Any],
    surface: str,
    field: str,
    default: Any = None,
) -> Any:
    """Extract a scalar value from a named surface field."""
    return _get(signals, surface, field, default=default)


def surface_has(signals: dict[str, Any], surface: str) -> bool:
    """Check if a surface exists and has no error."""
    data = signals.get(surface)
    if data is None:
        return False
    if isinstance(data, dict) and "error" in data:
        return False
    return True


# ── Singleton ──────────────────────────────────────────────────────────

_ENGINE: RuleEngine | None = None


def get_engine() -> RuleEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RuleEngine()
        _load_default_rules(_ENGINE)
    return _ENGINE


def _load_default_rules(engine: RuleEngine) -> None:
    """Import and register all default rule definitions."""
    # Lazy import to avoid circular deps at module level
    from core.services.rule_definitions import ALL_RULES

    engine.register_rules(ALL_RULES)


def reset_engine() -> None:
    """Reset the engine (useful for testing or hot-reload)."""
    global _ENGINE
    _ENGINE = None


def evaluate_rules(signals: dict[str, Any]) -> RuleCycleResult:
    """Convenience: get engine, evaluate, return result."""
    return get_engine().evaluate(signals)


def get_all_rules() -> list[dict[str, Any]]:
    """Return all registered rules as serializable dicts (for tools)."""
    return [
        {
            "name": r.name,
            "description": r.description,
            "domain": r.domain,
            "priority": r.priority,
        }
        for r in get_engine().rules
    ]

def build_rule_engine_surface() -> dict[str, object]:
    try:
        engine = get_engine()
        rule_count = len(getattr(engine, "rules", []) or [])
    except Exception:
        rule_count = 0
    return {
        "active": True,
        "mode": "forward-chaining-rule-engine",
        "rule_count": rule_count,
        "summary": f"{rule_count} rules registered.",
        "authority": "derived-read-only",
    }


def _emit_rule_fired_event(rule_name: str, urgency: str) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "rule_engine.rule_fired",
            {"rule_name": str(rule_name), "urgency": str(urgency)},
        )
    except Exception:
        pass
