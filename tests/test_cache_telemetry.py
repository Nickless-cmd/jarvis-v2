"""Per-request cache-telemetri (core/services/cache_telemetry.py, 2026-06-30).

Verificér at prefix-signaturen er deterministisk + følsom (tool-ændring → ny hash),
og at record_visible_cache skriver en korrekt JSONL-linje + er self-safe.
"""
from __future__ import annotations

import json

from core.services import cache_telemetry as ct


def test_prefix_signature_deterministic_and_tool_sensitive():
    tools_a = [{"type": "function", "function": {"name": "f", "parameters": {}}}]
    tools_b = [{"type": "function", "function": {"name": "g", "parameters": {}}}]
    sha1, n1 = ct.prefix_signature("system", tools_a)
    sha2, n2 = ct.prefix_signature("system", tools_a)
    sha3, _ = ct.prefix_signature("system", tools_b)
    assert sha1 and sha1 == sha2          # deterministisk
    assert n1 == n2 and n1 > 0
    assert sha1 != sha3                    # tool-ændring → ny hash (cache-breaker)


def test_prefix_signature_key_order_invariant():
    # sort_keys → samme indhold i forskellig dict-rækkefølge giver SAMME hash.
    a = [{"type": "function", "function": {"name": "f", "parameters": {}}}]
    b = [{"function": {"parameters": {}, "name": "f"}, "type": "function"}]
    assert ct.prefix_signature("s", a)[0] == ct.prefix_signature("s", b)[0]


def test_component_signatures_keep_the_dynamic_tail_separate():
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    before = [
        {"role": "system", "content": "stable identity"},
        {"role": "user", "content": "old turn"},
        {"role": "system", "content": "inner life at 09:00"},
        {"role": "user", "content": "new turn"},
    ]
    after = [*before[:2], {"role": "system", "content": "inner life at 09:01"}, before[3]]
    first = ct.component_signatures(before, tools)
    second = ct.component_signatures(after, tools)

    assert first["system_sha"] == second["system_sha"]
    assert first["tools_sha"] == second["tools_sha"]
    assert first["tail_sha"] != second["tail_sha"]
    assert first["system_len"] == len("stable identity")
    assert first["tail_len"] == len("inner life at 09:00")
    assert first["system_chunks"] == second["system_chunks"]
    assert "inner life" not in str(first)


def test_component_signatures_locate_a_change_within_stable_system():
    original = [{"role": "system", "content": "a" * 1024 + "time: 17:16" + "z" * 1024}]
    changed = [{"role": "system", "content": "a" * 1024 + "time: 17:19" + "z" * 1024}]
    before = ct.component_signatures(original, [])
    after = ct.component_signatures(changed, [])
    assert len(before["system_chunks"]) == 3
    assert [a != b for a, b in zip(before["system_chunks"], after["system_chunks"])] == [False, True, False]


def test_component_signatures_identify_system_and_tool_changes():
    messages = [{"role": "system", "content": "identity"}]
    tools = [{"function": {"name": "read_file"}}]
    base = ct.component_signatures(messages, tools)
    new_system = ct.component_signatures([{"role": "system", "content": "identity changed"}], tools)
    new_tools = ct.component_signatures(messages, [{"function": {"name": "write_file"}}])
    assert base["system_sha"] != new_system["system_sha"]
    assert base["tools_sha"] == new_system["tools_sha"]
    assert base["system_sha"] == new_tools["system_sha"]
    assert base["tools_sha"] != new_tools["tools_sha"]


def test_record_writes_jsonl_line(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ct.record_visible_cache(
        run_id="visible-abc", round_index=3, autonomous=False, lane="visible",
        provider="deepseek", model="deepseek-v4-flash",
        prefix_sha="deadbeef", prefix_len=12345, cache_hit=90000, cache_miss=1000,
        session_id="chat-1", system_sha="systemhash", tools_sha="toolhash",
        tail_sha="tailhash", system_len=100, tools_len=200, tail_len=300,
        system_chunks=["chunk-a", "chunk-b"],
    )
    log = tmp_path / "logs" / "cache_telemetry.jsonl"
    row = json.loads(log.read_text().strip())
    assert row["run_id"] == "visible-abc"
    assert row["round"] == 3
    assert row["prefix_sha"] == "deadbeef"
    assert row["session_id"] == "chat-1"
    assert row["system_sha"] == "systemhash"
    assert row["tools_sha"] == "toolhash"
    assert row["tail_sha"] == "tailhash"
    assert row["system_len"] == 100 and row["tools_len"] == 200
    assert row["tail_len"] == 300
    assert row["system_chunks"] == ["chunk-a", "chunk-b"]
    assert row["timestamp"].endswith("+00:00")
    assert row["hit"] == 90000 and row["miss"] == 1000
    assert row["pct"] == round(100.0 * 90000 / 91000, 1)


def test_record_is_self_safe_on_bad_input(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Ingen exception selv med rod-input.
    ct.record_visible_cache(run_id=None, round_index="x", cache_hit=None)  # type: ignore[arg-type]


def test_zero_total_pct_is_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ct.record_visible_cache(run_id="r", cache_hit=0, cache_miss=0)
    row = json.loads((tmp_path / "logs" / "cache_telemetry.jsonl").read_text().strip())
    assert row["pct"] == 0.0


def test_cache_feeds_central_when_active(tmp_path, monkeypatch):
    # spec §3.3: reel cache-aktivitet → observe til cost/prefix_cache + eventbus + tidsserie
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    observed, published, series = [], [], []

    class _FakeCentral:
        def observe(self, ev):
            observed.append(dict(ev))

    import core.services.central_core as cc
    import core.services.central_timeseries as cts
    import core.eventbus.bus as bus
    monkeypatch.setattr(cc, "central", lambda: _FakeCentral())
    monkeypatch.setattr(cts, "record", lambda c, n, value=None, meta=None: series.append((c, n, value)))
    monkeypatch.setattr(bus.event_bus, "publish", lambda k, p=None, **kw: published.append(k))

    ct.record_visible_cache(run_id="r1", lane="visible", prefix_sha="ab",
                            cache_hit=80, cache_miss=20)
    assert observed and observed[0]["cluster"] == "cost" and observed[0]["nerve"] == "prefix_cache"
    assert observed[0]["pct"] == 80.0
    assert "cache.telemetry" in published
    assert series and series[0][:2] == ("cost", "prefix_cache")


def test_cache_no_central_feed_when_idle(tmp_path, monkeypatch):
    # _in==0 (ingen cache-aktivitet) → INTET signal til Centralen (undgå støj)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    observed = []

    class _FakeCentral:
        def observe(self, ev):
            observed.append(ev)

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _FakeCentral())
    ct.record_visible_cache(run_id="r0", cache_hit=0, cache_miss=0)
    assert observed == []


# ── Ét aftryk pr. besked (28/9-2026) ─────────────────────────────────────────
#
# Hittet faldt fra 148.352 til 67.840 mellem runde 11 og 12 i ét synligt run og
# blev haengende dér i fem runder. system_sha, tools_sha og tail_sha var
# uaendrede hele vejen — bruddet laa inde i samtalen, hvor der ingen maaler var.
#
# `msg_shas` gør brudstedet til en simpel ting: den foerste plads hvor to
# runder er uenige. Summen af `msg_lens` foer den plads er hvor langt cachen
# kunne naa.


def _faelles(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def test_ren_tilfoejelse_giver_et_helt_faelles_praefiks():
    """Den normale runde: samtalen vokser bagi, intet skrives om."""
    base = [{"role": "system", "content": "id"}, {"role": "user", "content": "et"}]
    foer = ct.component_signatures(base, [])
    efter = ct.component_signatures([*base, {"role": "assistant", "content": "svar"}], [])
    assert _faelles(foer["msg_shas"], efter["msg_shas"]) == len(foer["msg_shas"])
    assert efter["msg_count"] == 3


def test_en_omskrevet_besked_MIDT_i_samtalen_peger_paa_sin_egen_plads():
    """Det er hele formaalet: bruddet skal kunne stedfaestes."""
    foer_msgs = [{"role": "system", "content": "id"}] + [
        {"role": "user", "content": f"tur {i}"} for i in range(6)]
    efter_msgs = list(foer_msgs)
    efter_msgs[3] = {"role": "user", "content": "tur 2 OMSKREVET"}
    foer = ct.component_signatures(foer_msgs, [])
    efter = ct.component_signatures(efter_msgs, [])
    assert foer["system_sha"] == efter["system_sha"], "systemdelen skal vaere uroert"
    assert foer["tools_sha"] == efter["tools_sha"]
    assert _faelles(foer["msg_shas"], efter["msg_shas"]) == 3


def test_stabile_tegn_taelles_frem_til_bruddet():
    """Tallet skal kunne holdes op mod det hit udbyderen rapporterer.

    Det maa altsaa foelge den FAKTISKE stoerrelse. En konstant pr. besked ville
    give et pænt tal der intet betyder — og bruddet ville se lige dyrt ud
    uanset hvor meget tekst der laa foran det.
    """
    msgs = [{"role": "user", "content": "x" * 100} for _ in range(4)]
    msgs[1] = {"role": "user", "content": "x" * 900}     # én er ni gange saa stor
    sig = ct.component_signatures(msgs, [])
    aendret = list(msgs); aendret[2] = {"role": "user", "content": "y" * 100}
    k = _faelles(sig["msg_shas"], ct.component_signatures(aendret, [])["msg_shas"])
    assert k == 2
    # Serialiseringen baerer ogsaa rolle og tegnsaetning, saa laengden er lidt
    # over indholdet — men den skal foelge det, ikke vaere et fast tal.
    assert sig["msg_lens"][1] > 900
    # Praecis forskellen mellem de to indhold. Et fast tal pr. besked ville
    # give 0 her; et loest "stoerre end"-forhold ville slippe det igennem.
    assert sig["msg_lens"][1] - sig["msg_lens"][0] == 800
    assert sum(sig["msg_lens"][:k]) > 1000


def test_noeglernes_raekkefoelge_maa_ikke_aendre_aftrykket():
    """Samme besked, bygget i en anden raekkefoelge, er SAMME besked.

    Uden `sort_keys` ville et harmloest skift i hvordan dict'en blev bygget se
    ud som et cache-brud — og vi ville jage et spoegelse.
    """
    a = [{"role": "assistant", "content": "svar", "name": "jarvis"}]
    b = [{"name": "jarvis", "content": "svar", "role": "assistant"}]
    assert ct.component_signatures(a, [])["msg_shas"] == ct.component_signatures(b, [])["msg_shas"]


def test_en_aendring_i_tool_calls_er_OGSAA_et_brud():
    """Kun `content` ville vaere blindt her — og et skift i tool_calls braekker
    cachen praecis lige saa haardt som et skift i teksten."""
    a = [{"role": "assistant", "content": "", "tool_calls": [{"id": "1", "name": "read_file"}]}]
    b = [{"role": "assistant", "content": "", "tool_calls": [{"id": "2", "name": "read_file"}]}]
    assert ct.component_signatures(a, [])["msg_shas"] != ct.component_signatures(b, [])["msg_shas"]


def test_naevner_aldrig_indholdet():
    """Telemetri, ikke en kopi af samtalen."""
    sig = ct.component_signatures(
        [{"role": "user", "content": "hemmelig sætning"}], [])
    assert "hemmelig" not in str(sig)
    assert all(len(h) == 6 for h in sig["msg_shas"])


def test_loftet_afkorter_listen_men_roeber_det():
    """En afkortet liste maa ALDRIG kunne laeses som en hel — saa ville et brud
    ude i halen se ud som en ren tilfoejelse."""
    n = ct._MSG_MAX + 25
    sig = ct.component_signatures([{"role": "user", "content": str(i)} for i in range(n)], [])
    assert len(sig["msg_shas"]) == ct._MSG_MAX
    assert sig["msg_count"] == n


def test_userialiserbart_indhold_vaelter_ikke_maaleren():
    """Telemetri maa aldrig kaste ind i stream-stien."""
    class Umulig:
        pass
    sig = ct.component_signatures([{"role": "user", "content": Umulig()}], [])
    assert len(sig["msg_shas"]) == 1


def test_linjen_baerer_besked_aftrykkene_videre(tmp_path, monkeypatch):
    """Felterne skal helt ud i loggen — ellers maaler scriptet paa ingenting."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ct.record_visible_cache(run_id="r", round_index=3, cache_hit=10, cache_miss=5,
                            msg_shas=["aaaaaa", "bbbbbb"], msg_lens=[12, 34], msg_count=2)
    linje = json.loads((tmp_path / "logs" / "cache_telemetry.jsonl").read_text().splitlines()[-1])
    assert linje["msg_shas"] == ["aaaaaa", "bbbbbb"]
    assert linje["msg_lens"] == [12, 34]
    assert linje["msg_count"] == 2
