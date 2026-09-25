"""«Ingen density-noter endnu» betød IKKE død.

`cognitive_architecture_surface.py` læser `active` som «systemet lever».
memory_density satte nøglen efter om der var INDHOLD, så et modul der tikkede
korrekt og rigtigt meldte «endnu ingenting» meldte sig dødt i mind-rapporten.

Målt 25/9-2026: 13 af 71 kognitive systemer stod `active: false`, og de fleste
af dem kørte fint. Tomheden hører i `summary`, ikke i livstegnet.

Modulet er begivenhedsdrevet (`tick` siger selv «No periodic work»), og
`write_density_note` kaldes fra `mic_listen_tool` og `voice_journal_tool`.
Ingen noter betyder at ingen har brugt dem — ikke at modulet er væk."""
from __future__ import annotations

import core.services.memory_density as M


def test_et_tomt_men_koerende_modul_er_LEVENDE():
    flade = M.build_memory_density_surface()
    assert flade["active"] is True


def test_tomheden_staar_i_summary_ikke_i_livstegnet():
    flade = M.build_memory_density_surface()
    assert isinstance(flade.get("summary"), str)
    assert flade["summary"], "summary maa ikke vaere tom — den baerer tilstanden"


def test_active_afhaenger_IKKE_af_en_taelling():
    """Vagten mod at nogen sætter `len(...) > 0` tilbage."""
    import ast
    import inspect

    kilde = inspect.getsource(M.build_memory_density_surface)
    traeet = ast.parse(kilde.lstrip())
    for n in ast.walk(traeet):
        if not isinstance(n, ast.Dict):
            continue
        for k, v in zip(n.keys, n.values):
            if isinstance(k, ast.Constant) and k.value == "active":
                assert isinstance(v, ast.Constant) and v.value is True, (
                    f"`active` er {ast.unparse(v)} — livstegnet maa ikke "
                    "afhaenge af om der er indhold"
                )
