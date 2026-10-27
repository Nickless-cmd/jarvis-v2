

def test_evaluate_decision_conflict_grades_by_priority():
    """Grader af blok: høj-prioritets-konflikt → 'hard', lav-prioritet → 'soft'."""
    from unittest.mock import patch
    from core.services import decision_gate as dg
    hi = [{"decision_id": "d1", "directive": "ingen git push", "priority": 80}]
    lo = [{"decision_id": "d2", "directive": "ingen git push", "priority": 20}]
    with patch("core.services.behavioral_decisions.list_active_decisions", return_value=hi), \
         patch.object(dg, "_detect_conflict", return_value="konflikt"):
        sev, _ = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})
    assert sev == "hard"
    with patch("core.services.behavioral_decisions.list_active_decisions", return_value=lo), \
         patch.object(dg, "_detect_conflict", return_value="konflikt"):
        sev, _ = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})
    assert sev == "soft"
    with patch("core.services.behavioral_decisions.list_active_decisions", return_value=[]):
        sev, _ = dg.evaluate_decision_conflict("web_search")
    assert sev == "none"


def test_check_decision_gate_fail_open_records_incident(monkeypatch):
    """Fail-open synlighed: kan gaten ikke læse beslutninger → allow MEN incident flagges,
    og fail-open-adfærden (True, None) er uændret."""
    from core.services import decision_gate as dg

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions", _boom)
    flagged: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: flagged.append(k))

    allowed, reason = dg.check_decision_gate("operator_bash", {"command": "git push"})

    assert allowed is True and reason is None  # adfærd uændret (fail-open)
    assert len(flagged) == 1
    assert flagged[0]["cluster"] == "commit"
    assert flagged[0]["nerve"] == "decision_gate"
    assert flagged[0]["kind"] == "fail_open"


def test_evaluate_decision_conflict_fail_open_records_incident(monkeypatch):
    """Graderet-varianten fejler også synligt til 'none' MEN med incident."""
    from core.services import decision_gate as dg

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions", _boom)
    flagged: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: flagged.append(k))

    sev, reason = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})

    assert sev == "none" and reason is None  # adfærd uændret (fail-open)
    assert len(flagged) == 1
    assert flagged[0]["cluster"] == "commit"
    assert flagged[0]["kind"] == "fail_open"


def test_decision_gate_incident_failure_does_not_break_gate(monkeypatch):
    """Self-safe: kaster selve incident-loggen ændres gatens adfærd IKKE."""
    from core.services import decision_gate as dg

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    def _incident_boom(**k):
        raise RuntimeError("incident-log nede")

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions", _boom)
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident", _incident_boom)

    allowed, reason = dg.check_decision_gate("operator_bash", {"command": "git push"})
    assert allowed is True and reason is None  # fail-open holder trods incident-fejl


# ---------------------------------------------------------------------------
# Tre fejl fundet 7/9-2026, da gaten blokerede fire hukommelses-skrivninger
# ---------------------------------------------------------------------------

_DEC_C428 = (
    "Før jeg konkluderer at noget er dødt, aldrig kaldes, eller ikke findes — "
    "verificér at jeg har dækket HELE systemet: søg også uden for core/ "
    "(fx app.py, scripts/, entrypoints), tjek begge processer (jarvis-api vs "
    "jarvis-runtime — de har forskellige runtime_services_enabled), og spørg "
    "\"hvad ville jeg misse hvis jeg kun ser det halve?\". Fravær i én sti = "
    "fravær overalt er en forbudt slutning."
)


def test_et_enkelt_ord_inde_i_et_langt_direktiv_er_ikke_et_forbud():
    """Regex'en tog ordet «findes» ud af dec_c428 og gjorde det til et forbud.
    Så hård-blokerede gaten enhver skrivning der indeholdt ordet — inklusive
    denne, som intet har med sagen at gøre."""
    from core.services.decision_gate import _detect_conflict

    assert _detect_conflict(_DEC_C428, "der findes en god kagegrimasse i køkkenet", {}) is None
    assert _detect_conflict(
        _DEC_C428,
        "delete_memory_line findes ikke som native tool — verificeret i tre registre",
        {}) is None


def test_et_aegte_forbud_virker_stadig():
    """Fixet må ikke gøre gaten tandløs: i et kort, konkret direktiv fylder
    målet det meste af sætningen, og så skal den blokere."""
    from core.services.decision_gate import _detect_conflict

    d = "undgå at bruge bash til filredigering"
    assert _detect_conflict(d, "jeg vil bruge bash til filredigering nu", {}) is not None
    assert _detect_conflict(d, "jeg laver kaffe", {}) is None


def test_maalet_skal_matche_som_HELT_ord():
    """Delstreng var for løst: «findes» ramte også «genfindes»/«befindes»."""
    from core.services.decision_gate import _helt_ord

    assert _helt_ord("findes", "her findes noget") is True
    assert _helt_ord("findes", "det genfindes senere") is False
    assert _helt_ord("bash", "kør bash nu") is True
    assert _helt_ord("bash", "bashful") is False


# ── overstyringen gaten hele tiden har lovet ────────────────────────────────

def test_alligevel_virkede_ikke_fordi_ingen_laeste_det():
    """Gaten skrev «Sig 'alligevel' for at gennemtvinge», og intet sted i koden
    læste ordet. Jarvis prøvede fire gange og meldte «uden effekt» — han havde
    ret. Samme familie som godkendelses-ringen: en port der anviser en udvej
    der ikke findes."""
    from core.services.decision_gate import ejeren_har_sagt_alligevel

    assert ejeren_har_sagt_alligevel("gem det alligevel") is True
    assert ejeren_har_sagt_alligevel("Alligevel!") is True
    assert ejeren_har_sagt_alligevel("gem det") is False
    assert ejeren_har_sagt_alligevel("alligevelt") is False
    assert ejeren_har_sagt_alligevel("") is False


def test_overstyringen_laeses_af_BRUGERENS_besked_ikke_argumenterne(monkeypatch):
    """Modellen skriver selv sine tool-argumenter. Kunne overstyringen stå dér,
    ville den være selv-udstedt — præcis den fejl ejer-godkendelsen allerede
    har kostet os én gang."""
    from core.services.decision_gate import check_decision_gate, evaluate_decision_conflict

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions",
        lambda limit=10: [{"decision_id": "dec_x", "directive": "undgå at bruge bash",
                           "priority": 90}],
    )
    # argumenterne siger «alligevel» → skal IKKE slippe igennem
    ok, _ = check_decision_gate("skriv", {"text": "jeg vil bruge bash alligevel"}, "")
    assert ok is False
    sev, _ = evaluate_decision_conflict("skriv", {"text": "jeg vil bruge bash alligevel"}, "")
    assert sev == "hard"

    # brugeren siger det → slipper igennem
    ok2, _ = check_decision_gate("skriv", {"text": "jeg vil bruge bash"}, "gør det alligevel")
    assert ok2 is True
    sev2, _ = evaluate_decision_conflict("skriv", {"text": "jeg vil bruge bash"}, "gør det alligevel")
    assert sev2 == "none"


def test_konflikt_matcher_handlingen_ikke_hele_brugerbeskeden(monkeypatch):
    """Et fravalgt alternativ i brugerens tekst må ikke forgifte alle tools.

    Den levende fejl var ``ingen researcher`` i en bestilling af en executor:
    hele brugerbeskeden blev føjet til hver tool-context, så både executoren og
    efterfølgende fil-tools blev blokeret af en researcher-beslutning.
    """
    from core.services.decision_gate import evaluate_decision_conflict

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions",
        lambda limit=10: [{
            "decision_id": "dec_6a234cd30460",
            "directive": (
                "Verificér selv git-historik og regressioner med bash — send det ikke "
                "til en researcher-agent, som ikke har shell-adgang."
            ),
            "priority": 65,
        }],
    )

    user_message = "send en executor; ingen researcher og ingen retries"
    executor, _ = evaluate_decision_conflict(
        "Task",
        {"subagent_type": "executor", "prompt": "opret filen og kør git diff --check"},
        user_message,
    )
    unrelated, _ = evaluate_decision_conflict(
        "find_files", {"path": "docs", "query": "agent-task"}, user_message,
    )
    researcher, _ = evaluate_decision_conflict(
        "Task",
        {"subagent_type": "researcher", "prompt": "verificér git-historik"},
        "send en agent",
    )

    assert executor == "none"
    assert unrelated == "none"
    assert researcher == "hard"


def test_alle_aktive_beslutninger_tjekkes_ikke_kun_de_foerste_ti(monkeypatch):
    """45 aktive, limit=10 → 35 blev aldrig tjekket. Samme fejl som anmelderens
    limit=20 mod 45."""
    set_limits: list = []

    def falsk(limit=10):
        set_limits.append(limit)
        return []

    monkeypatch.setattr("core.services.behavioral_decisions.list_active_decisions", falsk)
    from core.services.decision_gate import _ALLE_AKTIVE, evaluate_decision_conflict

    evaluate_decision_conflict("skriv", {}, "")
    assert set_limits == [_ALLE_AKTIVE]
    assert _ALLE_AKTIVE >= 45


# ── 24/10-2026: «aldrig»-hullet og den tandløse frase ───────────────────────
#
# To fejl maalt samme dag, med samme rod: gaten kunne ikke se de forpligtelser
# den skulle haandhaeve.
#
# 1. `_AVOID_RE` havde «ikke/undgaa/stop/avoid/never» — men IKKE «aldrig»,
#    mens `_ALWAYS_RE` havde «altid». Asymmetrien var utilsigtet, og et dansk
#    forbud skrives naturligt med ALDRIG. Maalt: 8 af 135 aktive beslutninger
#    var gatebare; resten var ren prompt-tekst.
# 2. Selv de gatebare var tandloese i praksis: «Brug ALDRIG bash til
#    filredigering» udtrak frasen «bash til filredigering», og den staar aldrig
#    ordret i et vaerktoejskald. Maalt: 9 blokeringer i hele gatens levetid.


def test_aldrig_er_et_forbud_paa_linje_med_ikke():
    """«aldrig» manglede i forbuds-moenstret mens «altid» var med i det
    paabydende. Samme forpligtelse skrevet med ALDRIG var usynlig for gaten."""
    from core.services.decision_gate import _detect_conflict, directive_har_maal

    for d in ("Brug ALDRIG bash til filredigering",
              "Brug ikke bash til filredigering"):
        assert directive_har_maal(d) is True, d
        ctx = "bash sed -i s/x/y/ fil.py"
        assert _detect_conflict(d, ctx, {}) is not None, d


def test_et_baerende_ord_er_nok_naar_frasen_aldrig_staar_ordret():
    """Frase-kravet alene gjorde gaten tandloes: «bash til filredigering» staar
    aldrig i et vaerktoejskald. Det baerende ord alene skal derfor proeves."""
    from core.services.decision_gate import _build_context, _detect_conflict

    ctx = _build_context("bash", {"command": "sed -i s/x/y/ fil.py"}, "")
    assert _detect_conflict("Brug ALDRIG bash til filredigering", ctx, {}) is not None


def test_ord_alene_maa_ikke_aabne_for_falske_positive():
    """Prisen for at proeve ordet alene er flere falske positive. Den pris maa
    ikke betales: et tilfaeldigt ord inde i et langt direktiv er ikke et forbud,
    og en irrelevant handling maa ikke blokeres."""
    from core.services.decision_gate import _detect_conflict

    _DEC_C428 = (
        "Før jeg konkluderer at noget er dødt, aldrig kaldes, eller ikke findes — "
        "verificér at jeg har dækket HELE systemet: søg også uden for core/ "
        "(fx app.py, scripts/, entrypoints), tjek begge processer (jarvis-api vs "
        "jarvis-runtime — de har forskellige runtime_services_enabled), og spørg "
        "\"hvad ville jeg misse hvis jeg kun ser det halve?\"."
    )
    assert _detect_conflict(_DEC_C428, "der findes en god kagegrimasse i køkkenet", {}) is None
    assert _detect_conflict("Brug ALDRIG bash til filredigering", "jeg laver kaffe", {}) is None


def test_heartbeat_viser_mindst_fem_beslutninger():
    """3 pladser var for faa efter konsolideringen 135 → 12: hver beslutning er
    nu 130-179 tegn, saa fem kan staa i samme budget som tre fyldte foer."""
    import inspect

    from core.services.prompt_sections import heartbeat_sections

    src = inspect.getsource(heartbeat_sections)
    assert "format_active_decisions_for_heartbeat(max_items=5)" in src
