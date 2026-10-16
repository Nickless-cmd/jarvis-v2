from core.services import side_tasks


def test_prompt_loftet_tillader_ankere(monkeypatch):
    """15/10-2026: loftet var 2000 tegn, og en sideopgave med ankere blev
    klippet i STILHED — accept-kriterierne faldt i gulvet.

    Målt: Bjørns opgave «Luk drømme-carry-over-sløjfen» fyldte præcis 2000
    tegn, og punkt 3, punkt 4 og alle accept-kriterier forsvandt. Loftet er
    hævet, så en opgave med ankere kan rummes."""
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(
        side_tasks, "save_json",
        lambda _key, items: state.__setitem__(slice(None), items),
    )

    lang_prompt = "P" * 5000
    r = side_tasks.flag(title="Opgave med ankere", prompt=lang_prompt)

    assert r["status"] == "ok"
    assert len(state[0]["prompt"]) == 5000


def test_flagged_task_stays_visible_when_activated_until_completed(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    task_id = side_tasks.flag(title="Ryd op", prompt="Ryd op i dokumenterne")["side_task_id"]
    assert [item["side_task_id"] for item in side_tasks.list_open()] == [task_id]

    side_tasks.resolve(task_id, decision="activated")
    assert [item["side_task_id"] for item in side_tasks.list_open()] == [task_id]
    assert task_id in side_tasks.side_tasks_prompt_section()

    side_tasks.resolve(task_id, decision="completed", bevis="Ryddet op i dokumenterne")
    assert side_tasks.list_open() == []
    assert side_tasks.side_tasks_prompt_section() is None
    assert side_tasks.resolve(task_id, decision="activated")["status"] == "error"
    assert state[0]["status"] == "completed"


def test_dismiss_tool_preserves_old_default_and_can_complete(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    first = side_tasks.flag(title="Én", prompt="Gør én ting")["side_task_id"]
    second = side_tasks.flag(title="To", prompt="Gør en anden ting")["side_task_id"]
    assert side_tasks._exec_dismiss_side_task(
        {"side_task_id": first, "reason": "ikke laengere relevant"},
    )["new_status"] == "dismissed"
    assert side_tasks._exec_dismiss_side_task(
        {"side_task_id": second, "decision": "completed", "bevis": "Gjort faerdig"},
    )["new_status"] == "completed"
    assert side_tasks.list_open() == []


def test_dismiss_tool_rejects_unknown_decision_and_lists_open_only(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    tid = side_tasks.flag(title="Tre", prompt="Gør en tredje ting")["side_task_id"]
    # «activated» er ikke en afslutning — værktøjet må ikke kunne bruges til det.
    assert side_tasks._exec_dismiss_side_task({"side_task_id": tid, "decision": "activated"})["status"] == "error"
    side_tasks.resolve(tid, decision="activated")
    listed = side_tasks._exec_list_side_tasks({})
    assert listed["count"] == 1 and listed["side_tasks"][0]["status"] == "activated"
    assert "(i gang)" in side_tasks.side_tasks_prompt_section()


# ── Linket til den samtale der LOESER opgaven (3/10-2026) ─────────────────
#
# Bjoern: «op til trods loeste han opgave og saa maatte jeg minde ham om at
# markere den flaggede opgave faerdig». Maalt: desk starter opgaven i en NY
# samtale og saetter status til `activated` — men den nye sessions id blev
# aldrig gemt, saa INTET kunne bagefter vide at samtalen hoerte til opgaven.
# Hverken runtimen eller Jarvis selv kunne derfor lukke den.

import pytest


@pytest.fixture
def lager(monkeypatch):
    state: list = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _k, _d: list(state))
    monkeypatch.setattr(side_tasks, "save_json",
                        lambda _k, items: state.__setitem__(slice(None), items))
    return state


def test_arbejds_sessionen_gemmes_ved_aktivering(lager):
    tid = side_tasks.flag(title="Fix tests", prompt="Ret de to fejlende tests")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    assert lager[0]["arbejds_session"] == "chat-abc"
    fundet = side_tasks.arbejds_session_for("chat-abc")
    assert fundet is not None and fundet["side_task_id"] == tid


def test_en_anden_samtale_finder_ikke_opgaven(lager):
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    assert side_tasks.arbejds_session_for("chat-andet") is None
    assert side_tasks.arbejds_session_for("") is None


def test_en_LUKKET_opgave_binder_ikke_samtalen_laengere(lager):
    """Ellers ville lukke-instruksen staa i prompten for evigt."""
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    side_tasks.resolve(tid, decision="completed", lukket_af="jarvis",
                       bevis="Testsuite groen efter rettelsen")
    assert side_tasks.arbejds_session_for("chat-abc") is None
    assert lager[0]["lukket_af"] == "jarvis"


def test_lukke_instruksen_staar_KUN_i_arbejds_samtalen(lager):
    """Kernen i rettelsen: listen viste «(i gang)», men intet sagde hvis
    ansvar det var at lukke den. Nu staar instruksen — og kun dér hvor
    arbejdet foregaar, saa den ikke bliver stoej i alle andre ture."""
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")

    i_arbejdet = side_tasks.side_tasks_prompt_section("chat-abc")
    assert "DENNE samtale er arbejdet" in i_arbejdet
    assert f'side_task_id="{tid}"' in i_arbejdet
    assert 'decision="completed"' in i_arbejdet
    assert "Ingen anden lukker den for dig" in i_arbejdet

    andetsteds = side_tasks.side_tasks_prompt_section("chat-andet")
    assert tid in andetsteds, "listen skal stadig vises"
    assert "DENNE samtale er arbejdet" not in andetsteds

    uden_session = side_tasks.side_tasks_prompt_section()
    assert tid in uden_session
    assert "DENNE samtale er arbejdet" not in uden_session


def test_instruksen_siger_hvad_der_skal_ske_hvis_den_IKKE_kan_loeses(lager):
    """Et loefte uden en udvej bliver en tavs loegn: kan opgaven ikke loeses,
    skal han sige HVORFOR og afvise den — ikke lukke den eller lade den staa.

    Formen skiftede 16/10-2026 sammen med kravet: vejen ud er nu `dismissed`
    med en grund, og `completed` kraever et bevis. Instruksen skal navngive
    BEGGE — ellers kender den naeste mig ikke udvejen, og kravet bliver en
    faelde uden udgang (samme fejlform som `bloker`-posten)."""
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    t = side_tasks.side_tasks_prompt_section("chat-abc")
    assert "Kan den ikke loeses" in t
    assert "bevis=" in t, "kravet skal staa i instruksen — ellers lukker han uden"
    assert 'reason="' in t, "udvejen skal staa i instruksen — ellers er den tavs"


def test_prompt_afsnittet_kaster_ikke_paa_en_halv_post(lager):
    """En post uden titel eller uden arbejds_session maa ikke vaelte afsnittet."""
    lager.append({"side_task_id": "side-xx", "status": "activated"})
    assert side_tasks.side_tasks_prompt_section("chat-abc") is not None
    assert side_tasks.arbejds_session_for("chat-abc") is None


# ── Forureningen: listen laestes som en arbejdsordre (3/10-2026) ──────────
#
# Bjoern: «noget forurener side-opgave sessionen! den starter hele tiden og det
# er samme opgave han laver i en anden session med mig».
#
# Maalt samme dag stod der i HVER sessions prompt:
#   [side-eea886e1e9] Giv vagtposterne en levende kanal — … Fixet er tre dele:
#   stop aesthetic-daemonens spam, flyt udgangen til send_session_notificati
# 240 tegn med fremgangsmaaden i, afkortet midt i et ord. Det er ikke et flag,
# det er en arbejdsordre.

def test_listen_siger_at_den_IKKE_er_opgaver_man_er_sat_til(lager):
    """Maerkningen. Samme tre egenskaber som vaerns-noterne: hvad listen ER,
    hvad den IKKE er, og et eksplicit forbud mod den forkerte laesning."""
    side_tasks.flag(title="Giv vagtposterne en levende kanal",
                    prompt="…", tldr="trigger-koeen er doed")
    t = side_tasks.side_tasks_prompt_section("en-anden-samtale")
    assert "HUSKELISTE" in t
    assert "ikke opgaver du er sat til" in t
    assert "IKKE begynde" in t
    assert "Ingen af dem er bedt om i denne samtale" in t


def test_tldr_afkortes_ved_en_ORDGRAENSE_og_ikke_midt_i_et_ord(lager):
    """`send_session_notificati` var det maalte symptom. En afkortet instruks
    er vaerre end ingen: den ser ud som et fuldt svar."""
    side_tasks.flag(
        title="Giv vagtposterne en levende kanal",
        prompt="…",
        tldr=("trigger-koeen er doed. Fixet er tre dele: stop "
              "aesthetic-daemonens spam, flyt udgangen til "
              "send_session_notification og luk koeen"))
    t = side_tasks.side_tasks_prompt_section()
    assert "send_session_notificati\n" not in t
    assert "send_session_notificati…" not in t, "afkortet midt i et ord"
    assert t.endswith("…") or "…" in t
    # Og fremgangsmaaden maa ikke staa der i sin helhed.
    assert "luk koeen" not in t


def test_korte_titler_og_tldr_er_UAENDREDE(lager):
    """Afkortningen maa ikke roere det der allerede er kort — ellers ville
    hver linje faa en vildledende ellipse."""
    side_tasks.flag(title="Fix badge", prompt="…", tldr="den er stale")
    t = side_tasks.side_tasks_prompt_section()
    assert "Fix badge — den er stale" in t
    assert "…" not in t


def test_kort_afkorter_ved_ord_og_rydder_tegnsaetning():
    assert side_tasks._kort("abc", 10) == "abc"
    assert side_tasks._kort("en to tre fire fem", 10) == "en to tre…"
    # Linjeskift og dobbelte mellemrum foldes, saa en flerlinjet tldr ikke
    # braekker bullet-listen.
    assert side_tasks._kort("en\n\n  to", 20) == "en to"
    # Et enkelt ord laengere end maks maa stadig afkortes.
    assert side_tasks._kort("a" * 30, 10) == "a" * 10 + "…"


# ── Automatikken: lukning naar arbejds-samtalen er gaaet i staa ───────────
#
# Bjoern 3/10: «opgaver markeres ikk automatisk sluttet». Linket fandtes, men
# intet lukkede noget. En lukning ved FOERSTE faerdige run ville ramme midt i
# et flerturs-arbejde — og `completed` er TERMINAL og kan ikke genaabnes.
# Derfor maales STILSTAND i stedet.

from datetime import UTC, datetime, timedelta


@pytest.fixture
def stilstand(monkeypatch):
    """Styr hvad samtalen sidst sagde noget. Returnerer en saetter i MINUTTER."""
    ur = {"sid": None, "min": 0.0}

    def _sidst(sid):
        if ur["sid"] is not None and sid != ur["sid"]:
            return None
        return (datetime.now(UTC) - timedelta(minutes=ur["min"])).isoformat()
    monkeypatch.setattr(side_tasks, "_sidst_aktiv", _sidst)
    return ur


def _aktiveret(lager, session="chat-arbejde"):
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session=session)
    return tid


def test_en_opgave_bliver_ventende_naar_samtalen_har_ligget_stille(lager, stilstand):
    tid = _aktiveret(lager)
    stilstand["min"] = 45.0
    ud = side_tasks.fej_faerdige()
    assert ud["lukket"] == 0 and ud["tilbage_til_venter"] == 1 and ud["ids"] == [tid]
    assert [t["side_task_id"] for t in side_tasks.list_open()] == [tid]
    assert lager[0]["status"] == "pending"
    assert "resolved_at" not in lager[0]


def test_en_opgave_lukkes_IKKE_mens_samtalen_er_i_gang(lager, stilstand):
    """Kernen i naadeperioden: en opgave kan tage flere ture, og en lukning
    midt i arbejdet kan ikke fortrydes."""
    _aktiveret(lager)
    stilstand["min"] = 3.0
    ud = side_tasks.fej_faerdige()
    assert ud == {"lukket": 0, "venter": 1, "uden_link": 0, "ids": [],
                  "vaagnet": 0, "booket": 0, "vaagnede_ids": []}
    assert len(side_tasks.list_open()) == 1


def test_graensen_er_praecis(lager, stilstand):
    """Lige under taersklen venter; lige over lukker. Vaelg én side og pin den."""
    _aktiveret(lager)
    stilstand["min"] = side_tasks.STILSTAND_MINUTTER - 0.1
    assert side_tasks.fej_faerdige()["lukket"] == 0
    stilstand["min"] = side_tasks.STILSTAND_MINUTTER + 0.1
    assert side_tasks.fej_faerdige()["tilbage_til_venter"] == 1


def test_en_PENDING_opgave_lukkes_aldrig_automatisk(lager, stilstand):
    """Den er ikke startet. En uberoert opgave er ikke en faerdig opgave —
    det ville slette hans huskeliste bag hans ryg.

    Posten faar et link MED VILJE, saa status-tjekket er det eneste der kan
    stoppe lukningen. Foerste udgave havde intet link, og saa blev den stoppet
    af link-tjekket i stedet — testen maalte ikke det den paastod."""
    side_tasks.flag(title="Ikke startet", prompt="…")
    lager[0]["arbejds_session"] = "chat-arbejde"
    assert lager[0]["status"] == "pending"
    stilstand["min"] = 999.0
    ud = side_tasks.fej_faerdige()
    assert ud == {"lukket": 0, "venter": 0, "uden_link": 0, "ids": [],
                  "vaagnet": 0, "booket": 0, "vaagnede_ids": []}, (
        "en pending opgave maa hverken lukkes eller taelles som ventende")
    assert len(side_tasks.list_open()) == 1


def test_en_opgave_UDEN_link_kan_ikke_lukkes_men_TAELLES(lager, stilstand):
    """De gamle opgaver blev startet foer linket fandtes. De skal ikke lukkes
    paa et gaet — men tallet skal kunne ses, saa man ved hvor mange der
    staar uden for automatikken."""
    tid = side_tasks.flag(title="Gammel", prompt="…")["side_task_id"]
    side_tasks.resolve(tid, decision="activated")  # ingen arbejds_session
    stilstand["min"] = 999.0
    ud = side_tasks.fej_faerdige()
    assert ud == {"lukket": 0, "venter": 0, "uden_link": 1, "ids": [],
                  "vaagnet": 0, "booket": 0, "vaagnede_ids": []}
    assert len(side_tasks.list_open()) == 1


def test_et_ULAESELIGT_tidsstempel_lukker_ikke(lager, monkeypatch):
    """«Ved ikke» maa ikke betyde «for laenge siden». En lukning paa et gaet
    er uigenkaldelig."""
    _aktiveret(lager)
    monkeypatch.setattr(side_tasks, "_sidst_aktiv", lambda _s: "ikke-en-dato")
    assert side_tasks.fej_faerdige() == {"lukket": 0, "venter": 1, "uden_link": 0,
                                         "ids": [], "vaagnet": 0, "booket": 0,
                                         "vaagnede_ids": []}
    monkeypatch.setattr(side_tasks, "_sidst_aktiv", lambda _s: None)
    assert side_tasks.fej_faerdige()["lukket"] == 0


def test_et_tidsstempel_i_FREMTIDEN_er_VED_IKKE(lager, monkeypatch):
    """Et ur der er gaaet forkert maa ikke blive en lukning.

    Vagten sidder i `_minutter_siden` og maales DER: gennem fejeren gav
    negative minutter samme udfald som `None` (venter), saa en test gennem
    fejeren bestod ogsaa uden vagten.
    """
    frem = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    assert side_tasks._minutter_siden(frem) is None, "fremtid skal vaere «ved ikke»"
    bagud = (datetime.now(UTC) - timedelta(minutes=42)).isoformat()
    assert 41.0 < (side_tasks._minutter_siden(bagud) or 0) < 43.0
    # Og gennem fejeren: den lukker ikke.
    _aktiveret(lager)
    monkeypatch.setattr(side_tasks, "_sidst_aktiv", lambda _s: frem)
    assert side_tasks.fej_faerdige()["lukket"] == 0


def test_fejningen_kaster_ALDRIG(lager, monkeypatch):
    """Den kaldes fra opstarten OG fra hver runs efterbehandling. En fejer der
    kaster ville vaelte begge."""
    _aktiveret(lager)
    monkeypatch.setattr(side_tasks, "_sidst_aktiv",
                        lambda _s: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert side_tasks.fej_faerdige()["lukket"] == 0
    monkeypatch.setattr(side_tasks, "list_open",
                        lambda: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert side_tasks.fej_faerdige()["lukket"] == 0


def test_taersklen_kan_overstyres_saa_den_kan_MAALES(lager, stilstand):
    """30 minutter er et udgangspunkt, ikke et maalt tal. Parameteren findes
    for at kunne proeve et andet uden en udrulning."""
    _aktiveret(lager)
    stilstand["min"] = 10.0
    assert side_tasks.fej_faerdige()["lukket"] == 0
    assert side_tasks.fej_faerdige(stilstand_minutter=5.0)["tilbage_til_venter"] == 1


# ── Visningen af ALLE opgaver, ogsaa de lukkede ──────────────────────────

def test_list_alle_viser_ogsaa_de_lukkede(lager):
    """Bjoern: «desk har ikk noget panel der viser opgaver der er flagged selv
    om jeg har trykket dem vaek». Maalt: alle seks poster i hans fil var
    terminale, saa kortet var korrekt TOMT — men umuligt at skelne fra tabt
    data. Persistensen virkede; visningen fandtes ikke."""
    a = side_tasks.flag(title="Lukket", prompt="…")["side_task_id"]
    b = side_tasks.flag(title="Aaben", prompt="…")["side_task_id"]
    side_tasks.resolve(a, decision="dismissed", reason="ikke laengere relevant")
    assert [r["side_task_id"] for r in side_tasks.list_open()] == [b]
    alle = {r["side_task_id"]: r["status"] for r in side_tasks.list_alle()}
    assert alle == {a: "dismissed", b: "pending"}


def test_list_alle_er_nyeste_foerst_og_har_et_loft(lager):
    for i in range(5):
        side_tasks.flag(title=f"nr {i}", prompt="…")
    alle = side_tasks.list_alle()
    assert [r["title"] for r in alle][0] == "nr 4" or len(alle) == 5
    assert len(side_tasks.list_alle(maks=2)) == 2
    assert len(side_tasks.list_alle(maks=0)) == 1, "et loft paa 0 giver mindst én"


# ── En lukning skal baere sin egen begrundelse (16/10-2026) ───────────────
#
# Bjoern: «Krav ved completed — men dismissed med begrundelse er altid en vej
# ud». Foer kraevede `completed` INTET. Det er derfor en sideopgave kunne
# lukkes uden belaeg, mens en MEMORY-sektion blev staaende og kaldte arbejdet
# «STADIG AABEN» laenge efter at det var gjort: lukningen og paastanden var to
# poster om samme faktum, og intet bandt dem sammen.


def test_completed_uden_bevis_afvises_og_roerer_ikke_status(lager):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    r = side_tasks.resolve(tid, decision="completed")
    assert r["status"] == "error" and "bevis" in r["error"]
    assert side_tasks.get(tid)["status"] == "pending", (
        "en AFVIST lukning maa ikke efterlade opgaven lukket"
    )


def test_completed_med_bevis_gemmer_beviset_paa_posten(lager):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    r = side_tasks.resolve(tid, decision="completed",
                           bevis="Commit 0ddcd976b landede paa main")
    assert r["status"] == "ok"
    assert side_tasks.get(tid)["bevis"] == "Commit 0ddcd976b landede paa main"


def test_kort_bevis_taelles_ikke_som_bevis(lager):
    """«ok» og «done» er paastande uden indhold — praecis dem kravet findes for."""
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    for tomt in ("", "   ", "ok"):
        assert side_tasks.resolve(tid, decision="completed", bevis=tomt)["status"] == "error"
    assert side_tasks.get(tid)["status"] == "pending"


def test_dismissed_uden_grund_afvises(lager):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    r = side_tasks.resolve(tid, decision="dismissed")
    assert r["status"] == "error" and "grund" in r["error"]
    assert side_tasks.get(tid)["status"] == "pending"


def test_dismissed_med_grund_er_altid_en_vej_ud(lager):
    """Selv en opgave der ALDRIG kan loeses skal kunne lukkes. Ellers er kravet
    en faelde uden udgang — samme fejlform som en `bloker`-post der spaerrer
    for de vaerktoejer der skulle rette den."""
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    r = side_tasks.resolve(tid, decision="dismissed", reason="kan ikke reproduceres")
    assert r["status"] == "ok"
    assert side_tasks.get(tid)["dismiss_reason"] == "kan ikke reproduceres"


def test_vaerktoejet_videresender_bevis_og_grund(lager):
    """Kravet skal ramme den vej Jarvis selv bruger — ikke kun servicen."""
    a = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    b = side_tasks.flag(title="B", prompt="goer B")["side_task_id"]
    assert side_tasks._exec_dismiss_side_task(
        {"side_task_id": a, "decision": "completed"})["status"] == "error"
    assert side_tasks._exec_dismiss_side_task(
        {"side_task_id": b, "decision": "dismissed"})["status"] == "error"
    assert side_tasks._exec_dismiss_side_task(
        {"side_task_id": a, "decision": "completed",
         "bevis": "Rettet i commit abc1234"})["status"] == "ok"
    assert side_tasks._exec_dismiss_side_task(
        {"side_task_id": b, "reason": "duplikat af A"})["status"] == "ok"


# ── Timeren: `not_before` (16/10-2026) ─────────────────────────────────────


def _om(sekunder: float) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) + timedelta(seconds=sekunder)).isoformat()


@pytest.fixture
def vaekninger(monkeypatch):
    """Falsk vækning-lager — bookinger, annulleringer og hvad der stadig venter."""
    from core.services import self_wakeup as sw
    bog = {"bookede": [], "annullerede": [], "ventende": set()}

    def _book(*, delay_seconds, prompt, reason="", extra="", session_id=None,
              task_id="", **kw):
        wid = f"wake-test{len(bog['bookede']) + 1}"
        bog["bookede"].append({"wakeup_id": wid, "delay_seconds": delay_seconds,
                               "prompt": prompt, "reason": reason,
                               "session_id": session_id, "task_id": task_id})
        bog["ventende"].add(wid)
        return {"status": "ok", "wakeup": {"wakeup_id": wid}}

    def _annuller(wid):
        bog["annullerede"].append(wid)
        bog["ventende"].discard(wid)
        return {"status": "ok", "wakeup_id": wid}

    monkeypatch.setattr(sw, "schedule_self_wakeup", _book)
    monkeypatch.setattr(sw, "cancel_wakeup", _annuller)
    monkeypatch.setattr(sw, "list_wakeups",
                        lambda *, status=None, limit=30: [{"wakeup_id": w}
                                                          for w in bog["ventende"]])
    return bog


def test_sovende_afledes_og_falder_mod_vaagen():
    """ÉN afledning, og fald-retningen er VÆK fra «sover».

    Et i stykker tidsstempel må ikke kunne skjule en opgave for evigt — den
    ville forsvinde fra «handlinger nu» uden at nogen så det.
    """
    assert side_tasks.sovende({"not_before": _om(3600)}) is True
    assert side_tasks.sovende({"not_before": _om(-3600)}) is False
    assert side_tasks.sovende({"not_before": "i morgen engang"}) is False
    assert side_tasks.sovende({}) is False
    assert side_tasks.sove_tekst({"not_before": _om(3600)}).startswith("sover til ")
    assert side_tasks.sove_tekst({}) == ""


def test_snooze_saetter_tiden_og_booker_en_vaekning(lager, vaekninger):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    r = side_tasks.snooze(tid, until=_om(3600), reason="efter deploy")
    assert r["status"] == "ok" and r["vaekning_id"]
    post = side_tasks.get(tid)
    assert side_tasks.sovende(post) is True
    assert post["snooze_reason"] == "efter deploy"
    # En udskydelse lukker INGEN opgave — den er stadig aaben.
    assert post["status"] == "pending"
    assert len(vaekninger["bookede"]) == 1
    assert vaekninger["bookede"][0]["task_id"] == tid


def test_snooze_afviser_fortid_igangvaerende_og_skrald(lager, vaekninger):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    assert side_tasks.snooze(tid, until=_om(-60))["status"] == "error"
    assert side_tasks.snooze(tid, until="i morgen")["status"] == "error"
    assert side_tasks.resolve(tid, decision="activated",
                              arbejds_session="chat-x")["status"] == "ok"
    r = side_tasks.snooze(tid, until=_om(3600))
    assert r["status"] == "error" and "igangvaerende" in r["error"]
    # Intet blev booket for en afvist udskydelse — der skal ikke staa en
    # vaekning tilbage for en opgave vi naegtede at udskyde.
    assert vaekninger["bookede"] == []


def test_vaagn_rydder_tiden_og_annullerer_vaekningen(lager, vaekninger):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(3600))
    vid = side_tasks.get(tid)["vaekning_id"]
    r = side_tasks.vaagn(tid)
    assert r["status"] == "ok" and r["vaekning_annulleret"] is True
    assert vid in vaekninger["annullerede"]
    assert "not_before" not in side_tasks.get(tid)
    assert side_tasks.vaagn(tid)["status"] == "error"


def test_en_lukket_opgave_vaekker_ingen(lager, vaekninger):
    """En lukning skal efterlade systemet uden noget der peger paa den."""
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(3600))
    vid = side_tasks.get(tid)["vaekning_id"]
    assert side_tasks.resolve(tid, decision="dismissed",
                              reason="ikke relevant")["status"] == "ok"
    assert vid in vaekninger["annullerede"]
    assert "not_before" not in side_tasks.get(tid)


def test_prompten_maerker_en_sovende_opgave(lager, vaekninger):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(3 * 3600))
    afsnit = side_tasks.side_tasks_prompt_section()
    assert "sover til" in afsnit and tid in afsnit


def test_fejeren_vaagner_naar_tiden_er_ind(lager, vaekninger):
    """KERNEN i timeren: `not_before` er SANDHEDEN, ogsaa naar vækningen svigter.

    Vækningen kan være fyret, sprunget over eller aldrig booket. Uden dette led
    ville ÉN tabt vækning efterlade opgaven sovende for evigt.
    """
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(3600))
    lager[0]["not_before"] = _om(-60)      # tiden gaar
    r = side_tasks.fej_faerdige()
    assert r["vaagnet"] == 1 and tid in r["vaagnede_ids"]
    assert "not_before" not in side_tasks.get(tid)
    assert side_tasks.sovende(side_tasks.get(tid)) is False


def test_fejeren_booker_naar_der_ikke_er_nogen_vaekning(lager, vaekninger):
    """En udskydelse uden en vækning skal ikke staa uden en — det er fejerens
    anden opgave, og den er grunden til at en udskydelse paa tre dage ogsaa
    bliver mindet om."""
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(7200))
    vaekninger["bookede"].clear()
    lager[0].pop("vaekning_id", None)
    r = side_tasks.fej_faerdige()
    assert r["booket"] == 1
    assert side_tasks.get(tid)["vaekning_id"]


def test_fejeren_booker_ikke_naar_ventende_ikke_kan_laeses(lager, vaekninger,
                                                           monkeypatch):
    """`None` og `set()` maa ikke mappes sammen.

    Kunne vi ikke laese hvad der venter, maa vi ikke booke en ny: vi ville ikke
    kunne se at der allerede staar én, og hver fejning ville laegge et led til.
    """
    from core.services import self_wakeup as sw
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(7200))
    vaekninger["bookede"].clear()

    def _braek(*a, **k):
        raise RuntimeError("kan ikke laese")

    monkeypatch.setattr(sw, "list_wakeups", _braek)
    r = side_tasks.fej_faerdige()
    assert r["booket"] == 0
    assert vaekninger["bookede"] == []


def test_udskydelse_over_24_timer_booker_ikke_endnu(lager, vaekninger):
    """Vækningens loft er 24 timer — det skal æres, ikke ties ihjel."""
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    side_tasks.snooze(tid, until=_om(3 * 86400))
    assert side_tasks.sovende(side_tasks.get(tid)) is True
    assert vaekninger["bookede"] == []
    assert not side_tasks.get(tid).get("vaekning_id")


def test_vaerktoejet_videresender_tiden(lager, vaekninger):
    tid = side_tasks.flag(title="A", prompt="goer A")["side_task_id"]
    assert side_tasks._exec_snooze_side_task(
        {"side_task_id": tid, "until": _om(1800)})["status"] == "ok"
    assert side_tasks._exec_wake_side_task({"side_task_id": tid})["status"] == "ok"


def test_flag_kan_rejses_med_en_tid(lager, vaekninger):
    r = side_tasks.flag(title="A", prompt="goer A", not_before=_om(1800))
    assert r["status"] == "ok"
    assert side_tasks.sovende(side_tasks.get(r["side_task_id"])) is True
    assert len(vaekninger["bookede"]) == 1
    # En passeret tid gemmes ikke som en sovende opgave — det ville se ud som
    # en indstilling der virkede, uden at goere noget.
    r2 = side_tasks.flag(title="B", prompt="goer B", not_before=_om(-60))
    assert "not_before" not in side_tasks.get(r2["side_task_id"])
    assert side_tasks.flag(title="C", prompt="goer C",
                           not_before="i morgen")["status"] == "error"
