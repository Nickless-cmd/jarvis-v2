"""De syv navngivne profiler — Fase 9.

Spec'en navngiver dem praecist: `visible-owner`, `visible-member`,
`jarvis-code`, `autonomous`, `maintenance`, `research`, `safe-offline`.
"""
import pytest

from core.runtime.profile_composer import SIKKERHEDS_AKSER, UKRAENKELIGE
from core.runtime.profiles import GRUND, PROFILER, byg, kendte

SPEC_NAVNE = (
    "visible-owner", "visible-member", "jarvis-code",
    "autonomous", "maintenance", "research", "safe-offline",
)


@pytest.mark.parametrize("navn", SPEC_NAVNE)
def test_hver_profil_spec_en_navngiver_findes(navn):
    assert navn in kendte()


def test_der_er_ikke_smuttet_flere_ind():
    """En profil er en sikkerhedsgraense. Kommer der én mere, skal den staa i
    spec'en foerst."""
    assert set(kendte()) == set(SPEC_NAVNE)


@pytest.mark.parametrize("navn", SPEC_NAVNE)
@pytest.mark.parametrize("akse", sorted(SIKKERHEDS_AKSER))
def test_ingen_profil_kan_give_mere_end_GRUNDEN(navn, akse):
    """Grunden saetter loftet. Kan en profil haeve sig over den, er loftet
    ikke et loft."""
    raekke = SIKKERHEDS_AKSER[akse]
    effektiv = byg(navn).felter.get(akse)
    if effektiv is None or GRUND.get(akse) is None:
        pytest.skip("aksen indgaar ikke")
    assert raekke.index(effektiv) >= raekke.index(GRUND[akse])


def test_safe_offline_er_den_mest_lukkede():
    """Den er sidste udvej. Er der en strammere profil, er navnet forkert."""
    so = byg("safe-offline").felter
    for navn in SPEC_NAVNE:
        andre = byg(navn).felter
        for akse, raekke in SIKKERHEDS_AKSER.items():
            if akse in so and akse in andre:
                assert raekke.index(so[akse]) >= raekke.index(andre[akse]), \
                    f"{navn} er strammere end safe-offline paa {akse}"


def test_safe_offline_kan_stadig_SVARE():
    """«Nul til alt» ville vaere ubrugeligt. Den skal kunne svare — den maa
    bare ikke raekke ud."""
    p = byg("safe-offline").felter
    assert p["tool_scope"] == "none"
    assert p["telemetry_sharing"] == "none"
    assert p["memory"] is True


@pytest.mark.parametrize("ukendt", ["", "  ", "findes-ikke", "visible_owner", None])
def test_et_UKENDT_navn_falder_til_safe_offline(ukendt):
    """Tvivl om hvilke regler der gaelder maa aldrig ende i de mest tilladte."""
    assert byg(ukendt).navn == "safe-offline"


def test_en_koerselsoverstyring_kan_indsnaevre():
    p = byg("visible-owner", overstyring={"tool_scope": "none"})
    assert p.felter["tool_scope"] == "none"


def test_en_koerselsoverstyring_kan_IKKE_udvide():
    """Det er komponistens regel, ikke en hoeflighed her — men netop derfor
    skal den ogsaa gaelde gennem denne vej."""
    p = byg("safe-offline", overstyring={"tool_scope": "all", "approval_mode": "never"})
    assert p.felter["tool_scope"] == "none"
    assert p.felter["approval_mode"] == "always"


@pytest.mark.parametrize("navn", SPEC_NAVNE)
def test_ingen_profil_slaar_revision_fra(navn):
    felter = byg(navn).felter
    for felt in UKRAENKELIGE:
        assert felter[felt] is True


@pytest.mark.parametrize("navn", SPEC_NAVNE)
def test_hver_profil_har_en_stabil_hash(navn):
    assert byg(navn).hash == byg(navn).hash
    assert len(byg(navn).hash) == 16


def test_to_forskellige_profiler_har_forskellig_hash():
    hashes = {byg(n).hash for n in SPEC_NAVNE}
    assert len(hashes) == len(SPEC_NAVNE), "to profiler kan ikke skelnes"


def test_en_koerselsoverstyring_VINDER_paa_ikke_sikkerheds_felter():
    """Overstyringen skal ligge SIDST. For sikkerhed er raekkefoelgen
    ligegyldig — man kan kun indsnaevre — og derfor saa mutations-proeven ikke
    at et ombyttet lag var forkert. For model og retry er den afgoerende: en
    koersel der beder om en anden model skal faa den, ikke profilens.
    """
    p = byg("visible-owner", overstyring={"model": "glm-5.2:cloud", "retry": 9})
    assert p.felter["model"] == "glm-5.2:cloud"
    assert p.felter["retry"] == 9
    assert p.lag[-1] == "overstyring", "overstyringen er ikke sidste lag"
