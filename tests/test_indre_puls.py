"""Vagten skal fange BEGGE retninger — og bøgerne der ikke stemmer.

24/9-2026: fire ægte fejl på én dag, alle af varighed dage til måneder, og
ingen af dem sagde til. Den vigtigste lære er at jeg designede vagten forkert
første gang: jeg byggede den mod *stoppede* ure, fordi det var det symptom jeg
lige havde set. Samme dag leverede systemet det modsatte — hjerteslaget tikkede
28 gange for hurtigt, og en aldersmåling ville have kaldt det friskt.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import indre_puls as ip


def test_et_ur_der_loeber_loebsk_fanges(monkeypatch) -> None:
    """DEN RETNING DER BLEV OVERSET.

    Hjerteslaget stod med 56 slag i et vindue hvor 2 var forventet. Hver eneste
    aldersbaserede måling ville have sagt «frisk» — værdien var jo splinterny.
    """
    p = ip.Puls("Hjerteslagets tik", "event", "heartbeat.phased_tick", 900.0)
    # 4 kadencer = 3600 s vindue → 4 forventede slag. 56 er langt over.
    monkeypatch.setattr(ip, "_antal", lambda *a, **k: 56)
    m = ip.maal_puls(p)
    assert m["tilstand"] == "loebsk", f"fik {m['tilstand']} — den løbske retning fanges ikke"
    assert m["antal"] == 56


def test_et_ur_der_staar_stille_fanges(monkeypatch) -> None:
    p = ip.Puls("Hjerteslagets tik", "event", "heartbeat.phased_tick", 900.0)
    monkeypatch.setattr(ip, "_antal", lambda *a, **k: 0)
    assert ip.maal_puls(p)["tilstand"] == "stille"


def test_en_normal_takt_er_frisk(monkeypatch) -> None:
    """Vagten må ikke melde på det normale — så bliver den slukket."""
    p = ip.Puls("Hjerteslagets tik", "event", "heartbeat.phased_tick", 900.0)
    monkeypatch.setattr(ip, "_antal", lambda *a, **k: 4)
    assert ip.maal_puls(p)["tilstand"] == "frisk"


def test_en_kv_noegle_uden_tidsstempel_melder_ikke(monkeypatch) -> None:
    """Fravær af et tidsstempel er ikke bevis for at uret står.

    Samme regel som `in_flight_runs._friskere_end`. En vagt der melder på
    manglende data melder på alt.
    """
    p = ip.Puls("Humørets ur", "kv", "mood_oscillator.state", 900.0)
    monkeypatch.setattr(ip, "_alder_af_kv", lambda n: None)
    assert ip.maal_puls(p)["tilstand"] == "ukendt"


def test_en_gammel_kv_noegle_er_stille(monkeypatch) -> None:
    p = ip.Puls("Humørets ur", "kv", "mood_oscillator.state", 900.0)
    monkeypatch.setattr(ip, "_alder_af_kv", lambda n: 900.0 * 7)
    assert ip.maal_puls(p)["tilstand"] == "stille"
    monkeypatch.setattr(ip, "_alder_af_kv", lambda n: 120.0)
    assert ip.maal_puls(p)["tilstand"] == "frisk"


def test_boegerne_der_ikke_stemmer_fanges(monkeypatch) -> None:
    """368 hændelser mod 3 bogførte — forhold 0,008 mod forventet 1,0.

    Begge tal fandtes i databasen i månedsvis. Begge var korrekte hver for sig.
    Ingen sammenlignede dem, og derfor så ingen at hjerteslaget arbejdede 122
    gange for hver gang det blev skrevet ned.
    """
    a = ip.Afstemning("Hjerteslagets bogføring", "heartbeat.phased_tick",
                      "heartbeat_runtime_ticks")

    def _falsk(tabel, tid, siden, hvor=None):
        return 368 if tabel == "events" else 3

    monkeypatch.setattr(ip, "_antal", _falsk)
    m = ip.maal_afstemning(a)
    assert m["tilstand"] == "uenig", "122:1 blev ikke fanget"
    assert m["forhold"] == 0.008


def test_boeger_der_stemmer_melder_ikke(monkeypatch) -> None:
    a = ip.Afstemning("Hjerteslagets bogføring", "heartbeat.phased_tick",
                      "heartbeat_runtime_ticks")
    # Efter rettelsen: 4 haendelser, 6 bogfoerte (opstarts-genopretning bogfoerer
    # ogsaa). Forhold 1,5 — inden for tolerancen, og det SKAL det vaere.
    monkeypatch.setattr(ip, "_antal",
                        lambda tabel, *a_, **k: 4 if tabel == "events" else 6)
    assert ip.maal_afstemning(a)["tilstand"] == "frisk"


def test_intet_arbejde_er_ikke_en_uenighed(monkeypatch) -> None:
    """Nul mod nul er ikke en fejl — ellers melder vagten hver nat."""
    a = ip.Afstemning("x", "k", "t")
    monkeypatch.setattr(ip, "_antal", lambda *a_, **k: 0)
    assert ip.maal_afstemning(a)["tilstand"] == "frisk"


def test_foerste_koersel_kvitterer_uden_at_larme(monkeypatch) -> None:
    """Syv kendte fejl må ikke drukne den ottende, ægte melding."""
    gemt: dict[str, object] = {}
    meldt: list[dict] = []
    monkeypatch.setattr(ip, "_gem_kvitterede", lambda s: gemt.update({"v": s}))
    monkeypatch.setattr(ip, "_kvitterede", lambda: set())
    monkeypatch.setattr(ip, "_meld", lambda m: meldt.append(m))
    monkeypatch.setattr(ip, "maal_puls",
                        lambda p, **k: {"navn": p.navn, "tilstand": "stille"})
    monkeypatch.setattr(ip, "maal_afstemning",
                        lambda a, **k: {"navn": a.navn, "tilstand": "frisk"})

    r = ip.tjek(foerste_koersel=True)
    assert meldt == [], "første kørsel larmede"
    assert r["kvitteret"], "den kvitterede ingenting"


def test_en_fejl_meldes_en_gang_men_igen_efter_den_er_rask(monkeypatch) -> None:
    """Ellers er valget mellem spam og tavshed."""
    tilstand = {"v": "stille"}
    kvitteringer: set[str] = set()
    meldt: list[str] = []
    monkeypatch.setattr(ip, "_kvitterede", lambda: set(kvitteringer))
    monkeypatch.setattr(ip, "_gem_kvitterede",
                        lambda s: (kvitteringer.clear(), kvitteringer.update(s)))
    monkeypatch.setattr(ip, "_meld", lambda m: meldt.append(str(m["navn"])))
    monkeypatch.setattr(ip, "maal_puls",
                        lambda p, **k: {"navn": "Humørets ur", "tilstand": tilstand["v"]})
    monkeypatch.setattr(ip, "maal_afstemning",
                        lambda a, **k: {"navn": a.navn, "tilstand": "frisk"})

    ip.tjek()
    assert meldt == ["Humørets ur"], "første fejl blev ikke meldt"
    ip.tjek()
    assert meldt == ["Humørets ur"], "samme fejl blev meldt igen"

    tilstand["v"] = "frisk"
    ip.tjek()
    tilstand["v"] = "stille"
    ip.tjek()
    assert meldt == ["Humørets ur", "Humørets ur"], (
        "et NYT udfald efter at pulsen var rask blev ikke meldt"
    )


def test_overfladen_melder_ikke(monkeypatch) -> None:
    """Centralens flade er en læsning. En flade der sender beskeder når nogen
    kigger, sender beskeder når nogen kigger."""
    meldt: list[object] = []
    monkeypatch.setattr(ip, "_meld", lambda m: meldt.append(m))
    monkeypatch.setattr(ip, "maal_puls",
                        lambda p, **k: {"navn": p.navn, "tilstand": "loebsk"})
    monkeypatch.setattr(ip, "maal_afstemning",
                        lambda a, **k: {"navn": a.navn, "tilstand": "uenig"})
    flade = ip.build_indre_puls_surface()
    assert meldt == []
    assert flade["daarlige"] == len(ip.PULSE) + len(ip.AFSTEMNINGER)
    assert "gale" in str(flade["summary"])


def test_registret_daekker_det_der_faktisk_gik_galt() -> None:
    """De fire fejl fra 24/9 skal være dækket — ellers har vi lært ingenting."""
    noegler = {p.noegle for p in PULSE_NAVNE()}
    assert "heartbeat.phased_tick" in noegler, "hjerteslaget vogtes ikke"
    assert "mood_oscillator.state" in noegler, "humøret vogtes ikke"
    afstemte = {a.event_kind for a in ip.AFSTEMNINGER}
    assert "heartbeat.phased_tick" in afstemte, "bøgerne afstemmes ikke"


def PULSE_NAVNE():
    return ip.PULSE


# ── Hændelsesdrevne tilstande (27/9-2026) ───────────────────────────────


def _base_med(tmp_path, monkeypatch, *, skrevet, drevet):
    """En base med én kv-nøgle og én driver-hændelse."""
    import sqlite3
    from contextlib import contextmanager

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE runtime_state_kv (key TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE events (kind TEXT, created_at TEXT)")
    if skrevet:
        conn.execute("INSERT INTO runtime_state_kv VALUES (?,?)", ("k", skrevet))
    if drevet:
        conn.execute("INSERT INTO events VALUES (?,?)", ("drv", drevet))
    conn.commit()

    @contextmanager
    def _c():
        yield conn

    monkeypatch.setattr("core.runtime.db.connect", _c)
    return conn


def _h():
    from core.services.indre_puls import Haendelsesdrevet
    return Haendelsesdrevet("Prøve", "k", "drv")


def test_driver_der_ikke_har_fyret_er_ikke_en_fejl(tmp_path, monkeypatch):
    """Ingen sansninger er ikke en fejl. Det var netop dén forveksling der
    sendte «Somatisk krop står stille» til Bjørns telefon hver stille nat."""
    from core.services.indre_puls import maal_haendelsesdrevet

    _base_med(tmp_path, monkeypatch, skrevet="2026-09-27T05:00:00+00:00", drevet=None)
    assert maal_haendelsesdrevet(_h())["tilstand"] == "frisk"


def test_noeglen_skrevet_lige_efter_driveren_er_frisk(tmp_path, monkeypatch):
    """Målt i produktionen 27/9: nøglen følger driveren med 49 MIKROsekunder."""
    from core.services.indre_puls import maal_haendelsesdrevet

    _base_med(tmp_path, monkeypatch,
              skrevet="2026-09-27T05:22:43.074460+00:00",
              drevet="2026-09-27T05:22:43.074411+00:00")
    ud = maal_haendelsesdrevet(_h())
    assert ud["tilstand"] == "frisk"
    # Seks decimaler i koden: med tre ville -49 µs blive til -0.0, og
    # målingen der viste hvor tæt koblingen er ville forsvinde i afrundingen.
    assert ud["bagud_s"] == -0.000049


def test_driveren_fyrede_men_tilstanden_fulgte_ikke_med(tmp_path, monkeypatch):
    """DEN ægte fejl: der SKETE noget, og kroppen reagerede ikke."""
    from core.services.indre_puls import maal_haendelsesdrevet

    _base_med(tmp_path, monkeypatch,
              skrevet="2026-09-27T05:00:00+00:00",
              drevet="2026-09-27T06:00:00+00:00")
    ud = maal_haendelsesdrevet(_h())
    assert ud["tilstand"] == "stille"
    assert ud["bagud_s"] == 3600.0


def test_naaden_taaler_en_langsom_skrivning(tmp_path, monkeypatch):
    """60 s er rigelig plads mod en målt afstand i mikrosekunder — stramt nok
    til at fange en brudt kobling, løst nok til at en travl skrivning ikke
    melder."""
    from core.services.indre_puls import maal_haendelsesdrevet

    _base_med(tmp_path, monkeypatch,
              skrevet="2026-09-27T05:00:00+00:00",
              drevet="2026-09-27T05:00:30+00:00")
    assert maal_haendelsesdrevet(_h())["tilstand"] == "frisk"


def test_de_to_er_flyttet_UD_af_pulse():
    """De havde en gættet kadence. `perceptual_event_engine` og
    `cognitive_episodes` har intet ur — de skriver når noget sker."""
    from core.services.indre_puls import HAENDELSESDREVNE, PULSE

    navne_puls = {p.navn for p in PULSE}
    assert "Somatisk krop" not in navne_puls
    assert "Driftsafvejning" not in navne_puls
    assert {h.navn for h in HAENDELSESDREVNE} == {"Somatisk krop", "Driftsafvejning"}


def test_meldingen_taler_om_driveren_og_ikke_om_en_kadence():
    """Den gamle tekst ville have sagt «et slag hvert 0. minut» og «Sidste
    spor: None», for en hændelsesdrevet tilstand har ingen kadence."""
    import inspect

    from core.services import indre_puls as M

    src = inspect.getsource(M._meld)
    assert 'm.get("kilde") == "haendelsesdrevet"' in src
    assert "følger ikke sin driver" in src
