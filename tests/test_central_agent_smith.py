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
    assert hi == 0.45
    assert hi < s._VOICE_THRESHOLD
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
        """29/10-2026: `corroborated` saettes IKKE laengere foraeret paa behaviour-
        kanalen. Foer stod der `True` ubetinget, og det var praecis dét der gjorde
        berettigelses-porten til en no-op: portens eget input var hardcodet.
        Nu kommer korroborationen fra den tunbare kanal — som for phrase/seq."""
        detected = s._detected_patterns({"behaviours": s.behaviour_patterns(31, 139)})
        key = s.pattern_key("behaviour", "tomme løfter")
        assert key in detected
        assert detected[key]["corroborated"] is False, (
            "korroboration blev foraeret — porten er en no-op igen"
        )
        # men den ER selv-bundet: et tomt loefte er definitionen paa et brudt eget loefte
        assert detected[key]["self_bound"] is True

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


# ---------------------------------------------------------------------------
# Vetoet i I/O-laget (7/9-2026)
#
# Den rene tilstandsmaskine beslutter stadig at minte; vetoet sidder dér hvor
# minten UDFØRES, så tilstandsmaskinen bliver ved at kunne testes uden DB og
# uden model.
# ---------------------------------------------------------------------------

def test_vetoet_stopper_minten_og_efterlader_et_spor(monkeypatch):
    import core.services.central_agent_smith as A

    mintet: list = []
    observeret: list = []
    monkeypatch.setattr(A, "_execute_mint", lambda *a, **kw: mintet.append(a) or "dec_1")
    monkeypatch.setattr(A, "_execute_observe", lambda act: observeret.append(act))
    monkeypatch.setattr(A, "_load_escalation_state", lambda: {})
    monkeypatch.setattr(A, "_save_escalation_state", lambda s: None)
    monkeypatch.setattr(A, "_detected_patterns", lambda a, c: {})
    monkeypatch.setattr(A, "_corroboration_signal", lambda: {})
    monkeypatch.setattr(A, "_escalation_criteria", lambda: {"risky_terms": []})
    monkeypatch.setattr(
        A, "step_escalation",
        lambda st, det, ts, cfg: ({"patterns": {"phrase:i stedet for": {}}},
                                  [{"type": "mint", "pattern_key": "phrase:i stedet for",
                                    "label": "i stedet for", "kind": "phrase", "metric": 10}]),
    )
    # 29/10-2026: `maa_minte` tager nu ogsaa `metric` med, saa dommeren kan se
    # omfanget («1320 forekomster») i stedet for kun den raa noegle. Mock'en skal
    # derfor acceptere det argument — ellers fejler kaldet, ikke vetoet.
    monkeypatch.setattr("core.services.smith_noise_veto.maa_minte",
                        lambda k, e="", c=None, metric=0.0: (False, "doemt_stoej"))

    A.run_escalation_tick({"felt": "", "score": 0.0, "verdict": False})

    assert mintet == [], "vetoet slap en mint igennem"
    assert any(o.get("event") == "veto" for o in observeret), (
        "et vetoet mønster forsvandt uden spor — så kan virkningen ikke måles"
    )


def test_et_risikabelt_moenster_bliver_stadig_mintet(monkeypatch):
    """Risiko går udenom modellen — en død model må ikke kunne tie et farligt
    mønster ihjel."""
    import core.services.central_agent_smith as A

    mintet: list = []
    monkeypatch.setattr(A, "_execute_mint", lambda *a, **kw: mintet.append(a) or "dec_1")
    monkeypatch.setattr(A, "_execute_observe", lambda act: None)
    monkeypatch.setattr(A, "_load_escalation_state", lambda: {})
    monkeypatch.setattr(A, "_save_escalation_state", lambda s: None)
    monkeypatch.setattr(A, "_detected_patterns", lambda a, c: {})
    monkeypatch.setattr(A, "_corroboration_signal", lambda: {})
    monkeypatch.setattr(A, "_escalation_criteria", lambda: {"risky_terms": ["delete"]})
    monkeypatch.setattr(
        A, "step_escalation",
        lambda st, det, ts, cfg: ({"patterns": {"seq:delete workspace memory line": {}}},
                                  [{"type": "mint",
                                    "pattern_key": "seq:delete workspace memory line",
                                    "label": "delete workspace memory line",
                                    "kind": "seq", "metric": 6}]),
    )
    # Modellen er utilgaengelig — og skal alligevel ikke spoerges.
    monkeypatch.setattr("core.services.local_small_model.spoerg_et_ord",
                        lambda *a, **kw: None)
    A.run_escalation_tick({"felt": "", "score": 0.0, "verdict": False})
    assert len(mintet) == 1, "risikabelt mønster blev vetoet — det skal gå udenom"


# ---------------------------------------------------------------------------
# Trin 1: den rå detektor-linje må ALDRIG nå prompten (7/9-2026)
#
# 19. aug blev berettigelsen udvidet til også at gælde trin 1 — er et mønster
# hverken risikabelt eller selv-lovet, har Smith ingenting at sige. Men
# `line = rung_line or a["felt"]` gav gaten en åbning i ryggen, og det var dén
# der talte:
#
#     «Mr. Anderson... du har sagt "nu har jeg" i 11 beskeder;
#      samme træk (run non-destructive command) 15 gange.»
#
# Linjen stod i halen, Jarvis gentog formuleringen, og Smith mintede så seks
# direktiver om sin egen replik. Sløjfen begyndte her — ikke ved minten.
# ---------------------------------------------------------------------------

def test_raa_detektorlinje_naar_ikke_prompten_naar_stigen_tier(monkeypatch):
    import core.services.central_agent_smith as A

    gemt: dict = {}
    monkeypatch.setattr(A, "assess", lambda: {
        "felt": 'Mr. Anderson... du har sagt "nu har jeg" i 11 beskeder.',
        "score": 0.9, "verdict": True,
    })
    monkeypatch.setattr(A, "run_escalation_tick", lambda a: {"line": ""})
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value",
                        lambda k, v: gemt.update({k: v}))

    A.record_agent_smith()
    st = gemt.get("agent_smith_state", {})
    assert st.get("line") == "", "den rå n-gram-linje slap ind som prompt-linje"
    # men den skal stadig kunne SES — vi mister ikke hvad detektoren så
    assert "nu har jeg" in str(st.get("felt_raw"))


def test_en_berettiget_trin1_kommentar_naar_stadig_frem(monkeypatch):
    """Trin 1 tabes ikke: top_line rangerer comment-stemmen med."""
    import core.services.central_agent_smith as A

    gemt: dict = {}
    monkeypatch.setattr(A, "assess", lambda: {"felt": "rå støj", "score": 0.1,
                                              "verdict": False})
    monkeypatch.setattr(A, "run_escalation_tick",
                        lambda a: {"line": "Mr. Anderson... «tomme løfter»: 4 gange."})
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value",
                        lambda k, v: gemt.update({k: v}))

    A.record_agent_smith()
    st = gemt.get("agent_smith_state", {})
    assert "tomme løfter" in st["line"]
    assert st["verdict"] is True, "en eskaleret linje skal tælle som en dom"


def test_prompt_sektionen_har_ingen_score_omvej(monkeypatch):
    """Uden rung_line er svaret None — uanset hvor høj scoren er."""
    import core.services.central_agent_smith as A

    monkeypatch.setattr("core.services.central_switches.is_enabled", lambda *a: True)
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda k, d=None: {"rung_line": "", "line": "rå n-gram-linje",
                           "score": 0.99, "felt_raw": "rå n-gram-linje"},
    )
    assert A.agent_smith_prompt_section() is None


def test_en_eskaleret_linje_surfacer_uanset_score(monkeypatch):
    import core.services.central_agent_smith as A

    monkeypatch.setattr("core.services.central_switches.is_enabled", lambda *a: True)
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda k, d=None: {"rung_line": "Nej, Mr. Anderson. «tomme løfter» igen.",
                           "line": "", "score": 0.0},
    )
    ud = A.agent_smith_prompt_section()
    assert ud is not None and "tomme løfter" in ud


def test_fejl_oejet_ser_kun_AKTIVE_lektioner(monkeypatch, tmp_path):
    """En fixet fejl maa ikke blive ved med at eskalere.

    Maalt 8/10-2026: `_a_truncated`-fejlen blev fixet 12. sep (commit
    e4a8565d1), men Smith pegede stadig paa den 26 dage senere — og gaten
    blokerede indbakken med en advarsel om et lukket problem. Forespoergslen
    filtrerede ikke paa `status`, saa `retired` lektioner var evigt
    braendstof for stigen. `retire_stale` kan heller ikke rydde dem selv:
    den roerer kun lektioner med evidence_count < 2 OG repeated_count = 0.
    """
    import sqlite3

    from core.runtime import db as db_mod

    sti = tmp_path / "lessons.db"
    kolonner = ("signature", "signature_key", "lesson", "source", "status",
                "evidence_count", "repeated_count", "user_words", "jarvis_words",
                "first_at", "last_at", "last_repeated_at")
    conn = sqlite3.connect(sti)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + ", ".join(f"{k} TEXT" for k in kolonner)
        + ")"
    )
    sql = (f"INSERT INTO lessons ({', '.join(kolonner)}) "
           f"VALUES ({', '.join('?' * len(kolonner))})")
    conn.execute(sql, ("sig-levende", "sig-levende", "levende fejl gentaget",
                       "tool_error", "active", 6, 4, "", "", "2026-09-09",
                       "2026-10-08", "2026-10-08"))
    conn.execute(sql, ("sig-fixet", "sig-fixet", "fixet fejl der stadig stod som aktiv",
                       "tool_error", "retired", 6, 4, "", "", "2026-09-09",
                       "2026-09-12", "2026-09-12"))
    conn.commit()
    conn.close()

    def _connect(*a, **k):
        c = sqlite3.connect(sti)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(db_mod, "connect", _connect)

    fundet = s._measured_error_patterns(limit=5)
    etiketter = " ".join(x["label"] for x in fundet)
    assert "levende fejl gentaget" in etiketter, "en aktiv fejl skal ses"
    assert "fixet fejl" not in etiketter, (
        "en pensioneret lektion maa ikke eskalere — det var hele fejlen"
    )


# ---------------------------------------------------------------------------
# Berettigelses-porten var en no-op for behaviour-kanalen (29/10-2026)
#
# `_detected_patterns` satte `"self_bound": True, "corroborated": True`
# UBETINGET paa alle behaviour-moenstre, med en kommentar om at moensteret
# «gaar gennem den eksisterende berettigelses-port frem for uden om den». Men
# at hardcode portens EGNE INPUT til True ER at gaa uden om den:
# `_is_self_bound` blev aldrig evalueret for den kanal.
#
# Maalt konsekvens: lektion #38 (source=regret, n=2) — «Bruger afviste
# tool-call til bash (forventede: approved; fik: rejected)» — blev et Trin
# 3-moenster og armerede standing order #22 med ordlyden «du forpligtede dig
# til at stoppe …». Det er BJOERNS afvisning af et approval-kort, ikke et
# brudt loefte fra Jarvis. To forekomster var hele grundlaget.
# ---------------------------------------------------------------------------

class TestBerettigelsesPortenErIkkeEnNoOp:
    def test_behaviour_uden_selv_lovet_cue_bliver_paa_trin_1(self):
        """Et maalt behaviour-moenster der IKKE er selv-bundet maa ikke klatre —
        uanset hvor mange gange det er set. Det er praecis den fejl der gav
        standing order #22 paa Bjoerns eget approval-afslag."""
        from core.services.central_agent_smith_escalation import step_escalation

        detected = s._detected_patterns({"behaviours": [{
            "kind": "behaviour",
            "label": "gentaget fejl: bruger afviste tool-call til bash",
            "metric": 2.0,
            "self_bound": False,
        }]})
        key = s.pattern_key("behaviour", "gentaget fejl: bruger afviste tool-call til bash")
        assert detected[key]["self_bound"] is False
        assert detected[key]["corroborated"] is False

        # Selv efter mange cykler med hoej metrik bliver den paa Trin 1 — eller
        # helt afvist. Begge er korrekte: `step_escalation` smider et moenster UD
        # naar det hverken er risikabelt eller selv-lovet (linje ~330), saa det
        # naar slet ikke ind i `patterns`. Det er staerkere end Trin 1.
        state: dict = {}
        cfg = {"risky_terms": [], "benign_terms": [], "self_commitments": [],
               "spike_factor": 1.5}
        for _ in range(10):
            state, actions = step_escalation(state, detected, "2026-10-29T16:00:00+00:00", cfg)
        runger = [v.get("rung") for v in (state.get("patterns") or {}).values()]
        assert runger in ([], [1]), f"moenster uden selv-lovet cue klatrede: {runger}"
        assert not any(a.get("type") in ("mint", "arm_confront") for a in actions), (
            "et ikke-selv-bundet moenster fik lov at binde eller konfrontere"
        )

    def test_regret_lesson_kan_ikke_baere_et_moenster_alene(self, monkeypatch):
        """`source=regret` er MIN reaktion paa noget — ikke en maalt fejl. Den maa
        ikke saette `self_bound`, for saa baerer Bjoerns afvisning af et
        approval-kort hele eskaleringen."""
        import sqlite3

        from core.runtime import db as db_mod

        import tempfile
        from pathlib import Path

        sti = Path(tempfile.mkdtemp()) / "lessons.db"
        # `repeated_count` skal vaere INTEGER, ikke TEXT: med TEXT sorterer
        # `ORDER BY repeated_count DESC` leksikalsk, saa «2» rangerer over
        # «1322» og den aegte fejl falder ud af LIMIT. Det var testens skema
        # der var forkert — ikke koden. (Maalt 29/10-2026.)
        kolonner = ("signature", "signature_key", "lesson", "source", "status",
                    "evidence_count", "repeated_count", "user_words", "jarvis_words",
                    "first_at", "last_at", "last_repeated_at")
        conn = sqlite3.connect(sti)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "signature TEXT, signature_key TEXT, lesson TEXT, source TEXT, "
            "status TEXT, evidence_count INTEGER, repeated_count INTEGER, "
            "user_words TEXT, jarvis_words TEXT, first_at TEXT, last_at TEXT, "
            "last_repeated_at TEXT)"
        )
        sql = (f"INSERT INTO lessons ({', '.join(kolonner)}) "
               f"VALUES ({', '.join('?' * len(kolonner))})")
        conn.execute(sql, ("sig-regret", "sig-regret",
                           "Bruger afviste tool-call til bash", "regret", "active",
                           2, 2, "", "", "2026-10-28", "2026-10-29", "2026-10-29"))
        conn.execute(sql, ("sig-tool", "sig-tool",
                           "En &&-kaede broed tavst", "tool_error", "active",
                           1322, 1322, "", "", "2026-10-01", "2026-10-29", "2026-10-29"))
        conn.commit()
        conn.close()

        def _connect(*a, **k):
            c = sqlite3.connect(sti)
            c.row_factory = sqlite3.Row
            return c

        monkeypatch.setattr(db_mod, "connect", _connect)

        fundet = {x["label"]: x for x in s._measured_error_patterns(limit=10)}
        regret = next(v for k, v in fundet.items() if "afviste tool-call" in k)
        tool = next(v for k, v in fundet.items() if "&&-kaede" in k)
        assert regret["self_bound"] is False, (
            "en regret-lesson blev selv-bundet — saa baerer Bjoerns afslag eskaleringen"
        )
        assert tool["self_bound"] is True, (
            "et maalt vaerktoejs-fejl-moenster skal stadig kunne baere sig selv"
        )
        # Og ingen af dem foraerer korroboration: den afgoeres af den tunbare kanal.
        assert "corroborated" not in regret
        assert "corroborated" not in tool

    def test_korroboration_kommer_fra_den_tunbare_kanal_ikke_fra_maalingen(self):
        """`corroborated` maa kun vaere sandt naar et ANDET vaern reelt har flagget
        labelen — praecis som phrase- og seq-kanalerne."""
        label = "gentaget fejl: en &&-kaede broed tavst"
        uden = s._detected_patterns({"behaviours": [
            {"kind": "behaviour", "label": label, "metric": 1322.0, "self_bound": True}]})
        key = s.pattern_key("behaviour", label)
        assert uden[key]["corroborated"] is False

        med = s._detected_patterns(
            {"behaviours": [{"kind": "behaviour", "label": label,
                             "metric": 1322.0, "self_bound": True}]},
            {label.lower()},
        )
        assert med[key]["corroborated"] is True


# ---------------------------------------------------------------------------
# Trin 3 skrev standing orders der per konstruktion ALDRIG kunne matche
# (rettet 29/10-2026)
#
# `_execute_arm_confront` skrev en ordre med `match_key` = mønsterets label,
# mens modtageren (`reasoning_detectors.standing_orders_on_reasoning`) gjorde
# `if mk in classes` mod fem FASTE klassenavne (cross_user_share, decision_gate,
# fact_gate, verification, veto). En label som «gentaget fejl: Bruger afviste
# tool-call til bash» kan per konstruktion aldrig være ét af dem.
#
# Målt i drift: 2 aktive ordrer, nul events der refererer standing orders.
# Det virksomme maskineri fandtes allerede — `smith_confrontation.
# smith_confront_on_action` læser STIGEN SELV og holder kaldet. Det har
# aldrig brug for en standing order.
# ---------------------------------------------------------------------------

class TestTrin3SkriverIkkeDoedeOrdrer:
    def test_arm_confront_registrerer_ingen_standing_order(self, monkeypatch):
        """Den gamle vej skrev en ordre der aldrig kunne ramme. Nu skrives ingen."""
        import core.services.central_agent_smith as A

        kaldt: list = []
        monkeypatch.setattr(A, "_agent_smith_enforced", lambda: True)
        monkeypatch.setattr(
            "core.services.standing_orders_registry.add_standing_order",
            lambda **kw: kaldt.append(kw) or 99,
        )
        A._execute_arm_confront("seq:delete workspace memory line",
                                "delete workspace memory line")
        assert kaldt == [], (
            "der blev skrevet en standing order — den kan ikke matche de fem "
            "faste klassenavne, saa den er teater"
        )

    def test_arm_confront_efterlader_et_spor_saa_effekten_kan_maales(self, monkeypatch):
        """Uden et spor kan forholdet arm→faktisk hold ikke måles bagefter — og
        saa er Trin 3 igen teater: armeret, men uden bevis for virkning."""
        import core.services.central_agent_smith as A
        from core.services import shared_cache

        gemt: dict = {}
        monkeypatch.setattr(A, "_agent_smith_enforced", lambda: True)
        monkeypatch.setattr(shared_cache, "set",
                            lambda k, v, ttl_seconds=None: gemt.update({k: v}))
        A._execute_arm_confront("seq:delete workspace memory line",
                                "delete workspace memory line")
        assert "smith_confront:armed:seq:delete workspace memory line" in gemt

    def test_behaviour_moenster_armeres_ikke(self, monkeypatch):
        """`behaviour:`-mønstre har intet tool-kald at holde — hollow_promise_guard
        dækker dem. Det er dækning, ikke en mangel."""
        import core.services.central_agent_smith as A
        from core.services import shared_cache

        gemt: dict = {}
        monkeypatch.setattr(A, "_agent_smith_enforced", lambda: True)
        monkeypatch.setattr(shared_cache, "set",
                            lambda k, v, ttl_seconds=None: gemt.update({k: v}))
        A._execute_arm_confront("behaviour:tomme løfter", "tomme løfter")
        assert gemt == {}

    def test_shadow_armerer_intet(self, monkeypatch):
        import core.services.central_agent_smith as A
        from core.services import shared_cache

        gemt: dict = {}
        monkeypatch.setattr(A, "_agent_smith_enforced", lambda: False)
        monkeypatch.setattr(shared_cache, "set",
                            lambda k, v, ttl_seconds=None: gemt.update({k: v}))
        A._execute_arm_confront("seq:delete workspace memory line",
                                "delete workspace memory line")
        assert gemt == {}
