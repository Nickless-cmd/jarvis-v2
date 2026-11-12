"""Test: maven måles mod en KONSTANT baseline, ikke kun mod sin egen hit-rate.

Hvorfor (12/11-2026): fladen viste `Calibration: 0.99 (4489/4523 correct)` og blev læst
som «maven har ret i 99% af tilfældene». Målt mod de faktiske events var maven 92,77%
korrekt, mens en konstant «proceed» ville være 99,71% — altså 6,94 procentpoint
DÅRLIGHERE, fordi runs lykkes 99,7% af tiden og enhver advarsel derfor næsten altid er
forkert.

Reglen testene værner om: en hit-rate uden baseline kan ikke skelne «mekanismen er
dygtig» fra «systemet fejler næsten aldrig». Er mekanismen ikke bedre end konstanten,
skal fladen sige det — ikke skjule det bag et højt tal.
"""
from __future__ import annotations

import json

import pytest

from core.services import gut_engine as ge


@pytest.fixture(autouse=True)
def _nulstil_cache():
    """_BASELINE_CACHE er modul-global — uden nulstilling lækker state mellem tests."""
    ge._BASELINE_CACHE["at"] = 0.0
    ge._BASELINE_CACHE["value"] = None
    yield
    ge._BASELINE_CACHE["at"] = 0.0
    ge._BASELINE_CACHE["value"] = None


def _events(par: list[tuple[str, str]]):
    """Byg fake event-rækker som dem `_observed_baseline` læser (payload_json,)."""
    return [(json.dumps({"hunch": h, "actual": a}),) for h, a in par]


def _patch_db(monkeypatch, par: list[tuple[str, str]]):
    rows = _events(par)

    class _Conn:
        def execute(self, *_a, **_k):
            return self

        def fetchall(self):
            return rows

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr("core.runtime.db.connect", lambda: _Conn(), raising=False)


def test_altid_proceed_paa_altid_succes_giver_nul_udbytte(monkeypatch):
    """Maven siger «proceed» og alt lykkes: korrekt, men udbyttet over baseline er 0."""
    _patch_db(monkeypatch, [("proceed", "completed")] * 10)
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 10
    assert b["maven_pct"] == 100.0
    assert b["baseline_pct"] == 100.0
    assert b["skill_pp"] == 0.0


def test_advarsel_om_succes_er_negativt_udbytte(monkeypatch):
    """DEN MÅLTE FEJLFORM: maven advarer, men runnet lykkes alligevel.

    Baseline (altid proceed) rammer alt; maven taber hver advarsel. Det er præcis
    situationen i produktion den 12/11-2026 (25 af 26 caution-runs lykkedes).
    """
    par = [("proceed", "completed")] * 8 + [("caution", "completed")] * 2
    _patch_db(monkeypatch, par)
    b = ge._observed_baseline()
    assert b is not None
    assert b["maven_pct"] == 80.0        # 8 korrekte af 10
    assert b["baseline_pct"] == 100.0    # alt lykkedes
    assert b["skill_pp"] == -20.0
    assert b["skill_pp"] < 0


def test_advarsel_om_fejl_er_positivt_udbytte(monkeypatch):
    """Bevis for at målingen KAN give overskud: en advarsel der rammer er en gevinst."""
    par = [("proceed", "completed")] * 5 + [("caution", "error")] * 5
    _patch_db(monkeypatch, par)
    b = ge._observed_baseline()
    assert b is not None
    assert b["maven_pct"] == 100.0
    assert b["baseline_pct"] == 50.0     # konstant proceed rammer kun halvdelen
    assert b["skill_pp"] == 50.0
    assert b["skill_pp"] > 0


def test_ukendt_hunch_tælles_ikke(monkeypatch):
    """Kun proceed/caution har en defineret forudsigelse — andre må ikke fortynde tallet."""
    _patch_db(monkeypatch, [("proceed", "completed"), ("tom", "completed")])
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 1


def test_beskadiget_payload_springes_over(monkeypatch):
    """Én ødelagt række må ikke skjule de andre eller kaste."""
    class _Conn:
        def execute(self, *_a, **_k):
            return self

        def fetchall(self):
            return [("{ikke json",), (json.dumps({"hunch": "proceed", "actual": "completed"}),)]

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr("core.runtime.db.connect", lambda: _Conn(), raising=False)
    b = ge._observed_baseline()
    assert b is not None
    assert b["n_observed"] == 1


def test_uden_db_giver_none_ikke_crash(monkeypatch):
    """Uden DB skal fladen stadig kunne vises — men sige at baseline er utilgængelig."""
    def _boom():
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", _boom, raising=False)
    assert ge._observed_baseline() is None


def test_summary_viser_baseline_og_dommen(monkeypatch):
    """Summary'en skal bære dommen — et højt hit-tal alene må ikke kunne læses som dygtighed."""
    par = [("proceed", "completed")] * 8 + [("caution", "completed")] * 2
    _patch_db(monkeypatch, par)
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 10, "calibrated_hits": 9,
                 "calibration_score": 0.9, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["baseline"] is not None
    assert s["baseline"]["skill_pp"] == -20.0
    assert "DAARLIGERE" in s["summary"]
    assert "baseline" in s["summary"]


def test_summary_siger_utilgaengelig_uden_baseline(monkeypatch):
    """Mangler baseline, skal fladen advare om at hit-raten ikke kan læses som dygtighed."""
    monkeypatch.setattr(ge, "_observed_baseline", lambda: None)
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 10, "calibrated_hits": 9,
                 "calibration_score": 0.9, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["baseline"] is None
    assert "IKKE" in s["summary"]


_MODEN_LEDGER = {"events": 500, "started_at": "2026-01-01T00:00:00+00:00"}


def _gut_state(total: int, hits: int) -> dict[str, object]:
    return {"total_predictions": total, "calibrated_hits": hits,
            "calibration_score": hits / max(total, 1), "last_hunch": "proceed → completed (✓)"}


def test_uden_livstidstaeller_siges_tallet_ikke(monkeypatch):
    """Uden en tæller med SAMME definition som eventloggen kan antallet af ryddede
    rækker ikke måles. Fladen må da sige det — ikke beregne `total - events`, som
    blander to definitioner (se testen nedenfor).

    Produktion målte 4527 akkumulerede mod 343 event-rækker. Den gamle formel kaldte
    differencen «4184 ligger foer vinduet». Det tal var ikke målt — det var en rest.
    """
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: None)
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 10, "event_rows": 11, "neutral_rows": 1,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(100, 99))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["evaluated"] == 100
    assert s["evaluated_verified"] == 10
    assert s["no_event_row"] is None, "et tal der ikke kan maales maa ikke se maalt ud"
    assert s["evaluated_unverifiable"] is None
    assert "kan ikke maales" in s["summary"]
    assert "kan efterproeves" in s["summary"]


def test_ung_ledger_maa_ikke_udtale_sig(monkeypatch):
    """En tæller der er yngre end retentionen kan ikke bruges: en række kan være
    ryddet FØR den begyndte at tælle, og så ville differencen underdrive antallet.
    """
    from datetime import UTC, datetime, timedelta

    ung = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: {"events": 50, "started_at": ung})
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 10, "event_rows": 11, "neutral_rows": 1,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(100, 99))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["no_event_row"] is None
    assert s["no_event_row_er_estimat"] is None, (
        "der findes INTET tal — flaget må ikke sige «ikke et estimat», for det "
        "læses som «præcis måling»"
    )
    assert "yngre end" in s["summary"]


def test_ingen_tal_tre_tilstande_ikke_to(monkeypatch):
    """TREDJE LAG (12/11-2026): de grene hvor tallet ikke KAN beregnes.

    Der er tre af dem — ingen livstidstæller, en tæller yngre end retentionen, og
    en dead-letter der ikke kan læses. Alle tre lod `no_event_row_er_estimat` stå
    på sin initialværdi `False`, og `False` læses som «dette er en præcis måling»
    — mens der slet ikke findes en måling. Målt i drift: fladen svarede
    `no_event_row: None` sammen med `no_event_row_er_estimat: False`.

    Flaget har derfor tre tilstande: `True` = der er et tal, men det er et
    estimat; `None` = der er intet tal; `False` bruges ikke længere.
    """
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(600, 500))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 10, "event_rows": 11, "neutral_rows": 1,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )

    # Gren 1: ingen livstidstæller.
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: None)
    s = ge.build_gut_surface()
    assert s["no_event_row"] is None
    assert s["no_event_row_er_estimat"] is None, "ingen tæller ⇒ intet tal"

    # Gren 3: tælleren er moden, men dead-letter kan ikke læses.
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: dict(_MODEN_LEDGER))
    monkeypatch.setattr(ge, "_dead_letter_gut_events", lambda: None)
    s = ge.build_gut_surface()
    assert s["no_event_row"] is None
    assert s["no_event_row_er_estimat"] is None, "ulæselig dead-letter ⇒ intet tal"


def test_moden_ledger_giver_et_rigtigt_tal(monkeypatch):
    """Er tælleren moden, må differencen bruges: livstidsevents minus events i
    vinduet = antal ryddede rækker. Det er den eneste formel hvor begge sider
    tæller den samme slags ting."""
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: dict(_MODEN_LEDGER))
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 99, "event_rows": 100, "neutral_rows": 1,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(600, 500))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["no_event_row"] == 400
    assert s["evaluated_unverifiable"] == 400
    assert "400 udfalds-events er ryddet" in s["summary"]


def test_tom_lokal_koe_goer_ikke_tallet_praecist(monkeypatch):
    """BJØRNS FJERDE INVENDING (12/11-2026): fladen læser sin EGEN proces' kø.

    jarvis-api og jarvis-runtime har hver sin EventBus med hver sin writer-kø
    (`core/eventbus/krydsproces.py`). Udfaldene registreres via run_closure_gate i
    RUNTIME-processen, men `/mc/gut` svarer fra API-processen — så
    `pending_count()` er per konstruktion 0 for netop de events regnskabet handler
    om.

    Testen giver den mest gunstige mulige situation: moden tæller OG tom lokal kø.
    Alligevel må tallet ikke erklæres præcist, for der findes intet globalt
    afgjort-punkt. Den gamle regel satte kun flaget når `i_flugt > 0`, så den ville
    svare False her — og dermed påstå en præcision den ikke kan se.
    """
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: dict(_MODEN_LEDGER))
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 99, "event_rows": 100, "neutral_rows": 1,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(600, 500))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})

    # Patch METODEN paa det aegte objekt — ikke singletonen. `from ... import
    # event_bus` inde i funktionen binder en kopi, saa en attr-stub paa `ge` rammer
    # intet (maalt: testen fejlede paa sin egen opstilling, ikke paa koden). Og
    # singletonen maa ikke udskiftes — se test_event_bus_singleton_maa_ikke_udskiftes.
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.pending_count", lambda: 0, raising=False
    )

    s = ge.build_gut_surface()
    assert s["no_event_row"] == 400, "tallet beregnes fortsat"
    assert s["no_event_row_er_estimat"] is True, (
        "en tom LOKAL kø er ikke bevis for at den anden proces har afgjort sine events"
    )
    assert "EGEN proces" in (s["no_event_row_grund"] or ""), (
        "grunden skal navngive at målingen kun dækker denne proces"
    )


def test_neutral_event_aendrer_ikke_antallet_af_ryddede(monkeypatch):
    """BJØRNS ANDEN INVENDING (12/11-2026), den afgørende test.

    `record_gut_outcome` returnerer FØR `update_cognitive_gut_state` når udfaldet er
    neutralt — så `total_predictions` tæller kun afgjorte udfald, mens eventloggen
    tæller alle. Differencen `total - event_rows` er derfor ikke et antal ryddede
    rækker: kommer der én ny NEUTRAL hændelse, stiger `event_rows` uden at `total`
    gør, og differencen FALDER med én — selvom ingen række er kommet tilbage.

    Testen tilføjer netop den hændelse og kræver at tallet står STILLE. Den gamle
    formel fejler her; det er hele pointen.
    """
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(500, 450))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})

    monkeypatch.setattr(ge, "_event_ledger_state", lambda: {"events": 100, "started_at": _MODEN_LEDGER["started_at"]})
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 9, "event_rows": 10, "neutral_rows": 1,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    foer = ge.build_gut_surface()

    # Én ny NEUTRAL hændelse: loggen og tælleren stiger begge med én.
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: {"events": 101, "started_at": _MODEN_LEDGER["started_at"]})
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 9, "event_rows": 11, "neutral_rows": 2,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    efter = ge.build_gut_surface()

    assert efter["neutral_rows"] == foer["neutral_rows"] + 1
    assert efter["evaluated"] == foer["evaluated"], "neutral opdaterer ikke total_predictions"
    assert efter["no_event_row"] == foer["no_event_row"], (
        "en ny NEUTRAL hændelse må ikke se ud som om en ryddet række kom tilbage"
    )


def test_neutral_udfald_taelles_ogsaa_i_livstidstaelleren(monkeypatch):
    """Tælleren skal have SAMME definition som eventloggen — også for neutrale udfald.

    Ellers arver den præcis den skævhed den skulle rette: `total_predictions` tæller
    kun afgjorte udfald (record_gut_outcome returnerer før opdateringen ved neutral),
    og så er differencen igen ubrugelig. Tælleren skal stige ved BEGGE klasser.
    """
    from contextlib import nullcontext

    from core.runtime import state_store

    store: dict[str, object] = {}
    monkeypatch.setattr(state_store, "load_json", lambda name, default: store.get(name, default))
    monkeypatch.setattr(state_store, "save_json", lambda name, data: store.__setitem__(name, data))
    monkeypatch.setattr(state_store, "med_laas", lambda name: nullcontext())
    monkeypatch.setattr(ge, "update_cognitive_gut_state", lambda **kw: {"updated_at": "x"})
    monkeypatch.setattr(ge.event_bus, "publish", lambda *a, **k: None)

    ge.record_gut_outcome(hunch="proceed", actual_outcome="interrupted")  # neutral
    efter_neutral = store[ge._EVENT_LEDGER_KEY]["events"]
    ge.record_gut_outcome(hunch="proceed", actual_outcome="completed")  # afgjort
    efter_afgjort = store[ge._EVENT_LEDGER_KEY]["events"]

    assert efter_neutral == 1, "et NEUTRALT udfald er stadig en udfaldshændelse i loggen"
    assert efter_afgjort == 2


def test_ingen_advarsel_naar_alt_er_verificerbart(monkeypatch):
    """Er intet ryddet, skal linjen ikke stå der. En advarsel der altid vises,
    læres der at overse — samme regel som alderslinjen."""
    monkeypatch.setattr(ge, "_event_ledger_state", lambda: {"events": 10, "started_at": _MODEN_LEDGER["started_at"]})
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 10, "event_rows": 10, "neutral_rows": 0,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(ge, "get_cognitive_gut_state", lambda: _gut_state(10, 9))
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["no_event_row"] == 0
    assert s["evaluated_unverifiable"] == 0
    assert "ryddet" not in s["summary"]
    assert "kan ikke maales" not in s["summary"]


def test_historisk_skaevhed_navngives_ikke_kun_alder(monkeypatch):
    """DEN ANDEN FEJL I DE HISTORISKE TAL (12/11-2026, Bjørns indvending).

    De akkumulerede tællere er ikke bare GAMLE — de er SKÆVE. Før den fælles
    udfaldsmodel blev `caution → interrupted` talt som en korrekt forudsigelse, fordi
    alt andet end completed/success var fiasko. Retningen er kendt; størrelsen kan ikke
    måles, fordi events ryddes efter 14 dage.

    Fladen må ikke kun sige «92% ligger før vinduet» og lade læseren tro at resten er
    et rent udsnit. Skævheden skal navngives som skævhed.
    """
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 10, "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 100, "calibrated_hits": 99,
                 "calibration_score": 0.99, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["historical_bias"], "skaevheden skal vaere et felt, ikke kun prosa"
    assert "caution" in s["historical_bias"]
    assert "kan ikke" in s["historical_bias"] or "kan ikke maales" in s["historical_bias"]
    assert "SKAEVE" in s["summary"]


def test_ingen_skaevhedsnote_naar_alt_er_verificerbart(monkeypatch):
    """Er der intet uverificerbart, findes der ingen historisk skævhed at navngive.

    En advarsel der altid vises, læres der at overse — samme regel som alderslinjen.
    """
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 10, "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 10, "calibrated_hits": 9,
                 "calibration_score": 0.9, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    s = ge.build_gut_surface()
    assert s["historical_bias"] is None
    assert "SKAEVE" not in s["summary"]


def test_droppet_event_taelles_ikke_som_ryddet(monkeypatch):
    """Et event der blev talt men aldrig afleveret er TAB, ikke retention.

    Bjørns tredje indvending (12/11-2026): livstidstælleren ligger i en JSON-fil,
    hændelsen går gennem eventbussens asynkrone kø. `publish` dropper TAVST ved
    fuld kø. Uden denne skelnen ville et tabt event se ud som en ryddet række —
    og `max(0, …)` ville skjule den modsatte retning.
    """
    monkeypatch.setattr(
        ge, "_observed_baseline",
        lambda: {"n_observed": 8, "event_rows": 8, "neutral_rows": 0,
                 "maven_pct": 90.0, "baseline_pct": 100.0, "skill_pp": -10.0},
    )
    monkeypatch.setattr(
        ge, "get_cognitive_gut_state",
        lambda: {"total_predictions": 10, "calibrated_hits": 9,
                 "calibration_score": 0.9, "last_hunch": "proceed → completed (✓)"},
    )
    monkeypatch.setattr("core.services.gate_verdict_ledger.summary", lambda: {})
    # Tælleren er moden, men to af dens events blev aldrig afleveret.
    monkeypatch.setattr(
        ge, "_event_ledger_state",
        lambda: {"events": 10, "started_at": "2026-01-01T00:00:00+00:00",
                 "unconfirmed": 2},
    )
    s = ge.build_gut_surface()
    assert s["no_event_row"] == 0, (
        "10 talt - 2 aldrig afleveret - 8 i vinduet = 0 ryddede; "
        "de to er tab, ikke retention"
    )
    assert "fuld koe" in (s["no_event_row_grund"] or "")


def test_taelleren_bekraeftes_efter_publish(monkeypatch):
    """Rækkefølgen: publish FØRST, tæller bagefter — ellers kan et drop ikke ses.

    Blev tælleren bumpet før publish, stod et droppet event som registreret, og
    differencen målte forskellen mellem to mekanismer i stedet for ryddede rækker.
    """
    kald: list[str] = []

    def _fake_publish(kind, payload=None, **kw):
        kald.append("publish")
        return 4711  # accepteret i køen

    # Lap METODEN på det ægte objekt — ikke singletonen (se
    # tests/test_event_bus_singleton_maa_ikke_udskiftes.py).
    monkeypatch.setattr(ge.event_bus, "publish", _fake_publish, raising=False)
    monkeypatch.setattr(ge, "_bump_event_ledger", lambda **kw: kald.append(
        f"bump:{kw.get('confirmed', True)}"
    ))
    monkeypatch.setattr(ge, "update_cognitive_gut_state", lambda **kw: {"ok": True})
    ge.record_gut_outcome(hunch="proceed", actual_outcome="completed")
    assert kald == ["publish", "bump:True"], f"forkert raekkefoelge: {kald}"


def test_droppet_publish_giver_ubekraeftet_taelling(monkeypatch):
    """Fuld kø: publish gør intet, køen vokser ikke — så skal tælleren være uafklaret."""
    kald: list[bool] = []

    def _fake_publish(kind, payload=None, **kw):
        return None  # droppet, som bussen gør det

    monkeypatch.setattr(ge.event_bus, "publish", _fake_publish, raising=False)
    monkeypatch.setattr(ge, "_bump_event_ledger", lambda **kw: kald.append(
        kw.get("confirmed", True)
    ))
    monkeypatch.setattr(ge, "update_cognitive_gut_state", lambda **kw: {"ok": True})
    ge.record_gut_outcome(hunch="proceed", actual_outcome="completed")
    assert kald == [False], "et droppet event maa ikke taelles som bekræftet"


def test_koe_stoerrelse_kan_ikke_afgoere_et_events_skæbne(monkeypatch):
    """Bjørns race (12/11-2026): writer-tråden dræner køen SAMTIDIG.

    Kø-størrelse kan derfor svare forkert i begge retninger. Testen fastlåser at
    svaret kommer fra bussens kvittering — ikke fra køen:

    A: eventet blev ACCEPTERET, men køen faldt igen (writer hentede det)
       → skal være bekræftet. En kø-måling ville have sagt «droppet».
    B: eventet blev DROPPET, men en anden producent fyldte køen
       → skal være ubekræftet. En kø-måling ville have sagt «afleveret».
    """
    svar: list[bool] = []

    class _Koe:
        def __init__(self, n: int) -> None:
            self.n = n

        def qsize(self) -> int:
            return self.n

    # A: accepteret, men køen skrumpede fordi writer-tråden hentede eventet.
    koe_a = _Koe(5)

    def _fake_a(kind, payload=None, **kw):
        koe_a.n = 0  # writer draenede koeen
        return 99

    monkeypatch.setattr(ge.event_bus, "publish", _fake_a, raising=False)
    monkeypatch.setattr(ge.event_bus, "_writer_queue", koe_a, raising=False)
    monkeypatch.setattr(ge, "_bump_event_ledger", lambda **kw: svar.append(
        kw.get("confirmed", True)
    ))
    monkeypatch.setattr(ge, "update_cognitive_gut_state", lambda **kw: {"ok": True})
    ge.record_gut_outcome(hunch="proceed", actual_outcome="completed")
    assert svar == [True], (
        "et accepteret event maa ikke se droppet ud fordi writer-traaden toemte koeen"
    )

    # B: droppet, men køen voksede fordi en ANDEN producent skrev i den.
    svar.clear()
    koe_b = _Koe(5)

    def _fake_b(kind, payload=None, **kw):
        koe_b.n = 9  # en anden producents event
        return None  # mit eget blev droppet

    monkeypatch.setattr(ge.event_bus, "publish", _fake_b, raising=False)
    monkeypatch.setattr(ge.event_bus, "_writer_queue", koe_b, raising=False)
    ge.record_gut_outcome(hunch="proceed", actual_outcome="completed")
    assert svar == [False], (
        "et droppet event maa ikke se afleveret ud fordi en anden fyldte koeen"
    )


def test_aegte_bus_kvitterer_accept_og_drop():
    """Mod den ÆGTE bus, ikke en stub: accept giver eventets seq, fuld kø giver None.

    Uden denne test ville kontrakten kun være bevist mod stubbe, og en fremtidig
    ændring i bussen kunne fjerne returværdien uden at nogen test faldt — samme
    fælde som da testene stubbede den regel de skulle teste.
    """
    import queue as _q
    import threading

    from core.eventbus.bus import EventBus

    b = EventBus.__new__(EventBus)  # uden __init__: ingen writer-traad, ingen DB
    b._seq_lock = threading.Lock()
    b._publish_seq = 0
    b._write_seq = 0
    b._pending = 0
    b._writer_queue = _q.Queue(maxsize=1)

    seq = b.publish("cognitive_gut.accepted")
    assert seq == 1, f"accept skal give eventets seq, fik {seq!r}"
    assert b.pending_count() == 1, (
        "et accepteret event er UAFGJORT indtil writer-traaden har behandlet det"
    )

    # Det første event fyldte køen (maxsize=1) — næste publish må derfor droppes.
    assert b.publish("cognitive_gut.dropped") is None, "fuld koe skal give None"

    # REGRESSION (Bjørn, 12/11-2026): drop-grenen satte `_write_seq` til det
    # droppede seq, så flush() kunne returnere mens de forudgående events stadig
    # lå i køen. Med 1 accepteret + 1 droppet ville write_seq vaere 2 — altså
    # "alt skrevet" — selvom intet var skrevet. Den maa ikke rykke frem.
    assert b._write_seq == 0, (
        "et droppet event maa ikke rykke write_seq frem over de events der stadig "
        "ligger i koeen"
    )
    assert b.pending_count() == 1, (
        "et droppet event blev aldrig accepteret og maa ikke efterlade en uafgjort post"
    )
