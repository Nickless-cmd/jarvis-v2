"""Jarvis' EGET forslag — lageret: gem, tag, kig.

## Hvad disse tests vogter

Forslaget hører til ÉN tur. Det lægges ned mens Jarvis er i turen, og hentes
når Bjørns felt er tomt og svaret er færdigt. To egenskaber bærer koblingen:

- **Éngangsbrug.** `tag_forslag` SLETTER rækken. Lå den og ventede, kunne
  næste turs slutning gribe et forslag skrevet til en samtale der er kørt
  videre — og vise ham et skridt der ikke passer længere. Et forældet bud er
  værre end intet bud.
- **Pr. session.** To samtaler må ikke kunne se hinandens forslag.

`kig_forslag` findes ved siden af, fordi værktøjets bekræftelse skal kunne
læse rækken tilbage UDEN at spise det forslag Bjørn endnu ikke har set.
"""
from __future__ import annotations

from core.runtime import db_composer_jarvis as dj


def test_gem_og_tag_returnerer_forslaget(isolated_runtime):
    fid = dj.gem_forslag(session_id="s1", forslag="Ret det og koer testene igen")
    assert fid.startswith("cj-")
    taget = dj.tag_forslag(session_id="s1")
    assert taget and taget["forslag"] == "Ret det og koer testene igen"


def test_forslaget_forbruges_ved_foerste_hentning(isolated_runtime):
    """Éngangsbrug: det hører til ÉN tur. Lå det og ventede, kunne næste turs
    slutning gribe et forslag skrevet til en samtale der er kørt videre."""
    dj.gem_forslag(session_id="s1", forslag="deploy det")
    assert dj.tag_forslag(session_id="s1") is not None
    assert dj.tag_forslag(session_id="s1") is None


def test_kig_forbruger_IKKE(isolated_runtime):
    """Bekræftelsen efter skriv må ikke spise det forslag Bjørn endnu ikke har set."""
    dj.gem_forslag(session_id="s1", forslag="deploy det")
    assert dj.kig_forslag(session_id="s1") is not None
    assert dj.tag_forslag(session_id="s1") is not None


def test_forslag_er_isolerede_pr_session(isolated_runtime):
    dj.gem_forslag(session_id="s1", forslag="til s1")
    dj.gem_forslag(session_id="s2", forslag="til s2")
    assert dj.tag_forslag(session_id="s2")["forslag"] == "til s2"
    assert dj.tag_forslag(session_id="s1")["forslag"] == "til s1"


def test_det_NYESTE_forslag_vinder(isolated_runtime):
    """Skrevet senere i turen = skrevet med mere af turen bag sig."""
    dj.gem_forslag(session_id="s1", forslag="det foerste", nu="2026-09-24T20:00:00+00:00")
    dj.gem_forslag(session_id="s1", forslag="det sidste", nu="2026-09-24T20:00:05+00:00")
    assert dj.tag_forslag(session_id="s1")["forslag"] == "det sidste"


def test_tomt_eller_langt_forslag_rensess(isolated_runtime):
    assert dj.gem_forslag(session_id="s1", forslag="   ") == ""
    assert dj.gem_forslag(session_id="", forslag="x") == ""
    langt = dj.gem_forslag(session_id="s1", forslag=" ".join(["ord"] * 100))
    assert langt
    tekst = dj.tag_forslag(session_id="s1")["forslag"]
    assert len(tekst) <= dj.MAKS_TEGN and not tekst.endswith(" ")


def test_omsluttende_anfoerselstegn_fjernes(isolated_runtime):
    """Modeller omslutter gerne forslaget i citationstegn. I Bjørns felt ville
    de stå som en del af beskeden."""
    dj.gem_forslag(session_id="s1", forslag='«Vis mig de to i karantaene»')
    assert dj.tag_forslag(session_id="s1")["forslag"] == "Vis mig de to i karantaene"


def test_aeldre_forslag_prunes_saa_hentning_efterlader_INTET(isolated_runtime):
    """Det ældre forslag må ikke ligge og vente bag det nyeste.

    Blev det ikke prunet, ville hentningen efter det nyeste give det GAMLE —
    et skridt fra en tur der er kørt videre. Garantien «forbrugt = intet»
    skal holde uanset hvor mange forslag der er skrevet i sessionen."""
    dj.gem_forslag(session_id="s1", forslag="det foerste", nu="2026-09-24T20:00:00+00:00")
    dj.gem_forslag(session_id="s1", forslag="det sidste", nu="2026-09-24T20:00:05+00:00")
    assert dj.tag_forslag(session_id="s1")["forslag"] == "det sidste"
    assert dj.tag_forslag(session_id="s1") is None
