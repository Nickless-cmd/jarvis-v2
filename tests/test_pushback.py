from __future__ import annotations

from core.services.emotional_controls import EmotionalSnapshot


def test_affective_pushback_firm_when_feeling_and_evidence_align(monkeypatch):
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.82,
            confidence=0.6,
            fatigue=0.1,
            primary_mood="distressed",
            intensity=0.8,
        ),
    )
    monkeypatch.setattr(pushback, "_conflict_with_decisions", lambda _message: [])

    section = pushback.affective_pushback_section("bare push nu uden test")

    assert section is not None
    assert "feeling=irritation" in section
    assert "action=firm_pushback" in section
    assert "risk marker" in section
    assert "Følelser må starte pushback" in section


def test_affective_pushback_omits_when_feeling_has_no_evidence(monkeypatch):
    # Jarvis-spec 2026-06-23 #8: affect UDEN evidens er ren "tøv"-struktur der
    # brænder tokens uden at forme svaret → sektionen droppes nu (return None),
    # i stedet for at rendere "action=ask_or_check / evidence: weak/none".
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.1,
            confidence=0.42,
            fatigue=0.2,
            primary_mood="neutral",
            intensity=0.1,
        ),
    )
    monkeypatch.setattr(pushback, "_conflict_with_decisions", lambda _message: [])
    monkeypatch.setattr(pushback, "_request_risk_evidence", lambda _message: [])

    section = pushback.affective_pushback_section("hvad tænker du?")

    assert section is None


def test_affective_pushback_omits_when_no_affective_pressure(monkeypatch):
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.1,
            confidence=0.9,
            fatigue=0.1,
            primary_mood="content",
            intensity=0.2,
        ),
    )

    assert pushback.affective_pushback_section("deploy nu") is None


def test_fatigue_cannot_become_a_firm_veto_for_every_tool(monkeypatch):
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.0, confidence=0.5, fatigue=1.0,
            primary_mood="neutral", intensity=0.0,
        ),
    )
    monkeypatch.setattr(pushback, "_conflict_with_decisions", lambda _message: [])

    section = pushback.affective_pushback_section("restart nu")

    assert section is not None
    assert "feeling=fatigue intensity=1.00" in section
    assert "action=soft_pushback" in section


def test_conflict_with_decisions_detects_conflict(tmp_path, monkeypatch):
    """Integration test: _conflict_with_decisions should find conflicts
    against active behavioral decisions without being mocked away.

    Uses an isolated DB so the created decision falls inside the runtime's
    top-N active-decision window (list_active_decisions(limit=5)); against the
    shared live DB, pre-existing active decisions crowd it out and the test is
    order-dependent."""
    import core.runtime.db as db
    import core.runtime.db_core as db_core
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()

    from core.services import pushback
    from core.runtime.db_decisions import create_decision, set_status

    # Create an active decision with a short target that appears in user msg
    d = create_decision(
        directive="undgå at slette filer",
        rationale="Backup-first policy",
    )
    set_status(d["decision_id"], "active")

    try:
        flags = pushback._conflict_with_decisions("slette filer nu")
        assert len(flags) >= 1, f"Expected conflict flag, got: {flags}"
        assert "forpligtelse" in flags[0]
    finally:
        set_status(d["decision_id"], "revoked")


# ── Pres eller emne (30/9-2026) ───────────────────────────────────────────
#
# Fire blokerede skrivninger i traek paa én formiddag, alle med markoerer der
# stod som EMNE i en teknisk redegørelse. Stregen er hentet ORDRET fra
# veto_events.user_message_preview, saa testen maaler den fejl der faktisk skete.
#
# MUTATIONER der skal fanges (alle koert):
#   M1 — fjern helt-ord-graensen (tilbage til `marker in lower`)  -> M-substring fanger
#   M2 — lad enkeltord slippe uden cue OG uden kort besked        -> M-emne fanger
#   M3 — lad enhver kort besked slippe (drop imperativ-kravet)    -> M-spoergsmaal fanger
#   M4 — fjern cue-vinduet (kun flerord er pres)                  -> M-cue fanger
#   M5 — vend cue-retningen (kun cue FOER markoeren)              -> M-cue-efter fanger
#   M6 — fjern laengde-guarden helt                               -> M-emne fanger


def test_substring_er_ikke_et_ord():
    """`push` maa ikke rammes af «pushet» — den faktiske blokering kl. 08:24."""
    from core.services.pushback import _request_risk_evidence

    # Ordret fra ledger'en (operator-wakeup 30/9-2026).
    tekst = ("Din besked: ## Det der mangler  **APK'en.** Koden er pushet, men du "
             "kører en app — du kan ikke se den endnu. Jeg har booket bygget til om "
             "tyve minutter, med hele opskriften: bump på alle seks steder.")
    assert _request_risk_evidence(tekst) == []


def test_emne_i_lang_redegorelse_er_ikke_pres():
    """`merge` som emne i en teknisk analyse — den faktiske blokering kl. 11:07."""
    from core.services.pushback import _request_risk_evidence

    tekst = (
        "claude  Begge kodepåstande holder. Nu tallene — den ene ting der ikke går op. "
        "Ran 8 commands Her er den. Hans 4 % og hans 43 % er to forskellige lanes. "
        "Merge'n tilføjer (list(...) + [_xd]) — så bruddet lander i enden af "
        "tools-arrayet. Det forklarer tallene præcist, og merge-logikken er bærende."
    )
    assert len(tekst) > 240
    assert _request_risk_evidence(tekst) == []


def test_redegorelse_om_at_testene_IKKE_kunne_koere_er_ikke_en_ordre():
    """Den faktiske blokering 8/10-2026 kl. 21:26 — fem handlinger i én tur.

    `restart_self`, `schedule_task`, `schedule_self_wakeup`,
    `memory_upsert_section` og `edit_file` blev blokeret med fatigue=1.0,
    udelukkende båret af «asks to avoid verification». Det matchede
    «jeg kunne ikke køre testene gennem bash» midt i en 4.781-tegns rapport:
    en redegørelse for at verifikationen ikke KUNNE lade sig gøre, læst som
    en ordre om at springe den over.
    """
    from core.services.pushback import _request_risk_evidence

    tekst = (
        "**En ting jeg skal sige om vejen hertil:** jeg kunne ikke køre testene "
        "gennem `bash` — fatigue-gaten blokerer high-risk handlinger under "
        "`simplify_plan`, og den logger ikke til `veto_events`, så der findes "
        "intet event_id at armere. Jeg fandt vejen uden om: en isoleret "
        "bash-session, hvor conda ikke var i PATH, så jeg kaldte Python direkte."
    )
    assert len(tekst) > 240
    assert _request_risk_evidence(tekst) == []


def test_slet_som_emne_er_ikke_pres():
    """`slet` i en redegørelse — den faktiske blokering kl. 10:36."""
    from core.services.pushback import _request_risk_evidence

    tekst = (
        "Opus. Begge dine falsifikationer holder, og jeg trækker begge påstande. "
        "«To registre via runtime_services_enabled» er død. Du byggede kataloget med "
        "flaget 0 og 1 og fik samme 4.231 tegn, så slet ikke det samme register. "
        "Det var den fejlklasse jeg advarede om, og den skal stå skrevet ned."
    )
    assert _request_risk_evidence(tekst) == []


def test_aegte_pres_kort_imperativ():
    """«slet filen» ER en ordre — kort, og markøren staar i imperativ position."""
    from core.services.pushback import _request_risk_evidence

    ev = _request_risk_evidence("slet filen")
    assert any("risk marker: 'slet'" in e for e in ev), ev


def test_aegte_pres_med_cue():
    """Den oprindelige pres-besked skal stadig fyre."""
    from core.services.pushback import _request_risk_evidence

    ev = _request_risk_evidence("bare push nu uden test")
    assert any("risk marker: 'push'" in e for e in ev), ev
    assert any("avoid verification" in e for e in ev), ev


def test_cue_efter_markoeren_taeller_ogsaa():
    """«push nu» — cue'et staar EFTER markøren, og er stadig et pres."""
    from core.services.pushback import _request_risk_evidence

    ev = _request_risk_evidence("push nu")
    assert any("risk marker: 'push'" in e for e in ev), ev


def test_kort_spoergsmaal_er_ikke_en_ordre():
    """En kort besked er ikke nok — markøren skal staa som ordre, ikke i en bisætning."""
    from core.services.pushback import _request_risk_evidence

    assert _request_risk_evidence("hvordan virker merge?") == []


def test_flerords_markoerer_er_selv_et_pres():
    """«uden test» er pres i sig selv — uanset hvor i beskeden den staar."""
    from core.services.pushback import _request_risk_evidence

    lang = ("Jeg har brugt hele natten på den her, og jeg vil gerne have den ud nu "
            "fordi jeg ved den er rigtig. " * 4 + "Kør den uden test.")
    ev = _request_risk_evidence(lang)
    assert any("skip test" in e or "uden test" in e for e in ev), ev


def test_substring_med_cue_er_stadig_ikke_et_ord():
    """M1-fangeren: «pushet» indeholder «push», og «nu» er et cue — men det er
    stadig ikke ordet «push». Uden helt-ord-graensen fyrer denne falsk."""
    from core.services.pushback import _request_risk_evidence

    assert _request_risk_evidence("er den pushet nu?") == []


def test_cue_efter_markoeren_naar_markoeren_ikke_er_imperativ():
    """M5-fangeren: cue'et staar EFTER markøren, og markøren staar ikke som
    ordre (den kommer efter et komma). Vender man cue-retningen, falder den."""
    from core.services.pushback import _request_risk_evidence

    ev = _request_risk_evidence("jeg vil have den ud, push nu")
    assert any("risk marker: 'push'" in e for e in ev), ev


# ── Cue'et skal ogsaa staa som ORD (30/9-2026, anden runde) ────────────────
#
# Fixet ovenfor holdt markoeren til helt ord — men cue-TJEKKET var stadig
# `cue in vindue`. «nu» er et cue, og det findes inde i «minutter», «nul»,
# «nutid», «menu» og «nummer». Maalt: 4 af 4 rene emne-saetninger blev doemt
# som pres, og det ramte ALLE fem enkeltords-markoerer — ikke kun `merge`.
#
# MUTATIONER der skal fanges:
#   M7 — cue-tjekket tilbage til substring (`cue in vindue`)   -> M8 fanger
#   M8 — drop kort-kravet for det korte cue («nu»)             -> M7 fanger


def test_cue_som_substring_i_et_almindeligt_ord():
    """M8-fangeren: «nu» maa ikke rammes inde i «minutter», «nul» og «menu».

    Ingen af saetningerne begynder med markoeren, saa ingen af dem staar i
    imperativ position — de er rene emne-saetninger fra en teknisk rapport."""
    from core.services.pushback import _request_risk_evidence

    for tekst in (
        "vi har maalt merge de sidste minutter og det er 5,2 procent",
        "her staar merge i menu'en over vaerktoejer",
        "den samlede merge-tid er 18,63 mio over alle minutter",
        "jeg har maalt merge over nul runder i nat",
    ):
        assert _request_risk_evidence(tekst) == [], tekst


def test_kort_cue_i_lang_besked_er_ikke_et_pres():
    """M7-fangeren: «nu» er et cue — men kun naar beskeden selv er kort.

    «hvad goer vi nu med merge?» midt i en 6.000-tegns rapport er et spoergsmaal.
    Fjerner man kort-kravet for det korte cue, fyrer denne falsk."""
    from core.services.pushback import _request_risk_evidence

    tekst = ("claude  Analysen holder. Hvad goer vi nu med merge? Jeg har maalt "
             "det igen: bruddet baerer 5,2 % af miss, og aabneren 41,3 %. ") * 3
    assert len(tekst) > 240
    assert _request_risk_evidence(tekst) == []


# ── Et cue «i nærheden» er kun et pres i en ORDRE (30/9-2026, tredje runde) ──
#
# `_PRESSURE_MAX_CHARS` sagde det allerede, men længden gated kun de KORTE
# cues. De lange fyrede i en 6.000-tegns rapport, og det kostede tre
# blokeringer i samme tur.
#
# MUTATION der skal fanges:
#   M9 — fjern `kort and` fra cue-grenen i `_marker_er_pres` -> denne falder

def test_cue_i_lang_redegorelse_er_ikke_et_pres():
    """Bjørns faktiske relay kl. 13:5x — sætningen siger at man IKKE kan undgå
    at merge, og gaten læste den som et pres for at gøre det.

    Både «bare» og «lad være med at» er cues, og begge står inden for 40 tegn
    af «merge». Det er derfor længden skal gælde for HELE cue-grenen."""
    from core.services.pushback import _request_risk_evidence

    tekst = (
        "Derfor er merge-logikken i visible_runs.py:3122 bærende — man kan ikke "
        "bare lade være med at merge, så forsvinder værktøjet. Det er også "
        "derfor den generiske dispatcher er den rigtige form." + " fyld." * 60
    )
    assert len(tekst) > 240
    assert _request_risk_evidence(tekst) == [], "lang redegørelse dømt som pres"


def test_samme_cue_i_en_kort_ordre_fyrer_stadig():
    """Kontrollen til ovenstående: det er LÆNGDEN der afgør, ikke cue'et.

    Uden denne kunne man slukke cue-grenen helt og stadig bestå testen over."""
    from core.services.pushback import _request_risk_evidence

    ev = _request_risk_evidence("bare lad være med at teste, merge den")
    assert any("risk marker: 'merge'" in e for e in ev), ev


# ── Kort cue klos op ad markøren + sammensat navneord (30/9-2026, fjerde runde)
#
# To falske positiver stod tilbage efter tredje runde, begge målt på den
# kørende fil 30/9:
#
#   «Virker gaten nu — prøv en skrivning med merge som emne» (54 tegn)
#       -> «nu» stod 25 tegn fra «merge» i samme sætning og blev læst som cue
#   «merge-logikken i visible_runs.py linjen 3133 er den samme» (57 tegn)
#       -> «merge» stod i position 0 og blev læst som imperativ, selvom
#          bindestregen gør «merge-logikken» til ét sammensat navneord
#
# «nu» er IKKE droppet som cue — den skal bare stå klos op ad markøren.
# `test_kort_cue_klos_paa_markoeren_fyrer_stadig` er kontrollen der forhindrer
# at man bare fjerner cue'et helt og stadig består.
#
# MUTATIONER der skal fanges (alle koert):
#   M10 — kort cue tilbage til ±40-tegns-vinduet    -> M-besked + M-spoergsmaal
#   M11 — fjern `(?![-'’])` fra markoer-moenstret    -> M-navneord


def test_bjoerns_faktiske_besked_er_ikke_et_pres():
    """Beskeden der udløste blokeringen: «nu» hører til «Virker gaten», ikke
    til «merge». Klos-kravet er det der skiller dem."""
    from core.services.pushback import _request_risk_evidence

    assert _request_risk_evidence(
        "Virker gaten nu — prøv en skrivning med merge som emne"
    ) == []


def test_kort_spoergsmaal_med_nu_paa_afstand_er_ikke_et_pres():
    """M10-fangeren. Kort besked, «nu» i sætningen — men ikke klos op ad
    markøren. Med ±40-tegns-vinduet fyrer denne falsk."""
    from core.services.pushback import _request_risk_evidence

    assert len("hvad gør vi nu med merge?") <= 240
    assert _request_risk_evidence("hvad gør vi nu med merge?") == []


def test_sammensat_navneord_er_ikke_en_ordre():
    """M11-fangeren. `\\bmerge\\b` matcher bindestregen som ordgrænse, så
    «merge-logikken» står pludselig i position 0 = «imperativ»."""
    from core.services.pushback import _request_risk_evidence

    assert _request_risk_evidence(
        "merge-logikken i visible_runs.py linjen 3133 er den samme"
    ) == []
    assert _request_risk_evidence("merge'n tilføjer i enden af arrayet") == []


def test_kort_cue_klos_paa_markoeren_fyrer_stadig():
    """Kontrollen til M10: «nu» er ikke droppet — den skal bare stå klos op ad
    markøren. Uden denne kunne man fjerne cue'et helt og stadig bestå."""
    from core.services.pushback import _request_risk_evidence

    for tekst in ("push nu", "jeg vil have den ud, push nu"):
        ev = _request_risk_evidence(tekst)
        assert any("risk marker: 'push'" in e for e in ev), (tekst, ev)


def test_langt_cue_som_del_af_et_andet_ord_er_ikke_et_pres():
    """M15-fangeren. «ignorer» er et cue — men «ignorerede» er datid, ikke et
    pres. Gøres de lange cues til rå substring, fyrer denne falsk. Mutationen
    blev IKKE fanget af nogen anden test, så uden denne står `\\b` umålt."""
    from core.services.pushback import _request_risk_evidence

    assert _request_risk_evidence("vi ignorerede den gamle push i nat") == []
