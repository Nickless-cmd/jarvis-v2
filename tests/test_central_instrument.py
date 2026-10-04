"""Tests for central_instrument — selv-instrumenterings-motoren (Jarvis-spec 2026-06-23)."""
from __future__ import annotations

from core.services import central_instrument as ci


def test_detects_bare_except_critical():
    src = "def f():\n    try:\n        x()\n    except:\n        pass\n"
    fs = ci.scan_source("core/x.py", src)
    kinds = {f.kind for f in fs}
    assert "bare_except" in kinds
    bare = next(f for f in fs if f.kind == "bare_except")
    assert bare.severity == "critical"


def test_except_returning_none_is_success_like():
    src = "def f():\n    try:\n        x()\n    except Exception:\n        return None\n"
    fs = ci.scan_source("core/x.py", src)
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.success_like is True and sil.severity == "high"


def test_guarded_except_is_not_flagged():
    # logger.error i except → ikke silent
    src = ("def f():\n    try:\n        x()\n    except Exception as e:\n"
           "        logger.error('boom', e)\n        return None\n")
    fs = ci.scan_source("core/x.py", src)
    assert not any(f.kind in ("except_silent", "except_pass", "bare_except") for f in fs)


def test_reraise_counts_as_guard():
    src = "def f():\n    try:\n        x()\n    except Exception:\n        raise\n"
    fs = ci.scan_source("core/x.py", src)
    assert not any(f.kind.startswith("except") for f in fs)


def test_error_return_without_observe():
    src = 'def f():\n    return {"error": "boom"}\n'
    fs = ci.scan_source("core/x.py", src)
    assert any(f.kind == "error_return_no_observe" for f in fs)


def test_long_function_unguarded():
    body = "\n".join(f"    a{i} = {i}" for i in range(60))
    src = f"def big():\n{body}\n"
    fs = ci.scan_source("core/x.py", src)
    assert any(f.kind == "long_unguarded" for f in fs)


def test_todo_low():
    fs = ci.scan_source("core/x.py", "x = 1  # TODO: ryd op\n")
    assert any(f.kind == "todo" and f.severity == "low" for f in fs)


def test_syntax_error_is_self_safe():
    assert ci.scan_source("core/x.py", "def (:::") == []


def test_signature_is_deterministic():
    src = "def f():\n    try:\n        x()\n    except:\n        pass\n"
    a = ci.scan_source("core/x.py", src)[0].signature
    b = ci.scan_source("core/x.py", src)[0].signature
    assert a == b and a.startswith("bare_except:")


def test_scoring_modifiers():
    f = ci.Finding("core/x.py", 1, "bare_except", "critical", "except:", "f", success_like=False)
    base = ci.score_finding(f, file_has_central=False, in_security=False)
    assert base == 3  # critical base
    assert ci.score_finding(f, file_has_central=False, in_security=True) == 5  # +2 security
    assert ci.score_finding(f, file_has_central=True, in_security=False) == 2  # -1 har central
    # lærings-dæmpning: afvist ≥3× → trækkes ned
    assert ci.score_finding(f, file_has_central=False, in_security=False, reject_count=3) == 0


def test_success_like_adds_two():
    f = ci.Finding("core/x.py", 1, "except_silent", "high", "except Exception:", "f", success_like=True)
    assert ci.score_finding(f, file_has_central=False, in_security=False) == 4  # 2 base + 2 succ


def test_acknowledged_self_safe_is_demoted():
    # except mærket "self-safe" → kendt beslutning → score under proposal-tærsklen
    src = ("def f():\n    # self-safe: må aldrig vælte runtime\n    try:\n        x()\n"
           "    except Exception:\n        return None\n")
    fs = ci.scan_source("core/x.py", src)
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.acknowledged is True
    score = ci.score_finding(sil, file_has_central=False, in_security=False)
    assert score < ci._PROPOSAL_THRESHOLD  # dæmpet til note


def test_acknowledged_does_not_save_bare_except():
    # bare except er ALDRIG forsvarligt — markør redder den ikke
    src = "def f():\n    # bevidst self-safe\n    try:\n        x()\n    except:\n        pass\n"
    fs = ci.scan_source("core/x.py", src)
    bare = next(f for f in fs if f.kind == "bare_except")
    assert ci.score_finding(bare, file_has_central=False, in_security=False) >= ci._PROPOSAL_THRESHOLD


# ── Mærket i funktionens DOCSTRING skal tælle ────────────────────────────────
# Målt 4/10-2026: af 1098 proposal-værdige fund havde 157 mærket i docstringen —
# men `_acknowledged` kiggede kun ±5 linjer omkring except'en, så kodebasens EGEN
# dokumentation («Selv-sikker → 0») var usynlig for scanneren. Fundet stod åbent
# og blev filét igen og igen. Mærket findes; vinduet nåede det ikke.


def _dokumenteret(doc: str) -> str:
    """En funktion hvor except'en ligger LANGT under docstringen (±5-vinduet når den ikke)."""
    return (
        f"def f():\n"
        f'    """{doc}"""\n'
        f"    x = 1\n"
        f"    y = 2\n"
        f"    z = 3\n"
        f"    w = 4\n"
        f"    try:\n"
        f"        return _hent(x)\n"
        f"    except Exception:\n"
        f"        return None\n"
    )


def test_maerket_i_docstringen_daemper_selv_langt_fra_excepten():
    fs = ci.scan_source("core/x.py", _dokumenteret("Laes en raekke. Selv-sikker: DB nede → None."))
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.acknowledged is True
    assert ci.score_finding(sil, file_has_central=False, in_security=False) < ci._PROPOSAL_THRESHOLD


def test_en_docstring_UDEN_maerke_daemper_ikke():
    """Modprøven: rettelsen må ikke gøre enhver docstring til et fribrev."""
    fs = ci.scan_source("core/x.py", _dokumenteret("Laes en raekke fra tabellen."))
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.acknowledged is False
    assert ci.score_finding(sil, file_has_central=False, in_security=False) >= ci._PROPOSAL_THRESHOLD


def test_docstring_maerke_redder_heller_ikke_bare_except():
    """Også her: bare except er aldrig forsvarligt, uanset hvor mærket står."""
    src = ("def f():\n"
           '    """Selv-sikker: maa aldrig vaelte runtime."""\n'
           "    x = 1\n    y = 2\n    z = 3\n    w = 4\n"
           "    try:\n        x()\n    except:\n        pass\n")
    fs = ci.scan_source("core/x.py", src)
    bare = next(f for f in fs if f.kind == "bare_except")
    assert bare.acknowledged is False
    assert ci.score_finding(bare, file_has_central=False, in_security=False) >= ci._PROPOSAL_THRESHOLD


def test_maerke_i_KROPPEN_langt_fra_faldet_daemper_ikke():
    """Grænsen, valgt med vilje: docstringen tæller — ikke hele funktions-kroppen.

    Et mærke langt nede i kroppen er ikke nødvendigvis en begrundelse for DETTE fald,
    og et bredt vindue ville lade én kommentar dæmpe alle funktionens fald på én gang.
    Målt 4/10-2026: 15 af 1098 proposal-værdige fund står netop her.
    """
    src = ("def f():\n"
           '    """Laes en raekke."""\n'
           "    x = 1\n"
           "    # selv-sikker: bevidst\n"
           "    y = 2\n    z = 3\n    w = 4\n    v = 5\n"
           "    try:\n        return _hent(x)\n"
           "    except Exception:\n        return None\n")
    fs = ci.scan_source("core/x.py", src)
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.acknowledged is False


def test_self_exclusion_in_file_list():
    files = ci._iter_py_files()
    assert ci._SELF_EXCLUDE not in files
    assert all("__pycache__" not in f and "/tests/" not in f for f in files)


# ── Dedup: et fund må filéres HØJST én gang (målt 4/10-2026) ──────────────
#
# `_file_proposals` tjekkede kun `pending`-køen. Så snart et forslag forlod
# køen — afvist, arkiveret eller udført — var fundet frit igen, og fordi
# `list_findings` sorterer deterministisk (`score DESC, severity, file`) ramte
# hver kørsel de SAMME fund. Målt i drift: 48 fund stod bag 1.129 forslag
# (~23 gen-filinger hver), mens 937 kandidater nedenfor i sorteringen aldrig
# blev nået.


def _fund(sig: str, *, score: int = 4) -> dict:
    return {"signature": sig, "line": 1, "kind": "except_silent",
            "severity": "high", "score": score, "function": "f", "snippet": "x"}


def test_et_fund_fileres_kun_en_gang(isolated_runtime):
    """Forslaget forlader køen uden at udføre — fundet må ikke filéres igen."""
    from core.runtime import db_instrument as dbi
    from core.services import autonomy_proposal_queue as q

    dbi.replace_file_findings("core/a.py", [_fund("sig-a")])
    assert ci._file_proposals(max_new=10) == 1

    forslag = q.list_pending_proposals(limit=10)
    assert len(forslag) == 1
    q.reject_proposal(forslag[0]["proposal_id"], resolution_note="nej")

    # Fundet er STADIG åbent — koden er ikke rettet. Men anmodningen er afvist,
    # og en anmodning der er afvist skal ikke gentages.
    assert any(r["signature"] == "sig-a"
               for r in dbi.list_findings(status="open", min_score=3, limit=10))
    assert ci._file_proposals(max_new=10) == 0


def test_filede_fund_optager_ikke_vinduet(isolated_runtime):
    """Et filéret fund må ikke SKUBBE et ufiléret ud af vinduet.

    Uden filtrering i SQL returnerer `LIMIT max_new` de samme filede fund hver
    kørsel, og daemonen står stille for evigt — de 937 nås aldrig.
    """
    from core.runtime import db_instrument as dbi
    from core.services.autonomy_proposal_queue import file_proposal

    # Ti filede fund der sorterer FORAN de tre ufilede: samme score og severity,
    # så rækkefølgen er filnavnet (core/f* < core/n*).
    for i in range(10):
        sig = f"sig-f{i:02d}"
        dbi.replace_file_findings(f"core/f{i:02d}.py", [_fund(sig)])
        file_proposal(kind="instrument_fix", title=f"gammel {i}", rationale="",
                      payload={"finding": _fund(sig)}, created_by="test",
                      canonical_key=sig)
    for i in range(3):
        dbi.replace_file_findings(f"core/n{i:02d}.py", [_fund(f"sig-n{i:02d}")])

    assert ci._file_proposals(max_new=3) == 3


def test_ukendt_filingstilstand_filer_intet(isolated_runtime, monkeypatch):
    """Kan vi ikke afgøre hvad der er filéret, filer vi INTET — ikke «løs».

    Et DB-fejl må ikke ligne «intet er filéret»: den ene udsætter en kørsel,
    den anden gentager en anmodning Bjørn allerede har set.
    """
    from core.runtime import db_instrument as dbi

    dbi.replace_file_findings("core/a.py", [_fund("sig-a")])
    monkeypatch.setattr(ci, "_allerede_filet", lambda: None)
    assert ci._file_proposals(max_new=10) == 0


def test_foraeldrede_fund_ryddes_naar_filen_forsvinder(isolated_runtime):
    """En fil der flyttes eller slettes scannes aldrig — dens fund skal ryddes.

    `replace_file_findings` rydder kun fund for filer der BLIVER scannet, og en
    fil der er væk besøges aldrig af `_iter_py_files()`. Målt 4/10-2026: 35
    forældede fund over 9 stier — `core/services/db_central_incidents.py` var
    flyttet til `core/runtime/`, `tiktok_tools.py` og `prospective_memory.py`
    var slettede. De talte med i køen som om koden stadig havde fejlen.
    """
    from core.runtime import db_instrument as dbi

    dbi.replace_file_findings("core/findes.py", [_fund("sig-findes")])
    dbi.replace_file_findings("core/vaek.py", [_fund("sig-vaek")])
    dbi.set_file_hash("core/vaek.py", "h", 1)

    assert dbi.prune_missing_files({"core/findes.py"}) == 1

    aabne = {f["signature"] for f in dbi.list_findings(status="open", limit=50)}
    assert "sig-vaek" not in aabne, "et fund for en fil der ikke findes skal ryddes"
    assert "sig-findes" in aabne, "et fund for en fil der FINDES maa ikke roeres"
    assert dbi.get_file_hash("core/vaek.py") is None, "scan-cachen skal ryddes med"


def test_rydningen_roerer_intet_naar_alle_filer_findes(isolated_runtime):
    """Modprøven: er der ingen forældede filer, sker der ingenting."""
    from core.runtime import db_instrument as dbi

    dbi.replace_file_findings("core/findes.py", [_fund("sig-findes")])
    assert dbi.prune_missing_files({"core/findes.py"}) == 0
    assert any(f["signature"] == "sig-findes"
               for f in dbi.list_findings(status="open", limit=50))


def test_scanningen_rydder_fund_for_en_fil_der_er_vaek(isolated_runtime, monkeypatch, tmp_path):
    """KOBLINGEN: `scan_repo` skal selv rydde fund for filer der ikke længere findes.

    Funktionen alene er ikke nok. Uden kaldet inde i `scan_repo` står fundet for
    en flyttet eller slettet fil i køen for evigt, fordi `replace_file_findings`
    kun besøger filer der BLIVER scannet — og den er væk.
    """
    from core.runtime import db_instrument as dbi
    from core.services import central_instrument as ci

    dbi.replace_file_findings("core/vaek.py", [_fund("sig-vaek")])
    (tmp_path / "core").mkdir(parents=True, exist_ok=True)
    (tmp_path / "core" / "findes.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(ci, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci, "_iter_py_files", lambda: ["core/findes.py"])
    monkeypatch.setattr(ci, "_security_files", lambda: set())

    rep = ci.scan_repo(changed_only=False)

    assert rep["pruned_files"] == 1
    aabne = {f["signature"] for f in dbi.list_findings(status="open", limit=50)}
    assert "sig-vaek" not in aabne, "scanningen skal have ryddet fundet for den væk fil"
