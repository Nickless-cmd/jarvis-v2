"""Spild: den overstore hale gemmes i stedet for at blive klippet væk.

Før stod der kun «N chars omitted», og halen var reelt væk — kaldte han om,
fik han samme klip igen. Testene her pinner de tre egenskaber der gør det
til andet end «skriv en fil»: privat mappe, uforudsigeligt navn, og at en
sti fra kalderen ikke kan pege ud af roden.
"""
import os
import time
from pathlib import Path

import core.services.spild as sp


def _peg_rod(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "_rod", lambda: tmp_path / "spild")


def test_hele_teksten_kan_hentes_igen(tmp_path, monkeypatch):
    _peg_rod(tmp_path, monkeypatch)
    tekst = "linje\n" * 5000
    sti = sp.gem(tekst, session_id="s1", vaerktoej="bash")
    assert Path(sti).read_text(encoding="utf-8") == tekst


def test_mappen_er_privat_og_navnet_uforudsigeligt(tmp_path, monkeypatch):
    _peg_rod(tmp_path, monkeypatch)
    a = sp.gem("x", session_id="s1", vaerktoej="bash")
    b = sp.gem("x", session_id="s1", vaerktoej="bash")
    assert a != b                                        # samme kald, nyt navn
    assert len(Path(a).stem.split("-")[-1]) == 32        # uuid4-hex, ikke en tæller
    assert oct(Path(a).parent.stat().st_mode)[-3:] == "700"
    assert oct(Path(a).stat().st_mode)[-3:] == "600"


def test_et_ondt_session_id_kan_ikke_skrive_uden_for_roden(tmp_path, monkeypatch):
    """Uden rensning ville kalderen bestemme hvor på disken vi skriver."""
    _peg_rod(tmp_path, monkeypatch)
    sti = sp.gem("x", session_id="../../../etc", vaerktoej="../../sh")
    rod = (tmp_path / "spild").resolve()
    assert rod in Path(sti).resolve().parents


def test_uden_session_grupperes_der_pr_dato(tmp_path, monkeypatch):
    _peg_rod(tmp_path, monkeypatch)
    sti = sp.gem("x", vaerktoej="bash")
    assert Path(sti).parent.name == time.strftime("dag-%Y-%m-%d")


def test_henvisningen_siger_baade_hvad_der_mangler_og_hvor(tmp_path, monkeypatch):
    _peg_rod(tmp_path, monkeypatch)
    sti = sp.gem("x" * 100, session_id="s1")
    tekst = sp.henvisning(sti, vist=30, i_alt=100)
    assert "70" in tekst and sti in tekst and "IKKE væk" in tekst


def test_gem_kaster_aldrig_men_giver_tom_streng(tmp_path, monkeypatch):
    """Kan vi ikke spilde, skal kalderen klippe som før — ikke vælte."""
    monkeypatch.setattr(sp, "_mappe", lambda sid: (_ for _ in ()).throw(OSError("fuld disk")))
    assert sp.gem("x", session_id="s1") == ""


def test_ryd_fjerner_gamle_og_beholder_friske(tmp_path, monkeypatch):
    _peg_rod(tmp_path, monkeypatch)
    gammel = Path(sp.gem("x", session_id="s1"))
    frisk = Path(sp.gem("y", session_id="s1"))
    fortid = time.time() - (sp.OPBEVARING_DAGE + 1) * 86400
    os.utime(gammel, (fortid, fortid))
    assert sp.ryd() == 1
    assert not gammel.exists() and frisk.exists()


def test_adapteren_spilder_i_stedet_for_at_klippe(tmp_path, monkeypatch):
    """Sømmen: det er adapteren der før tabte halen."""
    _peg_rod(tmp_path, monkeypatch)
    from core.services.visible_followup_adapters import OllamaFollowupAdapter
    from core.services.visible_followup_events import ToolExchange, ToolResult
    lang = "A" * 9000
    ex = ToolExchange(text="", tool_calls=[],
                      results=[ToolResult(tool_call_id="1", tool_name="bash", content=lang)])
    ud = OllamaFollowupAdapter()._compact_exchanges([ex])[0].results[0].content
    assert "chars omitted" not in ud          # den gamle blindgyde er væk
    sti = ud.rsplit("ligger i ", 1)[1].split(".", 1)[0]
    assert Path(sti + ".txt").read_text(encoding="utf-8") == lang


def test_adapteren_klipper_som_foer_hvis_spild_fejler(monkeypatch):
    from core.services import visible_followup_adapters as vfa
    from core.services.visible_followup_events import ToolExchange, ToolResult
    monkeypatch.setattr(vfa._spild, "gem", lambda *a, **k: "")
    ex = ToolExchange(text="", tool_calls=[],
                      results=[ToolResult(tool_call_id="1", tool_name="bash", content="A" * 9000)])
    ud = vfa.OllamaFollowupAdapter()._compact_exchanges([ex])[0].results[0].content
    assert "chars omitted" in ud
