"""Matrix-ensemblet skal tale i hans prompt — når de har noget at sige, og ikke ellers.

Bjørn 19. aug 2026: "hver karakter har en funktion der skal hjælpe jarvis. og de skal
dukke op realtime i hans prompt til at guide og huske og korrigere og eskalere... og de
skal ikk stå der hele tiden, men komme og gå efter behov og nødvendighed."

Før: karaktererne blev skrevet til nudge-brønden af `push_active_character_nudges()` —
kaldt på linje ~2852 i prompt_contract, mens nudge-sektionen bygges på ~1241. Beskederne
kunne altså ALDRIG nå den prompt de blev skabt i, og prompten fik kun et tal:
"🎬 Matrix: 3 karakter(er) har meldinger". Brønden pensionerede dem derefter efter
median 26 sekunder. 78 beskeder skrevet, nul læst.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.central_matrix_ensemble as me


class TestKommerOgGaar:
    def test_ingen_aktive_giver_ingen_sektion(self):
        """De skal ikke stå der hele tiden."""
        with patch.object(me, "active_character_voices", return_value=[]):
            assert me.build_matrix_voices_section() is None

    def test_aktiv_karakter_taler_med_egne_ord(self):
        v = [{"cid": "trinity", "label": "[💜 Trinity]", "line": "Det her er rigtigt.",
              "unaddressed": 0, "text": "[💜 Trinity] Det her er rigtigt."}]
        with patch.object(me, "active_character_voices", return_value=v):
            out = me.build_matrix_voices_section()
        assert "Trinity" in out and "Det her er rigtigt." in out
        assert "tjek pending nudges" not in out, "prompten må ikke bare få et tal"

    def test_fejl_giver_ingen_sektion_i_stedet_for_at_kaste(self):
        with patch.object(me, "active_character_voices", side_effect=RuntimeError):
            assert me.build_matrix_voices_section() is None


class TestRelevansLiggerIKaraktererne:
    def _surf(self, active):
        return {"active": active, "items": [], "line": "min replik"}

    def test_kun_karakterer_hvis_check_er_sand(self):
        builders = {c["id"]: (lambda a=(c["id"] == "seraph"): self._surf(a))
                    for c in me._CHARACTERS}
        with patch.object(me, "_SURFACE_BUILDERS", builders), \
             patch.object(me, "get_unaddressed", return_value=0):
            got = {v["cid"] for v in me.active_character_voices(limit=99)}
        assert "seraph" in got
        assert "trainman" not in got, "en inaktiv surface må ikke give en stemme"

    def test_loft_paa_antal_stemmer(self):
        builders = {c["id"]: (lambda: self._surf(True)) for c in me._CHARACTERS}
        with patch.object(me, "_SURFACE_BUILDERS", builders), \
             patch.object(me, "get_unaddressed", return_value=0):
            voices = me.active_character_voices(limit=3)
        assert len(voices) == 3, "prompten må ikke oversvømmes"

    def test_en_kastende_karakter_tier_de_andre_ikke(self):
        def _boom():
            raise RuntimeError("surface nede")
        builders = {c["id"]: (lambda: self._surf(True)) for c in me._CHARACTERS}
        builders[me._CHARACTERS[0]["id"]] = _boom
        with patch.object(me, "_SURFACE_BUILDERS", builders), \
             patch.object(me, "get_unaddressed", return_value=0):
            voices = me.active_character_voices(limit=3)
        assert voices, "de øvrige stemmer skal overleve én defekt karakter"


class TestEskalering:
    def _one_active(self):
        return {me._CHARACTERS[1]["id"]: (lambda: {"active": True, "line": "l", "items": []})}

    def test_ubesvaret_giver_skarpere_replik(self):
        with patch.object(me, "_SURFACE_BUILDERS", self._one_active()), \
             patch.object(me, "get_unaddressed", return_value=3):
            v = me.active_character_voices(limit=1)
        assert v and v[0]["unaddressed"] == 3
        assert v[0]["text"] != f"{v[0]['label']} l", "eskaleret replik forventes"

    def test_sektionen_naevner_gentagen_ignorering(self):
        v = [{"cid": "smith", "label": "[🕴️ Smith]", "line": "l", "unaddressed": 4,
              "text": "[🕴️ Smith] Nok."}]
        with patch.object(me, "active_character_voices", return_value=v):
            out = me.build_matrix_voices_section()
        assert "4 gange" in out

    def test_visning_er_ikke_svar(self):
        """At have set en stemme er ikke at have svaret den — samme fejl som brønden."""
        with patch.object(me, "increment_unaddressed") as inc:
            me.note_voices_shown(["neo", "smith"])
        assert inc.call_count == 2


class TestSignOffErVaek:
    """Bjørn: sign-off'en var lavet som en joke og skal fjernes."""

    def test_ingen_signoff_funktioner_tilbage(self):
        for name in ("build_matrix_signoff_section", "signoff_enabled", "_most_active_character"):
            assert not hasattr(me, name), f"{name} skulle være fjernet"

    def test_prompt_contract_bruger_stemme_sektionen_ikke_et_tal(self):
        import inspect

        from core.services import prompt_contract
        src = inspect.getsource(prompt_contract)
        assert "build_matrix_voices_section" in src
        assert "tjek pending nudges" not in src
        assert "build_matrix_signoff_section" not in src
