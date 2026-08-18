"""Persistent bash-session: én dårlig kommando må ALDRIG forgifte sessionen.

Rod (Bjørn 18. aug 2026 — "alle hans tools sluges, især bash"): `bash` kører gennem en
DELT persistent PTY-shell. Hver kommando sendes som `{ <cmd>\\n } ; echo "MARKER $?"` og
der læses indtil MARKER. Efterlader en kommando shell'en i continuation-tilstand
(uafsluttet quote/brace/heredoc), bliver `}`-linjen OG markeren spist som en del af den
ventende konstruktion → markeren kommer aldrig → timeout. Shell'en forbliver desynket,
og da `_drain_pending` kun kaldes ved session-ÅBNING og `_reset_default_bash_session` kun
ved "session terminated", blev HVER efterfølgende kommando slugt: intet output, ingen
filer oprettet, ingen fejl. Jarvis så det som "kommandoen sluges FØR eksekvering" — korrekt
observeret: shell'en nåede aldrig at parse den.

Reproduceret før fix:
    1 echo HELLO_A                      → ok
    2 echo "unterminated                → timeout
    3 echo B && echo M > /tmp/f.txt     → timeout, fil IKKE oprettet
    4 pwd                               → timeout
"""
from __future__ import annotations

import os

import pytest

from core.tools.bash_session import _Session


@pytest.fixture()
def session():
    s = _Session(session_id="pytest-bash-session")
    yield s
    try:
        s.close()
    except Exception:
        pass


def test_sund_kommando_virker(session):
    r = session.run("echo HELLO_A", timeout=10)
    assert r["status"] == "ok"
    assert r["exit_code"] == 0
    assert "HELLO_A" in (r.get("output") or "")


def test_desync_forgifter_ikke_sessionen(session, tmp_path):
    """KERNEN: efter en desyncende kommando skal den NÆSTE kommando stadig virke."""
    session.run("echo HELLO_A", timeout=10)

    # Uafsluttet quote → efterlader shell'en i continuation-tilstand.
    bad = session.run('echo "unterminated', timeout=5)
    assert bad["status"] in {"timeout", "error"}   # den selv må gerne fejle

    # ...men sessionen skal være resynkroniseret, så DENNE kører.
    marker_file = tmp_path / "after_desync.txt"
    good = session.run(f"echo RECOVERED > {marker_file} && echo DONE_OK", timeout=15)
    assert good["status"] == "ok", f"session forblev desynket: {good}"
    assert "DONE_OK" in (good.get("output") or "")
    assert marker_file.exists(), "kommandoen nåede aldrig shell'en (slugt)"


def test_flere_kommandoer_efter_desync(session):
    """Sessionen skal blive ved at virke — ikke kun ét kald efter recovery."""
    session.run('echo "unterminated', timeout=5)
    for i in range(3):
        r = session.run(f"echo LOOP_{i}", timeout=10)
        assert r["status"] == "ok", f"kald {i} slugt: {r}"
        assert f"LOOP_{i}" in (r.get("output") or "")


def test_uafsluttet_heredoc_forgifter_ikke(session):
    """Jarvis' faktiske trigger-klasse: `python - <<'EOF'` uden afsluttende EOF."""
    session.run("cat <<'EOF'\nlinje1", timeout=5)
    r = session.run("echo AFTER_HEREDOC", timeout=15)
    assert r["status"] == "ok", f"heredoc-desync forgiftede sessionen: {r}"
    assert "AFTER_HEREDOC" in (r.get("output") or "")


def test_timeout_paa_langvarig_kommando_afbrydes(session):
    """En kommando der bare tager for lang tid skal afbrydes, ikke efterlade sessionen død."""
    slow = session.run("sleep 30", timeout=3)
    assert slow["status"] in {"timeout", "error"}
    r = session.run("echo AFTER_SLOW", timeout=15)
    assert r["status"] == "ok", f"session død efter langsom kommando: {r}"
    assert "AFTER_SLOW" in (r.get("output") or "")
