"""Import-sanity-test for db.py split.

Verificerer at alle symboler som split-faserne flytter stadig er
importerbare fra `core.runtime.db` (facaden). Hvis Phase 0 eller
senere fase brækker en re-eksport, fejler denne test med klar
besked om hvilket symbol der mangler.

Tilføj symboler her per fase efterhånden som de flyttes.
"""
from __future__ import annotations

import importlib


def _assert_importable(module: str, symbols: list[str]) -> None:
    mod = importlib.import_module(module)
    missing = [s for s in symbols if not hasattr(mod, s)]
    assert not missing, (
        f"Mangler symboler i {module}: {missing}. "
        f"Sikr at facaden re-eksporterer fra det nye submodul."
    )


# Phase 0: infrastructure symboler — skal være importerbare fra
# BÅDE core.runtime.db (facade) OG core.runtime.db_core (direkte).
PHASE_0_SYMBOLS = [
    "DB_PATH",
    "_CONFIDENCE_RANKS",
    "_EVIDENCE_CLASS_RANKS",
    "_SOURCE_KIND_RANKS",
    "_SIGNAL_TABLES_WITH_STATUS",
    "_ENSURED_TABLES",
    "ClosingConnection",
    "connect",
    "_now_iso",
    "_rank_for",
    "_stronger_ranked_value",
    "_merge_text_fragments",
    "set_runtime_state_value",
    "get_runtime_state_value",
    "_conn_db_id",
    "_install_ensure_once_cache",
    "invalidate_ensure_once_cache",
]


def test_phase0_symbols_on_facade():
    _assert_importable("core.runtime.db", PHASE_0_SYMBOLS)


def test_phase0_symbols_on_db_core():
    _assert_importable("core.runtime.db_core", PHASE_0_SYMBOLS)


def test_connect_returns_working_connection():
    from core.runtime.db import connect
    with connect() as conn:
        row = conn.execute("SELECT 1 AS one").fetchone()
        assert row["one"] == 1


def test_ensure_once_cache_is_installed():
    """Verificer at _install_ensure_once_cache har wrapped _ensure_*_table funcs."""
    from core.runtime import db
    ensure_funcs = [
        getattr(db, n) for n in dir(db)
        if n.startswith("_ensure_") and n.endswith("_table") and callable(getattr(db, n, None))
    ]
    assert ensure_funcs, "Forventede mindst én _ensure_*_table funktion på facaden"
    wrapped = [f for f in ensure_funcs if getattr(f, "_ensure_once_wrapped", False)]
    assert wrapped, (
        f"Ingen _ensure_*_table funktioner er wrappet. "
        f"Sikr at _install_ensure_once_cache() kaldes efter facade-re-eksporterne. "
        f"Fundet: {len(ensure_funcs)} _ensure_* funcs, {len(wrapped)} wrappet."
    )
