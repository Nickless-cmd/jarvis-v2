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

import pytest

import core.services.central_matrix_ensemble as me


@pytest.fixture(autouse=True)
def _isoler_livscyklus(monkeypatch, tmp_path):
    """Livscyklus-tilstanden er en ÆGTE fil under ~/.jarvis-v2/state.

    Uden denne isolering læser og SKRIVER hver test produktions-tilstanden, så
    en testkørsel kan «opgive» en karakter der aldrig kommer tilbage i drift.
    Målt 13/11-2026: `smith` stod opgivet med behovet `smith:aktiv`, og testen
    så det som en kodefejl.
    """
    monkeypatch.setattr(me, "_LIFECYCLE_PATH", tmp_path / "lc.json")


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
        # Fixturen bærer de felter producenterne FAKTISK leverer — ellers måler
        # testen en surface der ikke findes. Seraph kræver `ready_to_surface`,
        # trainman `recent`, oracle `approaching`; uden dem ville behovs-porten
        # afvise dem af grunde der intet har med gaten at gøre.
        return {
            "active": active,
            "items": [],
            "line": "min replik",
            "ready_to_surface": [{"hyp_id": "clh-test", "statement": "en hypotese"}],
            "recent": [{"dream_id": "dream-test", "theme": "test"}],
            "approaching": [{"label": "test-linje", "eta_hours": 2}],
            "safe_to_silence": [{"nerve": "test_nerve"}],
        }

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


class TestBehovErIkkeEnTautologi:
    """Målt 13/11-2026: 13 af 17 var aktive SAMTIDIG, og prompten viste altid de
    samme fem. Betingelserne var «min analyse kan køre» — ikke «der er brug for
    mig». En betingelse der aldrig kan blive falsk er ikke en betingelse."""

    def test_check_er_gaten_og_behov_er_identiteten(self):
        """`behov` beskriver HVAD behovet er — den kan ikke springe gaten over."""
        ch = next(c for c in me._CHARACTERS if c["id"] == "seraph")
        surf = {"active": False, "ready_to_surface": [{"hyp_id": "clh-1"}]}
        assert me._behov(ch, surf) is None

    def test_en_moden_bunke_uden_klar_hypotese_er_ikke_et_behov(self):
        ch = next(c for c in me._CHARACTERS if c["id"] == "seraph")
        assert me._behov(ch, {"active": True, "ready_to_surface": []}) is None
        assert me._behov(ch, {"active": True, "ready_to_surface": [{"hyp_id": "clh-1"}]})

    def test_oracle_er_tav_om_en_projektion_langt_ude(self):
        ch = next(c for c in me._CHARACTERS if c["id"] == "oracle")
        fjern = {"crossed": [], "approaching": [{"label": "latens", "eta_hours": 134.2}]}
        assert me._behov(ch, fjern) is None, "134 timer ude er en baggrund, ikke et behov"
        naer = {"crossed": [], "approaching": [{"label": "latens", "eta_hours": 2.0}]}
        assert me._behov(ch, naer), "under et døgn er et behov"

    def test_behovet_er_emnet_ikke_antallet(self):
        """Et tal der kun vokser (121 drømme) ville gøre karakteren permanent til stede."""
        ch = next(c for c in me._CHARACTERS if c["id"] == "trainman")
        a = {"active": True, "woven_total": 121, "recent": [{"dream_id": "dream-a"}]}
        b = {"active": True, "woven_total": 999, "recent": [{"dream_id": "dream-a"}]}
        assert me._behov(ch, a) == me._behov(ch, b), "antallet må ikke være identiteten"
        c = {"active": True, "woven_total": 121, "recent": [{"dream_id": "dream-b"}]}
        assert me._behov(ch, a) != me._behov(ch, c), "en ny drøm er et nyt behov"


class TestLivscyklus:
    """Karakteren skal dukke op, tie, vende tilbage og til sidst trække sig."""

    def _setup(self, monkeypatch, tmp_path, surf):
        monkeypatch.setattr(me, "_LIFECYCLE_PATH", tmp_path / "lc.json")
        ch = next(c for c in me._CHARACTERS if c["id"] == "seraph")
        monkeypatch.setattr(me, "_SURFACE_BUILDERS", {"seraph": lambda: surf})
        monkeypatch.setattr(me, "_CHARACTERS", [ch])
        monkeypatch.setattr(me, "get_unaddressed", lambda _c: 0)
        return ch

    def _alder(self, tmp_path):
        import json as _j
        p = tmp_path / "lc.json"
        d = _j.loads(p.read_text())
        d["_sidst_aldret"] = "2020-01-01T00:00:00+00:00"
        p.write_text(_j.dumps(d))

    def _vist(self):
        """Antal stemmer i den ÆGTE sektion — visningen er det der tæller `sagt`.

        (13/11-2026) Testen målte før `active_character_voices()` direkte, som med
        vilje er ren læsning. Men så blev `sagt` aldrig talt, og reglen om at et
        behov ikke må trække sig uhørt kunne aldrig indfries — karakteren blev
        stående for evigt. Prompten bruger `build_matrix_voices_section`, så det
        er den vej testen skal måle.
        """
        sec = me.build_matrix_voices_section()
        if not sec:
            return 0
        return sum(1 for ln in sec.splitlines() if ln.startswith("  ["))

    def test_frem_tav_tilbage_trukket(self, monkeypatch, tmp_path):
        surf = {"active": True, "ready_to_surface": [{"hyp_id": "clh-1"}],
                "felt": "en hypotese er klar"}
        self._setup(monkeypatch, tmp_path, surf)
        antal = []
        for _ in range(me._GIV_OP_SEEN + 1):
            me.tick_matrix_lifecycle()
            antal.append(self._vist())
            self._alder(tmp_path)
        assert antal[0] == 1, "et nyt behov skal dukke op med det samme"
        assert antal[1] == 0, "sagt én gang — den gentager sig ikke næste tur"
        assert antal[me._GENTAG_HVER - 1] == 1, "den vender tilbage"
        assert antal[me._GIV_OP_SEEN - 1] == 0, "den har sagt sit og trækker sig"
        assert all(n == 0 for n in antal[me._GIV_OP_SEEN - 1:]), (
            "den kommer ikke igen om det samme emne"
        )

    def test_opgivet_emne_sover_men_et_nyt_vaekker(self, monkeypatch, tmp_path):
        """De skal komme og gå EFTER BEHOV — også når de er gået.

        Målt 13/11-2026: `opgivet` faldt kun ved et nyt emne, men Smiths behov
        var konstanten `smith:aktiv`. Så en karakter der først havde trukket sig
        kunne ALDRIG vende tilbage, uanset hvor ny fangsten var — «kom og gå»
        blev «kom aldrig igen».
        """
        surf_a = {"active": True, "ready_to_surface": [{"hyp_id": "clh-1"}], "felt": "a"}
        self._setup(monkeypatch, tmp_path, surf_a)
        for _ in range(me._GIV_OP_SEEN + 1):
            me.tick_matrix_lifecycle()
            self._vist()  # visningen tæller `sagt` — uden den kan intet opgives
            self._alder(tmp_path)
        import json as _j
        state = _j.loads((tmp_path / "lc.json").read_text())
        assert state["seraph"].get("opgivet") is True, "forudsætning: karakteren ER gået"
        assert self._vist() == 0, "det samme emne skal den ikke gentage"
        # Et NYT emne er et nyt behov — og skal vække den opgivne karakter.
        monkeypatch.setattr(me, "_SURFACE_BUILDERS",
                            {"seraph": lambda: {"active": True,
                                                "ready_to_surface": [{"hyp_id": "clh-2"}],
                                                "felt": "b"}})
        self._alder(tmp_path)
        me.tick_matrix_lifecycle()
        assert self._vist() == 1, "et nyt behov skal vække den opgivne karakter"

    def test_behovet_vaek_rydder_posten(self, monkeypatch, tmp_path):
        surf = {"active": True, "ready_to_surface": [{"hyp_id": "clh-1"}], "felt": "x"}
        self._setup(monkeypatch, tmp_path, surf)
        me.tick_matrix_lifecycle()
        assert "seraph" in me._load_lifecycle()
        monkeypatch.setattr(me, "_SURFACE_BUILDERS",
                            {"seraph": lambda: {"active": False, "ready_to_surface": []}})
        self._alder(tmp_path)
        me.tick_matrix_lifecycle()
        assert "seraph" not in me._load_lifecycle(), "et løst behov skal ryddes, ikke huskes"
        assert me.active_character_voices(limit=9) == []


class TestStemmenErAegte:
    """En karakter der siger en hardcodet replik mens den ægte aflæsning ligger
    ulæst i surfacen, er staffage — ikke en stemme."""

    def test_surfacens_felt_bruges_frem_for_den_statiske_replik(self):
        ch = next(c for c in me._CHARACTERS if c["id"] == "construct")
        assert me._stemme({"felt": "3 nerver kan slukkes"}, ch) == "3 nerver kan slukkes"

    def test_uden_en_aflaesning_falder_den_tilbage(self):
        ch = next(c for c in me._CHARACTERS if c["id"] == "construct")
        assert me._stemme({}, ch) == ch["line"]

    def test_trainman_siger_drommen_ikke_sloganet(self):
        ch = next(c for c in me._CHARACTERS if c["id"] == "trainman")
        surf = {"active": True, "recent": [{"narrative": "I nat drømte jeg om værktøj."}]}
        tekst = me._stemme(surf, ch)
        assert "værktøj" in tekst
        assert "perronen" not in tekst
