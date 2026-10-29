"""Read-before-write guard — operator-side new-file behavior.

Regression: the operator guard blocked creating a BRAND-NEW file because it
ignored file_exists and always demanded a prior read. You can't read what
doesn't exist (ENOENT), so the write deadlocked → the LLM bypassed the guard
via `bash cat >`. Fix: honor file_exists=False (guard) + probe existence on
the operator side before blocking (handler).
"""
from __future__ import annotations

from unittest.mock import patch

from core.services.read_before_write_guard import check_operator_read_before_write


# ── Guard-level ───────────────────────────────────────────────────────────

def test_new_file_allowed_without_prior_read():
    ok, reason = check_operator_read_before_write(
        "/home/bs/brand-new.md", session_id="s1", file_exists=False
    )
    assert ok is True
    assert reason is None


def test_existing_unread_blocked():
    ok, _ = check_operator_read_before_write(
        "/home/bs/existing.md", session_id="s1", file_exists=True
    )
    assert ok is False


def test_unknown_existence_unread_blocked_conservative():
    ok, _ = check_operator_read_before_write(
        "/home/bs/maybe.md", session_id="s1", file_exists=None
    )
    assert ok is False


# ── Handler-level (_exec_operator_write_file) ─────────────────────────────

def _list_dir_result(names):
    return {"status": "ok", "result": [{"name": n, "type": "file"} for n in names]}


def test_handler_allows_new_file(monkeypatch):
    """Parent dir lists no matching name → new file → write proceeds."""
    from core.tools import simple_tools as st

    calls = {"wrote": False}

    def fake_run_operator_async(coro_fn, *, tool_name, timeout_s=35.0):
        if tool_name == "operator_list_dir":
            return _list_dir_result(["other.md"])  # target NOT present
        if tool_name == "operator_write_file":
            calls["wrote"] = True
            return {"status": "ok", "result": {"written": True}}
        return {"status": "ok", "result": None}

    monkeypatch.setattr(st, "_run_operator_async", fake_run_operator_async)
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")
    # operator_write_file_async is imported lazily inside the handler; the
    # fake _run_operator_async never calls it, so no further patch needed.

    out = st._exec_operator_write_file(
        {"path": "/media/projects/jarvis-v2/vesc-open-client-spec.md", "content": "hello"}
    )
    assert calls["wrote"] is True
    assert out.get("status") == "ok"


def test_handler_blocks_existing_unread_file(monkeypatch):
    """Parent dir lists the target → existing + unread → guard blocks."""
    from core.tools import simple_tools as st

    def fake_run_operator_async(coro_fn, *, tool_name, timeout_s=35.0):
        if tool_name == "operator_list_dir":
            return _list_dir_result(["vesc-open-client-spec.md"])  # target present
        return {"status": "ok", "result": None}

    monkeypatch.setattr(st, "_run_operator_async", fake_run_operator_async)
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")

    out = st._exec_operator_write_file(
        {"path": "/media/projects/jarvis-v2/vesc-open-client-spec.md", "content": "hello"}
    )
    assert out.get("status") == "error"
    assert out.get("blocked_by") == "read_before_write_guard"


def test_handler_force_skips_guard(monkeypatch):
    """force=true bypasses the READ-BEFORE-WRITE guard (no existence probe).

    Stien er flyttet ind i workspacet 7/9-2026. Operator-skrivning fik samme
    sti-gate som den lokale write_file, og /home/bs/... doemmes `approval` dér
    — saa testen ville maale sti-gaten i stedet for vagten. Se
    test_force_bypasser_IKKE_sti_gaten nedenfor for den nye egenskab.
    """
    from core.tools import simple_tools as st

    seen = {"list_dir": False, "wrote": False}

    def fake_run_operator_async(coro_fn, *, tool_name, timeout_s=35.0):
        if tool_name == "operator_list_dir":
            seen["list_dir"] = True
            return _list_dir_result(["vesc-open-client-spec.md"])
        if tool_name == "operator_write_file":
            seen["wrote"] = True
            return {"status": "ok", "result": {"written": True}}
        return {"status": "ok", "result": None}

    monkeypatch.setattr(st, "_run_operator_async", fake_run_operator_async)
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")

    out = st._exec_operator_write_file(
        {"path": "/media/projects/jarvis-v2/vesc-open-client-spec.md",
         "content": "x", "force": True}
    )
    assert seen["wrote"] is True
    assert seen["list_dir"] is False  # force → no probe
    assert out.get("status") == "ok"


def test_force_bypasser_IKKE_sti_gaten(monkeypatch):
    """`force` siger «filen er ny» — ikke «jeg maa skrive hvor som helst».

    Flaget saettes af MODELLEN. Kunne det ogsaa aabne sti-gaten, ville
    ~/.ssh/id_rsa staa aabent for enhver tur der bare huskede at sende
    force=true.
    """
    from core.tools import simple_tools as st

    skrev = {"ja": False}
    monkeypatch.setattr(
        st, "_run_operator_async",
        lambda coro_fn, *, tool_name, timeout_s=35.0: skrev.update(ja=True) or {"status": "ok"},
    )
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")

    ud = st._exec_operator_write_file(
        {"path": "/home/bs/.ssh/id_rsa", "content": "x", "force": True}
    )
    assert ud.get("status") == "blocked"
    assert skrev["ja"] is False


# ── is_protected — fail-closed ────────────────────────────────────────────

def test_is_protected_fail_closed_ved_parse_fejl(monkeypatch):
    """Ukendt sti → beskyttet (fail-closed), ikke åben.

    Den gamle `except: return False` var fail-open: en sti der ikke kunne
    parses ville slippe forbi skrive-vagten.
    """
    from core.services import read_before_write_guard as g

    class _Boom:
        def __init__(self, *a, **k):
            raise ValueError("kan ikke parses")

    monkeypatch.setattr(g, "Path", _Boom)
    assert g.is_protected("/noget/underligt") is True


def test_is_protected_kender_beskyttede_navne(monkeypatch):
    from core.services import read_before_write_guard as g

    navn = next(iter(g._PROTECTED_FILENAMES))
    assert g.is_protected(f"/vilkårlig/sti/{navn}") is True
    assert g.is_protected("/vilkårlig/sti/helt-normal.txt") is False


# ── Kode-daekning (29/10-2026) ────────────────────────────────────────────
#
# Vagtens daekning var NAVNE-baseret: ni filer, alle identitet/hukommelse —
# nul kode. Maalt samme dag: `edit_file` 2.229 kald mod `write_file` 444, og
# ingen af dem blev daekket naar filen var kode. Claudes harness blokerede 222
# blinde skrivninger fordi det daekkede `Edit`; mit daekkede kun ni filnavne.

def test_kodefil_kraever_laesning(tmp_path):
    from core.services import read_before_write_guard as rbw
    f = tmp_path / "modul.py"
    f.write_text("x = 1\n")
    assert rbw._kraever_laesning(f) is True


def test_markdown_kraever_ikke_laesning(tmp_path):
    """.md er BEVIDST udeladt: workspace-noter og brain-poster skrives i et
    tempo hvor et genlaesningskrav hvert 10. minut ville goere vagten til stoj."""
    from core.services import read_before_write_guard as rbw
    f = tmp_path / "note.md"
    f.write_text("# note\n")
    assert rbw._kraever_laesning(f) is False


def test_identitetsfil_kraever_laesning_uanset_endelse(tmp_path):
    from core.services import read_before_write_guard as rbw
    assert rbw._kraever_laesning(tmp_path / "SOUL.md") is True


def test_ulaest_kodefil_blokeres(tmp_path, monkeypatch):
    from core.services import read_before_write_guard as rbw
    f = tmp_path / "modul.py"
    f.write_text("x = 1\n")
    monkeypatch.setattr(rbw, "_was_read", lambda p, s: False)
    ok, reason = rbw.check_read_before_write(str(f), session_id="s1")
    assert ok is False
    assert "READ-BEFORE-WRITE" in reason


def test_laest_kodefil_tillades(tmp_path, monkeypatch):
    from core.services import read_before_write_guard as rbw
    f = tmp_path / "modul.py"
    f.write_text("x = 1\n")
    monkeypatch.setattr(rbw, "_was_read", lambda p, s: True)
    ok, reason = rbw.check_read_before_write(str(f), session_id="s1")
    assert ok is True
    assert reason is None


def test_ny_kodefil_tillades_uden_laesning(tmp_path):
    """Man kan ikke laese hvad der ikke findes — en ny fil har intet at clobbe."""
    from core.services import read_before_write_guard as rbw
    ok, reason = rbw.check_read_before_write(
        str(tmp_path / "helt-ny.py"), session_id="s1"
    )
    assert ok is True
    assert reason is None


def test_was_read_er_sti_baseret(tmp_path, monkeypatch):
    """Den offentlige wrapper maa ikke arve navne-filteret: telemetrien spoerger
    om en VILKAARLIG fil, ikke kun de ni beskyttede navne."""
    from core.services import read_before_write_guard as rbw
    f = tmp_path / "tilfaeldig.py"
    f.write_text("x\n")
    set_flag: dict[str, str] = {}

    def fake(p, s):
        set_flag["p"] = p
        return True

    monkeypatch.setattr(rbw, "_was_read", fake)
    assert rbw.was_read(str(f), session_id="s1") is True
    assert set_flag["p"] == str(f.resolve())


def test_was_read_kaster_aldrig(monkeypatch):
    """En maaling maa ikke vaelte det den maaler."""
    from core.services import read_before_write_guard as rbw

    def braek(p, s):
        raise RuntimeError("cachen er nede")

    monkeypatch.setattr(rbw, "_was_read", braek)
    assert rbw.was_read("/x.py") is False


# ── Ende-til-ende: guarden svarer, men HVEM læser svaret? (29/10-2026) ────
#
# Da vagten blev udvidet til kodefiler, viste `execute_tool` at en ulæst `.py`
# gik igennem uden en advarsel. Årsagen var ikke guarden: `check_file` svarede
# korrekt `guard_blocked` — men `_exec_edit_file` tjekkede kun `blocked` og
# `approval`, så svaret faldt igennem. Guarden havde ret hele tiden; ingen
# læste svaret. Det er samme fejlform som `silent_chain_break`-fundet: en
# mekanisme der returnerer sit fund til en kalder der kaster det væk.

def test_edit_file_returnerer_guard_blocked(tmp_path, monkeypatch):
    """Den gren der manglede. En ulæst kodefil skal give `guard_blocked` —
    ikke `ok`, og ikke en skrivning."""
    from core.tools import file_tools_exec as fte

    f = tmp_path / "ulast.py"
    f.write_text("x = 1\n")

    monkeypatch.setattr(
        "core.services.read_before_write_guard._was_read", lambda p, s: False
    )
    ud = fte._exec_edit_file({
        "path": str(f),
        "old_text": "x = 1",
        "new_text": "x = 2",
        "_runtime_session_id": "test-edit-guard",
    })
    assert ud.get("status") == "guard_blocked"
    assert "READ-BEFORE-WRITE" in str(ud.get("error"))
    # Og det afgørende: filen blev IKKE ændret.
    assert f.read_text() == "x = 1\n"


def test_edit_file_slipper_naar_filen_er_laest(tmp_path, monkeypatch):
    """Modstykket — vagten må ikke blokere den legitime vej."""
    from core.tools import file_tools_exec as fte

    f = tmp_path / "laest.py"
    f.write_text("x = 1\n")

    monkeypatch.setattr(
        "core.services.read_before_write_guard._was_read", lambda p, s: True
    )
    ud = fte._exec_edit_file({
        "path": str(f),
        "old_text": "x = 1",
        "new_text": "x = 2",
        "_runtime_session_id": "test-edit-guard",
    })
    assert ud.get("status") == "ok"
    assert f.read_text() == "x = 2\n"


# ── Vagten skal efterlade sig et spor (29/10-2026) ────────────────────────
#
# Det åbne spørgsmål var «bliver vagten for ivrig?» — og det kunne ikke
# afgøres. Ikke fordi den blokerede for lidt eller for meget, men fordi den
# var STUM: `_emit_read_before_write_guard_event` havde nul kaldere, og
# familien var ikke registreret, så et kald ville kaste og blive slugt af
# `except: pass`. Målt i den levende DB: nul guard-events blandt 854.376
# rækker mens bussen ellers skrev samme minut.
#
# Samme fejlform som Smith-rettelsen: en funktion der ser ud som om den
# virker, men aldrig kaldes. Testene her pinner at hvert udfald efterlader
# et spor — og at den ikke-governede flade forbliver stille.

def test_familien_er_registreret():
    """Et kald til en uregistreret familie kaster `Unsupported event family`,
    og kaldestedets `except` sluger den. Familien SKAL stå i registret, ellers
    er et kald ikke et spor."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event

    assert "read_before_write_guard" in ALLOWED_EVENT_FAMILIES
    Event.create("read_before_write_guard.blocked", {"path": "/x.py"})


def _fang(monkeypatch):
    fanget: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda kind, payload=None, **kw: fanget.append((kind, payload or {})),
    )
    return fanget


def test_blokering_efterlader_et_spor(tmp_path, monkeypatch):
    from core.services import read_before_write_guard as rbw

    f = tmp_path / "ulast.py"
    f.write_text("x = 1\n")
    monkeypatch.setattr(rbw, "_was_read", lambda p, s: False)
    fanget = _fang(monkeypatch)

    ok, _ = rbw.check_read_before_write(str(f), session_id="s1")

    assert ok is False
    kinds = [k for k, _ in fanget]
    assert "read_before_write_guard.blocked" in kinds, (
        f"vagten blokerede uden at efterlade et spor — fanget: {kinds}"
    )
    payload = next(p for k, p in fanget if k == "read_before_write_guard.blocked")
    assert payload.get("name") == "ulast.py"
    assert payload.get("session_id") == "s1"


def test_tilladelse_efterlader_et_spor(tmp_path, monkeypatch):
    """Uden dette spor kan jeg ikke skelne «vagten sagde ja» fra «vagten blev
    aldrig kaldt» — og så er blokeringstallet meningsløst."""
    from core.services import read_before_write_guard as rbw

    f = tmp_path / "laest.py"
    f.write_text("x = 1\n")
    monkeypatch.setattr(rbw, "_was_read", lambda p, s: True)
    fanget = _fang(monkeypatch)

    ok, _ = rbw.check_read_before_write(str(f), session_id="s1")

    assert ok is True
    assert "read_before_write_guard.allowed" in [k for k, _ in fanget]


def test_ny_fil_efterlader_et_spor(tmp_path, monkeypatch):
    from core.services import read_before_write_guard as rbw

    fanget = _fang(monkeypatch)
    ok, _ = rbw.check_read_before_write(str(tmp_path / "helt-ny.py"), session_id="s1")

    assert ok is True
    assert "read_before_write_guard.new_file" in [k for k, _ in fanget]


def test_ikke_governed_fil_stoejer_ikke(tmp_path, monkeypatch):
    """En .txt er ikke vagtens domæne. Ville den emittere for hvert sådant
    kald, druknede blokeringerne i støj — og så kunne spørgsmålet stadig ikke
    besvares."""
    from core.services import read_before_write_guard as rbw

    f = tmp_path / "note.txt"
    f.write_text("hej\n")
    fanget = _fang(monkeypatch)

    ok, _ = rbw.check_read_before_write(str(f), session_id="s1")

    assert ok is True
    assert fanget == [], f"ikke-governed fil emitterede: {fanget}"


def test_edit_sender_session_id_til_gaten(tmp_path, monkeypatch):
    """Læsningen registreres under sessions-id'et; blev der spurgt under
    "default", ville svaret være «nej» om en fil der netop var læst."""
    from core.tools import file_tools_exec as fte
    from core.services import gate_execution

    f = tmp_path / "sess.py"
    f.write_text("x = 1\n")
    set_flag: dict[str, str] = {}

    def fake_check_file(path, session_id="default", **kw):
        set_flag["sid"] = session_id
        return gate_execution._to_check(gate_execution._green("exec_file", "auto"))

    monkeypatch.setattr(gate_execution, "check_file", fake_check_file)
    fte._exec_edit_file({
        "path": str(f),
        "old_text": "x = 1",
        "new_text": "x = 2",
        "_runtime_session_id": "min-session-42",
    })
    assert set_flag["sid"] == "min-session-42"
