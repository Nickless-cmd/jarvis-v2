"""Cache-bevidst microcompact (19/9-2026).

Reglen er kalibreret paa maalte ture (se core/context/microcompact.py):
cachen er varm til og med 1-3 t (median 84-88 %) og kold fra 3 t (26 %).
Maal igen med foerste kald pr. tur i `costs` (lane='primary',
provider='deepseek', run_id 'visible-%'), grupperet paa pausen siden
forrige tur — kun data EFTER 11/9, hvor caching blev rettet; aeldre data
forurener billedet.

De to fejl testene holder fast i:
1. Den gamle regel stubbede efter 60 min — midt i en varm cache.
2. Den slap stubbene igen ved naeste tur. To cache-brud pr. pause.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.context import microcompact as mc
from core.services.prompt_sections import transcript_sections as ts

NU = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def _msg(mid: int, role: str, content: str, created_at: datetime) -> dict[str, object]:
    return {"id": mid, "role": role, "content": content,
            "created_at": created_at.isoformat(), "user_id": ""}


def _historik(sidst: datetime, n_tools: int = 7) -> list[dict[str, object]]:
    m = [_msg(1, "assistant", "done", sidst)]
    for i in range(2, 2 + n_tools):
        m.append(_msg(i, "tool", f"tool result {i}", sidst))
    return m


def _tools(out):
    return [str(m["content"]) for m in out if m["role"] == "tool"]


def test_kold_cache_flytter_graensen_og_stubber_de_gamle(isolated_runtime) -> None:
    out, st = mc.apply_cache_aware_microcompact(
        _historik(NU - timedelta(hours=4)), session_id="s1", now=NU, keep_recent_tools=2)
    assert st["reason"] == "cold_cache_advance"
    assert st["folded_tool_results"] == 5
    assert _tools(out)[-2:] == ["tool result 7", "tool result 8"]
    assert _tools(out)[0].startswith("[old_tool_result:2")


# Fejl 1: 60 min er midt i en varm cache (maalt median 86 % ved 1-3 t).
def test_en_times_pause_roerer_IKKE_en_varm_cache(isolated_runtime) -> None:
    h = _historik(NU - timedelta(minutes=61))
    out, st = mc.apply_cache_aware_microcompact(h, session_id="s1", now=NU, keep_recent_tools=2)
    assert out == h
    assert st["folded_tool_results"] == 0


# Fejl 2: stubbene maa ikke slippes ved naeste tur. Det var andet brud.
def test_graensen_er_klaebende_ogsaa_naar_pausen_er_vaek(isolated_runtime) -> None:
    kold = NU - timedelta(hours=4)
    mc.apply_cache_aware_microcompact(_historik(kold), session_id="s1", now=NU, keep_recent_tools=2)

    # Naeste tur, to minutter senere: ingen pause, men samme stubbe.
    h = _historik(kold) + [_msg(20, "assistant", "nyt svar", NU)]
    out, st = mc.apply_cache_aware_microcompact(
        h, session_id="s1", now=NU + timedelta(minutes=2), keep_recent_tools=2)
    assert st["reason"] == "sticky_cutoff"
    assert _tools(out)[0].startswith("[old_tool_result:2")
    assert _tools(out)[-2:] == ["tool result 7", "tool result 8"]


def test_samme_input_giver_samme_output(isolated_runtime) -> None:
    """Praefikset skal vaere det samme tur efter tur — ellers rammer cachen ikke."""
    kold = NU - timedelta(hours=4)
    a, _ = mc.apply_cache_aware_microcompact(_historik(kold), session_id="s1", now=NU, keep_recent_tools=2)
    b, _ = mc.apply_cache_aware_microcompact(_historik(kold), session_id="s1",
                                             now=NU + timedelta(minutes=5), keep_recent_tools=2)
    assert a == b


def test_ny_komprimering_nulstiller_graensen(isolated_runtime) -> None:
    from core.services.chat_sessions import create_chat_session, store_compact_marker
    sid = str(create_chat_session(title="t")["id"])
    mc.apply_cache_aware_microcompact(_historik(NU - timedelta(hours=4)), session_id=sid,
                                      now=NU, keep_recent_tools=2)
    assert mc.laes_graense(sid) > 0

    # En ny markoer aendrer praefikset alligevel: ny epoke, ingen arvet graense.
    store_compact_marker(sid, "resumé")
    assert mc.laes_graense(sid) == 0


def test_ring_pollen_maa_ikke_flytte_graensen(isolated_runtime) -> None:
    """persist=False: desks kontekst-ring maaler; den bestemmer ikke."""
    out, st = mc.apply_cache_aware_microcompact(
        _historik(NU - timedelta(hours=4)), session_id="s1", now=NU,
        keep_recent_tools=2, persist=False)
    assert st["folded_tool_results"] == 5          # maalingen ser det samme
    assert mc.laes_graense("s1") == 0              # men intet er gemt


def test_input_muteres_ikke(isolated_runtime) -> None:
    h = _historik(NU - timedelta(hours=4))
    foer = [dict(m) for m in h]
    mc.apply_cache_aware_microcompact(h, session_id="s1", now=NU, keep_recent_tools=0)
    assert h == foer


def test_uden_ids_fejler_den_aabent(isolated_runtime) -> None:
    h = [{"role": "assistant", "content": "x", "created_at": (NU - timedelta(hours=4)).isoformat()},
         {"role": "tool", "content": "y" * 50}]
    out, _ = mc.apply_cache_aware_microcompact(h, session_id="s1", now=NU, keep_recent_tools=0)
    assert out == h


def test_prompt_byggeren_bruger_den_klaebende_graense(isolated_runtime) -> None:
    kold = NU - timedelta(hours=4)
    hist = [_msg(1, "user", "run tools", kold), _msg(2, "assistant", "ok", kold),
            _msg(3, "tool", "x" * 200, kold)]
    hist += [_msg(i, "tool", f"new {i}", kold) for i in range(4, 9)]
    hist += [_msg(9, "assistant", "done", kold)]

    with patch.object(ts, "chat_session_messages_since_last_compact", return_value=hist), \
         patch.object(ts, "_lifecycle_enabled", return_value=False), \
         patch.object(ts, "_round_collapse_enabled", return_value=False), \
         patch("core.context.microcompact._now_utc", return_value=NU), \
         patch("core.services.prompt_contract._get_compact_marker_for_transcript", return_value=None), \
         patch("core.services.prompt_contract._maybe_auto_compact_session"):
        out = ts._build_structured_transcript_messages("s1", limit=60, include=True)

    blob = "\n".join(m["content"] for m in out)
    assert "[old_tool_result:" in blob
    assert "x" * 100 not in blob
    assert mc.laes_graense("s1") == 3
