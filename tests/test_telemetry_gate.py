"""Telemetri er ikke sandhed — Fase 10, kriterium 2.

    «telemetry records are classified separately from canonical truth, use
     mandatory export-copy redaction, tolerate loss/duplication honestly, and
     cannot authorize or settle work»
"""
from __future__ import annotations

import pytest

from core.services import telemetry_gate as t


@pytest.fixture(autouse=True)
def _rent_regnskab():
    t.nulstil_tab()
    yield
    t.nulstil_tab()


# --------------------------------------------------- taber AERLIGT

def test_beskaering_TAELLER_det_den_kaster_vaek():
    """Maalt paa runtime 13/9-2026: begge ringe i `decision_signal_telemetry`
    stod praecis paa 500/500 — de HAVDE kastet vaek, og der fandtes ikke ét tal
    for hvor meget. `list(...)[-500:]` taber i tavshed.

    Kriteriet siger «tolerate loss honestly». Ikke «undgaa tab» — tab er i orden
    for telemetri, det er netop forskellen paa telemetri og sandhed. Usynligt
    tab er ikke.
    """
    ud = t.beskaer(list(range(600)), 500, navn="ring")
    assert len(ud) == 500
    assert ud[0] == 100 and ud[-1] == 599, "beholdt de forkerte — skal vaere de NYESTE"
    assert t.tabt("ring") == 100


def test_tabet_akkumuleres_over_flere_runder():
    """Ét tal pr. beskaering ville kun sige hvad den SIDSTE runde tabte."""
    t.beskaer(list(range(600)), 500, navn="ring")
    t.beskaer(list(range(520)), 500, navn="ring")
    assert t.tabt("ring") == 120


def test_intet_tab_naar_der_er_plads():
    ud = t.beskaer(list(range(10)), 500, navn="ring")
    assert len(ud) == 10 and t.tabt("ring") == 0


def test_regnskabet_holdes_pr_ring():
    t.beskaer(list(range(600)), 500, navn="a")
    t.beskaer(list(range(700)), 500, navn="b")
    assert t.tabt() == {"a": 100, "b": 200}


def test_tabet_SIGES_i_loggen(caplog):
    """Et tal ingen ser er lige saa tavst som intet tal."""
    with caplog.at_level("INFO"):
        t.beskaer(list(range(600)), 500, navn="ring")
    # `getMessage()`, ikke `message % args` — den sidste braekker paa records
    # uden args, og min egen test roeg paa den.
    assert any("kastede 100 vaek" in r.getMessage() for r in caplog.records), \
        [r.getMessage() for r in caplog.records]


def test_decision_telemetry_BRUGER_den_taellende_beskaering():
    """Kilde-vagt. En taeller ingen kalder taeller ingenting.

    AST, ikke tekstsoegning: `beskaer` kunne staa i en kommentar.
    """
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path(
        "core/services/decision_signal_telemetry.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "_save"), None)
    assert fn is not None, "_save er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "beskaer" in kaldt, "_save beskaerer stadig i tavshed"


# ------------------------------------- adskilt fra kanonisk sandhed

def test_de_kanoniske_tabeller_er_kendte():
    for tabel in ("visible_runs", "agent_runs", "events", "costs", "audit"):
        assert t.er_kanonisk(tabel), f"{tabel} regnes ikke som kanonisk"


def test_telemetriens_eget_lager_er_IKKE_kanonisk():
    """Telemetri ligger i `state_store`, ikke i tabellerne. Adskillelsen fandtes
    allerede — men som et tilfaelde af lagring, ikke som en regel."""
    for ikke in ("state_store", "decision_signal_telemetry", "runtime_state"):
        assert not t.er_kanonisk(ikke)


def test_er_kanonisk_taaler_rod():
    assert t.er_kanonisk("  VISIBLE_RUNS  ")
    assert not t.er_kanonisk("")
    assert not t.er_kanonisk(None)  # type: ignore[arg-type]


# --------------------------------- kan ALDRIG autorisere eller afgoere

def test_telemetri_kan_ALDRIG_afgoere():
    """Telemetri er per definition ufuldstaendig: den taber (se ovenfor), den
    kan komme dobbelt, og den er afledt. En beslutning paa det grundlag kan
    ikke efterproeves bagefter."""
    assert t.maa_afgoere() is False


def test_ingen_telemetri_modul_kalder_en_godkendelses_vej():
    """Invarianten haandhaevet paa KILDEN, ikke kun paa en funktion der
    returnerer False. En invariant uden en vagt er en hensigt.

    Maalt foer: intet i huset lader telemetri autorisere arbejde. Denne test er
    til den dag nogen finder det praktisk.
    """
    import pathlib
    import re

    FORBUDT = re.compile(
        r"\b(execute_tool_force|owner_approval|set_trust|_runtime_trust_all|"
        r"approve_|grant_|authorize)\w*\s*\(")
    brud: list[str] = []
    for sti in pathlib.Path("core").rglob("*telemetry*.py"):
        tekst = sti.read_text()
        # kommentarer og docstrings taeller ikke — de BESKRIVER forbuddet
        kode = "\n".join(l for l in tekst.splitlines()
                         if not l.lstrip().startswith("#"))
        for m in FORBUDT.finditer(kode):
            brud.append(f"{sti}: {m.group(0)}")
    assert not brud, "telemetri kalder en godkendelses-vej:\n  " + "\n  ".join(brud)


# ------------------------------------------- eksport-kopi renses

def test_redigering_rammer_KOPIEN_ikke_originalen():
    """Ordet «copy» i kriteriet baerer det: en rensning der ramte originalen
    ville goere husets egen telemetri ubrugelig for at beskytte en udgaaende vej
    der ikke findes endnu."""
    original = {"m": "skriv til a@b.dk", "liste": ["Bearer abcdefghijkl"]}
    kopi = t.redigér_til_eksport(original)
    assert original["m"] == "skriv til a@b.dk", "originalen blev aendret"
    assert original["liste"][0] == "Bearer abcdefghijkl"
    assert kopi["m"] == "skriv til <email>"
    assert kopi["liste"][0] == "Bearer <token>"


@pytest.mark.parametrize("raa,forventet", [
    ("mail a@b.dk", "mail <email>"),
    ("cpr 010190-1234", "cpr <cpr>"),
    ("cpr 0101901234", "cpr <cpr>"),
    ("Bearer abcdefghijklmnop", "Bearer <token>"),
    ("noegle jvs_abcdefghijkl", "noegle <noegle>"),
    ("discord 1246415163603816499", "discord <langt-ciffer-id>"),
    ("kort 4111 1111 1111 1111", "kort <langt-ciffer-id>"),
])
def test_moenstrene_rammer(raa, forventet):
    assert t.redigér_til_eksport(raa) == forventet


def test_etiketten_LYVER_ikke():
    """Foerste udgave havde `<kortnummer>` (13-19 cifre) OG `<discord-id>`
    (17-20). De overlapper, det foerste vandt, og Bjoerns discord-id blev
    maerket «kortnummer».

    Det var stadig fjernet — men en rensnings-log man ikke kan stole paa er
    vaerre end en grovkornet én, fordi nogen bruger den til at lede efter et
    laek der ikke findes.
    """
    ud = t.redigér_til_eksport("1246415163603816499")
    assert "kortnummer" not in ud, "etiketten paastaar noget den ikke kan vide"


def test_almindelige_tal_roeres_IKKE():
    """En maske der aeder aarstal og maalinger goer telemetrien ubrugelig."""
    assert t.redigér_til_eksport("42 runder, 2026, 500 poster") == \
        "42 runder, 2026, 500 poster"


def test_redigering_gaar_gennem_hele_traeet():
    ind = {"a": ["x@y.dk", {"b": ("Bearer abcdefghijkl",)}]}
    ud = t.redigér_til_eksport(ind)
    assert ud["a"][0] == "<email>"
    assert ud["a"][1]["b"][0] == "Bearer <token>"
    assert isinstance(ud["a"][1]["b"], tuple), "typen blev byttet undervejs"


def test_redigering_roerer_ikke_ikke_tekst():
    ind = {"n": 42, "b": True, "tom": None}
    assert t.redigér_til_eksport(ind) == ind


# ------------------------------------------ maaleren skal se gaten

def test_profile_enforcement_FINDER_telemetri_gaten():
    """`profile_enforcement` ledte efter netop `gaeldende_niveau` her og
    rapporterede «ingen haandhaever»."""
    from core.runtime.profile_enforcement import maal
    post = maal({"telemetry_sharing": "none"})["telemetry_sharing"]
    assert post["kilde"] != "ingen haandhaever", "gaten findes nu — maaleren ser den ikke"


def test_ubestemt_bruger_giver_ubestemt_ikke_none(monkeypatch):
    """Samme regel som kryds-session-gaten: en umaalt vaerdi er ikke et maalt nej."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: "")
    assert t.gaeldende_niveau() == t.UBESTEMT


def test_gaeldende_niveau_kaster_aldrig(monkeypatch):
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    assert t.gaeldende_niveau() == t.UBESTEMT
