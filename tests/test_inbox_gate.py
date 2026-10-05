"""Indbakkens to-trins gate — Opgave 4 og 12.

Rigtig sqlite, fordi tælleren er durabel og `UPDATE … WHERE status='aaben'` er
det der gør påmindelsen idempotent. En fake forbindelse kan ikke se nogen af dem.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.runtime import db_inbox
from core.services.inbox_gate import evaluer_inbox_mutation

BJORN = "bjorn"
ANDEN = "en-anden-bruger"


@pytest.fixture
def inbox_db(monkeypatch, tmp_path, ejeren_er_bjorn):
    sti = tmp_path / "gate.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def _egen_aaben_post(bruger=BJORN, id="wake-49b89a51de", **kw) -> dict:
    """En post der MÅ gate: verificeret som hans eget, åben, handlingskrævende."""
    r = db_inbox.opret_eller_hent(
        bruger_id=bruger, kildetype=kw.pop("kildetype", "wakeup"), kilde_id=id,
        oprettende_run_id="visible-abc123",
        verificeret_ejer=kw.pop("ejer", db_inbox.EJER_JARVIS),
        kraever_handling=kw.pop("kraever_handling", True),
        beskrivelse=kw.pop("beskrivelse", "foelg op paa Michelles brief"), **kw)
    assert r["status"] == "ok", r
    return r["post"]


def _lever_paamindelse(post: dict, tur: str):
    r = db_inbox.noter_paamindelse(bruger_id=post["bruger_id"],
                                   kilde_id=post["id"], tur=tur)
    assert r["status"] == "ok", r


# ── Trin 1: to leverede påmindelser før en mutation nægtes ──────────────────

def test_to_leverede_paamindelser_foer_mutation_naegtes(inbox_db):
    """Spec'ens egen test, og hele to-trins-formen i én.

    Bemærk at den IKKE går gennem R2.5's `should_block_for_verification`. Den
    har fire tidlige `return None` (cooldown <60 s, gate-fejl, under tærskel,
    heed_rate), så en test ad den vej måler ingenting med mindre alle fire
    styres. Inboxen har sin EGEN forudsætning i samme mutationspunkt, og her
    måles inbox-leddet alene.

    RETTET: spec'ens egen sekvens (kald, lever, kald, lever, kald) DOBBELT-
    taeller, og testen afsloerede det. Gatens trin-1-svar ER leveringen —
    varslet gaar tilbage som tool-resultat — saa `evaluer_inbox_mutation`
    taeller selv. Blandes den med en eksplicit `_lever_paamindelse`, naas
    taersklen én tur for tidligt.

    Her maales mekanismen som den virker: tre aegte mutationer i tre ture.
    Foerste paaminder, anden paaminder, tredje naegter.
    """
    post = _egen_aaben_post(id="wake-49b89a51de")
    foerste = evaluer_inbox_mutation(BJORN, "edit_file", tur="t1")
    assert foerste["blokeret"] is False and foerste["varsel"] != ""
    anden = evaluer_inbox_mutation(BJORN, "edit_file", tur="t2")
    assert anden["blokeret"] is False and anden["varsel"] != ""
    assert db_inbox.hent(bruger_id=BJORN, kilde_id=post["id"])["paamindelser"] == 2
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is True
    assert "wake-49b89a51de" in v["poster"]


def test_taersklen_rammes_PRAECIS_ved_antallet_ikke_foer(inbox_db):
    """Grænsen selv. Med tærskel 2 skal ÉN påmindelse ikke blokere — ellers er
    to-trins-formen kollapset til øjeblikkelig blokering, og det var præcis den
    vurdering Bjørns ord afviste."""
    post = _egen_aaben_post(id="wake-g")
    _lever_paamindelse(post, tur="t1")
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-g")["paamindelser"] == 1
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t2")["blokeret"] is False
    # Kaldet ovenfor leverede selv paamindelse nr. 2.
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-g")["paamindelser"] == 2
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is True


def test_naegtelsen_NAVNGIVER_posten(inbox_db):
    """En blokering uden en adresse er en blokering man ikke kan rette."""
    post = _egen_aaben_post(id="wake-abc", beskrivelse="foelg op paa brief")
    _lever_paamindelse(post, "t1")
    _lever_paamindelse(post, "t2")
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert "wake-abc" in v["varsel"]
    assert "foelg op paa brief" in v["varsel"]
    assert "inbox_done" in v["varsel"] and "inbox_drop" in v["varsel"]


def test_trin_1_paaminder_og_TAELLER_i_samme_greb(inbox_db):
    """«Tæl kun når påmindelsen faktisk blev leveret til modellen.» Tælles der
    når gaten blev SPURGT, ville en mutation der aldrig nåede modellen kunne
    tælle sig op til blokeringen."""
    _egen_aaben_post(id="wake-t")
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t1")
    assert v["blokeret"] is False
    assert v["poster"] == ["wake-t"]
    from core.services.visible_run_guard_notices import SYSTEM_MAERKE
    assert SYSTEM_MAERKE in v["varsel"]
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-t")["paamindelser"] == 1


def test_trin_1_fyrer_IKKE_i_hver_runde_af_samme_tur(inbox_db):
    """Uden tur-nøglen kunne én tur med mange mutationer tælle sig op til
    tærsklen alene og springe hele den høflige anmodning over — præcis den støj
    R2 blev kritiseret for."""
    _egen_aaben_post(id="wake-r")
    a = evaluer_inbox_mutation(BJORN, "edit_file", tur="SAMME")
    b = evaluer_inbox_mutation(BJORN, "write_file", tur="SAMME")
    c = evaluer_inbox_mutation(BJORN, "edit_file", tur="SAMME")
    assert a["varsel"] != ""
    assert b["varsel"] == "" and c["varsel"] == "", "varslet gentages i samme tur"
    assert all(x["blokeret"] is False for x in (a, b, c))
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-r")["paamindelser"] == 1


# ── Trin 2: huset og andre brugere kan IKKE nægte ───────────────────────────

def test_husets_post_naegter_IKKE_selv_med_mange_paamindelser(inbox_db):
    """«Huset kan informere, men ikke kræve.» Dobbelt værn: `kraever_handling`
    sættes falsk ved registrering, OG gaten kræver ejer == jarvis her. Et
    FEJLMÆRKET `kraever_handling` i basen må ikke alene kunne gate."""
    p = _egen_aaben_post(id="d-1", kildetype="daemon",
                         ejer=db_inbox.EJER_HUSET, kraever_handling=True)
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is False


def test_en_UKENDT_ejer_naegter_aldrig(inbox_db):
    """«[ukendt] er aldrig blokerende.» Kunne den gate, ville man kunne opnå en
    blokering ved at gøre proveniensen utydelig."""
    p = _egen_aaben_post(id="u-1", ejer=db_inbox.EJER_UKENDT, kraever_handling=True)
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is False


def test_en_ANDEN_brugers_poster_naegter_ikke_mine(inbox_db):
    p = _egen_aaben_post(bruger=ANDEN, id="wake-andens")
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is False
    assert evaluer_inbox_mutation(ANDEN, "edit_file", tur="t4")["blokeret"] is True


def test_UDEN_bruger_blokeres_intet(inbox_db):
    """En ubundet kontekst (scripts, daemoner) må ikke kunne låse sig selv ude
    af en flade den ikke har poster i."""
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert evaluer_inbox_mutation("", "edit_file", tur="t3")["blokeret"] is False


# ── Trin 3: læsninger og bagdøre slipper igennem ────────────────────────────

def test_LAESE_vaerktoejer_slipper_altid_igennem(inbox_db):
    """Han skal kunne komme fri. Blokeredes læsninger, kunne han ikke engang
    kalde `inbox` for at se hvad der blokerer."""
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    for navn in ("read_file", "inbox", "inbox_done", "inbox_drop",
                 "list_self_wakeups", "grep_files"):
        v = evaluer_inbox_mutation(BJORN, navn, tur="t3")
        assert v["blokeret"] is False, f"{navn} blev naegtet"


def test_BAGDOERENE_slipper_igennem(inbox_db):
    """`bash_session*` og `operator_bash_session*` er Bjørns aftalte vej udenom
    systemet. En inbox-post må ikke utilsigtet fjerne den bypass."""
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    for navn in ("bash_session_run", "bash_session_start",
                 "operator_bash_session_run"):
        v = evaluer_inbox_mutation(BJORN, navn, {"command": "rm -rf x"}, tur="t3")
        assert v["blokeret"] is False, f"bagdoeren {navn} blev naegtet"
        assert v["grund"] == "bagdoer"


def test_et_ikke_muterende_SHELL_kald_naegtes_ikke(inbox_db):
    """Et `grep` gennem bash er ikke en mutation. Klassifikationen deles med
    R2.5 netop for at ét sted afgør det."""
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    v = evaluer_inbox_mutation(BJORN, "bash", {"command": "grep -rn x ."}, tur="t3")
    assert v["blokeret"] is False


# ── Opgave 12: det ÆGTE navn OG de ægte argumenter ──────────────────────────

def test_et_INDPAKKET_muterende_shell_kald_naegtes(inbox_db):
    """Den fælde jeg selv gik i, og den Opgave 12 er skrevet om.

    Et indpakket kald bærer transport-navnet `call_loaded_tool`, og dets
    `command` ligger i de INDRE argumenter. Hentede man kun det indre NAVN og
    sendte det videre med de YDRE argumenter, ville
    `shell_command_is_mutating("")` svare False — og en `rm -rf` ville slippe
    uhindret gennem gaten.
    """
    from core.tools.kaldt_vaerktoej import KALD_NAVN
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    v = evaluer_inbox_mutation(
        BJORN, KALD_NAVN,
        {"navn": "bash", "argumenter": {"command": "rm -rf /tmp/x"}}, tur="t3")
    assert v["blokeret"] is True, "et indpakket muterende shell-kald slap igennem"
    assert "bash" in v["varsel"], "naegtelsen navngav transport-navnet"


def test_et_INDPAKKET_laese_kald_slipper_igennem(inbox_db):
    """Modprøven: udpakningen må ikke gøre alt til en mutation."""
    from core.tools.kaldt_vaerktoej import KALD_NAVN
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    v = evaluer_inbox_mutation(
        BJORN, KALD_NAVN, {"navn": "read_file", "argumenter": {"path": "x"}},
        tur="t3")
    assert v["blokeret"] is False


def test_et_indpakket_kald_UDEN_indre_navn_bliver_staaende(inbox_db):
    """`pak_ud` returnerer dispatcher-navnet uændret når der ikke er et brugbart
    indre navn — så det fejler HØJLYDT som ukendt værktøj frem for at udføre
    ingenting i stilhed. Gaten må ikke lave sit eget gæt i stedet."""
    from core.tools.kaldt_vaerktoej import KALD_NAVN
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    for args in ({}, {"navn": ""}, {"navn": KALD_NAVN}, {"navn": None}):
        v = evaluer_inbox_mutation(BJORN, KALD_NAVN, args, tur="t3")
        assert v["blokeret"] is False, f"{args} blev udnaevnt til en mutation"


def test_udpakningen_defineres_kun_EET_sted(inbox_db):
    """Vagt mod at reglen gentages (Opgave 12 trin 6).

    To definitioner kan drive fra hinanden, og det er præcis hvordan et filter
    bliver stille virkningsløst. AST, ikke grep: en kommentar der NÆVNER
    `pak_ud` må ikke vælte vagten, og denne fils egne docstrings gør det.
    """
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path("core/services/inbox_gate.py").read_text())
    for n in ast.walk(træ):
        if isinstance(n, ast.FunctionDef):
            assert "pak_ud" not in n.name, "inbox_gate definerer sin egen udpakning"
        if isinstance(n, ast.Assign):
            # En lokal genimplementering ville typisk laese `argumenter["navn"]`
            # direkte. Det ER regelen, og den hoerer i kaldt_vaerktoej.
            kilde = ast.unparse(n)
            assert '"navn"' not in kilde or "pak_ud" in kilde, \
                f"inbox_gate laeser det indre navn selv: {kilde[:60]}"


# ── Trin 4: kun done/drop frigiver ──────────────────────────────────────────

def test_R2_5_readback_og_timeout_frigiver_IKKE_inbox_blokken(inbox_db):
    """R2.5's `_blok` frigives ved første readback eller efter 10 minutter.
    Begge er forkert livscyklus her: posten er stadig åben.

    Kunne et blik frigive den, var læsningen en formalitet — og vi var tilbage
    i banner blindness, bare med en blokering i stedet for en advarsel.
    """
    p = _egen_aaben_post(id="wake-fri")
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is True
    from core.services import r2_5_haandhaevelse as r25
    r25.nulstil()                      # R2.5's egen blok lukkes helt
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t4")["blokeret"] is True
    # Og et blik paa indbakken frigiver heller ikke.
    evaluer_inbox_mutation(BJORN, "inbox", tur="t5")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t6")["blokeret"] is True


def test_done_frigiver_i_SAMME_greb(inbox_db):
    from core.services import inbox_state
    p = _egen_aaben_post(id="wake-d", kildetype="job")
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is True
    assert inbox_state.done(BJORN, "wake-d")["status"] == "ok"
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t4")["blokeret"] is False


def test_drop_frigiver_ogsaa(inbox_db):
    from core.services import inbox_state
    p = _egen_aaben_post(id="wake-dr", kildetype="job")
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    assert inbox_state.drop(BJORN, "wake-dr", "ikke relevant")["status"] == "ok"
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t5")["blokeret"] is False


def test_EN_af_TO_poster_lukket_blokerer_stadig(inbox_db):
    """«Hver handlingskrævende post skal lukkes.» Frigav én lukning det hele,
    kunne man slippe fri ved at afgøre den nemmeste."""
    from core.services import inbox_state
    for i in (1, 2):
        p = _egen_aaben_post(id=f"job-{i}", kildetype="job", beskrivelse=f"nr {i}")
        _lever_paamindelse(p, "t1")
        _lever_paamindelse(p, "t2")
    inbox_state.done(BJORN, "job-1")
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is True
    assert v["poster"] == ["job-2"]


# ── Kontakt og fail-open ────────────────────────────────────────────────────

def test_kontakten_slukker_BEGGE_trin(inbox_db):
    """En gate der skærer skal kunne slukkes uden et deploy."""
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    from core.runtime import settings as st
    with patch.object(st, "load_settings",
                      return_value=type("S", (), {"inbox_gate_enabled": False})()):
        v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is False and v["varsel"] == ""
    assert v["grund"] == "kontakt slukket"


def test_TAERSKLEN_kommer_fra_settings_og_er_mindst_1(inbox_db):
    """2 er et startpunkt, ikke en måling. Står tærsklen hårdkodet, kan Opgave
    7 ikke flytte den — og `max(1, …)` findes fordi 0 ville betyde «bloker
    straks», altså præcis den form Bjørn afviste."""
    from core.runtime import settings as st

    def _med(vaerdi, navn, tur):
        """Én sag ad gangen. Hver iteration LUKKER alt andet foerst.

        Uden den oprydning naaede den FORRIGE iterations post taersklen og
        blokerede den naeste — testen maalte sin egen ophobning. Den slags er
        grunden til at en groen test ikke er et bevis foer man har set den
        faelde paa det den paastaar.
        """
        for gammel in db_inbox.liste(bruger_id=BJORN):
            db_inbox.afgoer(bruger_id=BJORN, kilde_id=gammel["id"],
                            ny_status=db_inbox.STATUS_DROP, grund="ryd foer sag")
        _egen_aaben_post(id=navn)
        with patch.object(st, "load_settings", return_value=type(
                "S", (), {"inbox_gate_enabled": True,
                          "inbox_paamindelser_foer_blok": vaerdi})()):
            return evaluer_inbox_mutation(BJORN, "edit_file", tur=tur)

    # En HELT NY post med nul paamindelser maa ALDRIG blokere, uanset hvad
    # taersklen staar paa. Det er `max(1, ...)`s hele formaal, og det var den
    # eneste mutation der slap igennem foerste gang: min gamle test leverede
    # én paamindelse foerst, og saa blokerede baade 0 og 1 — den maalte intet.
    #
    # Taerskel 0 UDEN gulvet ville betyde «bloker straks, uden at paaminde» —
    # praecis den form Bjoerns ord afviste.
    for vaerdi in (0, -3):
        v = _med(vaerdi, f"wake-nul{vaerdi}", f"t{vaerdi}")
        assert v["blokeret"] is False, \
            f"taerskel {vaerdi} blokerede med NUL paamindelser: {v}"
        assert v["varsel"] != "", "den hoeflige anmodning blev sprunget over"

    # Og taersklen skal faktisk komme FRA settings, ikke fra en konstant:
    # SAMME post med én paamindelse, to forskellige taerskler, to svar.
    assert _med(1, "wake-s", "t-a")["blokeret"] is False   # leverer nr. 1
    with patch.object(st, "load_settings", return_value=type(
            "S", (), {"inbox_gate_enabled": True,
                      "inbox_paamindelser_foer_blok": 1})()):
        assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t-b")["blokeret"] is True
    with patch.object(st, "load_settings", return_value=type(
            "S", (), {"inbox_gate_enabled": True,
                      "inbox_paamindelser_foer_blok": 5})()):
        assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t-c")["blokeret"] is False


def test_en_DB_FEJL_slipper_mutationen_igennem(inbox_db, monkeypatch):
    """Fail-open, synligt. En mutation må ikke blokeres på et gæt, og en gate
    der blokerer når den ikke kan læse sin egen tilstand er værre end ingen
    gate — den kan ikke slås fri."""
    p = _egen_aaben_post()
    _lever_paamindelse(p, "t1")
    _lever_paamindelse(p, "t2")
    monkeypatch.setattr(db_inbox, "liste",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is False
    assert "fail-open" in v["grund"]


def test_fail_open_og_TOM_indbakke_er_IKKE_samme_svar(inbox_db, monkeypatch):
    """`None` og `[]` må ikke mappes sammen: blev de ét, ville en DB-fejl se ud
    som en ren indbakke, og gaten var tavst slukket."""
    tom = evaluer_inbox_mutation(BJORN, "edit_file", tur="t1")
    monkeypatch.setattr(db_inbox, "liste",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("nede")))
    fejl = evaluer_inbox_mutation(BJORN, "edit_file", tur="t2")
    assert tom["grund"] == "intet venter"
    assert fejl["grund"] != tom["grund"]


def test_varslet_baerer_system_maerkningen(inbox_db):
    """Stående regel fra Bjørn: alt der ikke er skrevet fra hans composer SKAL
    bære en kilde-mærkning. Umærket tekst i jeg-form startede runder i hans
    navn. Og mærket skal eksplicit forbyde at læse den som samtykke — uden den
    linje kan en systembesked blive et «ja»."""
    from core.services.visible_run_guard_notices import SYSTEM_MAERKE
    _egen_aaben_post()
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t1")
    # HUSETS maerkning, ikke min egen. Jeg skrev foerst en anden her, og det
    # var den samme fejl jeg lige havde advaret om i Opgave 12: to
    # definitioner af samme regel driver fra hinanden.
    assert SYSTEM_MAERKE in v["varsel"], "varslet baerer ikke husets systemmaerke"
    for krav in ("IKKE en besked fra brugeren", "samtykke"):
        assert krav in v["varsel"], f"varslet mangler: {krav}"


def test_sporets_familier_ER_registrerede(inbox_db):
    """Hele Opgave 7's måling hænger på dette.

    Jeg glemte at registrere `inbox` og `inbox_gate` i
    `ALLOWED_EVENT_FAMILIES`. `Event.create()` kaster «Unsupported event
    family», `_spor` fangede det, og sporet publicerede i **tavshed** — en
    måling der ville have vist nul i ugevis.

    Min egen advarselslinje i `_spor` fangede det, og det er grunden til at den
    logger på WARNING frem for DEBUG. Men en log man skal huske at læse er
    ikke en vagt; denne test er.

    Det er samme fejlklasse som `core/eventbus/publish_scan.py` blev skrevet
    for: «64 familier publiceres uden at være tilladt. Nul events i databasen
    for dem alle.» Jeg læste den docstring samme dag.
    """
    from core.eventbus.bus import event_bus
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES
    for familie in ("inbox", "inbox_gate"):
        assert familie in ALLOWED_EVENT_FAMILIES, \
            f"{familie} er ikke registreret — sporet publicerer i tavshed"
    # Og den skal faktisk kunne publicere. En registreret familie kan stadig
    # afvises af en anden validering.
    for kind in ("inbox.registreret", "inbox.afgjort", "inbox_gate.reminded",
                 "inbox_gate.blocked", "inbox_gate.fail_open"):
        event_bus.publish(kind, {"bruger_id": BJORN, "poster": ["t"]})


def test_spor_der_fejler_vaelter_IKKE_gaten(inbox_db, monkeypatch):
    """Telemetrien må aldrig vælte beslutningen. En bus der er nede gør Opgave
    7 blind, men den må ikke gøre Jarvis handlingslammet."""
    import core.services.inbox_gate as ig
    _egen_aaben_post()
    monkeypatch.setattr(ig, "_spor",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bus nede")))
    with pytest.raises(RuntimeError):
        # `_spor` selv fanger; en patch der kaster beviser at der IKKE er et
        # ekstra lag omkring kaldet — altsaa at `_spor`s egen except ER vagten.
        ig.evaluer_inbox_mutation(BJORN, "edit_file", tur="t1")


def test_en_DOED_eventbus_stopper_ikke_gaten(inbox_db, monkeypatch):
    """Den anden halvdel: med den AEGTE `_spor` og en bus der kaster, skal
    gaten svare normalt.

    Foerste udgave af denne test laa i samme funktion som ovenstaaende og
    brugte `monkeypatch.undo()` imellem. Den ruller ALLE patches tilbage —
    ogsaa fixturens DB-patch — saa anden halvdel ramte den rigtige database,
    fandt ingen poster, og fejlede af en grund der intet havde med emnet at
    goere.
    """
    import core.services.inbox_gate as ig
    from core.eventbus.bus import event_bus
    _egen_aaben_post()
    monkeypatch.setattr(event_bus, "publish",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    v = ig.evaluer_inbox_mutation(BJORN, "edit_file", tur="t1")
    assert v["blokeret"] is False
    assert v["varsel"] != "", "en doed bus slugte paamindelsen"


# ── En PLANLAGT vækning venter ikke på nogen ───────────────────────────────

def test_en_PLANLAGT_vaekning_gater_IKKE(inbox_db, monkeypatch):
    """`pending` = planlagt, ikke ventende — også når påmindelserne er brugt op.

    Målt 4/10-2026 i drift: gaten nægtede et `bash`-kald med min egen netop
    bookede efterkontrol som grund (`wake-155d570154`, `paamindelser=1`,
    tærskel 2). Rækkens `kraever_handling` sættes ved BOOKINGEN og opdateres
    aldrig når vækningen fyrer — `meld_kilde_faerdig` har nul kaldere — så
    posten gatede før vækningen overhovedet havde fyret.
    """
    import core.services.inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [
        {"wakeup_id": "wake-planlagt", "user_id": BJORN, "status": "pending"}])
    post = _egen_aaben_post(id="wake-planlagt")
    _lever_paamindelse(post, "t1")
    _lever_paamindelse(post, "t2")
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-planlagt")["paamindelser"] == 2
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is False, v


def test_en_FYRET_vaekning_gater_STADIG(inbox_db, monkeypatch):
    """Den anden halvdel: en vækning der ER fyret venter faktisk på ham.

    Uden denne ville rettelsen kunne være «gaten gater ikke længere» — og det
    er ikke det samme som at den gater det rigtige.
    """
    import core.services.inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [
        {"wakeup_id": "wake-fyret", "user_id": BJORN, "status": "fired"}])
    post = _egen_aaben_post(id="wake-fyret")
    _lever_paamindelse(post, "t1")
    _lever_paamindelse(post, "t2")
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is True, v
    assert "wake-fyret" in v["poster"]


def test_en_vaekning_uden_foraeldre_gater_som_foer(inbox_db, monkeypatch):
    """Findes vækningen slet ikke i kilden, må posten IKKE blive usynlig.

    Den er så en post man ikke kan afgøre — husets værste fejlform. Rækken
    findes, så den skal både vises og kunne lukkes; derfor falder vi tilbage
    til rækkens eget flag.
    """
    import core.services.inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [])
    post = _egen_aaben_post(id="wake-uden-kilde")
    _lever_paamindelse(post, "t1")
    _lever_paamindelse(post, "t2")
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is True, v
    assert "wake-uden-kilde" in v["poster"]


# ── Opgave 8's FORBINDELSE: en udløbet post gater ikke (5/10-2026) ───────────
#
# Funktionerne i `db_inbox` var grundigt dækket. Det var FORBINDELSEN der
# manglede: `er_udloebet` blev kaldt NUL steder i produktionen, og
# `fej_udloebne` blev aldrig kørt. Målt 5/10-2026 i drift: nul poster havde
# nogensinde båret en frist, så en hvilken som helst frist var virkningsløs.
# Testen her måler derfor vejen gennem GATEN — ikke funktionen, som allerede
# havde sin egen test og bestod hele tiden.

def test_en_UDLOEBET_post_gater_IKKE_selv_om_raekken_staar_aaben(inbox_db):
    """Den beregnede tilstand skal bide i gaten, ikke kun i fejeren.

    Rækken står bevidst stadig `aaben` i basen — fejeren har IKKE kørt. Det er
    den beregnede tilstand alene der skal holde posten fra at nægte. Ellers
    kunne en post gate i det uendelige, hvis blot ingen rørte den, og det er
    præcis hvad spec'ens Opgave 8 findes for at forhindre.
    """
    from datetime import UTC, datetime, timedelta

    post = _egen_aaben_post(id="wake-udloebet")
    _lever_paamindelse(post, "t1")
    _lever_paamindelse(post, "t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is True

    db_inbox.saet_udloeb(
        bruger_id=BJORN, kilde_id="wake-udloebet",
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat())
    assert db_inbox.hent(bruger_id=BJORN,
                         kilde_id="wake-udloebet")["status"] == db_inbox.STATUS_AABEN

    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t4")
    assert v["blokeret"] is False, v
    # ... og posten kan stadig LÆSES. Udløb er en tilstand, ikke en sletning.
    p = db_inbox.hent(bruger_id=BJORN, kilde_id="wake-udloebet")
    assert p is not None and p["kraever_handling"] is False
