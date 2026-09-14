"""Fire kørsler hang i ~900 sekunder og gav intet. Nu er der et loft.

## Målt 14/9-2026

Bjørn: «Den hænger bar på tænker..». Fire synlige kørsler samme aften:

    20:31:57 → 20:47:04   907 s
    20:35:52 → 20:51:00   908 s
    21:59:21 → 22:14:45   924 s
    22:08:43 → 22:24:23   940 s

`py-spy` fandt tråden i `ssl.read`, og `ss -tin` viste at der KOM bytes — ca.
41 hvert 8. sekund. Sporet afslørede hvad de var: «FIRST item efter 905.6s:
VisibleModelStreamDone» — en strøm der lukkede uden indhold. Keepalive, ikke
tekst.

Derfor kunne httpx' 60-sekunders læse-timeout aldrig fyre. **Den måler om der
kommer bytes. Ingen målte om der kom fremdrift.**

## Tærsklen kommer fra data

227 første-elementer over tre døgn. De 222 sunde: p95 = 25,3 s, p99 = 27,2 s,
max = 40,0 s. De fem syge lå alle på 900+. Loftet på 120 s ligger midt i et
tomrum på over tyve gange.
"""
from __future__ import annotations

import ast
import pathlib

from core.services import visible_run_firstpass as fp


# ────────────────────────────────────────────────────────────── selve loftet

def test_den_langsomste_MAALTE_sunde_koersel_slipper_igennem():
    """40,0 s er den langsomste sunde kørsel i tre døgn. Rammer loftet den,
    har vi lavet en fejlagtig afvisning ud af en rettelse."""
    assert not fp.loft_naaet(40.0)


def test_der_er_rigelig_luft_over_den_langsomste():
    """Tre gange den værste målte. En tærskel der lige akkurat klarer
    historikken vil fejle på den første kørsel der er en smule langsommere."""
    assert fp.FOERSTE_ELEMENT_LOFT_S >= 40.0 * 3


def test_de_syge_koersler_ville_vaere_blevet_fanget():
    """907, 908, 924 og 940 sekunder — alle fire."""
    for ventet in (907.0, 908.0, 924.0, 940.0):
        assert fp.loft_naaet(ventet), ventet


def test_loftet_fanger_7_gange_hurtigere_end_i_aften():
    """Pointen er ikke bare at fange det, men at fange det mens han stadig
    sidder der. 900 sekunder er femten minutter."""
    assert 907.0 / fp.FOERSTE_ELEMENT_LOFT_S >= 7.0


# ───────────────────────────────────────────────────── hjerteslaget skal ikke lyve

def test_hjerteslaget_paastaar_ikke_at_vide_hvor_ventetiden_ligger():
    """Den gamle kode sagde «prompt_assembly» uanset hvor længe der var gået —
    også efter ni minutter, hvor den beviseligt sad i udbyderens socket. Den
    løgn narrede mig selv under fejlsøgningen i aften."""
    for ventet in (1.0, 30.0, 90.0, 900.0):
        assert "assembly" not in fp.hjerteslag_fase(ventet), ventet


def test_en_normal_ventetid_ser_normal_ud():
    """p90 er 22,3 s. Et alarmerende ord dér ville gøre hver eneste kørsel
    skræmmende."""
    assert fp.hjerteslag_fase(6.8) == "afventer_foerste_svar"
    assert "usaedvanlig" not in fp.hjerteslag_fase(22.3)


def test_en_unormal_ventetid_siger_til():
    assert "usaedvanlig" in fp.hjerteslag_fase(60.0)


def test_opgiv_teksten_siger_HVEM_der_tav():
    """Uden udbyderens navn kan man ikke skelne «min prompt var for stor» fra
    «udbyderen svarede aldrig». Det var hele aftenens forvirring."""
    tekst = fp.opgiv_tekst(907.0, provider="deepseek", model="deepseek-v4-flash")
    assert "deepseek" in tekst
    assert "907" in tekst


# ───────────────────────────────────────────── og KALDER nogen det? (aftenens lektie)

def _generatoren() -> ast.AST:
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    for n in ast.walk(ast.parse(kilde)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_stream_visible_run":
            return n
    raise AssertionError("_stream_visible_run findes ikke laengere")


def _kaldte_navne(node: ast.AST) -> set[str]:
    ud = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                ud.add(f.attr)
            elif isinstance(f, ast.Name):
                ud.add(f.id)
    return ud


def test_loftet_er_faktisk_KOBLET_ind_i_stroemmen():
    """Aftenens dyreste lektie: en mutation der fjernede kaldet fra
    `start_listener` overlevede alle ni tests, fordi de kaldte funktionen selv.

    Her kan loopet ikke drives i en test — det ligger inde i en 5.000-linjers
    async-generator. Så dette er en kilde-vagt, og den er svagere end en ægte
    kørsel. Men den fanger præcis den fejl der ellers ville gøre hele filen
    til død kode: at loftet findes og ingen spørger det.
    """
    kaldt = _kaldte_navne(_generatoren())
    assert "loft_naaet" in kaldt, "loftet bliver aldrig spurgt"
    assert "hjerteslag_fase" in kaldt, "hjerteslaget bruger ikke den aerlige fase"
    assert "opgiv_tekst" in kaldt, "brugeren faar ingen besked naar loftet rammer"


def test_pumpen_standses_naar_loftet_rammer():
    """Ellers bliver kørslen 'afsluttet' på skærmen mens tråden bliver siddende
    i socket'en og holder forbindelsen — og så har vi flyttet lækagen i stedet
    for at lukke den."""
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    i = kilde.index("[firstpass-loft]")
    vindue = kilde[i - 900:i + 900]
    assert "controller.cancel()" in vindue
