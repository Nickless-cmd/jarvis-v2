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
    tilfaelde = [
        ("lever-her", denne_proces(), False, "koerer i EN LEVENDE proces"),
        ("doed-proces", f"{vaert}:999999:123", True, "processen er vaek"),
        ("uden-maerke", "", True, "raekke fra foer migreringen"),
        ("anden-vaert", "en-anden-maskine:1:2", False, "kan ikke afgoeres"),
    ]
    for aid, maerke, _, _ in tilfaelde:
        db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
        db.update_agent_registry_entry(aid, status="active")
        # Skriv maerket direkte: stemplingen satte DENNE proces paa dem alle.
        with db.connect() as conn:
            conn.execute("UPDATE agent_registry SET runtime_owner=? WHERE agent_id=?",
                         (maerke, aid))

    recover_crashed_agents()

    for aid, _, skulle_fejes, hvorfor in tilfaelde:
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
