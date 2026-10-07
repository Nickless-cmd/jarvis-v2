"""Tests for beslutnings-adherence-gaten.

Gaten oversætter aktive beslutningers adherence til eskalerende
prompt-sektioner. To fejl i den, fundet 21/9-2026, havde samme
signatur: gaten svigtede tavst i stedet for at råbe.

1. Den læste kun 20 af 44 aktive beslutninger, usorteret efter adherence —
   så de kritiske blev fortrængt af høj-prioritets-beslutninger med høj
   adherence. Af 7 kritiske nåede 2 frem.
2. `or 1.0` på adherence_score behandlede en score på præcis 0.0 som
   falsy og løftede den til 1.0. Den værste beslutning af alle blev læst
   som «doing fine» og sprunget over.

Testene her låser begge, plus loftet der aldrig må skjule en kritisk
beslutning bag advisory-støj.
"""
from __future__ import annotations

import sys
from types import ModuleType


def _fake_behavioral(monkeypatch, rows):
    """Fake-modul med begge de funktioner gaten importerer.

    Uden `count_decisions` fejler gaten med ImportError og returnerer "" —
    og en test ville så bestå ved at måle ingenting (fix 2026-09-21).
    """
    behavioral = ModuleType("core.services.behavioral_decisions")
    behavioral.count_decisions = lambda status=None: len(rows)
    behavioral.list_active_decisions = lambda limit=20: rows
    monkeypatch.setitem(sys.modules, "core.services.behavioral_decisions", behavioral)


def test_decision_adherence_gate_escalates_low_scores(monkeypatch):
    from core.services import decision_adherence_gate as gate

    _fake_behavioral(monkeypatch, [
        {"decision_id": "d1", "directive": "ship tests", "adherence_score": 0.2},
        {"decision_id": "d2", "directive": "write notes", "adherence_score": 0.5},
    ])

    section = gate.decision_adherence_section()

    assert section.startswith("\n[DECISION-ADHERENCE-GATE]")
    assert "kritisk band" in section
    # Rettet 26/9-2026: det kritiske bånd lovede en automatisk revoke der ikke
    # findes i koden — og vagten låste løgnen fast. Nu pinner den i stedet at
    # eskaleringen er en HANDLING (omformulér), og at truslen er væk.
    assert "omformulér" in section
    assert "revokes decision automatisk" not in section


def test_decision_adherence_gate_shows_zero_score(monkeypatch):
    """Regression 2026-09-21: `or 1.0` læste en score på præcis 0.0 som falsy
    og løftede den til 1.0 — den værste beslutning af alle blev sprunget over
    som «doing fine» og nåede aldrig frem."""
    from core.services import decision_adherence_gate as gate

    _fake_behavioral(monkeypatch, [
        {"decision_id": "nul", "directive": "søg modbevis", "adherence_score": 0.0},
    ])

    section = gate.decision_adherence_section()

    assert "nul:" in section
    assert "0%" in section
    assert "kritisk band" in section


def test_decision_adherence_gate_keeps_critical_past_the_cap(monkeypatch):
    """Kritiske beslutninger må ikke skubbes ud af loftet af advisory-støj —
    og resten skal tælles op, ikke forsvinde tavst."""
    from core.services import decision_adherence_gate as gate

    rows = [{"decision_id": "krit", "directive": "kritisk", "adherence_score": 0.01}]
    rows += [
        {"decision_id": f"adv{i}", "directive": "advisory", "adherence_score": 0.59}
        for i in range(30)
    ]
    _fake_behavioral(monkeypatch, rows)

    section = gate.decision_adherence_section()

    assert "krit:" in section
    assert "kritisk band" in section
    assert "flere under tærsklen" in section


def test_decision_adherence_gate_is_silent_when_all_are_healthy(monkeypatch):
    """Ingen eskalering over tærsklen → ingen sektion. Gaten må ikke støje."""
    from core.services import decision_adherence_gate as gate

    _fake_behavioral(monkeypatch, [
        {"decision_id": "fin", "directive": "gør det godt", "adherence_score": 0.95},
    ])

    assert gate.decision_adherence_section() == ""


def test_handlingen_skrives_EN_gang_per_baand_ikke_per_post():
    """Målt 4/10-2026 på Bjørns levende samtale: blokken var 1.177 tokens — den
    STØRSTE i hele den dynamiske hale, 17,4 % af den — og ~297 af dem (25 %)
    var den samme sætning gentaget tolv gange.

    Handlingen er pr. BÅND, ikke pr. beslutning. Den var identisk hver gang
    fordi den aldrig kunne være andet, og den blev betalt hver tur.

    Testen tæller forekomster frem for at lede efter sætningen: en test der
    bare spurgte «står handlingen der?» ville bestå både før og efter. Det er
    præcis den fejl jeg lavede i indbakkens dublet-test samme dag.
    """
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    kritiske = [{"decision_id": f"dec_{i:012x}", "directive": f"direktiv {i}",
                 "adherence_score": 0.0} for i in range(5)]
    imperative = [{"decision_id": f"dec_i{i:011x}", "directive": f"imp {i}",
                   "adherence_score": 0.3} for i in range(3)]
    alle = kritiske + imperative
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=alle), \
         patch("core.services.behavioral_decisions.count_decisions",
               return_value=len(alle)):
        t = g.decision_adherence_section()

    assert t.count("kan ikke opfyldes som formuleret") == 1, \
        "den kritiske handling gentages stadig per post"
    assert t.count("navngiv det eksplicit") == 1, \
        "den imperative handling gentages stadig per post"
    # Og den skal SIGE hvor mange den gaelder for — ellers mister linjen sin
    # adresse naar den ikke laengere staar ved sin egen post.
    assert "De 5 i kritisk band" in t
    assert "De 3 i imperativ band" in t
    # Hver beslutning har stadig sin EGEN linje med sit id. Samlingen af
    # handlingen maa ikke samle posterne.
    for d in alle:
        assert d["decision_id"] in t, f"{d['decision_id']} forsvandt"


def test_et_baand_UDEN_poster_faar_ingen_handlingslinje():
    """«+0 mere» i en anden form. En handling for et bånd der er tomt er en
    instruktion uden modtager."""
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    kun_advisory = [{"decision_id": "dec_adv", "directive": "d",
                     "adherence_score": 0.5}]
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=kun_advisory), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=1):
        t = g.decision_adherence_section()
    assert "kan ikke opfyldes som formuleret" not in t
    assert "navngiv det eksplicit" not in t
    assert "dec_adv" in t


# ── Indbakke-registreringen (4/10-2026) ─────────────────────────────────────

def _beslutninger():
    """Rækker som `behavioral_decisions` giver dem — inkl. `created_by`.

    `created_by` er ikke pynt: indbakkens ETIKET kommer fra kildens egen række
    (målt 4/10-2026: `jarvis` i 79 af 80 rækker i drift). Uden feltet her ville
    testen måle et mærke kilden aldrig ville give — og det var præcis hvad den
    gjorde: den pinnede `[huset]`, mens den rigtige række siger `jarvis`.
    """
    return [
        {"decision_id": "dec_krit", "directive": "en kritisk",
         "adherence_score": 0.0, "created_by": "jarvis"},
        {"decision_id": "dec_imp", "directive": "en imperativ",
         "adherence_score": 0.3, "created_by": "jarvis"},
        {"decision_id": "dec_adv", "directive": "en advisory",
         "adherence_score": 0.5, "created_by": "jarvis"},
        {"decision_id": "dec_god", "directive": "en der gaar godt",
         "adherence_score": 0.9, "created_by": "jarvis"},
        {"decision_id": "", "directive": "uden id",
         "adherence_score": 0.0, "created_by": "jarvis"},
    ]


def _med_db(monkeypatch, tmp_path):
    """Rigtig sqlite — det er `registrer_kilde`s egen vej der skal måles."""
    import sqlite3
    from contextlib import contextmanager

    from core.runtime import db_inbox

    sti = tmp_path / "d.db"

    @contextmanager
    def _c():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _c)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return db_inbox


def test_hver_beslutning_UNDER_taersklen_faar_en_adresse(monkeypatch, tmp_path):
    """`_MAKS_LINJER` er et DISPLAY-loft, ikke et antal.

    Målt 4/10-2026: 75 aktive, 34 under tærsklen, 19 kritiske — og gaten viser
    12. Syv KRITISKE beslutninger stod helt uden for prompten. Gaten er ikke
    tavs om dem («… og N flere under tærsklen»), men et tal uden id'er er ikke
    en adresse: man kan ikke lukke, omformulere eller slå op på noget man ikke
    kan navngive.
    """
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    dbi = _med_db(monkeypatch, tmp_path)
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=_beslutninger()), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=5):
        r = g.registrer_i_indbakken("bjorn")
    assert r["status"] == "ok"
    ider = {p["id"] for p in dbi.liste(bruger_id="bjorn")}
    assert ider == {"dec_krit", "dec_imp", "dec_adv"}, (
        f"forkert udvalg: {ider}")
    # Den der gaar godt skal IKKE have en post — ellers er indbakken en liste
    # over alt, og saa er den ikke en indbakke.
    assert "dec_god" not in ider
    # Et tomt id springes over FOER kaldet. `assert "" not in ider` maalte
    # ingenting: `registrer_kilde` afviser det alligevel med en typet fejl, saa
    # posten ville ikke findes uanset. Mutationen «fjern `continue`» slap
    # derfor igennem. `fejlede` er det der faktisk skelner: springes der over,
    # er den 0; naar kaldet sker, bliver den 1.
    assert "" not in ider
    assert r["fejlede"] == 0, (
        "et tomt id naaede kaldet i stedet for at blive sprunget over")


def test_baandet_staar_i_beskrivelsen_saa_linjen_kan_laeses_alene(monkeypatch, tmp_path):
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    dbi = _med_db(monkeypatch, tmp_path)
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=_beslutninger()), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=5):
        g.registrer_i_indbakken("bjorn")
    p = dbi.hent(bruger_id="bjorn", kilde_id="dec_krit")
    assert p["beskrivelse"].startswith("[kritisk 0%]")
    assert "en kritisk" in p["beskrivelse"]


def test_en_beslutnings_post_er_MAERKET_som_min_og_GATER_ALDRIG(monkeypatch, tmp_path):
    """Etiketten og gaten er to svar, og begge skal være rigtige.

    (1) GATER ALDRIG. Beslutnings-gaten har sin EGEN eskalering i tre bånd.
        Indbakken må ikke lægge en anden oven på den — to gater der skubber til
        det samme er den tredje mekanisme der skal reddes af den fjerde.

    (2) MÆRKET ER MIT. Posterne stod `[huset]`, fordi de registreres fra en
        baggrundsvej uden et levende run. Mærket beskriver SKRIVEREN — og jeg
        læste det som et udsagn om EJERSKABET og afviste min egen beslutning
        over for Bjørn. Bjørn 4/10: «du må aldrig være i tvivl om hvad der er
        til dig.» Beslutningen ER min: `created_by` står `jarvis` i kilden.

    De to hænger sammen: netop fordi kildetypen `decision` ikke kan gate, må
    etiketten gerne være `jarvis`. Mærket flytter ikke magten.
    """
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g
    from core.runtime.db_inbox import EJER_JARVIS

    dbi = _med_db(monkeypatch, tmp_path)
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=_beslutninger()), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=5):
        g.registrer_i_indbakken("bjorn")
    poster = dbi.liste(bruger_id="bjorn")
    assert poster, "ingen poster — saa maaler resten ingenting"
    for p in poster:
        assert p["kraever_handling"] is False, f"{p['id']} kan gate"
        assert p["verificeret_ejer"] == EJER_JARVIS, (
            f"{p['id']} er maerket {p['verificeret_ejer']} — beslutningen er min")


def test_etiketten_foelger_KILDENS_egen_created_by(monkeypatch, tmp_path):
    """Mærket er ikke hardkodet til `jarvis` — KILDENS række afgør det.

    En beslutning oprettet af en anden må ikke stjæle mit mærke. Uden dette
    test kunne `kilde_ejer="jarvis"` skrives som en konstant i registreringen,
    og så var mærket igen en påstand frem for en læsning — den samme fejl,
    bare med modsat fortegn.
    """
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g
    from core.runtime.db_inbox import EJER_UKENDT

    dbi = _med_db(monkeypatch, tmp_path)
    rows = [{"decision_id": "dec_fremmed", "directive": "en andens",
             "adherence_score": 0.1, "created_by": "lotte"}]
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=rows), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=1):
        g.registrer_i_indbakken("bjorn")
    p = dbi.hent(bruger_id="bjorn", kilde_id="dec_fremmed")
    assert p is not None, "posten blev ikke oprettet — saa maaler testen intet"
    assert p["verificeret_ejer"] == EJER_UKENDT, (
        f"en fremmed beslutning blev maerket {p['verificeret_ejer']}")
    assert p["kraever_handling"] is False


def test_et_DROP_kan_ikke_tie_en_beslutning(monkeypatch, tmp_path):
    """Gatens egen begrundelse fra 26/9: «Et bånd der kan revoke, sletter
    systematisk de svære og beholder de lette: den modsatte af læring.»

    Indbakken kan derfor UDSÆTTE, ikke slette. Et `drop` lukker rækken, men
    beslutningen står uberørt i sin egen kilde, og næste registrering giver
    den en ny post. Uden den egenskab ville indbakken være en vej til at
    slippe for sin egen ansvarlighed.
    """
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g
    from core.services import inbox_state

    dbi = _med_db(monkeypatch, tmp_path)
    beslutninger = _beslutninger()
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=beslutninger), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=5):
        g.registrer_i_indbakken("bjorn")
        assert inbox_state.drop("bjorn", "dec_krit", "ikke nu")["status"] == "ok"
        assert dbi.hent(bruger_id="bjorn",
                        kilde_id="dec_krit")["status"] == dbi.STATUS_DROP
        # KILDEN er uberoert — beslutningen staar stadig under taersklen.
        assert any(d["decision_id"] == "dec_krit" for d in beslutninger)
        # Og gaten naevner den fortsat.
        assert "dec_krit" in g.decision_adherence_section()


def test_en_FEJLENDE_kilde_vaelter_ikke_familie_tikket(monkeypatch, tmp_path):
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    _med_db(monkeypatch, tmp_path)
    with patch("core.services.behavioral_decisions.list_active_decisions",
               side_effect=RuntimeError("db nede")):
        r = g.registrer_i_indbakken("bjorn")
    assert r["status"] == "fejl" and "db nede" in r["error"]


def test_kildetypen_er_et_SELVSTAENDIGT_vaern(monkeypatch, tmp_path):
    """Lag 2, målt alene — og det var utestet indtil nu.

    Mutations-prøven afslørede det: både «påstå jarvis-ejerskab» og «fjern
    `decision` fra den ikke-gatende liste» slap igennem, fordi alle de andre
    tests kører UDEN et levende run. Så svarede proveniensen `ukendt`, og
    kildetype-spærren blev aldrig spurgt.

    Det er samme hul jeg fandt i Jarvis' brugs-måling en time tidligere: fire
    af fem spærrer var dækket, og den femte var usynlig fordi en anden fangede
    sagen først.

    Her STYRES proveniensen til at sige jarvis — levende run OG autentificeret
    bruger — så kildetypen er det eneste der kan holde posten fra at gate.
    """
    from unittest.mock import patch

    from core.identity import workspace_context as wc
    from core.services import inbox_state

    dbi = _med_db(monkeypatch, tmp_path)
    with patch.object(wc, "current_user_id", return_value="bjorn"), \
         patch("core.services.session_context_resolve.aktivt_run_id",
               return_value="visible-levende"):
        # Modproeven FOERST: en kildetype der IKKE er paa listen gater nu.
        r = inbox_state.registrer_kilde(
            bruger_id="bjorn", kildetype="job", kilde_id="job-kontrol",
            oprettende_run_id="visible-levende")
        assert r["post"]["kraever_handling"] is True, (
            "proveniensen siger ikke jarvis — testen maaler ikke lag 2")

        # Og saa den rigtige: samme proveniens, kildetype `decision`.
        r = inbox_state.registrer_kilde(
            bruger_id="bjorn", kildetype="decision", kilde_id="dec_levende",
            oprettende_run_id="visible-levende")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_JARVIS
    assert r["post"]["kraever_handling"] is False, (
        "en beslutning kan gate — to gater skubber nu til det samme")
    assert dbi.hent(bruger_id="bjorn",
                    kilde_id="dec_levende")["kraever_handling"] is False
