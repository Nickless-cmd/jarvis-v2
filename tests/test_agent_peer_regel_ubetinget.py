"""Peer-reglen skal staa i prompten UBETINGET — listen er det dynamiske element (22/11-2026).

MAALT 22/11-2026 i `agent_assignments`: et team oprettes SPREDT — op til 708 sekunder
mellem foerste og sidste soeskende i samme `parent_run_id`.

`send_message_to_agent` blev givet til alle kontraktagenter i `10e2c9d11`, saa den
tidlige agent KAN svare. Men `peer_section` returnerede tom streng naar listen var tom
VED PROMPT-KONSTRUKTIONEN — og saa stod den tidlige agent med et vaerktoej hun ikke
vidste hvad var, uden kendskab til at kanalen fandtes, og uden at vide at en soester
kunne dukke op senere. Vaerktoejet var der; instruksen manglede.

Det er samme fejlform som `_AGENT_COVERAGE_RULE`: mekanismen er monteret, men naar
aldrig frem i en form agenten faktisk laeser.
"""
from __future__ import annotations

from core.services.prompt_sections.agent_orchestration import peer_section


def test_en_agent_uden_peers_faar_alligevel_reglen():
    """Kaernen: tom liste maa ikke fjerne reglen — kun navnene."""
    tekst = peer_section([])
    assert tekst, "reglen forsvandt naar listen var tom — det er hele fejlen"
    assert "send_message_to_agent" in tekst, tekst
    assert "alene" in tekst.lower(), "agenten skal vide at hun er alene NU, ikke at kanalen er lukket"


def test_en_agent_med_peers_faar_navnene():
    tekst = peer_section(["agent-a", "agent-b"])
    assert "agent-a" in tekst and "agent-b" in tekst, tekst
    assert "send_message_to_agent" in tekst, tekst


def test_tomme_og_hvide_poster_taelles_ikke_som_peers():
    """En liste med kun tomme strenge er reelt tom — den maa ikke give en tom navneliste."""
    tekst = peer_section(["", "   ", None])  # type: ignore[list-item]
    assert "alene" in tekst.lower(), tekst
    assert "Dine peers i samme opgave (agent_id): ." not in tekst, tekst


def test_reglen_fortæller_at_en_soester_kan_dukke_op_senere():
    """Den tidlige agent skal vide at listen kan vokse — ellers giver reglen ingen mening."""
    tekst = peer_section([])
    assert "undervejs" in tekst.lower() or "senere" in tekst.lower(), tekst


def test_beskedens_form_er_nævnt_i_begge_tilstande():
    """`[fra <agent_id>]` er den form drainen leverer — agenten skal kunne genkende den."""
    for ids in ([], ["agent-a"]):
        tekst = peer_section(ids)
        assert "[fra <agent_id>]" in tekst, (ids, tekst)
