"""Én bash, ikke to — og force springer godkendelse over, ikke destruktion.

`_force_bash` var indtil 6/9-2026 en PARALLEL implementation: raa subprocess
uden persistent shell, operator-kanal, sandkasse, egress-observation eller
bevaring af det fulde output. Autonome runs koerte altsaa en ANDEN bash end
synlige ture, og alt der blev bygget paa `_exec_bash` gjaldt kun halvdelen af
systemet.
"""
import core.tools.simple_tools as st


def test_force_bash_delegerer_til_den_rigtige_bash(monkeypatch):
    """Ikke en kopi — samme funktion, med ét flag."""
    set_args = {}

    def _falsk(args):
        set_args.update(args)
        return {"status": "ok", "text": "ok", "exit_code": 0}

    monkeypatch.setattr(st, "_exec_bash", _falsk)
    st._force_bash({"command": "echo hej"})
    assert set_args["command"] == "echo hej"
    assert set_args["_runtime_trust_all"] is True


def test_force_uden_kommando():
    assert st._force_bash({})["status"] == "error"


def test_mutation_koerer_uden_prompt_i_force():
    """Det er dét force ER til for."""
    r = st.execute_tool_force("bash", {"command": "echo hej-fra-force"})
    assert r["status"] == "ok"
    assert "hej-fra-force" in r["text"]


def test_DESTRUKTIVT_springes_ALDRIG_over():
    """`rm -rf /` er 'destructive', ikke 'blocked'.

    Den gamle `_force_bash` tjekkede KUN for 'blocked' — saa den koerte
    destruktive kommandoer i autonome runs. Hullet er aeldre end
    sammenlaegningen.
    """
    r = st.execute_tool_force("bash", {"command": "rm -rf /"})
    assert r["status"] == "approval_needed", r


def test_blokeret_er_stadig_blokeret():
    r = st.execute_tool_force("bash", {"command": "sudo rm -rf /home"})
    assert r["status"] in ("gate_blocked", "blocked"), r


def test_force_faar_ogsaa_det_fulde_output(monkeypatch):
    """Alt hvad der er bygget paa _exec_bash gaelder nu BEGGE veje."""
    kaldt = {}

    def _falsk(args):
        kaldt["ja"] = True
        return {"status": "ok", "text": "kort", "text_full": "meget laengere", "exit_code": 0}

    monkeypatch.setattr(st, "_exec_bash", _falsk)
    r = st._force_bash({"command": "x"})
    assert kaldt.get("ja")
    assert r.get("text_full") == "meget laengere"
