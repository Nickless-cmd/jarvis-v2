"""Typed contracts and source normalization for explicit research runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAMS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source",
}
_MINIMUM_INSTRUCTIONS = """Use primary and authoritative sources when available.
Keep facts separate from inference, preserve source URLs, check freshness, and
state material uncertainty. Never invent citations or claim coverage you do not have."""


@dataclass(frozen=True)
class ResearchPolicy:
    max_workers: int = 3
    max_tasks: int = 6
    max_tool_calls: int = 24
    wall_time_seconds: int = 600
    source_target: int = 6


@dataclass(frozen=True)
class ResearchDecision:
    tier: str
    signals: tuple[str, ...] = ()
    max_workers: int = 1
    max_tasks: int = 1
    max_tool_calls: int = 8
    wall_time_seconds: int = 180
    source_target: int = 3


@dataclass(frozen=True)
class ResearchTask:
    title: str
    objective: str
    ordinal: int = 0


@dataclass(frozen=True)
class ResearchPlan:
    tasks: tuple[ResearchTask, ...]
    requested_facets: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchSource:
    url: str
    canonical_url: str
    title: str = ""
    publisher: str = ""
    published_at: str = ""
    retrieved_at: str = ""
    snippet: str = ""
    source_type: str = "web"
    authority: str = "unknown"


@dataclass(frozen=True)
class ResearchFinding:
    task_ordinal: int
    claim: str
    source_urls: tuple[str, ...] = ()
    confidence: str = "medium"
    caveat: str = ""


@dataclass(frozen=True)
class ResearchContract:
    policy: ResearchPolicy
    instructions: str
    skill_available: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def canonicalize_url(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    scheme = parts.scheme.lower() or "https"
    hostname = (parts.hostname or "").lower()
    if not hostname:
        return value.split("#", 1)[0]
    port = f":{parts.port}" if parts.port else ""
    query = [
        (key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit((scheme, hostname + port, parts.path or "/", urlencode(query), ""))


def normalize_source(value: ResearchSource | dict[str, object]) -> ResearchSource:
    if isinstance(value, ResearchSource):
        return value
    url = str(value.get("url") or value.get("canonical_url") or "").strip()
    return ResearchSource(
        url=url,
        canonical_url=canonicalize_url(url),
        title=_clean(value.get("title")),
        publisher=_clean(value.get("publisher")),
        published_at=_clean(value.get("published_at")),
        retrieved_at=_clean(value.get("retrieved_at")),
        snippet=_clean(value.get("snippet")),
        source_type=_clean(value.get("source_type")) or "web",
        authority=_clean(value.get("authority")) or "unknown",
    )


def load_research_contract(query: str = "") -> ResearchContract:
    """Load the canonical skill deterministically; fall back without hiding it."""
    from core.services import skill_engine

    result: dict[str, object]
    try:
        result = skill_engine.get_skill_instructions("deep-research")
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
    available = result.get("status") == "ok" and bool(result.get("instructions"))
    try:
        skill_engine.record_skill_usage(
            "deep-research",
            source="explicit_research_mode",
            success=available,
            query=query,
            context_tags="research",
            score=1.0,
        )
    except Exception:
        pass
    if available:
        return ResearchContract(ResearchPolicy(), str(result["instructions"]), True)
    warning = str(result.get("error") or "deep-research skill unavailable")
    return ResearchContract(ResearchPolicy(), _MINIMUM_INSTRUCTIONS, False, (warning,))
