# tests/test_notifikations_valg.py
from __future__ import annotations

import re
from pathlib import Path

_NAVN_TSX = (
    Path(__file__).resolve().parents[1]
    / "apps/jarvis-desk/src/components/settings/NotifikationsValg.tsx"
)


def _navn_noegler() -> set[str]:
    """Traekker noeglerne ud af `NAVN`-tabellen i NotifikationsValg.tsx.

    Kun en regex over det konkrete objekt-literal — ikke en fuld TS-parser —
    men formatet er snaevert (én `slags: 'Navn',` pr. linje), saa den maaler
    praecis det den skal, og fejler hoejt hvis nogen aendrer formen."""
    tekst = _NAVN_TSX.read_text(encoding="utf-8")
    m = re.search(r"const NAVN: Record<string, string> = \{(.*?)\n\}", tekst, re.DOTALL)
    assert m, "NAVN-tabellen blev ikke fundet i NotifikationsValg.tsx — har filen flyttet sig?"
    noegler = re.findall(r"^\s*(\w+):\s*'", m.group(1), re.MULTILINE)
    assert noegler, "NAVN-tabellen er tom eller regex'en matcher ikke laengere — se _navn_noegler()"
    return set(noegler)


def test_navn_og_standard_daekker_de_samme_slags() -> None:
    """`NAVN` (TS, brugerens ord for hver slags) og `STANDARD` (Python, feedens
    politik) skal daekke praecis de samme slags. Komponenten renderer via
    `Object.keys(NAVN)` filtreret til det serveren sendte — mangler en slags i
    NAVN, forsvinder den TAVST fra indstillingerne uden fejl eller indikation."""
    from core.services.notifikations_valg import STANDARD

    navn = _navn_noegler()
    standard = set(STANDARD.keys())
    assert navn == standard, (
        f"NAVN og STANDARD er skredet fra hinanden — kun i NAVN: {navn - standard or '—'}, "
        f"kun i STANDARD: {standard - navn or '—'}"
    )


def test_standard_er_tavs_undtagen_det_der_haster(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    assert v.kanal_for("bjorn", "approval") == "auto"
    assert v.kanal_for("bjorn", "question") == "auto"
    assert v.kanal_for("bjorn", "run_failed") == "auto"
    assert v.kanal_for("bjorn", "release") == "ingen"
    assert v.kanal_for("bjorn", "run_done") == "ingen"


def test_eget_valg_slaar_standarden(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    v.saet("bjorn", "release", "push")
    assert v.kanal_for("bjorn", "release") == "push"
    assert v.alle("bjorn")["release"] == "push"


def test_migreringen_baerer_de_fem_kolonner_over(isolated_runtime) -> None:
    """En halvvejs migreret base maa ikke tabe nogens valg."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder, briefing)"
            " VALUES (?,?,?,?)", ("bjorn", "auto", "mobile", "ingen"))
        conn.commit()

    assert v.migrer_kolonner() == 2
    assert v.kanal_for("bjorn", "reminder") == "mobile"
    assert v.kanal_for("bjorn", "briefing") == "ingen"


def test_migreringen_overskriver_ikke_et_nyere_valg(isolated_runtime) -> None:
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reminder)"
            " VALUES (?,?,?)", ("bjorn", "auto", "mobile"))
        conn.commit()
    v.saet("bjorn", "reminder", "ingen")
    v.migrer_kolonner()
    assert v.kanal_for("bjorn", "reminder") == "ingen"


# ── STANDARD er feedens politik, ikke systemets (task 5-rettelse) ──────────────
def test_kanal_for_ukendt_slags_falder_til_auto_ikke_ingen(isolated_runtime) -> None:
    """`STANDARD` daekker kun feedens elleve slags. `route_proactive_notification()`
    kaldes ogsaa med slags der aldrig hoerer til feeden — fx `membrane_breach`
    (kritisk sikkerhed) og `infra_security`. De maa IKKE stilles som «fravalgt»
    bare fordi de ikke staar i feedens tabel."""
    from core.services import notifikations_valg as v

    assert v.kanal_for("bjorn", "membrane_breach") == "auto"
    assert v.kanal_for("bjorn", "infra_security") == "auto"
    assert v.kanal_for("bjorn", "keymaker_key_earned") == "auto"


def test_membrane_breach_leveres_gennem_routeren(isolated_runtime, monkeypatch) -> None:
    """Beviser fejlen med den rigtige router, ikke en mock af routeren selv.
    Foer rettelsen returnerede `kanal_for()` "ingen" for `membrane_breach`, og
    routerens tidlige udgang stoppede leveringen af en sikkerhedsalarm uden at
    noget fejlede. Kun transportlaget (`_deliver_to_channel`) mockes her —
    soemmen hvor fejlen sad (kanal_for -> route_proactive_notification) er
    umocket."""
    import core.services.notification_router as nr

    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel",
                        lambda *a, **k: delivered.append(a) or True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    res = nr.route_proactive_notification(
        "bjorn", "membrane_breach", {"preview": "breach"}, importance="critical")

    assert res["channel"] != "fravalgt"
    assert res["delivered"] is True
    assert delivered  # transportlaget blev faktisk kaldt


def test_eksplicit_raekke_vinder_ogsaa_for_ukendt_slags(isolated_runtime) -> None:
    """En eksplicit raekke i notifikations_valg skal vinde over fald-tilbaget,
    ogsaa naar slags'en ikke er en af feedens elleve — nogen kan saette et
    eksplicit valg for en slags der ikke staar i STANDARD."""
    from core.services import notifikations_valg as v

    v.saet("bjorn", "central_flag", "push")
    assert v.kanal_for("bjorn", "central_flag") == "push"
