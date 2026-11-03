"""Honored-stien: fra en kvittering i r2.5 til tærsklens tæller.

3/11-2026 var asymmetrien målt: `veto_adaptive_counters` kunne kun bevæge sig
én vej. Overrides hævede tærsklen, honored sænkede den aldrig — fordi
`resolve_veto_event(..., "honored")` havde nul kaldere i produktion. Gaten
blev altså gradvist mere eftergivende uden at nogen havde besluttet det.

`r2_5_haandhaevelse._kvitter_adlydt` er den kalder der gør stien levende:
en blok der løftes af et faktisk kig tilbage skrives som `honored`.

⚠️ MEN — målt samme aften, efter at testene var skrevet: forbindelsen er
ikke det samme som virkningen. r2.5 logger sin blokering med
`feeling=NERVE` (`"r2_5_gate"`), mens `veto_gate._adaptive_threshold` kun
kaldes med de følelser `pushback._affective_pressure` kan producere
(irritation, unease, fatigue, protectiveness, hesitation). `r2_5_gate` er
ikke blandt dem. Tærsklen for `(edit_file, "r2_5_gate")` — 7 overrides,
målt i drift — bliver derfor beregnet og vist i summaries, men aldrig
brugt til at afvise noget. r2.5 træffer sin beslutning på
`_afvist_i_blokken`, ikke på tærsklen.

Så: kvitteringen gør `resolution`-feltet sandt (en adlydt blok står ikke
længere `pending`), men den lukker IKKE asymmetrien for den almindelige
veto-gate. Den har stadig ingen observerbar adlydelses-hændelse.

Disse tests binder de to moduler sammen OG fastholder den målte grænse.
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


def test_r2_5_kvitteringen_kalder_honored_stien(monkeypatch):
    """Bindeleddet: `_kvitter_adlydt` skal kalde `resolve_veto_event(..., "honored")`.

    3/11-2026 (tolvte lag): den første udgave af denne test læste kildekoden
    med en streng-søgning. Det er ikke en test af adfærd — den består så længe
    teksten står der, også hvis kaldet var gjort betinget af noget der aldrig
    er sandt. Her kaldes funktionen i stedet, med en fake-connection der giver
    præcis to `pending` blokke, og vi observerer hvilke event-ids der kvitteres.
    """
    from datetime import UTC, datetime

    from core.services import r2_5_haandhaevelse as r25

    kvitteret: list[tuple[str, str]] = []
    forespoergsler: list[tuple[str, tuple]] = []

    class _Result:
        def fetchall(self):
            return [("evt-a",), ("evt-b",)]

    class _Conn:
        def execute(self, sql, params=()):
            forespoergsler.append((sql, params))
            return _Result()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr("core.runtime.db_core.connect", lambda: _Conn())
    monkeypatch.setattr(
        "core.services.veto_gate.resolve_veto_event",
        lambda eid, res: kvitteret.append((eid, res)),
    )

    r25._kvitter_adlydt(datetime.now(UTC))

    assert kvitteret == [("evt-a", "honored"), ("evt-b", "honored")], (
        "r2.5-kvitteringen kaldte ikke honored-stien for hver pending blok — "
        f"så bliver rækkerne stående uafklaret: {kvitteret}"
    )
    # Den skal kun røre r2.5's EGEN nerve — ikke låne veto-gatens rækker.
    assert forespoergsler, "kvitteringen lavede ingen forespørgsel"
    assert r25.NERVE in forespoergsler[0][1], (
        f"kvitteringen filtrerede ikke på r2_5's nerve: {forespoergsler[0][1]}"
    )


def test_r2_5_foeler_ikke_som_pushback_og_taersklen_naas_derfor_ikke():
    """Den målte grænse: r2.5's honored-nøgle gates ikke af nogen beslutning.

    Målt 3/11-2026: `(edit_file, "r2_5_gate")` har 7 overrides, og
    `_adaptive_threshold` beregner en tærskel for den — men kaldes kun med de
    følelser `pushback._affective_pressure` kan producere. `r2_5_gate` er ikke
    en følelse; det er en nerve. Så tærsklen for det par bliver beregnet og vist
    i summaries, men aldrig brugt til at afvise noget.

    Testen fastholder den kendsgerning, så den ikke kan forsvinde stiltiende:
    bliver `r2_5_gate` koblet på beslutningsvejen, skal denne test opdateres med
    vilje — ikke ved et tilfælde.
    """
    from core.services import pushback

    class _S:
        def __init__(self, **kw):
            self.frustration = kw.get("frustration", 0.0)
            self.confidence = kw.get("confidence", 1.0)
            self.fatigue = kw.get("fatigue", 0.0)
            self.primary_mood = kw.get("mood", "")
            self.intensity = kw.get("intensity", 0.0)

    producerede = set()
    for snap in (
        _S(frustration=0.9),
        _S(confidence=0.2),
        _S(fatigue=0.9),
        _S(mood="distressed", intensity=0.8),
        _S(mood="melancholic", intensity=0.8),
    ):
        par = pushback._affective_pressure(snap)
        if par:
            producerede.add(par[0])

    assert producerede == {
        "irritation", "unease", "fatigue", "protectiveness", "hesitation"
    }, f"pushback producerer nu andre følelser end målt: {sorted(producerede)}"
    assert "r2_5_gate" not in producerede, (
        "r2_5_gate optræder nu som en pushback-følelse — så er nøglen måske "
        "koblet på beslutningsvejen; mål det og opdatér denne test"
    )
