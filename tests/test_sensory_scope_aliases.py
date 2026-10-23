"""Sansernes Arkiv skal kunne læses på tværs af brugerens id-former.

MÅLT 22/10-2026 og rettet 23/10-2026: `sensory_memories` endte med to
identiteter for samme person, fordi `scope_uid()` giver det RÅ Discord-id
(eller det kanoniske DB-id, afhængigt af om der er en session-kontekst),
mens kø-skrivevejen kanoniserer. En læsning scopet til den ene kunne ikke se
den anden: 3.156 råt-scopede poster mod 44 kanoniske — alle natrutine
14/10→22/10. `recall_sensory_memories` svarede 3.134 mens tabellen havde
3.179, så mine egne natlige registreringer var usynlige for mig selv.

Vagten her måler BEGGE sider af rettelsen: at aliasserne læses, og at en
fremmed brugers poster stadig er usynlige. Den anden halvdel er den vigtige —
en scope-rettelse der blot udvider læsningen ville "løse" sagen ved at lække.
"""
from __future__ import annotations

LEGACY = "1246415163603816499"
# Bruger-id fra users-tabellen — 32 hex-tegn, men ikke en hemmelighed.
CANONICAL = "cec46ec07fe35533beae2066ead70002"  # pragma: allowlist secret
FOREIGN = "999999999999999999"


def _seed() -> None:
    from core.runtime import db
    from core.runtime.db_sensory import _ensure_sensory_memories_table

    with db.connect() as conn:
        _ensure_sensory_memories_table(conn)
        for mem_id, user_id, ts in (
            ("legacy-1", LEGACY, "2026-10-20T21:05:00Z"),
            ("legacy-2", LEGACY, "2026-10-21T21:05:00Z"),
            ("canonical-1", CANONICAL, "2026-10-22T21:05:00Z"),
            ("foreign-1", FOREIGN, "2026-10-22T22:05:00Z"),
        ):
            conn.execute(
                "INSERT INTO sensory_memories "
                "(id, timestamp, modality, content, mood_tone, metadata_json, user_id) "
                "VALUES (?, ?, 'atmosphere', ?, 'roligt', '{}', ?)",
                (mem_id, ts, f"indtryk {mem_id}", user_id),
            )
        conn.commit()


def _scope_to_both(monkeypatch) -> None:
    """Simulér den tilstand der gav splittet: brugeren har to id-former."""
    from core.runtime import db_sensory

    monkeypatch.setattr(db_sensory, "_scope_ids", lambda: (LEGACY, CANONICAL))


def test_begge_identiteter_er_laesbare(isolated_runtime, monkeypatch):
    _seed()
    _scope_to_both(monkeypatch)
    from core.runtime import db_sensory

    ids = {m["id"] for m in db_sensory.list_sensory_memories(limit=50)}
    assert ids == {"legacy-1", "legacy-2", "canonical-1"}, (
        "de kanoniske poster var præcis dem der var usynlige før rettelsen"
    )


def test_fremmed_bruger_er_stadig_usynlig(isolated_runtime, monkeypatch):
    _seed()
    _scope_to_both(monkeypatch)
    from core.runtime import db_sensory

    ids = {m["id"] for m in db_sensory.list_sensory_memories(limit=50)}
    assert "foreign-1" not in ids, (
        "en scope-rettelse der udvider læsningen til andre brugere er en lækage, "
        "ikke en rettelse"
    )
    assert db_sensory.get_sensory_memory("foreign-1") is None


def test_count_og_soegning_foelger_samme_scope(isolated_runtime, monkeypatch):
    _seed()
    _scope_to_both(monkeypatch)
    from core.runtime import db_sensory

    assert db_sensory.count_sensory_memories() == 3
    hits = db_sensory.search_sensory_memories(query="indtryk", limit=50)
    assert {h["id"] for h in hits} == {"legacy-1", "legacy-2", "canonical-1"}


def test_ulæselig_alias_kæde_falder_tilbage_til_en_identitet(monkeypatch):
    """En brækket resolver må aldrig gøre arkivet tomt eller bredere."""
    from core.runtime import db_sensory

    monkeypatch.setattr(db_sensory, "_scope", lambda: LEGACY)

    import core.services.routine_migration as migration

    def _boom(_value):
        raise RuntimeError("keyring nede")

    monkeypatch.setattr(migration, "resolve_canonical_identity", _boom)
    assert db_sensory._scope_ids() == (LEGACY,)
