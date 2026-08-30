"""Tool-result lifecycle (visible-lane). Spec 2026-07-16.

cold_floor = persisted integer message-id. Tool-results with id < cold_floor
render as byte-stable stubs. cold_floor advances ONLY at run-end, in discrete
batches with hysteresis (hybrid: last N user-turns OR T warm-tokens). Pure
computation here; DB storage below. NO recency-relative logic (breaks the cache).
"""
from __future__ import annotations


def user_message_ids(messages: list[dict]) -> list[int]:
    """Ids for role=='user' messages, ascending (= run boundaries)."""
    out = []
    for m in messages:
        if str(m.get("role")) == "user":
            try:
                out.append(int(m["id"]))
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(out)


def estimate_tool_tokens(messages: list[dict]) -> int:
    """Sum of tool-result tokens (heuristic len//4). Only role=='tool'."""
    total = 0
    for m in messages:
        if str(m.get("role")) == "tool":
            total += len(str(m.get("content") or "")) // 4
    return total


def _candidate_by_runs(user_ids: list[int], run_window: int) -> int:
    """Floor so exactly the last `run_window` user-turns stay warm."""
    if len(user_ids) <= run_window:
        return 0
    keep_from = user_ids[-run_window]  # oldest user-turn we KEEP warm
    return keep_from - 1               # warm = id > floor  <=>  id >= keep_from


def _candidate_by_tokens(messages: list[dict], token_ceiling: int) -> int:
    """Floor so warm tool-tokens <= ceiling. Walks newest->oldest."""
    cum = 0
    floor = 0
    for m in reversed(messages):
        if str(m.get("role")) == "tool":
            cum += len(str(m.get("content") or "")) // 4
            if cum > token_ceiling:
                floor = int(m["id"])  # this msg (and older) goes cold
                break
    return floor


def compute_new_floor(
    messages: list[dict],
    *,
    current_floor: int,
    run_window: int,
    token_ceiling: int,
    hysteresis: float,
) -> int:
    """New cold_floor. Monotonic (>= current_floor). 0 = nothing cold yet.

    Warm = messages with id > current_floor. Advance only if warm EXCEEDS the
    limit by the hysteresis margin. On advance, trim warm to the BASE limits.
    """
    warm = [m for m in messages if int(m.get("id", 0)) > current_floor]
    user_ids_warm = user_message_ids(warm)
    tokens_warm = estimate_tool_tokens(warm)

    # >= so warm reaching exactly the hysteresis threshold advances (the margin
    # is inclusive); strict > would stall at the exact boundary (e.g. 50k vs 40k*1.25).
    over_runs = len(user_ids_warm) >= run_window * (1 + hysteresis)
    over_tokens = tokens_warm >= token_ceiling * (1 + hysteresis)
    if not (over_runs or over_tokens):
        return current_floor

    all_user_ids = user_message_ids(messages)
    cand_runs = _candidate_by_runs(all_user_ids, run_window)
    cand_tokens = _candidate_by_tokens(messages, token_ceiling)
    return max(current_floor, cand_runs, cand_tokens)


from core.runtime.db import connect

def as_bool(value: object, default: bool = True) -> bool:
    """Robust bool-tolkning. ``bool("off")`` er True — den fælde har kostet os før.

    Strenge tolkes efter indhold, ikke efter om de er tomme. Ukendt værdi →
    ``default``, så en tastefejl i config ikke slukker et værn i tavshed.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on", "ja", "enabled"):
        return True
    if text in ("0", "false", "no", "off", "nej", "disabled", ""):
        return False
    return default


def should_advance(
    *,
    warm_tool_tokens: int,
    current_epoch: int,
    recorded_epoch: int,
    hard_ceiling: int,
    only_on_compact: bool = True,
) -> tuple[bool, str]:
    """Må gulvet rykke nu? Ren beslutning. Returnerer (ja/nej, grund).

    MÅLT 2026-08-30: hver gulv-avancering omskriver historik TIDLIGT i prompten,
    fordi gulvet vandrer fremad fra de ældste beskeder — de nyligt kolde er altid
    de ældste stadig-varme. Rendering af samme historik med successive gulve viste
    at kun 5-48 % af prefixet overlevede (brud ved besked #4 af 49 i værste fald).
    DeepSeek genbruger kun et prefix der matcher FULDT fra første token, så resten
    genfaktureres — og et miss koster 31,4× et hit.

    Derfor: rør kun ved historikken når den ALLIGEVEL bliver omskrevet, dvs. ved
    compaction. Så klatrer cachen monotont imellem compactions i stedet for at
    kollapse ved hvert spring (målt 7 spring på 3,5 time).

    Sikkerhedsventil: overstiger de varme tool-tokens ``hard_ceiling`` rykker vi
    alligevel. Uden den kunne en værktøjstung session vokse ud over model-vinduet
    før compaction nåede at udløse — og et for langt prompt fejler HELT (Ollama
    svarer 400 "prompt too long" og turen bliver tavs), hvilket er værre end et
    cache-brud.
    """
    if not only_on_compact:
        return True, "gate slået fra"
    if hard_ceiling > 0 and warm_tool_tokens > hard_ceiling:
        return True, f"sikkerhedsventil ({warm_tool_tokens} > {hard_ceiling} varme tool-tokens)"
    if current_epoch != recorded_epoch:
        return True, f"compaction (epoke {recorded_epoch}->{current_epoch})"
    return False, "ingen compaction siden sidste avancering — beskytter cache-prefixet"


_TABLE = "tool_result_cold_floor"


def _ensure_table(conn) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "session_id TEXT PRIMARY KEY, floor_id INTEGER NOT NULL, "
        "updated_at TEXT NOT NULL)"
    )
    # compact_epoch = id på den compact_marker der var nyest sidst vi rykkede
    # gulvet. Se should_advance() for hvorfor. Idempotent tilføjelse — ældre
    # databaser har kolonnen ikke.
    try:
        conn.execute(
            f"ALTER TABLE {_TABLE} ADD COLUMN compact_epoch INTEGER NOT NULL DEFAULT 0"
        )
    except Exception:
        pass


def latest_compact_marker_id(session_id: str) -> int:
    """Id på sessionens nyeste compact_marker, 0 hvis den aldrig er komprimeret.

    Markøren er en række i ``chat_messages`` med role='compact_marker'. Dens id
    stiger kun når historikken faktisk bliver omskrevet — derfor er den den
    rigtige epoke at binde gulv-avanceringer til.
    """
    sid = (session_id or "").strip()
    if not sid:
        return 0
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT id FROM chat_messages WHERE session_id = ? "
                "AND role = 'compact_marker' ORDER BY id DESC LIMIT 1",
                (sid,),
            ).fetchone()
        if row is None:
            return 0
        try:
            return int(row["id"])
        except (KeyError, TypeError, ValueError):
            return int(row[0])
    except Exception:
        return 0


def get_cold_floor(session_id: str) -> int:
    sid = (session_id or "").strip()
    if not sid:
        return 0
    with connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            f"SELECT floor_id FROM {_TABLE} WHERE session_id = ?", (sid,)
        ).fetchone()
    if row is None:
        return 0
    try:
        return int(row["floor_id"])
    except (KeyError, TypeError, ValueError):
        return int(row[0])


def get_compact_epoch(session_id: str) -> int:
    """Compact-markør-id fra sidste gang gulvet rykkede (0 = aldrig)."""
    sid = (session_id or "").strip()
    if not sid:
        return 0
    try:
        with connect() as conn:
            _ensure_table(conn)
            row = conn.execute(
                f"SELECT compact_epoch FROM {_TABLE} WHERE session_id = ?", (sid,)
            ).fetchone()
        if row is None:
            return 0
        try:
            return int(row["compact_epoch"])
        except (KeyError, TypeError, ValueError):
            return int(row[0])
    except Exception:
        return 0


def set_cold_floor(session_id: str, floor_id: int, compact_epoch: int = 0) -> None:
    """Monotonic: writes only if floor_id > existing.

    ``compact_epoch`` gemmes sammen med gulvet, så næste run-slut kan se om der
    er sket en compaction siden — se should_advance().
    """
    sid = (session_id or "").strip()
    if not sid:
        return
    from datetime import datetime, UTC
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_table(conn)
        conn.execute(
            f"INSERT INTO {_TABLE} (session_id, floor_id, updated_at, compact_epoch) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "floor_id = excluded.floor_id, updated_at = excluded.updated_at, "
            "compact_epoch = excluded.compact_epoch "
            "WHERE excluded.floor_id > tool_result_cold_floor.floor_id",
            (sid, int(floor_id), now, int(compact_epoch)),
        )


def _load_session_messages(session_id: str) -> list[dict]:
    """Growing-window messages WITH id (a later task adds id to the return dict)."""
    from core.services.chat_sessions import chat_session_messages_since_last_compact
    return chat_session_messages_since_last_compact(session_id)


def _load_settings():
    from core.runtime.settings import load_settings
    return load_settings()


def evaluate_and_advance(session_id: str, *, settings=None) -> int:
    """Called at RUN-END (sole writer). Returns new cold_floor (0=none).

    Fault-tolerant: must never raise into the run-completion path.
    """
    sid = (session_id or "").strip()
    if not sid:
        return 0
    s = settings or _load_settings()
    if not bool(getattr(s, "tool_result_lifecycle_enabled", False)):
        return get_cold_floor(sid)
    try:
        messages = _load_session_messages(sid)
        current = get_cold_floor(sid)
        _ceiling = int(getattr(s, "tool_warm_token_ceiling", 40000))
        new_floor = compute_new_floor(
            messages,
            current_floor=current,
            run_window=int(getattr(s, "tool_warm_run_window", 8)),
            token_ceiling=_ceiling,
            hysteresis=float(getattr(s, "tool_warm_hysteresis", 0.25)),
        )
        if new_floor <= current:
            return new_floor

        # Cache-gaten: en avancering omskriver historik tidligt i prompten og
        # koster 52-95 % af det cachede prefix (målt 30-08). Vent til compaction
        # alligevel omskriver den — med en sikkerhedsventil mod runaway-vækst.
        _epoch = latest_compact_marker_id(sid)
        _warm = estimate_tool_tokens(
            [m for m in messages if int(m.get("id", 0)) > current]
        )
        _ok, _why = should_advance(
            warm_tool_tokens=_warm,
            current_epoch=_epoch,
            recorded_epoch=get_compact_epoch(sid),
            hard_ceiling=int(getattr(s, "tool_warm_hard_ceiling", _ceiling * 3)),
            only_on_compact=as_bool(
                getattr(s, "tool_warm_advance_only_on_compact", None), default=True
            ),
        )
        if not _ok:
            print(f"[tool-lifecycle] cold_floor {current}->{new_floor} UDSKUDT "
                  f"({_why}, {_warm} varme tool-tokens) session={sid[:20]}",
                  flush=True)
            return current
        set_cold_floor(sid, new_floor, compact_epoch=_epoch)
        print(f"[tool-lifecycle] cold_floor {current}->{new_floor} "
              f"[{_why}] session={sid[:20]}", flush=True)
        return new_floor
    except Exception as exc:
        print(f"[tool-lifecycle] evaluate_and_advance error: {exc}", flush=True)
        return get_cold_floor(sid)
