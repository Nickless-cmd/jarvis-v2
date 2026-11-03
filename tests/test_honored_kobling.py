"""Honored-stien: fra en kvittering i r2.5 til tærsklens tæller.

3/11-2026 var asymmetrien målt: `veto_adaptive_counters` kunne kun bevæge sig
én vej. Overrides hævede tærsklen, honored sænkede den aldrig — fordi
`resolve_veto_event(..., "honored")` havde nul kaldere i produktion. Gaten
blev altså gradvist mere eftergivende uden at nogen havde besluttet det.

`r2_5_haandhaevelse._kvitter_adlydt` er den kalder der lukker asymmetrien:
en blok der løftes af et faktisk kig tilbage skrives som `honored`, og det
skal ramme tælleren for netop det (tool, feeling)-par der blev blokeret.

Disse to tests binder de to moduler sammen. Uden dem kan hver af dem se
korrekt ud mens forbindelsen mellem dem er væk — og det er præcis den
fejlform aftenen handlede om.
"""
from __future__ import annotations


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConn:
    """Kun nok DB til at `resolve_veto_event` kan læse og opdatere én række."""

    def __init__(self, row):
        self._row = row
        self.updated: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple = ()):
        if "SELECT tool_name" in sql:
            return _FakeResult(self._row)
        self.updated.append((sql, params))
        return _FakeResult(None)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_honored_rammer_taelleren_for_det_blokerede_par(monkeypatch):
    """`resolve_veto_event(..., "honored")` skal øge honored-tælleren.

    Uden dette kald er dæmpningen i `_adaptive_threshold` en term der altid
    er nul — en symmetri der ser ud som en mekanisme.
    """
    from core.services import veto_gate

    kaldt: list[tuple[str, str]] = []
    fake = _FakeConn(("edit_file", "irritation"))
    monkeypatch.setattr("core.runtime.db_core.connect", lambda: fake)
    monkeypatch.setattr(
        veto_gate,
        "_increment_honored_count",
        lambda tool, feeling: kaldt.append((tool, feeling)) or 1,
    )
    monkeypatch.setattr(veto_gate, "_emit_veto_gate_event", lambda *a, **k: None)

    veto_gate.resolve_veto_event("evt-honored-1", "honored")

    assert kaldt == [("edit_file", "irritation")], (
        "honored-kvitteringen ramte ikke tælleren — så kan tærsklen aldrig "
        "sænkes igen efter en override"
    )


def test_en_override_taeller_ikke_som_honored(monkeypatch):
    """Modsat retning må ikke snige sig ind: kun `honored` dæmper.

    En override er «kør alligevel» og hæver tærsklen ad en anden vej. Blev
    den også talt som honored, ville de to modsatrettede kræfter udligne
    hinanden og begge målinger blive meningsløse.
    """
    from core.services import veto_gate

    kaldt: list[tuple[str, str]] = []
    fake = _FakeConn(("edit_file", "irritation"))
    monkeypatch.setattr("core.runtime.db_core.connect", lambda: fake)
    monkeypatch.setattr(
        veto_gate,
        "_increment_honored_count",
        lambda tool, feeling: kaldt.append((tool, feeling)) or 1,
    )
    monkeypatch.setattr(veto_gate, "_emit_veto_gate_event", lambda *a, **k: None)

    veto_gate.resolve_veto_event("evt-override-1", "overridden_by_user")

    assert kaldt == [], "en override blev talt som honored"


def test_r2_5_kvitteringen_kalder_honored_stien():
    """Bindeleddet: `_kvitter_adlydt` skal kalde `resolve_veto_event(..., "honored")`.

    Testen læser kilden frem for at kalde funktionen, fordi den kræver en
    levende DB med en `pending` blok. Det den kan fastslå statisk er at
    forbindelsen findes — og at den ikke kan forsvinde uden at testen falder.
    """
    import pathlib

    kilde = pathlib.Path(
        "core/services/r2_5_haandhaevelse.py").read_text(encoding="utf-8")
    assert "resolve_veto_event(event_id, \"honored\")" in kilde, (
        "r2.5-kvitteringen kalder ikke længere honored-stien — så er "
        "asymmetrien tilbage: kun overrides kan flytte tærsklen"
    )
