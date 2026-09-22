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
    """En slags `STANDARD` intet siger om maa IKKE stilles som «fravalgt» bare
    fordi den ikke staar i tabellen — det ville tavst slukke for en kildes
    signal ingen bad om at slukke.

    `membrane_breach`/`infra_security`/`keymaker_key_earned` proevede dette
    foer (opgave "routeren-foeder", 2026-09-22) — de har nu hver deres egen,
    bevidste STANDARD-vaerdi (se `test_de_seks_router_slags_har_bevidste_
    standarder`) og tester derfor ikke laengere "ukendt" her. `keymaker_
    key_pending` er stadig genuint ukendt for STANDARD."""
    from core.services import notifikations_valg as v

    assert v.kanal_for("bjorn", "keymaker_key_pending") == "auto"
    assert v.kanal_for("bjorn", "et_navn_ingen_har_opfundet_endnu") == "auto"


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
# tavst — ogsaa dem der aldrig var feedens at styre.
#
# `briefing`, `reminder`, `initiative` staar STADIG udenfor STANDARD: der
# findes ingen afsender for dem nogen steder i repoet (grep for dem som
# notification_type finder kun urelaterede traef) — de er navne fra den gamle
# notification_preferences-tabel, ikke rigtige haendelser, og en STANDARD-
# vaerdi for en slags der aldrig fødes ville vaere ren fiktion.
def test_briefing_reminder_initiative_staar_stadig_ikke_i_standard(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    for slags in ("briefing", "reminder", "initiative"):
        assert slags not in v.STANDARD, (
            f"{slags} har ingen afsender nogen steder i repoet — en "
            "STANDARD-vaerdi for den ville vaere fiktion"
        )
        assert v.kanal_for("bjorn", slags) == "auto"


# `reach_out` er siden (opgave "routeren-foeder", samme dag) flyttet TILBAGE i
# STANDARD. K4s aegte problem var ikke at "ingen" betoed "ingen push" — det var
# at "ingen" dengang betoed at notifikationen forsvandt HELT, fordi routeren
# ikke havde nogen anden vej for reach_out. Den vej findes nu:
# `notification_router.route_proactive_notification()` laegger altid en
# feed-raekke naar den leverer, UANSET hvad `kanal_for()` svarer (se
# `_foed_feed_raekke()`), saa "ingen" er igen kun en push-praeference —
# praecis som for run_done/release/incident/quota.
def test_reach_out_har_faaet_en_standard_igen(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    assert "reach_out" in v.STANDARD
    assert v.kanal_for("bjorn", "reach_out") == "auto"


# ── De seks router-ejede slags har hver en bevidst STANDARD (samme opgave) ──
def test_de_seks_router_slags_har_bevidste_standarder(isolated_runtime) -> None:
    from core.services import notifikations_valg as v

    forventet = {
        "reach_out": "auto",
        "central_flag": "ingen",
        "membrane_breach": "auto",
        "infra_security": "auto",
        "keymaker_key_earned": "ingen",
        "moltbook_mention": "ingen",
    }
    for slags, kanal in forventet.items():
        assert slags in v.STANDARD, f"{slags} mangler i STANDARD"
        assert v.kanal_for("bjorn", slags) == kanal


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


# ── V8 (2026-09-22): migreringen taber et valg ──────────────────────────────
def test_migreringen_taber_ikke_wakeup(isolated_runtime) -> None:
    """`_GAMLE_KOLONNER` mappede foer BAADE `team_invite` og `wakeup` til
    `initiative`; med `INSERT OR IGNORE` vandt den foerste, og wakeup's
    vaerdi forsvandt. Specen lover at de fem kolonner baeres over uden tab —
    `wakeup` faar derfor sin egen slags."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, team_invite, wakeup)"
            " VALUES (?,?,?,?)", ("bjorn", "auto", "mobile", "push"))
        conn.commit()

    assert v.migrer_kolonner() == 2
    assert v.kanal_for("bjorn", "initiative") == "mobile", "team_invite's valg"
    assert v.kanal_for("bjorn", "wakeup") == "push", "wakeup maa ikke forsvinde"


# ── K5 (2026-09-22): wakeup flyttet helt over i den nye model ──────────────
def test_wakeup_har_egen_standard_og_ny_vej_vinder(isolated_runtime) -> None:
    """`wakeup` boede foer to steder: kolonnen i `notification_preferences`
    (den gamle `NotificationsSection.tsx`) OG raekken i `notifikations_valg`
    (den nye `NotifikationsValg.tsx`, som reelt vinder). Brugeren kunne se
    "discord" i den gamle sektion mens systemet brugte "push" fra raekken —
    tavst, ingen fejl. `wakeup` er nu tilfoejet til `STANDARD`, saa den har
    en standard OG kan saettes gennem den ene, nye vej."""
    from core.services import notifikations_valg as v

    assert v.kanal_for("bjorn", "wakeup") == "ingen", (
        "standarden for wakeup boer vaere 'ingen' — se STANDARD's kommentar"
    )
    v.saet("bjorn", "wakeup", "desktop")
    assert v.kanal_for("bjorn", "wakeup") == "desktop", (
        "et eksplicit valg gennem den nye vej skal vinde over standarden"
    )
    assert v.alle("bjorn")["wakeup"] == "desktop"


def test_migreringen_klemmer_ukendte_kanaler_ned_i_gyldige(isolated_runtime) -> None:
    """Migreringen validerede foer ikke mod `GYLDIGE_KANALER` — de gamle
    kolonner kan lovligt indeholde `discord`/`telegram`
    (notification_router.VALID_CHANNELS), som klientens vaelger ikke
    kender. En saadan vaerdi skal klemmes ned til en kanal feeden faktisk
    forstaar, ikke skrives uaendret over."""
    from core.runtime.db import connect
    from core.services import notifikations_valg as v

    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences (user_id, pref_global, reach_out)"
            " VALUES (?,?,?)", ("bjorn", "auto", "discord"))
        conn.commit()

    v.migrer_kolonner()

    kanal = v.kanal_for("bjorn", "reach_out")
    assert kanal in v.GYLDIGE_KANALER, (
        f"migreret kanal {kanal!r} er ikke en klienten forstaar"
    )
