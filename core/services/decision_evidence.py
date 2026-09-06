"""Ekstern sandhed til adfærds-reviews — hvad der FAKTISK skete i vinduet.

Baggrunden er en konkret hændelse. Den 11/6-2026 hævdede Jarvis «Time pin fixet
er live. Tests grønne. Committer den nu» uden at have kørt et eneste værktøj i
samme run — og `decision_review` gav ham samtidig «kept» på hans egen beslutning
«verify before I narrate». Modellen bedømte sig selv og gav sig selv ret.
Daemonen blev slået fra, og registret noterede at den «skal erstattes af
external-truth review (læser git-log + tool-history) i fix C3».

C3 blev aldrig bygget. Det er dette modul.

Pointen er ikke at spørge modellen bedre. Det er at holde dens svar op mod et
regnskab den ikke selv har skrevet: hvilke værktøjer der rent faktisk blev kørt
(eventbus), og hvilke commits der rent faktisk blev lavet (git). Uden et sådant
regnskab må en dom ikke blive til «kept» — så er svaret «unknown», og
adherence-gennemsnittet lader den ligge.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Event-arter der beviser at et værktøj rent faktisk blev udført. `tool.invoked`
# alene er ikke nok — et kald kan afvises af en gate; `completed` er gerningen.
_TOOL_EVENT_KINDS = ("tool.completed", "tool.force_invoked")

_MAX_TOOLS_IN_SUMMARY = 8
_MAX_COMMITS_IN_SUMMARY = 5


def _repo_root() -> Path:
    """Repoets rod, fundet ud fra dette moduls egen placering."""
    return Path(__file__).resolve().parents[2]


def _tool_names_since(since: datetime, until: datetime) -> dict[str, int]:
    """Hvilke værktøjer blev udført i vinduet, og hvor mange gange.

    Læser eventbus'ens egne rækker. Self-safe: kan DB'en ikke læses, returnerer
    vi tomt — og et tomt regnskab betyder «ingen bevis», ikke «intet skete».
    """
    counts: dict[str, int] = {}
    try:
        from core.runtime.db import connect

        pladsholdere = ",".join("?" for _ in _TOOL_EVENT_KINDS)
        with connect() as conn:
            rows = conn.execute(
                "SELECT kind, payload_json FROM events "
                " WHERE kind IN (%s) AND created_at >= ? AND created_at <= ?" % pladsholdere,
                (*_TOOL_EVENT_KINDS, since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("decision_evidence: kunne ikke laese tool-events: %s", exc)
        return {}

    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            continue
        navn = str(
            payload.get("tool")
            or payload.get("tool_name")
            or payload.get("name")
            or ""
        ).strip()
        if navn:
            counts[navn] = counts.get(navn, 0) + 1
    return counts


def _commits_since(since: datetime, until: datetime) -> list[str]:
    """Commits i vinduet, som korte emnelinjer.

    Bruger repoets git-log direkte. Self-safe: git kan mangle, mappen kan være
    et andet checkout, kommandoen kan hænge — alt det giver tom liste.
    """
    try:
        out = subprocess.run(
            ["git", "log",
             "--since", since.isoformat(),
             "--until", until.isoformat(),
             "--pretty=format:%h %s"],
            cwd=str(_repo_root()),
            capture_output=True, text=True, timeout=15,
        )
    except Exception as exc:
        logger.debug("decision_evidence: git log fejlede: %s", exc)
        return []
    if out.returncode != 0:
        return []
    return [linje.strip() for linje in (out.stdout or "").splitlines() if linje.strip()]


def gather_evidence(
    *, since: datetime, until: datetime | None = None,
) -> dict[str, Any]:
    """Saml regnskabet for vinduet. Returnerer også en kompakt tekst.

    ``has_evidence`` er det felt der betyder noget: er den falsk, findes der
    intet ydre spor af aktivitet, og så må ingen dom hævde at en beslutning
    blev holdt.
    """
    until = until or datetime.now(UTC)
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)

    tools = _tool_names_since(since, until)
    commits = _commits_since(since, until)
    kald_i_alt = sum(tools.values())

    timer = max((until - since).total_seconds() / 3600.0, 0.0)
    linjer: list[str] = []
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:_MAX_TOOLS_IN_SUMMARY]
        linjer.append(
            "Værktøjer kørt (%d kald): %s"
            % (kald_i_alt, ", ".join("%s×%d" % (n, a) for n, a in top))
        )
    else:
        linjer.append("Værktøjer kørt: ingen")
    if commits:
        linjer.append(
            "Commits (%d): %s"
            % (len(commits), " | ".join(c[:70] for c in commits[:_MAX_COMMITS_IN_SUMMARY]))
        )
    else:
        linjer.append("Commits: ingen")

    return {
        "window_hours": round(timer, 1),
        "since": since.isoformat(),
        "until": until.isoformat(),
        "tools": tools,
        "tool_calls_total": kald_i_alt,
        "commits": commits,
        "has_evidence": bool(tools or commits),
        "summary": " · ".join(linjer),
    }


def evidence_permits_verdict(verdict: str, evidence: dict[str, Any]) -> str:
    """Nedgradér en positiv dom der ikke har ydre dækning.

    ``broken`` slipper altid igennem: at konstatere et brud kræver ikke bevis
    for aktivitet — fraværet af handling ER ofte bruddet, og
    `decision_enforcement` skriver i forvejen brud ud fra faktisk output.

    ``kept`` og ``partial`` løfter derimod adherence-scoren, og de må derfor
    kun stå hvis der findes et ydre spor. Ellers bliver dommen ``unknown``,
    som det rullende gennemsnit i append_review ignorerer.
    """
    v = str(verdict or "").strip().lower()
    if v == "broken":
        return "broken"
    if v in ("kept", "partial"):
        return v if bool(evidence.get("has_evidence")) else "unknown"
    return v or "unknown"
