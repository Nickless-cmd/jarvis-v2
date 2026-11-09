"""Referatets klip — det maa ikke skaere midt i et ord eller inde i markdown.

Maalt 9/11-2026 (Bjoerns observation, kl. 06:12):
    «Det er alle de afskåret hjerteslag beskeder… hvorfor lander de afskåret»

Maalt i `visible_runs`: alle seks seneste `text_preview` var PRÆCIS 320 tegn og
sluttede midt i et ord. Derefter klippede referatet igen ved 220 — råt, hvis
der ikke var et sætningsskel efter tegn 60. Resultatet var `**` og backtick der
stod åbent i det Bjørn så («Posten `visib», «Felt-te…»).

Disse tests fejler på begge dele.
"""

from __future__ import annotations

from core.services.autonomous_run_digest import _foerste_afsnit, byg_referat


def test_klippet_ender_ved_et_helt_ord():
    """Ingen fallback til råt klip: sidste ord skal være HELT."""
    lang = "ord " * 200
    ud = _foerste_afsnit(lang)
    assert ud.endswith("…")
    uden_ellipse = ud[:-1].rstrip()
    assert uden_ellipse.split(" ")[-1] == "ord", ud[-40:]


def test_uafsluttet_backtick_fjernes():
    """Det målte tilfælde: «Posten `visib» — en åben kode-token midt i et ord."""
    tekst = (
        "Jeg læste checkpointet direkte i stedet for at stole på statusfeltet. "
        "Posten `visible-47fc84e2178d43e1bbbe11d2a9d9a840` blev aldrig "
        "genoptaget, og det er målt i begge ender nu, så posten `visib"
    )
    ud = _foerste_afsnit(tekst)
    assert ud.count("`") % 2 == 0, ud


def test_uafsluttet_fed_markdown_fjernes():
    tekst = (
        "Det er målt i begge ender og der er ingen tvivl om at den her sætning "
        "fortsætter i lang tid endnu med mere og mere tekst **Beslutningen er "
        "gemt og aktiv:** `dec_be479ca703a4`"
    )
    ud = _foerste_afsnit(tekst)
    assert ud.count("**") % 2 == 0, ud
    assert ud.count("`") % 2 == 0, ud


def test_saetningsskel_bruges_stadig_naar_det_findes():
    lang = "Første sætning er færdig her. " * 20
    ud = _foerste_afsnit(lang)
    assert ud.endswith(".") and len(ud) <= 225


def test_kort_output_beholdes_uaendret():
    assert _foerste_afsnit("Kort og færdigt.") == "Kort og færdigt."


def test_referatet_baerer_ingen_uafluttet_markdown():
    """Ende-til-ende: det Bjørn ser, ikke kun uddraget."""
    tekst = (
        "Arbejdet ligger i field_theory/ og det er større end jeg havde i "
        "hovedet. **Det er et helt forskningsprojekt med otte protokoller og "
        "findings 001-006, og det hele står uændret med 27 markdown-filer"
    )
    ud = byg_referat(session_id="auto-heartbeat-1", output=tekst)
    assert ud.count("**") % 2 == 0, ud
    assert ud.count("`") % 2 == 0, ud
