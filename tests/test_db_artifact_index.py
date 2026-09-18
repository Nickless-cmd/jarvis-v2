"""Artefakt-indekset: filerne Jarvis har rørt i en mappe, paa tvaers af samtaler.

Fixturerne bruger de former der FAKTISK staar i databasen — maalt paa CT105
18/9-2026: nøglen hedder `path`, stierne er absolutte, og `edit_file` baerer
`old_text`/`new_text`. Tidligere samme dag var en klient-test grøn i maaneder
fordi den selv leverede et argumentnavn intet kald bruger.
"""
from __future__ import annotations

import json

from core.runtime.db_artifact_index import list_artifacts

ROD = "/media/projects/jarvis-v2"


def _svar(sid: str, *kald: tuple[str, dict], ts: str) -> None:
    from core.services.chat_sessions import append_chat_message
    blokke = [{"type": "text", "text": "ok"}] + [
        {"type": "tool_use", "id": f"t{i}", "name": n, "input": inp}
        for i, (n, inp) in enumerate(kald)
    ]
    append_chat_message(session_id=sid, role="assistant", content="ok",
                        content_json=json.dumps(blokke), created_at=ts)


def _session(titel: str) -> str:
    from core.services.chat_sessions import create_chat_session
    return str(create_chat_session(title=titel)["id"])


def test_filer_i_mappen_nyeste_foerst(isolated_runtime) -> None:
    s = _session("login")
    _svar(s, ("edit_file", {"path": f"{ROD}/core/a.py", "old_text": "x", "new_text": "y\nz"}),
          ts="2026-09-18T10:00:00+00:00")
    _svar(s, ("write_file", {"path": f"{ROD}/docs/b.md", "content": "l1\nl2\nl3\n"}),
          ts="2026-09-18T11:00:00+00:00")

    r = list_artifacts(ROD)

    assert r["ok"] is True
    assert [a["rel"] for a in r["artifacts"]] == ["docs/b.md", "core/a.py"]
    b, a = r["artifacts"]
    assert (a["add"], a["del"]) == (2, 1)
    # write_file: kun tilfoejet; linjeskift + 1 som Claude Desktop.
    assert (b["add"], b["del"]) == (4, 0)


def test_filer_uden_for_mappen_er_ikke_med(isolated_runtime) -> None:
    s = _session("x")
    _svar(s, ("edit_file", {"path": "/tmp/skrald.py", "old_text": "a", "new_text": "b"}),
          ("edit_file", {"path": f"{ROD}-kopi/c.py", "old_text": "a", "new_text": "b"}),
          ts="2026-09-18T10:00:00+00:00")

    # `jarvis-v2-kopi` starter med samme tegn, men er en ANDEN mappe.
    assert list_artifacts(ROD)["artifacts"] == []


def test_paa_tvaers_af_samtaler_samles_pr_fil(isolated_runtime) -> None:
    s1, s2 = _session("foerste"), _session("anden")
    _svar(s1, ("edit_file", {"path": f"{ROD}/a.py", "old_text": "a", "new_text": "b"}),
          ts="2026-09-18T10:00:00+00:00")
    _svar(s2, ("edit_file", {"path": f"{ROD}/a.py", "old_text": "c\nd", "new_text": "e"}),
          ts="2026-09-18T12:00:00+00:00")

    (a,) = list_artifacts(ROD)["artifacts"]
    assert a["edits"] == 2
    assert a["session_count"] == 2
    assert (a["add"], a["del"]) == (2, 3)
    # Den SENESTE berøring bestemmer tidspunkt og samtale.
    assert a["last_at"].startswith("2026-09-18T12")
    assert a["session_title"] == "anden"


def test_broens_vaerktoejer_og_multi_edit_taeller_med(isolated_runtime) -> None:
    s = _session("bro")
    _svar(s,
          ("operator_edit_file", {"path": f"{ROD}/a.py", "old_text": "a", "new_text": "b"}),
          ("multi_edit", {"path": f"{ROD}/b.py", "edits": [
              {"old_text": "a", "new_text": "b\nc"}, {"old_text": "d\ne", "new_text": "f"}]}),
          ts="2026-09-18T10:00:00+00:00")

    r = {a["rel"]: a for a in list_artifacts(ROD)["artifacts"]}
    assert set(r) == {"a.py", "b.py"}
    assert (r["b.py"]["add"], r["b.py"]["del"]) == (3, 3)


def test_laesende_vaerktoejer_er_ikke_artefakter(isolated_runtime) -> None:
    s = _session("laes")
    _svar(s, ("read_file", {"path": f"{ROD}/a.py"}), ts="2026-09-18T10:00:00+00:00")
    assert list_artifacts(ROD)["artifacts"] == []


def test_navngiven_rod_oversaettes(isolated_runtime) -> None:
    from core.runtime.config import PROJECT_ROOT
    assert list_artifacts("repo")["root"] == str(PROJECT_ROOT)


# En tom rod ville matche ALT og saa var listen ikke «denne mappe» laengere.
def test_tom_eller_relativ_rod_giver_intet(isolated_runtime) -> None:
    for rod in ("", "/", "relativ/sti"):
        r = list_artifacts(rod)
        assert r["ok"] is False
        assert r["artifacts"] == []


# Faelden huset har gaaet i fire gange: et `limit`-vindue der skjuler halen.
def test_ingen_vindue_gamle_beskeder_kommer_med(isolated_runtime) -> None:
    s = _session("lang")
    _svar(s, ("edit_file", {"path": f"{ROD}/gammel.py", "old_text": "a", "new_text": "b"}),
          ts="2026-01-01T10:00:00+00:00")
    for i in range(300):
        _svar(s, ("read_file", {"path": f"{ROD}/x{i}.py"}), ts=f"2026-09-18T10:{i // 60:02d}:{i % 60:02d}+00:00")

    r = list_artifacts(ROD)
    assert [a["rel"] for a in r["artifacts"]] == ["gammel.py"]
    assert r["scanned"] == 301
