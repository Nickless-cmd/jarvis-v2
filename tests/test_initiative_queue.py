"""Initiativ-køen — Jarvis' egne impulser skal nå hans SYNLIGE samtale.

Rod (Bjørn 17. aug 2026): `[INITIATIV: …]` blev kun injiceret via
`_heartbeat_living_context_line()` → altså kun i HEARTBEAT-prompten. I den
faktiske samtale med Bjørn vidste Jarvis intet om sine egne initiativer.
Bjørne-drømme-initiativet blev derfor rejst 130 gange på fire måneder (76
markeret `acted` = postet til proaktivitets-kanalen som ingen læste), uden
nogensinde at blive til en samtale. Impulsen blev genereret, aldrig læst
tilbage — og derfor genereret igen.
"""
from __future__ import annotations

import core.services.initiative_queue as iq


def _fake(focus: str, *, priority: str = "medium", detected_at: str = "2026-08-17T18:47:00+00:00",
          first_seeded_at: str = "") -> dict[str, object]:
    return {
        "initiative_id": f"init-{abs(hash(focus)) % 9999}",
        "focus": focus,
        "priority": priority,
        "detected_at": detected_at,
        "first_seeded_at": first_seeded_at or detected_at,
    }


class TestInitiativesPromptSection:
    def test_ingen_initiativer_giver_ingen_sektion(self, monkeypatch):
        monkeypatch.setattr(iq, "get_pending_initiatives", lambda: [])
        assert iq.initiatives_prompt_section() is None

    def test_viser_initiativets_tekst(self, monkeypatch):
        monkeypatch.setattr(iq, "get_pending_initiatives", lambda: [
            _fake("Tilbagevendende drømme-tema: bjørn (3× på 7 dage) — værd at udforske?"),
        ])
        s = iq.initiatives_prompt_section()
        assert s is not None
        assert "bjørn" in s

    def test_markerer_gentagelse_naar_impulsen_er_gammel(self, monkeypatch):
        """Et initiativ der først blev rejst for måneder siden er ikke nyt —
        det er noget han bliver ved at vende tilbage til. Det SKAL være synligt."""
        monkeypatch.setattr(iq, "get_pending_initiatives", lambda: [
            _fake("drømme-tema: bjørn",
                  detected_at="2026-08-17T18:47:00+00:00",
                  first_seeded_at="2026-04-11T07:53:00+00:00"),
        ])
        s = iq.initiatives_prompt_section() or ""
        assert "2026-04-11" in s or "april" in s.lower()

    def test_frisk_impuls_markeres_ikke_som_gentagelse(self, monkeypatch):
        monkeypatch.setattr(iq, "get_pending_initiatives", lambda: [
            _fake("noget helt nyt",
                  detected_at="2026-08-17T18:47:00+00:00",
                  first_seeded_at="2026-08-17T18:40:00+00:00"),
        ])
        s = iq.initiatives_prompt_section() or ""
        assert "2026-04" not in s

    def test_prioriterer_og_begraenser_til_to(self, monkeypatch):
        monkeypatch.setattr(iq, "get_pending_initiatives", lambda: [
            _fake("lav ting", priority="low"),
            _fake("høj ting", priority="high"),
            _fake("mellem ting", priority="medium"),
            _fake("fjerde ting", priority="high"),
        ])
        s = iq.initiatives_prompt_section() or ""
        assert "høj ting" in s
        assert "lav ting" not in s          # capped: lavest prioritet falder ud
        assert s.count("•") <= 2

    def test_inviterer_men_kommanderer_ikke(self, monkeypatch):
        """Awareness, ikke ordre — han skal selv vælge om det passer nu."""
        monkeypatch.setattr(iq, "get_pending_initiatives", lambda: [_fake("noget")])
        s = (iq.initiatives_prompt_section() or "").lower()
        assert "du vælger" in s or "hvis det passer" in s

    def test_self_safe_ved_db_fejl(self, monkeypatch):
        def _boom():
            raise RuntimeError("db nede")
        monkeypatch.setattr(iq, "get_pending_initiatives", _boom)
        assert iq.initiatives_prompt_section() is None


# ---------------------------------------------------------------------------
# En kø mennesker skal svare på, må ikke fyldes med promptens eget indhold
#
# Målt 2026-09-05: 48 initiativer i køen — 6 ventende, 26 udløbet uden svar,
# NUL nogensinde godkendt eller afvist. Af de seks ventende var kun ÉN et
# rigtigt initiativ. To var output-kontrakten («Use JSON format with thought,
# initiative (null if no real next step), mode (optional).»), ét var et
# spørgsmål, to var tankefragmenter.
#
# Det gør mere skade her end i det indre liv: en kø fuld af promptens format
# er værre end en tom kø, fordi den ligner beslutninger der venter.
# ---------------------------------------------------------------------------

from core.services.initiative_queue import _er_ikke_et_initiativ as _port


def test_output_kontrakten_er_ikke_et_initiativ():
    assert _port("Use JSON format with thought, initiative (null if no real next step), mode (optional).")
    assert _port("Choose initiative only if there's a genuine next step.")
    assert _port("Return JSON with the following fields")


def test_et_spoergsmaal_er_ikke_et_forslag():
    """«What might the next move be?» beder om et svar, ikke om lov til at handle."""
    assert _port("What might the next move be?") == "spørgsmål"
    assert _port("Skal jeg rydde op i brain-grafen?") == "spørgsmål"


def test_tankefragment_uden_sammenhaeng_afvises():
    assert _port("Or since mode is clarify and there's an inner-conflict record") == "tankefragment"
    assert _port("Eller måske skulle jeg vente med det") == "tankefragment"


def test_udbyder_fejl_er_ikke_et_initiativ():
    assert _port(
        "Sorry, to prevent abuse of free resources, accounts that have not been "
        "recharged can only try 10 times."
    )


def test_aegte_initiativer_slipper_igennem():
    """Porten skal være konservativ — tvivlstilfælde beholdes."""
    for aegte in (
        "Slå det seneste bash-run op og sammenhold det med kode-æstetik-noten",
        "Ryd op i de 2,8 mio. temporale kanter i brain-grafen",
        "Skriv en opsummering af ugens arbejde til Bjørn",
        "Undersøg hvorfor cache-hitraten falder om aftenen",
    ):
        assert _port(aegte) == "", "afviste et ægte initiativ: %s" % aegte


def test_afvisning_returnerer_tom_id_uden_at_kaste(monkeypatch):
    from core.services import initiative_queue as Q

    hændelser: list = []
    monkeypatch.setattr(
        Q.event_bus, "publish",
        lambda kind, payload: hændelser.append((kind, payload)),
    )
    ud = Q.push_initiative(focus="Use JSON format with thought, initiative")
    assert ud == ""
    assert any(k == "heartbeat.initiative_rejected" for k, _p in hændelser), (
        "afvisningen skal være synlig i eventbussen — vi taber ikke noget i tavshed"
    )
