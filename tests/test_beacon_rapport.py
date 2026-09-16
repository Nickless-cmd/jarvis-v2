"""Opgørelsen fra vaertens crash-beacon-log.

Det der kan gaa galt uden at nogen ser det:
  1. en genstart taelles ikke — og et haardt crash har intet ANDET spor
  2. pumpen laeses paa en haardkodet kanal (den flyttede fan5→fan2 15/9)
  3. to vinduer med forskellig proevetakt sammenlignes som om de var ens
"""
from datetime import datetime

from scripts.beacon_rapport import (
    find_genstarter, opgoer, parse_linje, proevetakt_sekunder, pumpekanal,
)

LINJE = (
    "2026-09-16T19:33:22+02:00 up=14651.24 load=0.85 pkgC=57.0 hotC=58.0 sysC=26.0 "
    "fan1=955,fan2=5648,fan3=0,fan4=0,fan5=1486,fan6=1485,fan7=0 "
    "in0=1.15V,in1=1.02V,in2=3.39V gpuW_C=11.61,38 memkB=27196332 streak=0"
)


def _linje(tid: str, up: float, *, pkg=50.0, fan2=5600, fan5=1400, gpu_w=12.0, gpu_c=40) -> str:
    return (f"{tid} up={up} load=0.5 pkgC={pkg} hotC={pkg} sysC=26.0 "
            f"fan1=900,fan2={fan2},fan5={fan5} "
            f"gpuW_C={gpu_w},{gpu_c} memkB=26000000 streak=0")


def test_en_linje_laeses_helt():
    p = parse_linje(LINJE)
    assert p is not None
    assert p.tid == datetime.fromisoformat("2026-09-16T19:33:22+02:00")
    assert p.uptime == 14651.24
    assert p.pkg_c == 57.0 and p.sys_c == 26.0
    # gpuW_C baerer TO tal i ét felt — watt og grader.
    assert p.gpu_w == 11.61 and p.gpu_c == 38.0
    assert p.blaesere["fan2"] == 5648.0


def test_linjer_uden_tidsstempel_springes_over():
    # Beacon'ens egne opstartsnoter er ikke maalinger. Taelles de med, forskyder
    # de proevetakten — og takten er det tal en sammenligning staar og falder med.
    assert parse_linje("beacon startet, pumpekanal=fan2") is None
    assert parse_linje("") is None
    assert parse_linje("2026-09-16T19:33:22+02:00 noget uden up") is None


def test_et_fald_i_uptime_ER_en_genstart():
    """Det eneste spor et haardt crash efterlader: journalen skriver intet."""
    proever = [parse_linje(_linje(t, up)) for t, up in [
        ("2026-09-16T01:00:00+02:00", 5000.0),
        ("2026-09-16T01:00:05+02:00", 5005.0),
        ("2026-09-16T01:02:00+02:00", 70.0),     # <- nede imellem
        ("2026-09-16T01:02:05+02:00", 75.0),
    ]]
    genstarter = find_genstarter([p for p in proever if p])
    assert len(genstarter) == 1
    assert genstarter[0].hour == 1 and genstarter[0].minute == 2


def test_stigende_uptime_er_ALDRIG_en_genstart():
    proever = [parse_linje(_linje(f"2026-09-16T01:00:{s:02d}+02:00", 100.0 + s))
               for s in (0, 5, 10, 15)]
    assert find_genstarter([p for p in proever if p]) == []


def test_pumpen_findes_som_den_hurtigste_kanal():
    # Haardkodet fan5 gav en falsk pumpealarm paa hans telefon 15/9-2026,
    # fordi pumpen var flyttet til fan2. Find den, vid den ikke.
    proever = [parse_linje(_linje(f"2026-09-16T01:00:{s:02d}+02:00", 100.0 + s,
                                  fan2=5600, fan5=1400)) for s in (0, 5, 10)]
    assert pumpekanal([p for p in proever if p]) == "fan2"

    flyttet = [parse_linje(_linje(f"2026-09-16T01:00:{s:02d}+02:00", 100.0 + s,
                                  fan2=1400, fan5=5600)) for s in (0, 5, 10)]
    assert pumpekanal([p for p in flyttet if p]) == "fan5"


def test_proevetakten_lader_sig_ikke_rykke_af_et_genstarts_hul():
    """Takten skal vaere 5 s ogsaa naar der ligger en nedetid midt i vinduet.

    ÆRLIG NOTE OM HVAD DENNE TEST KAN OG IKKE KAN.

    Funktionen har TO uafhaengige lag mod et genstarts-hul: vagten
    `if efter.uptime >= foer.uptime` kasserer hullet, og medianen er robust
    over for det. Jeg proevede dem hver for sig:

        vagt fjernet, median beholdt   → 5 s (groen)
        vagt beholdt, gennemsnit       → 5 s (groen)
        BEGGE fjernet                  → 76,25 s (ROED)

    Ét lag alene baerer altsaa resultatet, og derfor kan en test udefra ikke
    skelne dem. Det er baelte og seler, ikke en blind test — og forskellen er
    vaerd at skrive ned, for min foerste udgave af noten her PAASTOD at maale
    vagten, og det var forkert.

    Egenskaben testen holder fast i: takten maa ikke kunne rykkes af en
    enkelt nedetid. Falder begge lag, er tallet 76 s, og saa ville en
    sammenligning mellem to doegn vaere forkert uden at nogen kunne se det."""
    proever = [parse_linje(_linje(t, up)) for t, up in [
        ("2026-09-16T01:00:00+02:00", 5000.0),
        ("2026-09-16T01:00:05+02:00", 5005.0),
        ("2026-09-16T01:00:10+02:00", 5010.0),
        ("2026-09-16T01:05:00+02:00", 70.0),     # 290 s hul = nedetid, ikke takt
        ("2026-09-16T01:05:05+02:00", 75.0),
    ]]
    assert proevetakt_sekunder([p for p in proever if p]) == 5.0


def test_opgoerelsen_samler_det_der_skal_siges():
    proever = [parse_linje(_linje(f"2026-09-16T01:00:{s:02d}+02:00", 100.0 + s,
                                  pkg=40.0 + s, gpu_c=30 + s, gpu_w=10.0 + s))
               for s in (0, 5, 10, 15, 20)]
    r = opgoer([p for p in proever if p])
    assert r["proever"] == 5
    assert r["genstarter"] == []
    assert r["takt_s"] == 5.0
    assert r["cpu"]["maks"] == 60.0
    assert r["gpu_c"]["maks"] == 50.0
    assert r["pumpe_navn"] == "fan2"
    assert r["pumpe_min"] == 5600.0


def test_tomt_vindue_paastaar_ingenting():
    # «Ingen data» og «alt var roligt» er ikke det samme.
    assert opgoer([])["proever"] == 0
