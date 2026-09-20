"""Nudgen der ser HANS kald — den halvdel der manglede.

Bjørn bad 6/9-2026 om en mekanisme der «nudgeder dig **i runet**». Det der blev
bygget, læste hans egen besked i prompt-assembly, altså før turen gik i gang.
Den her hænger i `_finalize_call` og ser hvert værktøjskald efter det er kørt.

Den farligste fejl her er ikke en manglende note. Det er en note der fyrer for
tit: en kanal man lærer at overse, er værre end ingen kanal. Derfor handler
halvdelen af testene om hvornår den skal TIE.
"""
from __future__ import annotations

import pytest

from core.services import tool_hunt_nudge as n


@pytest.fixture(autouse=True)
def _ren_tur():
    n._GRAVNINGER.clear()
    n._SAGT.clear()
    n._UDESTAAENDE.clear()
    yield
    n._GRAVNINGER.clear()
    n._SAGT.clear()
    n._UDESTAAENDE.clear()


# ── regel 3: park det i stedet for at glemme det ───────────────────────────

def test_TODO_i_det_han_laeste_foreslaar_en_sideopgave():
    note = n.note(navn="read_file", argumenter={"path": "x.py"}, run_id="r3",
                  resultat_tekst="# TODO ryd op\n# FIXME den her er gal")
    assert "flag_side_task" in note


def test_ÉT_maerke_er_ikke_et_moenster():
    assert n.note(navn="read_file", argumenter={"path": "x.py"}, run_id="r3",
                  resultat_tekst="# TODO engang") == ""


def test_har_han_SELV_flagget_noget_mindes_han_ikke_om_det():
    n.note(navn="flag_side_task", argumenter={"title": "ryd op"}, run_id="r4")
    assert n.note(navn="read_file", argumenter={"path": "x.py"}, run_id="r4",
                  resultat_tekst="TODO a\nFIXME b") == ""


# ── regel 4: en fil på containeren er ikke en fil Bjørn har ────────────────

def test_en_AFLEVERING_skal_udgives():
    note = n.note(navn="write_file", argumenter={"path": "/home/bs/rapport.md"}, run_id="r5")
    assert "publish_file" in note and "rapport.md" in note


@pytest.mark.parametrize("sti", [
    "docs/superpowers/specs/2026-09-20-x.md",   # hans eget arbejde i repoet
    "/media/projects/jarvis-v2/core/x.md",
    "tests/test_x.py",
    "/home/bs/script.py",                        # kode er ikke en aflevering
])
def test_KODE_og_repo_filer_er_ikke_afleveringer(sti):
    assert n.note(navn="write_file", argumenter={"path": sti}, run_id="r6") == ""


def test_har_han_SELV_udgivet_mindes_han_ikke_om_det():
    n.note(navn="publish_file", argumenter={"path": "/home/bs/a.md"}, run_id="r7")
    assert n.note(navn="write_file", argumenter={"path": "/home/bs/b.md"}, run_id="r7") == ""


# ── vagterne ───────────────────────────────────────────────────────────────

def test_HOEJST_én_note_pr_tur():
    """To noter i samme tur er ikke en påmindelse, det er en afbrydelse."""
    foerste = n.note(navn="write_file", argumenter={"path": "/home/bs/a.md"}, run_id="r8")
    assert foerste
    anden = n.note(navn="read_file", argumenter={"path": "x.py"}, run_id="r8",
                   resultat_tekst="TODO a\nFIXME b")
    assert anden == ""


def test_kontakten_slukker_det_hele(monkeypatch):
    monkeypatch.setattr(n, "_taendt", lambda: False)
    assert n.note(navn="write_file", argumenter={"path": "/home/bs/a.md"}, run_id="r9") == ""


def test_en_FEJL_koster_aldrig_et_vaerktoejsresultat(monkeypatch):
    """Noten er en bekvemmelighed. Vælter den et kald, har den kostet mere
    end den nogensinde kan give."""
    monkeypatch.setattr(n, "_leverbar_fil",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert n.note(navn="write_file", argumenter={"path": "/home/bs/a.md"}, run_id="r10") == ""


def test_ryd_tur_glemmer_turen():
    n.note(navn="write_file", argumenter={"path": "/home/bs/a.md"}, run_id="r11")
    n.ryd_tur("r11")
    assert n.note(navn="write_file", argumenter={"path": "/home/bs/b.md"}, run_id="r11") != ""


def test_krogen_er_FAKTISK_haengt_paa_i_executoren():
    """Den fælde huset kender bedst: bygget, korrekt — og ingen kalder den."""
    import inspect

    from core.services import simple_tool_executor as ex
    kilde = inspect.getsource(ex._finalize_call)
    assert "tool_hunt_nudge" in kilde
    # EFTER cache-lagringen: cachen skal gemme værktøjets svar, ikke en note.
    assert kilde.index("store_result") < kilde.index("tool_hunt_nudge")


def test_en_fil_i_TMP_er_undervejs_ikke_afleveret():
    assert n.note(navn="write_file", argumenter={"path": "/tmp/jarvis-bro-test/test.txt"},
                  run_id="r12") == ""


# ── målingen: tog han imod? ────────────────────────────────────────────────
#
# Spec'ens mål nummer fire fra 6/9-2026 — «Lærer af sine egne hits» — blev
# aldrig bygget. Uden det tal ved vi kun at vi HAR sagt noget, og en
# eskalering ville straffe ham for at ignorere en note der måske var forkert.
# Tørløbet 20/9 viste hvorfor: tre ud af fire af de første noter var forkerte.


def _svar(monkeypatch) -> list[tuple[str, dict]]:
    sendt: list[tuple[str, dict]] = []
    monkeypatch.setattr(n, "_log_svar", lambda udfald, noegle, sag: sendt.append((udfald, sag)))
    return sendt


def test_kalder_han_vaerktoejet_er_det_et_JA(monkeypatch):
    sendt = _svar(monkeypatch)
    n.note(navn="write_file", argumenter={"path": "/home/bs/r.md"}, run_id="t1")
    n.note(navn="publish_file", argumenter={"path": "/home/bs/r.md"}, run_id="t1")
    assert [u for u, _ in sendt] == ["hit"]
    assert sendt[0][1]["slags"] == "udgiv"


def test_gaar_der_seks_kald_uden_er_det_et_NEJ(monkeypatch):
    sendt = _svar(monkeypatch)
    n.note(navn="write_file", argumenter={"path": "/home/bs/r.md"}, run_id="t2")
    for _ in range(n.MISS_EFTER):
        n.note(navn="read_file", argumenter={"path": "x.py"}, run_id="t2")
    assert [u for u, _ in sendt] == ["miss"]


def test_et_UBESVARET_nudge_er_hverken_ja_eller_nej(monkeypatch):
    """Han kan stadig nå at gøre det. Talte vi det som et nej, ville korte
    ture se ud som ulydighed."""
    sendt = _svar(monkeypatch)
    n.note(navn="write_file", argumenter={"path": "/home/bs/r.md"}, run_id="t3")
    n.note(navn="read_file", argumenter={"path": "x.py"}, run_id="t3")
    assert sendt == []


def test_turens_afslutning_goer_et_ubesvaret_til_et_nej(monkeypatch):
    sendt = _svar(monkeypatch)
    n.note(navn="write_file", argumenter={"path": "/home/bs/r.md"}, run_id="t4")
    n.ryd_tur("t4")
    assert [u for u, _ in sendt] == ["miss"]


def test_hukommelsen_vokser_ikke_i_det_uendelige():
    """Ingen krog fyrer ved turens afslutning — R2.5 har samme hul. Så loftet
    er det der holder, ikke oprydningen."""
    for i in range(n._MAKS_TURE + 20):
        n.note(navn="write_file", argumenter={"path": "/home/bs/r.md"}, run_id=f"t-{i}")
    assert len(n._UDESTAAENDE) <= n._MAKS_TURE


def test_rapporten_regner_andelen_af_dem_der_SVAREDE(monkeypatch):
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.recent_by_family",
        lambda family, limit=50: [
            {"kind": "tool_discovery.hunt_nudge", "payload": {"slags": "udgiv"}},
            {"kind": "tool_discovery.hunt_nudge", "payload": {"slags": "udgiv"}},
            {"kind": "tool_discovery.hunt_nudge", "payload": {"slags": "udgiv"}},
            {"kind": "tool_discovery.hunt_hit", "payload": {"slags": "udgiv"}},
            {"kind": "tool_discovery.hunt_miss", "payload": {"slags": "udgiv"}},
        ],
    )
    r = n.rapport()
    assert r["noter"] == 3 and r["ja"] == 1 and r["nej"] == 1
    # Den tredje er ubesvaret og tæller hverken med eller imod.
    assert r["andel_taget_imod"] == 0.5


def test_rapporten_kaster_aldrig(monkeypatch):
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.recent_by_family",
        lambda family, limit=50: (_ for _ in ()).throw(RuntimeError("basen er nede")))
    assert n.rapport()["noter"] == 0


# ── R5: han bad om et værktøj der ikke findes ──────────────────────────────
#
# Målt 20/9-2026 over 14 døgn: 9 ukendte navne mod 30 kendte — hver fjerde
# by-name-forespørgsel rammer ved siden af. I én tur prøvede han
# `memory_delete_line`, `delete_memory_line`, `memory_remove_line` og
# `memory_line_delete`: fire stavemåder af et værktøj han fandt på.

def test_et_navn_der_ikke_findes_faar_de_naermeste_der_goer():
    note = n.note(navn="load_more_tools", argumenter={"names": ["memory_delete_line"]},
                  run_id="u1", resultat_tekst="tools not found: memory_delete_line")
    assert "memory_delete_line` findes ikke" in note
    assert "Nærmeste der gør" in note and "pause_and_ask" in note


def test_et_navn_der_FINDES_giver_ingen_note():
    assert n.note(navn="load_more_tools", argumenter={"names": ["read_file"]},
                  run_id="u2", resultat_tekst="ok") == ""


def test_uden_fejl_i_svaret_siges_der_intet():
    """Værktøjets eget svar er signalet. Uden det gætter vi."""
    assert n.note(navn="load_more_tools", argumenter={"names": ["findes_ikke_xyz"]},
                  run_id="u3", resultat_tekst="loaded 1 tool") == ""


# ── R6: tredje skema-gæt ───────────────────────────────────────────────────

def test_tredje_skema_gaet_peger_paa_at_slaa_skemaet_op():
    fejl = "Error: no such table: heartbeat_ticks"
    for _ in range(n.SKEMA_GRAENSE - 1):
        assert n.note(navn="bash", argumenter={"command": "sqlite3 x"},
                      run_id="s1", resultat_tekst=fejl) == ""
    note = n.note(navn="bash", argumenter={"command": "sqlite3 x"},
                  run_id="s1", resultat_tekst=fejl)
    assert "db_query" in note and "sqlite_master" in note


def test_én_skema_fejl_er_ikke_et_moenster():
    assert n.note(navn="bash", argumenter={"command": "sqlite3 x"}, run_id="s2",
                  resultat_tekst="Error: no such column: foo") == ""


# ── R8: anden søgning uden træf ────────────────────────────────────────────

def test_anden_tomme_soegning_foreslaar_at_han_spoerger():
    """Den ærlige udgave: første udgave talte HVER søgning — også dem der
    lykkedes. Et tomt resultat er selve signalet om at søgningen slog fejl."""
    assert n.note(navn="search", argumenter={"pattern": "x"}, run_id="q1",
                  resultat_tekst="[no matches]") == ""
    note = n.note(navn="search", argumenter={"pattern": "y"}, run_id="q1",
                  resultat_tekst="[no matches]")
    assert "pause_and_ask" in note


def test_en_soegning_MED_traef_taeller_ikke():
    for _ in range(5):
        assert n.note(navn="search", argumenter={"pattern": "x"}, run_id="q2",
                      resultat_tekst="core/x.py:12: fundet") == ""


# ── R7: udgiv-reglen efter målingen ────────────────────────────────────────

def test_TMP_er_ikke_udelukket_laengere():
    """Mit første gæt var at `/tmp` var skrabbe. Målingen modsagde det:
    `/tmp/xlsxwork/ugedage.xlsx` blev faktisk udgivet til Bjørn."""
    assert n.note(navn="write_file", argumenter={"path": "/tmp/xlsxwork/ugedage.xlsx"},
                  run_id="w1") != ""


@pytest.mark.parametrize("sti", [
    "/tmp/commit_msg_abc.md",      # netop den arbejdsgang CLAUDE.md påbyder
    "/tmp/merge_msg.md",
    "/home/bs/test-rapport.md",
    "/tmp/rediger-mig.md",
])
def test_arbejdsfiler_er_ikke_afleveringer(sti):
    """Af 45 træf i første udgave var 12 commit-beskeder og 6 testfixtures."""
    assert n.note(navn="write_file", argumenter={"path": sti}, run_id="w2") == ""


# ── R9: han startede noget der kører videre ────────────────────────────────

def test_baggrundsarbejde_uden_en_wakeup_bliver_paamindet():
    """Målt 20/9-2026: 20 ture startede baggrundsarbejde, 15 af dem satte
    ALDRIG en wakeup. Arbejdet kører, turen slutter, ingen kommer tilbage."""
    note = n.note(navn="run_in_background", argumenter={"command": "pytest"}, run_id="v1")
    assert "schedule_self_wakeup" in note


def test_har_han_ALLEREDE_sat_en_wakeup_siges_der_intet():
    n.note(navn="schedule_self_wakeup", argumenter={"when": "+1h"}, run_id="v2")
    assert n.note(navn="run_in_background", argumenter={"command": "pytest"}, run_id="v2") == ""


def test_et_almindeligt_kald_udloeser_den_ikke():
    assert n.note(navn="bash", argumenter={"command": "pytest -q"}, run_id="v3") == ""
