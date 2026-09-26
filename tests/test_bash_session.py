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
import threading
import time

import pytest

from core.tools.bash_session import _Session, _list_row


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


# ── Låsen: to fejl målt 26/9-2026 ───────────────────────────────────────
#
# Begge sad i `close()`, som tog sessionens egen lås. En kørende kommando
# holder den i op til 300 sekunder.


def test_close_maa_ikke_deadlocke_naar_run_kalder_den_selv():
    """`run` kalder `close()` INDE i sin egen lås-blok.

    Grenen er «timeout og resync kunne ikke redde shellen». `threading.Lock`
    er ikke rekursiv, så tråden ventede på sig selv. Målt før rettelsen: `run`
    vendte aldrig tilbage, og `lock.locked()` var stadig True efter 15 s.
    Derfra hang sessionens daemon-tråd for evigt, reaperen hang på den samme
    session, og klienten fik til sidst `_client_call` til at dræbe hele
    daemonen — med alle andre sessioner.
    """
    s = _Session(session_id="pytest-deadlock")
    try:
        s._resync = lambda *a, **k: False      # tving den uredelige gren
        svar: dict = {}
        t = threading.Thread(target=lambda: svar.update(s.run("sleep 10", timeout=2)),
                             daemon=True)
        t.start()
        t.join(timeout=12)
        assert not t.is_alive(), "run vendte aldrig tilbage — låsen venter på sig selv"
        assert not s.lock.locked()
        assert svar.get("status") == "error"
    finally:
        s.close()


def test_close_paa_en_OPTAGET_session_vender_tilbage_med_det_samme():
    """Målt før rettelsen: 10,2 s, hvorefter klienten dræbte hele daemonen.

    `terminate()` slår shellen ihjel uden at tage låsen; den kørende `run` får
    EOF på pty'en og slipper den selv.
    """
    s = _Session(session_id="pytest-busy-close")
    t = threading.Thread(target=lambda: s.run("sleep 30", timeout=60), daemon=True)
    t.start()
    time.sleep(1.0)
    assert s.lock.locked(), "opsætningen virker ikke — kommandoen kører ikke"
    t0 = time.time()
    s.close()
    brugt = time.time() - t0
    assert brugt < 5.0, f"close tog {brugt:.1f}s på en optaget session"
    assert not s.alive()
    t.join(timeout=10)
    assert not t.is_alive()


# ── Hvad `list` svarer ──────────────────────────────────────────────────


class _Attrap:
    """Nok af en session til at `_list_row` kan læses uden en daemon."""

    def __init__(self, *, laast: bool, kommando: str, levende: bool = True):
        self.lock = threading.Lock()
        if laast:
            self.lock.acquire()
        self.running_command = kommando
        self.last_used = time.time() - 42
        self._levende = levende

    def alive(self) -> bool:
        return self._levende


def test_list_siger_om_sessionen_er_optaget_og_hvad_der_koerer():
    # Daemonen er tråd-per-forbindelse, så `list` besvares MIDT i en kørsel.
    # Før dette felt svarede den det samme uanset, og panelet skrev «intet
    # kører» på ren tro.
    r = _list_row("bsh-x", _Attrap(laast=True, kommando="npm run build"), time.time())
    assert r["busy"] is True
    assert r["command"] == "npm run build"
    # `last_used` sættes ved kommandoens START, så tallet ER køretiden.
    assert r["idle_seconds"] == 42


def test_list_viser_ikke_en_gammel_kommando_paa_en_ledig_session():
    # `running_command` ryddes aldrig — den er kun sand mens låsen holdes.
    # Uden den kobling ville en ledig session stå og vise sit sidste kald.
    r = _list_row("bsh-y", _Attrap(laast=False, kommando="npm run build"), time.time())
    assert r["busy"] is False
    assert r["command"] == ""
