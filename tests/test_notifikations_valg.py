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


def test_standard_slags_findes_alle_i_navn() -> None:
    """`NAVN` (TS, brugerens ord for hver slags) skal daekke MINDST de slags
    `STANDARD` (Python, feedens politik) har en mening om. Komponenten
    renderer via `Object.keys(NAVN)` filtreret til det serveren sendte —
    mangler en slags i NAVN som STANDARD styrer, forsvinder den TAVST fra
    indstillingerne uden fejl eller indikation.

    Omvendt (K4, 2026-09-22): NAVN maa gerne vise FLERE toggles end STANDARD
    har en default for — `briefing`, `reminder`, `reach_out`, `initiative`
    staar i NAVN, men er bevidst IKKE i STANDARD, fordi `reach_out` allerede
    er et andet, eksisterende systems `notification_type` (proactivity_bridge
    m.fl.), og at give feedens tavse standard forrang derovre slukkede for det
    system. De falder til routerens egen "auto" i stedet, se
    `test_de_fire_navne_staar_ikke_i_standard`."""
    from core.services.notifikations_valg import STANDARD

    navn = _navn_noegler()
    standard = set(STANDARD.keys())
    assert standard <= navn, (
        f"STANDARD styrer slags NAVN slet ikke kender — de ville aldrig kunne "
        f"aendres fra klienten: {standard - navn}"
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


# ── K4 (2026-09-22): STANDARD slukkede for et EKSISTERENDE proaktivt system ────
# `briefing`, `reminder`, `reach_out` og `initiative` er IKKE kun feedens egne
# ord — `reach_out` bruges allerede som `notification_type` af
# proactivity_bridge.py, autonomous_outreach_daemon.py, action_router.py og
# central_moltbook.py (via broen), som intet har med notifikations-feeden at
# goere. Da de fire stod i STANDARD med "ingen", stoppede kanal_for() dem ALLE
# tavst — ogsaa dem der aldrig var feedens at styre. De er derfor fjernet fra
# STANDARD: fald-tilbaget for dem er nu det samme "auto" som for enhver anden
# slags STANDARD ikke har en mening om (se `kanal_for()`s docstring), indtil
# `fra_jarvis()` faktisk faar et kaldested for en af dem.
def test_de_fire_navne_staar_ikke_i_standard(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    for slags in ("briefing", "reminder", "reach_out", "initiative"):
        assert slags not in v.STANDARD, (
            f"{slags} staar stadig i STANDARD og kan igen slukke for et "
            "system der ikke er feedens"
        )
        assert v.kanal_for("bjorn", slags) == "auto"


def test_reach_out_leveres_gennem_routeren(isolated_runtime, monkeypatch) -> None:
    """Beviser at den AEGTE `route_proactive_notification()` stadig leverer
    `reach_out` — den slags proactivity_bridge/autonomous_outreach/
    action_router/central_moltbook bruger. Kun transportlaget mockes."""
    import core.services.notification_router as nr

    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel",
                        lambda *a, **k: delivered.append(a) or True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    res = nr.route_proactive_notification(
        "bjorn", "reach_out", {"preview": "tekst", "body": "tekst"}, importance="normal")

    assert res["channel"] != "fravalgt"
    assert res["delivered"] is True
    assert delivered


def test_briefing_leveres_gennem_routeren(isolated_runtime, monkeypatch) -> None:
    """Samme bevis for `briefing`."""
    import core.services.notification_router as nr

    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel",
                        lambda *a, **k: delivered.append(a) or True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    res = nr.route_proactive_notification(
        "bjorn", "briefing", {"preview": "god morgen"}, importance="normal")

    assert res["channel"] != "fravalgt"
    assert res["delivered"] is True
    assert delivered
