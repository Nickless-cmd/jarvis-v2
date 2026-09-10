"""Ejerskabs-maerket der lader opstarts-fejningen skelne — Fase 6.

MAALT 10/9-2026: `jarvis-api` og `jarvis-runtime` koerer SAMME app
(`uvicorn apps.api.jarvis_api.app:app`), saa begge processer eksekverer
opstarts-hooken — inklusive `recover_crashed_agents()`, som doemte enhver
agent i `starting/active/blocked` som styrtet.

Registret havde intet ejerskabs-maerke, saa en genstart af den ene proces
kunne markere en agent der levede i den anden som `failed`. Kun ÉN agent af
198 er nogensinde ramt (og den talte ikke bagefter), fordi agenter er
kortlivede — men mekanismen var der, og et deploy genstarter begge units.
"""
from __future__ import annotations

import os
import socket

from core.services.process_identity import denne_proces, lever


def test_egen_proces_lever():
    m = denne_proces()
    assert m, "kunne ikke danne et maerke for min egen proces"
    assert m.startswith(socket.gethostname() + ":")
    assert lever(m) is True


def test_doed_pid_er_beviseligt_vaek():
    # 999999 ligger over det normale pid_max og findes ikke.
    assert lever(f"{socket.gethostname()}:999999:123") is False


def test_pid_genbrug_giver_ikke_falsk_liv():
    """Kernen i maerket. En NY proces med samme pid har en anden starttid, saa
    et gammelt maerke maa ikke se levende ud bare fordi pid'en er i brug igen."""
    ægte = denne_proces()
    host, pid, start = ægte.rsplit(":", 2)
    forfalsket = f"{host}:{pid}:{int(start) + 1}"
    assert lever(ægte) is True
    assert lever(forfalsket) is False, (
        "et maerke med forkert starttid saa levende ud — pid-genbrug ville "
        "kunne skjule en doed proces")


def test_uafgoerlige_former_giver_None():
    """`None` betyder «roer den ikke». Kalderen skal lade agenten vaere, saa
    TTL-udloebet tager den — en fejet LEVENDE agent mister arbejde uden spor."""
    for maerke, hvorfor in [
        ("", "tomt maerke (raekke fra foer migreringen)"),
        ("noget-uden-koloner", "ulaeselig form"),
        ("a:b", "for faa dele"),
        (f"{socket.gethostname()}:ikke-et-tal:1", "pid er ikke et heltal"),
        ("en-anden-maskine:1:2", "en anden host — /proc siger intet om den"),
    ]:
        assert lever(maerke) is None, hvorfor


def test_starttid_taaler_mellemrum_i_procesnavnet():
    """Felt 2 i /proc/<pid>/stat er kommandonavnet i parenteser og KAN indeholde
    mellemrum og parenteser. Splittes der paa mellemrum fra starten, forskubbes
    alle felter — og starttiden bliver forkert for netop de processer."""
    from core.services import process_identity as pi

    assert pi._starttid(os.getpid()).isdigit()
    assert pi._starttid(999999) == ""


# ── fejningen skal skaane naboprocessens levende agenter ────────────────

def test_fejning_skaaner_agent_der_lever_i_en_anden_proces(isolated_runtime):
    """Selve hullet, i adfaerd: fire agenter, fire ejerskabs-tilstande.

    Kun de to hvor processen er BEVISELIGT vaek — eller hvor der aldrig var
    et maerke (raekker fra foer migreringen, hvor vi beholder den gamle
    opfoersel) — maa doemmes.
    """
    import core.runtime.db_agent_runtime as db
    from core.services.agent_runtime_spawn import recover_crashed_agents

    vaert = socket.gethostname()
    gammel = "2020-01-01T00:00:00+00:00"
    tilfaelde = [
        ("lever-her", denne_proces(), None, False, "koerer i EN LEVENDE proces"),
        ("doed-proces", f"{vaert}:999999:123", None, True, "processen er vaek"),
        # Jarvis' fund: under «tomt maerke» gemmer der sig TO situationer.
        ("gammel-uden-maerke", "", gammel, True, "raekke fra foer migreringen"),
        ("frisk-uden-maerke", "", None, False,
         "en LEVENDE agent hvis proces ikke kunne stemple sig"),
        ("anden-vaert", "en-anden-maskine:1:2", None, False, "kan ikke afgoeres"),
    ]
    for aid, maerke, roert, _, _ in tilfaelde:
        db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
        db.update_agent_registry_entry(aid, status="active")
        # Skriv maerket direkte: stemplingen satte DENNE proces paa dem alle.
        with db.connect() as conn:
            conn.execute("UPDATE agent_registry SET runtime_owner=? WHERE agent_id=?",
                         (maerke, aid))
            if roert:
                conn.execute("UPDATE agent_registry SET updated_at=? WHERE agent_id=?",
                             (roert, aid))

    recover_crashed_agents()

    for aid, _, _, skulle_fejes, hvorfor in tilfaelde:
        status = str(db.get_agent_registry_entry(aid)["status"])
        if skulle_fejes:
            assert status == "failed", f"{aid} blev IKKE fejet, men {hvorfor}"
        else:
            assert status == "active", (
                f"{aid} blev fejet selvom {hvorfor} — en levende agent mistede "
                "sit arbejde uden spor")


def test_stemplet_saettes_ved_aktivering_og_ryddes_ved_afslutning(isolated_runtime):
    """Stemplet skal saettes dér hvor agenten begynder at koere, og ryddes naar
    den er faerdig — ellers slaeber en afsluttet agent en doed pid med sig."""
    import core.runtime.db_agent_runtime as db

    db.create_agent_registry_entry(agent_id="a", role="r", goal="g")
    assert db.get_agent_registry_entry("a")["runtime_owner"] == "", (
        "en agent oprettes som queued/planned og maa ikke baere et maerke endnu")

    for status in ("starting", "active", "blocked"):
        db.update_agent_registry_entry("a", status=status)
        assert db.get_agent_registry_entry("a")["runtime_owner"] == denne_proces(), (
            f"status={status} er en KOERENDE tilstand og skal baere maerket")

    db.update_agent_registry_entry("a", status="completed")
    assert db.get_agent_registry_entry("a")["runtime_owner"] == ""


def test_maerket_degraderer_i_stedet_for_at_blive_tomt():
    """Jarvis' fund, praeciseret. Faldt `denne_proces()` tilbage til TOMT naar
    starttiden ikke kunne laeses, ville en levende proces komme til at ligne en
    raekke fra foer migreringen — og dens agenter blive fejet af netop det vaern
    der er bygget mod det.

    Derfor degraderer den til starttid `0`: pid'en kan stadig efterproeves,
    bare uden vaernet mod pid-genbrug.
    """
    from core.services import process_identity as pi

    original = pi._starttid
    try:
        pi._starttid = lambda _pid: ""     # /proc svarer ikke
        m = pi.denne_proces()
    finally:
        pi._starttid = original

    assert m, "maerket blev TOMT — en levende proces ligner nu en gammel raekke"
    assert m.endswith(":0")
    # Med et laesbart /proc igen: `0` betyder «starttid ukendt», og pid'ens
    # blotte eksistens raekker. Er /proc STADIG ulaeseligt, svarer `lever()`
    # None — og et ikke-tomt maerke med None faar fejningen til at springe
    # over. Begge veje skaaner den levende agent, hvilket er hele pointen.
    assert pi.lever(m) is True
    assert pi.lever(m.rsplit(":", 2)[0] + ":999999:0") is False, (
        "et degraderet maerke maa stadig kunne vise at processen er VAEK")


def test_docstring_og_kode_er_enige_om_tomt_maerke():
    """Fundet var en SAETNING der ikke var sand: dokumentet lovede at et
    uafgoerligt maerke skaanede agenten, mens kaldstedet fejede det tomme.

    Testen holder de to sammen om det der faktisk gaelder.
    """
    from core.services import process_identity as pi

    assert lever("") is None                       # formen kan ikke afgoeres ...
    tekst = (pi.__doc__ or "") + (pi.lever.__doc__ or "")
    assert "foer migreringen" in tekst, (
        "dokumentet forklarer ikke at TOMT betyder noget andet end uafgoerligt")
