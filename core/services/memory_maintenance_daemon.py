"""Memory maintenance daemon — periodic dedup and health of every user's MEMORY.md.

Runs every 12 hours and covers ALL registered workspaces (12/10-2026). Until
then it maintained one hardcoded file — `shared_dir()/MEMORY.md`, 24 KB — which
is not any user's memory: each user's MEMORY.md lives in their own workspace.
Bjørn: «der er flere brugere».

Two report-only tiers:
  Tier A: exact + fuzzy heading duplicates → propose, never auto-merge.
  Tier B: overlapping content across headings → publish event for review.

This is the daemon companion to the writer-level fuzzy dedup in
candidate_workflow._fuzzy_line_match (Lag 1). Lag 1 prevents
near-duplicate *lines* from being appended. This daemon prevents
near-duplicate *sections* from accumulating over time.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.workspace_paths import shared_dir

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 12
_TIER_A_HEADING_SIMILARITY = 0.85  # Jaccard threshold for duplicate proposals
_TIER_B_CONTENT_SIMILARITY = 0.50  # Jaccard threshold for flagging
_MIN_SECTION_LINES = 2  # skip sections with fewer lines

#: Kun TOPNIVEAU-sections sammenlignes (12/10-2026). Målt på Bjørns fil: af 53
#: eksakte dubletter lå ALLE på niveau 3 — `### Læren`, `### Fejlen`,
#: `### Status` under FORSKELLIGE forældre. Merge-reglen sammenligner kun
#: overskriftsteksten, så den ville lime to ubeslægtede hændelser sammen.
#: Daemonens eget formål er topniveau-dubletter («'## Decisions' twice»).
_TOP_LEVEL = 2

#: Tier B er O(n²) på indhold. Målt 12/10-2026: 1.178 topniveau-sections i
#: Bjørns fil = 694k par à ~38 µs ≈ 27 s — over halvdelen af familie-tikkets
#: 60 s-budget. Tier B udsender kun review-flag, så på store filer springer vi
#: den over og RAPPORTERER det, frem for at æde budgettet tavst.
_MAX_TIER_B_SECTIONS = 400


def _memory_md(workspace: str) -> Path:
    """Stien til ÉN brugers MEMORY.md.

    Indtil 12/10-2026 pegede daemonen på `shared_dir()/MEMORY.md` — 24 KB, som
    ikke er nogen brugers hukommelse. Hver brugers MEMORY.md ligger i deres
    eget workspace, så daemonen tager nu et workspace-navn og tikker ALLE
    registrerede brugere.
    """
    return shared_dir().parent / "workspaces" / workspace / "MEMORY.md"


def _target_workspaces() -> list[str]:
    """Alle registrerede brugeres workspace-navne.

    To kilder: users.json (discord-id-brugere) og SQLite users-tabellen
    (selvbetjenings-brugere med UUID). Union — en bruger må ikke falde ud af
    vedligeholdelsen, fordi de er registreret den ene vej og ikke den anden.
    """
    names: set[str] = set()
    try:
        from core.identity.users import list_member_workspaces
        names.update(w for w in list_member_workspaces() if w)
    except Exception:  # users.json utilgængelig → SQLite-kilden nedenfor bærer
        pass
    try:
        from core.runtime.db_users import list_user_rows
        for row in list_user_rows():
            ws = str(row.get("workspace") or "").strip()
            if ws:
                names.add(ws)
    except Exception:  # SQLite utilgængelig → users.json-kilden ovenfor bærer
        pass
    return sorted(names)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_memory_maintenance_daemon(now: datetime | None = None) -> dict:
    """Run the 12h maintenance cycle on EVERY registered user's MEMORY.md.

    12/10-2026 (Bjørn: «der er flere brugere»): indtil nu vedligeholdt cyklussen
    én hardkodet fil som ikke var nogen brugers hukommelse. Den går nu gennem
    alle registrerede workspaces og rapporterer Tier A + Tier B for hver. Én brugers
    fejl isoleres pr. fil og stopper ikke de øvrige.

    Returns dict med summerede tier_a/tier_b-tal plus et `workspaces`-kort.
    """
    global _last_tick_at, _last_result

    now = now or datetime.now(UTC)

    # Cadence gate — gælder HELE cyklussen, ikke pr. bruger.
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"maintained": False, "reason": "cadence"}

    per_workspace: dict[str, dict] = {}
    tier_a_total = 0
    tier_a_candidate_total = 0
    tier_b_total = 0
    for workspace in _target_workspaces():
        try:
            res = _maintain_workspace(workspace)
        except Exception as exc:  # én brugers fil må ikke dræbe de andres
            per_workspace[workspace] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        if res:
            per_workspace[workspace] = res
            tier_a_total += int(res.get("tier_a_merged") or 0)
            tier_a_candidate_total += int(res.get("tier_a_candidates") or 0)
            tier_b_total += int(res.get("tier_b_flagged") or 0)

    if not per_workspace:
        return {"maintained": False, "reason": "no_workspaces"}

    _last_tick_at = now
    _last_result = {
        "tier_a_merged": tier_a_total,
        "tier_a_candidates": tier_a_candidate_total,
        "tier_b_flagged": tier_b_total,
        "workspaces": per_workspace,
        "users": len(per_workspace),
    }

    # Publish event
    try:
        event_bus.publish(
            "memory.maintenance",
            {
                "tier_a_merged": tier_a_total,
                "tier_a_candidates": tier_a_candidate_total,
                "tier_b_flagged": tier_b_total,
                "users": len(per_workspace),
                "timestamp": now.isoformat(),
            },
        )
    except Exception:
        pass

    return _last_result


def _maintain_workspace(workspace: str) -> dict:
    """Tier A + Tier B for ÉN brugers MEMORY.md. Tom dict = intet at gøre."""
    text = _read_memory(workspace)
    if not text.strip():
        return {}
    sections = _parse_sections(text)
    if len(sections) < 2:
        return {}

    sections_before = len(sections)
    # Report-only: maintenance must never rewrite identity memory unattended.
    tier_a_candidates = _tier_a_duplicate_candidates(sections)

    # Tier B: flag overlapping content across different headings
    top_level = [s for s in sections if s["level"] == _TOP_LEVEL]
    out = {
        "tier_a_merged": 0,
        "tier_a_candidates": len(tier_a_candidates),
        "report_only": True,
        "tier_b_flagged": 0,
        "sections_before": sections_before,
        "sections_after": len(sections),
    }
    if len(top_level) > _MAX_TIER_B_SECTIONS:
        # Se _MAX_TIER_B_SECTIONS: O(n²) på indhold. Rapporteret, ikke skjult.
        out["tier_b_skipped"] = f"too_many_sections:{len(top_level)}"
    else:
        out["tier_b_flagged"] = len(_tier_b_flag_overlaps(sections))
    try:
        from core.services.memory_hygiene import audit_workspace

        out["hygiene"] = audit_workspace(
            workspace, path=_memory_md(workspace), publish_inbox=True,
        )
    except Exception as exc:
        out["hygiene_error"] = f"{type(exc).__name__}: {exc}"
    return out


def build_memory_maintenance_surface() -> dict:
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "last_result": _last_result,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_memory(workspace: str) -> str:
    try:
        return _memory_md(workspace).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_sections(text: str) -> list[dict]:
    """Parse MEMORY.md into sections: [{heading, level, content, start_line, end_line}]."""
    sections: list[dict] = []
    current_heading = None
    current_level = 0
    current_lines: list[str] = []
    start_line = 0

    for i, line in enumerate(text.splitlines()):
        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            if current_heading is not None:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": "\n".join(current_lines).strip(),
                    "start_line": start_line,
                    "end_line": i - 1,
                })
            current_level = len(m.group(1))
            current_heading = m.group(2).strip()
            current_lines = []
            start_line = i
        else:
            current_lines.append(line)

    if current_heading is not None:
        sections.append({
            "heading": current_heading,
            "level": current_level,
            "content": "\n".join(current_lines).strip(),
            "start_line": start_line,
            "end_line": len(text.splitlines()) - 1,
        })

    return sections


def _jaccard(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two strings."""
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _tier_a_duplicate_candidates(sections: list[dict]) -> list[dict]:
    """Find duplicate top-level headings without mutating ``MEMORY.md``.

    Reglerne blev strammet 12/10-2026 efter en måling på Bjørns fil (1.410
    sektioner, 94 kandidater). To ting var i stykker:

    1. **Containment-reglen** («én overskrift er indeholdt i den anden») stod
       for 81 af de 94, og de var alle forkerte: `Hardware` blev slået sammen
       med `VESC — hardware-status (2026-09-26)`, `Status` med `jarvis-code —
       projekt status`, `Bygget` med `mobile companion (planlagt — IKKE
       bygget)`. Det er semantisk sammenfald, ikke dubletter. Reglen er væk.
    2. **Niveau-blindheden**: af 53 eksakte dubletter lå ALLE på niveau 3
       (`### Læren`, `### Fejlen`, `### Status`) under FORSKELLIGE forældre.
       Daemonen sammenlignede kun overskriftsteksten, så den ville lime to
       ubeslægtede hændelser sammen. Den merger nu kun topniveau.

    Tilbage på Bjørns fil: 2 kandidater mod 94 før.

    Historical versions auto-merged these sections. That is no longer safe:
    even an exact heading can contain distinct events, and identity-memory
    mutation requires an explicit reviewed plan. Return bounded metadata only.
    """
    candidates: list[dict] = []
    claimed: set[int] = set()

    for i, s1 in enumerate(sections):
        for j, s2 in enumerate(sections):
            if j <= i:
                continue
            if s1["level"] != s2["level"] or s1["level"] != _TOP_LEVEL:
                continue
            if i in claimed or j in claimed:
                continue

            h1, h2 = s1["heading"], s2["heading"]
            is_exact = h1.lower().strip() == h2.lower().strip()
            is_fuzzy_high = _jaccard(h1, h2) >= _TIER_A_HEADING_SIMILARITY
            if not (is_exact or is_fuzzy_high):
                continue

            claimed.add(j)
            candidates.append({
                "section_a": h1,
                "section_b": h2,
                "line_a": int(s1["start_line"]) + 1,
                "line_b": int(s2["start_line"]) + 1,
                "heading_similarity": round(_jaccard(h1, h2), 3),
            })
            if len(candidates) >= 50:
                return candidates
    return candidates


def _tier_b_flag_overlaps(sections: list[dict]) -> list[dict]:
    """Flag sections with different headings but overlapping content.

    Does NOT auto-merge — just publishes events for review.
    """
    flagged: list[dict] = []

    for i, s1 in enumerate(sections):
        for j, s2 in enumerate(sections):
            if j <= i:
                continue
            if s1["level"] != s2["level"]:
                continue
            # Skip sections with very little content
            if len(s1["content"].splitlines()) < _MIN_SECTION_LINES:
                continue
            if len(s2["content"].splitlines()) < _MIN_SECTION_LINES:
                continue

            content_sim = _jaccard(
                s1["content"][:500],
                s2["content"][:500],
            )
            if content_sim >= _TIER_B_CONTENT_SIMILARITY:
                flag = {
                    "section_a": s1["heading"],
                    "section_b": s2["heading"],
                    "similarity": round(content_sim, 3),
                }
                flagged.append(flag)
                try:
                    event_bus.publish(
                        "memory.overlap_detected",
                        {
                            **flag,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                except Exception:
                    pass

    return flagged


# No mutation helper belongs in this daemon. Approved archival is a separate,
# manifest-backed operation.
