# tests/test_central_agent_smith.py
from core.services import central_agent_smith as s


def test_repeated_phrases_catches_cross_message():
    msgs = ["jeg kører nu med det samme", "jeg kører nu igen", "helt andet emne her", "jeg kører nu tredje gang"]
    hits = s.repeated_phrases(msgs, min_msgs=3)
    assert any("jeg kører nu" in h["phrase"] for h in hits)


def test_repeated_phrases_ignores_unique():
    msgs = ["alfa beta gamma delta", "epsilon zeta eta theta", "en to tre fire fem"]
    assert s.repeated_phrases(msgs, min_msgs=3) == []


def test_cluster_similarity_high_vs_low():
    same = ["cache hit er 38 procent på flash"] * 4
    assert s.cluster_similarity(same) > 0.9
    diverse = ["alfa beta", "helt andre ord her", "tredje unikke sætning nu"]
    assert s.cluster_similarity(diverse) < 0.4


def test_decision_patterns_catches_repeated_sig():
    sigs = ["semantic_search", "semantic_search", "read_file", "semantic_search"]
    hits = s.decision_patterns(sigs, min_runs=3)
    assert hits and hits[0]["signature"] == "semantic_search" and hits[0]["in_runs"] == 3


def test_score_monotone_and_bounds():
    assert s.score([], 0.0, []) == 0.0
    hi = s.score([{"phrase": "x", "in_messages": 5}] * 5, 1.0, [{"signature": "y", "in_runs": 5}] * 3)
    # 5/9-2026: vaegtene omfordelt. Sproget deler 0,50 og adfaerd har 0,50, saa
    # sprog maxet ud lander PRAECIS paa stemme-taerskelen — han maa stadig tale,
    # men ord alene kan ikke baere ham hoejere. Foer kunne ren hyppighed naa 0,9+,
    # og dét var mekanismen der 19. aug sendte «det er ikke» op paa prioritet 85.
    assert hi == 0.5
    assert s.score([], 0.0, []) < hi
    # Maalt adfaerd ALENE — uden en eneste gentaget frase — skal kunne faa ham
    # til at tale. Det er hele pointen: han skal se handlinger, ikke ord.
    b = s.behaviour_patterns(31, 139)
    assert s.score([], 0.0, [], b) >= s._VOICE_THRESHOLD
    # og den vejer tungere end nogen enkelt sproglig kanal
    assert s.score([], 0.0, [], b) > s.score([], 1.0, [])


def test_smith_voice_points_at_top_repeat_when_high():
    v = s.smith_voice([{"phrase": "jeg kører nu", "in_messages": 9}], 0.7, [], 0.8)
    assert "jeg kører nu" in v and "Varier" in v
    low = s.smith_voice([], 0.0, [], 0.1)
    assert "Varier" not in low


# ── Smiths nye øjne, 05-09-2026 ─────────────────────────────────────────────
# Smith blev bygget som «standing self-similarity critic», men han kunne kun se
# SPROG: n-grams over sine egne beskeder. 19. aug eskalerede han «og det er» og
# «det er ikke» til prioritet 85 og forbød i praksis dansk. Rettelserne bagefter
# gjorde ham tavs — de undertrykte den naive detektor uden at give ham en bedre.
#
# Ironien 5/9: 31 tomme løfter på én dag — præcis den klasse gentagen adfærd han
# blev bygget til at fange — mens han ikke kunne se noget.

class TestBehaviourEyes:
    def test_maalt_adfaerd_bliver_et_moenster(self):
        b = s.behaviour_patterns(31, 139)
        assert len(b) == 1
        assert b[0]["kind"] == "behaviour"
        assert b[0]["metric"] == 31.0
        assert "31 af 139" in b[0]["detail"]

    def test_faa_gange_er_ikke_et_moenster(self):
        """Et enkelt tomt løfte er et uheld. Tre er en vane."""
        assert s.behaviour_patterns(2, 100) == []
        assert s.behaviour_patterns(3, 100) != []

    def test_baerer_korroboration_saa_den_gaar_gennem_berettigelses_porten(self):
        """Et andet værn HAR talt den — det er ikke Smiths egen mistanke. Derfor
        gennem den eksisterende port, ikke uden om den."""
        assert s.behaviour_patterns(31, 139)[0]["corroborated"] is True

    def test_stemmen_anklager_handlingen_ikke_ordet(self):
        b = s.behaviour_patterns(31, 139)
        v = s.smith_voice([], 0.0, [], s.score([], 0.0, [], b), b)
        assert "tomme løfter" in v
        assert "Du sagde du ville" in v
        assert "Varier" not in v          # det er ikke en sprogkritik

    def test_adfaerd_fortraenger_frase_snakken(self):
        """«Du gentager et ord» og «du sagde du ville og lod være» er ikke samme
        anklage. Blandes de, drukner den vigtige i den trivielle."""
        b = s.behaviour_patterns(31, 139)
        v = s.smith_voice([{"phrase": "det er ikke", "in_messages": 9}], 0.9, [], 0.9, b)
        assert "det er ikke" not in v

    def test_stigen_ser_adfaerden(self):
        detected = s._detected_patterns({"behaviours": s.behaviour_patterns(31, 139)})
        key = s.pattern_key("behaviour", "tomme løfter")
        assert key in detected
        assert detected[key]["corroborated"] is True

    def test_daarlige_tal_vaelter_ingenting(self):
        assert s.behaviour_patterns(None, None) == []
        assert s.behaviour_patterns(31, 0) != []      # division med nul


class TestAugustRegression:
    """August-fejlen må ikke kunne ske igen ad den nye vej."""

    def test_normale_danske_ord_bliver_ALDRIG_et_adfaerds_moenster(self):
        """Kanalen tager tal, ikke tekst. Der findes ingen vej fra et ord til et
        behaviour-mønster — det er dét der gør øjnene skarpere."""
        detected = s._detected_patterns({
            "repeated_phrases": [{"phrase": "det er ikke", "in_messages": 15}],
            "behaviours": [],
        })
        assert all(v["kind"] != "behaviour" for v in detected.values())

    def test_en_frase_faar_stadig_IKKE_korroboration_foraeret(self):
        detected = s._detected_patterns({
            "repeated_phrases": [{"phrase": "det er ikke", "in_messages": 15}],
        })
        key = s.pattern_key("phrase", "det er ikke")
        assert detected[key]["corroborated"] is False


def test_adfaerds_direktivet_siger_GOER_det_ikke_vaelg_en_anden_vej(monkeypatch):
    """Direktivet står på prioritet 85 og surfacer hver heartbeat. Sekvens-
    skabelonen sagde «vælg en anden tilgang» om et tomt løfte — forkert råd:
    rettelsen er ikke en anden vej, den er at GØRE det han lige sagde."""
    fanget = {}

    def _fake_create(**kw):
        fanget.update(kw)
        return {"decision_id": "dec_test"}

    import core.services.behavioral_decisions as bd
    monkeypatch.setattr(bd, "create_decision", _fake_create)
    monkeypatch.setattr(s, "_agent_smith_enforced", lambda: True)
    s._execute_mint("behaviour:tomme løfter", "tomme løfter", "behaviour", 33.0)
    assert "anden vej" not in fanget["trigger_cue"]
    assert "anden tilgang" not in fanget["directive"]
    assert "kald vaerktoejet" in fanget["trigger_cue"].lower()


def test_stigens_vindue_er_kort_nok_til_at_en_bedring_kan_ses():
    """Med 24t blev baseline 33, og de-eskalering kræver <19,8. Det tal kan ikke
    falde før gårsdagens fejl er aldret ud — uanset om han holder op med det
    samme. Så ville stigen kun kunne klatre, aldrig lukke."""
    assert s._LADDER_WINDOW_HOURS <= 6
