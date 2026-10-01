"""Events-table retention — bound the unbounded ``events`` telemetry table.

The eventbus persists every event to ``events`` with no retention. Left alone it
grows without limit (measured 2.56M rows / ~4 months / 2.7GB DB, ~211k rows/day
under the cheap-lane churn). A large table means slower INSERTs (deeper index) →
longer WAL write-lock holds → more contention with API chat/cost writes (the
amplifier behind API latency spikes, alongside per-event commits which the writer
now batches).

``prune_old_events`` deletes rows older than a cutoff in SMALL batches (one commit
per batch → never a long lock), capped per invocation so the initial drain of a
huge table happens gradually across ticks rather than in one table-locking sweep.
Self-safe: never raises.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

_DEFAULT_MAX_AGE_DAYS = 14
_DEFAULT_MAX_DELETE = 50_000   # per invocation — gradual drain of a huge backlog
_DEFAULT_BATCH_SIZE = 5_000    # rows per transaction — short lock holds


def _retention_days() -> int:
    try:
        from core.runtime.settings import load_settings
        v = int(load_settings().extra.get("events_retention_days", _DEFAULT_MAX_AGE_DAYS))
        return max(1, v)
    except Exception:
        return _DEFAULT_MAX_AGE_DAYS


def prune_old_events(
    *,
    max_age_days: int | None = None,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete events older than ``max_age_days`` in batches. Returns {"deleted": N}.

    Batched (one commit per ``batch_size`` rows) so no single long lock; capped at
    ``max_delete`` per call so a huge backlog drains gradually. Self-safe."""
    days = int(max_age_days) if max_age_days is not None else _retention_days()
    return prune_table_by_age(
        "events", "created_at", max_age_days=days,
        max_delete=max_delete, batch_size=batch_size,
    )


def prune_table_by_age(
    table: str,
    ts_column: str,
    *,
    max_age_days: int,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete rows from ``table`` where ``ts_column`` < cutoff, in small capped
    batches (one commit each → short locks). ``table``/``ts_column`` are validated
    against an identifier allowlist to keep the f-string SQL injection-safe. Self-safe."""
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table) or \
       not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ts_column):
        return {"deleted": 0, "error": "invalid identifier", "table": table}
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, int(max_age_days)))).isoformat()
    total = 0
    try:
        from core.runtime.db import connect
        while total < max_delete:
            take = min(batch_size, max_delete - total)
            with connect() as conn:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE rowid IN "
                    f"(SELECT rowid FROM {table} WHERE {ts_column} < ? "
                    f"ORDER BY rowid ASC LIMIT ?)",
                    (cutoff, take),
                )
                n = cur.rowcount or 0
                conn.commit()
            if n <= 0:
                break
            total += n
    except Exception as exc:
        return {"deleted": total, "error": str(exc)[:200], "table": table}
    return {"deleted": total, "table": table, "retention_days": int(max_age_days)}


# Pure-telemetry tables safe to age-prune (logs/metrics, no cognitive value).
# (table, ts_column, retention_days). Load-bearing memory/identity/learning tables
# are DELIBERATELY excluded — they are pruned only on explicit owner decision.
_TELEMETRY_RETENTION: tuple[tuple[str, str, int], ...] = (
    ("daemon_output_log", "created_at", 21),
    ("cheap_provider_invocations", "created_at", 60),
    ("tool_router_decisions", "created_at", 45),
    ("reasoning_conclusions", "created_at", 45),
    # Recency-bounded readers (verified 2026-07-17): each reads only recent/by-id
    # rows (ORDER BY ... LIMIT, WHERE id=?, WHERE status IN proposed/applied), never
    # aggregates full history → rows older than 60d have no effect on learning.
    ("runtime_action_outcomes", "recorded_at", 60),
    ("runtime_contract_candidates", "created_at", 60),
    ("behavioral_decision_reviews", "created_at", 60),
    # 2026-09-27: tabellen blev oprettet 18. september og var ni dage senere
    # 2.381 MB — 45 % af hele jarvis.db. 6.000 rutebeslutninger om dagen, hver
    # med alle 101 kandidat-slots og deres fulde kvote-tilstand (48 KB pr.
    # række indtil `15e04466f` skar den til 4 KB). Den kom aldrig på denne
    # liste, og intet sagde til; `retention_coverage` er vagten mod at det
    # gentager sig.
    #
    # SYV DAGE, ikke de 60 som `cheap_provider_invocations` har, og det er
    # ikke en glidning: de to tabeller er ikke samme slags. En invocation-
    # række er et par hundrede bytes udfald — hvad blev kaldt, hvad skete der.
    # En rutebeslutning er et fejlfindings-spor over HVORDAN der blev valgt,
    # ti til hundrede gange så fedt. Udfaldet er værd at gemme i to måneder;
    # sporet er det ikke.
    #
    # Syv dage er valgt ud fra læserne, ikke på fornemmelse.
    # `route_integrity` og `health_divergence` ser 24 timer tilbage — syv dage
    # er syv gange det. Den eneste læser derudover er `get_route_decision`,
    # et opslag på id fra detalje-visningen af en invocation; den felt er
    # allerede valgfrit (None når `route_decision_id` er tom), så en ældre
    # invocation mister sit spor uden at noget går i stykker.
    #
    # KOBLINGEN ER DEN VIGTIGE: retentionen SKAL være bredere end
    # diagnostik-vinduet. Bliver vinduet en dag udvidet til en uge, begynder
    # `route_integrity` at melde «invocation uden rute» om rækker vi selv har
    # slettet. `test_retention_coverage.py` læser vinduet ud af
    # `cheap_lane_diagnostics` og fejler hvis de to nærmer sig hinanden.
    ("cheap_lane_route_decisions", "created_at", 7),
    # 2026-09-27, punkt 3: tre tabeller mere, hver med sit tal fundet ved at
    # læse HVEM der læser dem — ikke ved at gætte.
    #
    # `inner_voice_shadow`: 30 dage. Tidskolonnen hedder `generated_at`, ikke
    # `created_at` — derfor så tabellen ud til at mangle et tidsstempel helt.
    #
    # Jeg skrev først «ingen læser den overhovedet» og satte 14 dage. Det var
    # forkert, og testen `test_inner_voice_shadow_laesere_er_kendte` fangede
    # det: der er tre. To — `recent_comparisons` og `shadow_stats` — bor i
    # modulet selv og har ingen kaldere. Den tredje er
    # `scripts/meta_evne_healthcheck.py`, som køres i hånden og regner
    # succesrate og gennemsnitlig latenstid over HELE historikken.
    #
    # Ingen produktionssti læser tabellen. 30 dage gør healthcheckets tal til
    # «den seneste måned» i stedet for «siden 24. maj», hvilket for et
    # helbredstjek er det mere brugbare — men det ER en ændring af hvad det
    # svarer. Målt: 66 % af de 73.750 rækker er over 30 dage.
    ("inner_voice_shadow", "generated_at", 30),
    # 60 dage, samme som `runtime_action_outcomes` — de to hører sammen.
    # Læserne er udelukkende afgrænsede: `ORDER BY id DESC LIMIT`, opslag på
    # `outcome_id`, og pr. `decision_id` med `LIMIT 20`. Den join'es fra
    # `cognitive_decisions` med LEFT JOIN og `ORDER BY cd.created_at DESC
    # LIMIT`, så en gammel beslutning uden bevaret gennemgang giver NULL i
    # stedet for at forsvinde.
    #
    # 90 dage havde ikke virket: tabellen går kun tilbage til 9. juli, så et
    # 90-dages filter ville matche NUL rækker — samme strukturelt døde
    # oprydning som `brain_temporal_edges` havde i tre måneder. 60 rammer
    # 15,7 % i dag og vokser derfra.
    ("runtime_self_review_outcomes", "created_at", 60),
    # 90 dage — rundhåndet, fordi den grænser op til kronikken (hukommelse),
    # ikke til telemetri. Læserne er `ORDER BY id DESC LIMIT` og opslag på
    # `brief_id`; ingen aggregerer over hele historikken. Rækker tilbage til
    # 6. april, så 90 dage rammer 39 % med det samme.
    ("runtime_chronicle_consolidation_briefs", "created_at", 90),
)


#: Styres af ÉN indstilling, `cheap_lane_metadata_retention_days`, så de ikke
#: kan glide fra hinanden. Rutebeslutningerne står med vilje UDENFOR: de er et
#: fejlfindings-spor, ikke metadata om et udfald — se kommentaren ved deres
#: linje i `_TELEMETRY_RETENTION`.
_CHEAP_LANE_METADATA_TABLER = frozenset({"cheap_provider_invocations"})


#: Hvor længe et ubehandlet forslag bliver i review-køen før det pensioneres.
#: Tabellens 60-dages vindue ovenfor binder HELE tabellen; dette binder hver TYPE,
#: fordi de ikke er lige handlingsanrettede.
#:
#: Målt 1/10-2026: 5.231 proposed, hvoraf 3.144 var `chronicle_draft` — og 0 af
#: 1.847 er NOGENSINDE blevet applied. `chronicle_draft` har ingen auto-apply-vej:
#: `_should_auto_apply` dækker kun MEMORY.md/USER.md, og dens eneste læsere TÆLLER
#: den (`runtime_candidates.py:162/242`). Den hober sig altså op i hele det 60-dages
#: vindue uden at nogen ser eller bruger den — en blindgyde. `memory_promotion` og
#: `preference_update` HAR en vej (auto-apply gennem memory-gaten) og beholder det
#: lange vindue; de er reelt review-bare.
#:
#: Syv dage for chronicle er ikke en gætning: den er 8× det vindue den ugentlige
#: chronicle-konsolidering arbejder i, så en ægte frisk kandidat er for længst
#: fanget inden den pensioneres.
_CANDIDATE_TYPE_MAX_AGE: tuple[tuple[str, int], ...] = (
    ("chronicle_draft", 7),
    ("memory_promotion", 30),
    ("preference_update", 30),
    ("prompt_feedback_update", 30),
)


def prune_stale_contract_candidates() -> dict[str, object]:
    """Type-bevidst alders-pruning af ``runtime_contract_candidates``.

    Den generiske 60-dages regel rammer hele tabellen; denne giver hver type sit
    eget vindue, så en blindgyde ikke fylder køen op i to måneder. Sletter KUN
    ubehandlede (``status='proposed'``) rækker — approved/applied røres ikke.
    Små kappede batches (ét commit hver → korte låse). Self-safe: rejser aldrig.
    """
    import re
    out: dict[str, object] = {}
    try:
        from core.runtime.db import connect
    except Exception as exc:  # self-safe: uden DB-forbindelse rapporteres fejlen — retentionen vaelter ikke
        return {"error": str(exc)[:120]}
    for candidate_type, days in _CANDIDATE_TYPE_MAX_AGE:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate_type):
            continue
        cutoff = (datetime.now(UTC) - timedelta(days=max(1, int(days)))).isoformat()
        deleted = 0
        try:
            while deleted < _DEFAULT_MAX_DELETE:
                take = min(_DEFAULT_BATCH_SIZE, _DEFAULT_MAX_DELETE - deleted)
                with connect() as conn:
                    cur = conn.execute(
                        "DELETE FROM runtime_contract_candidates WHERE rowid IN ("
                        "SELECT rowid FROM runtime_contract_candidates "
                        "WHERE candidate_type = ? AND status = 'proposed' "
                        "AND created_at < ? ORDER BY rowid ASC LIMIT ?)",
                        (candidate_type, cutoff, take),
                    )
                    n = cur.rowcount or 0
                    conn.commit()
                if n <= 0:
                    break
                deleted += n
            out[candidate_type] = deleted
        except Exception as exc:  # self-safe: en fejlende type maa ikke stoppe de oevrige
            out[candidate_type] = f"err:{str(exc)[:60]}"
    return out


def prune_telemetry_tables() -> dict[str, object]:
    """Age-prune the safe telemetry tables. Self-safe. Returns per-table deleted counts."""
    out: dict[str, object] = {}
    try:
        out["runtime_contract_candidates_by_type"] = prune_stale_contract_candidates()
    except Exception as exc:
        out["runtime_contract_candidates_by_type"] = f"err:{str(exc)[:60]}"
    for table, ts_col, days in _TELEMETRY_RETENTION:
        try:
            if table in _CHEAP_LANE_METADATA_TABLER:
                try:
                    from core.runtime.settings import load_settings

                    days = max(1, int(load_settings().extra.get(
                        "cheap_lane_metadata_retention_days", days
                    )))
                except Exception:
                    pass
            out[table] = prune_table_by_age(table, ts_col, max_age_days=days).get("deleted", 0)
        except Exception as exc:
            out[table] = f"err:{str(exc)[:60]}"
    try:
        from core.services.cheap_lane_payloads import purge_expired_payloads

        out["cheap_lane_redacted_payloads"] = purge_expired_payloads()
    except Exception as exc:
        out["cheap_lane_redacted_payloads"] = f"err:{str(exc)[:60]}"
    return out


# Versioned cognitive snapshot tables: one append-only row per version of a SINGLE
# evolving entity (relationship texture, personality vector). ``texture_id``/
# ``vector_id`` are unique-per-row; ``version`` is a monotonic global counter. The
# tables grew ~550 rows/day since April (49k/24k rows) but every reader uses only
# ORDER BY version DESC LIMIT 1..20 (db_cognitive.py) — never old versions. Keeping
# the latest N versions preserves current state + recent evolution history with a
# 50× reader margin. Owner-approved keep-latest (Bjørn 2026-07-19). (table, version_col, keep_latest).
_VERSIONED_RETENTION: tuple[tuple[str, str, int], ...] = (
    ("cognitive_relationship_textures", "version", 1000),
    ("cognitive_personality_vectors", "version", 1000),
)


def prune_versioned_table(
    table: str,
    version_col: str,
    *,
    keep_latest: int,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete all but the newest ``keep_latest`` versions from a versioned snapshot
    table. Deletes rows where ``version_col`` <= (max_version - keep_latest), in small
    capped batches (one commit each → short locks). Identifiers are allowlist-validated.
    Self-safe: never raises, never touches the current (max-version) row."""
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table) or \
       not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", version_col):
        return {"deleted": 0, "error": "invalid identifier", "table": table}
    total = 0
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(f"SELECT MAX({version_col}) AS m FROM {table}").fetchone()
        maxv = row[0] if row is not None else None
        if maxv is None:
            return {"deleted": 0, "table": table}
        threshold = int(maxv) - int(max(1, keep_latest))
        if threshold <= 0:
            return {"deleted": 0, "table": table, "keep_latest": keep_latest}
        while total < max_delete:
            take = min(batch_size, max_delete - total)
            with connect() as conn:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE rowid IN "
                    f"(SELECT rowid FROM {table} WHERE {version_col} <= ? "
                    f"ORDER BY rowid ASC LIMIT ?)",
                    (threshold, take),
                )
                n = cur.rowcount or 0
                conn.commit()
            if n <= 0:
                break
            total += n
    except Exception as exc:
        return {"deleted": total, "error": str(exc)[:200], "table": table}
    return {"deleted": total, "table": table, "keep_latest": int(keep_latest)}


def prune_versioned_tables() -> dict[str, object]:
    """Keep-latest-N prune the versioned cognitive snapshot tables. Self-safe."""
    out: dict[str, object] = {}
    for table, vcol, keep in _VERSIONED_RETENTION:
        try:
            out[table] = prune_versioned_table(table, vcol, keep_latest=keep).get("deleted", 0)
        except Exception as exc:
            out[table] = f"err:{str(exc)[:60]}"
    return out
