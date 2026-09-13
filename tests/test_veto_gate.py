"""Fail-open-synlighed for core/services/veto_gate.py (dø-skjult-fix)."""
from __future__ import annotations
import importlib
from pathlib import Path


def test_imports():
    assert importlib.import_module("core.services.veto_gate") is not None


def test_fail_open_is_visible():
    src = Path("core/services/veto_gate.py").read_text(encoding="utf-8")
    assert "record_central_incident" in src, "check_veto fail-open skal flagge til Centralen"


# ── record_event-vagten (fix 13/9-2026) ──────────────────────────────────────
# Baggrund: `reasoning_detectors.veto_on_reasoning` genanvendte gaten på Jarvis' EGEN
# reasoning og sendte den ind som `user_message`. Det skrev 77 rækker i veto_events
# med veto_result='blocked' og tool_name='' — hvor intet værktøj blev blokeret.
# Vagtens kontrakt: en genanvendelse uden brugermelding må ikke skrive i ledger'en,
# men den ÆGTE præ-eksekverings-vej skal skrive præcis som før.

_FIRM_SECTION = (
    "PUSHBACK\n"
    "- feeling=protectiveness intensity=0.81 action=firm_pushback\n"
    "- evidence: risk marker: 'push'\n"
)
_SOFT_SECTION = (
    "PUSHBACK\n"
    "- feeling=hesitation intensity=0.46 action=soft_pushback\n"
    "- evidence: risk marker: 'restart'\n"
)


def _hermetic(monkeypatch, section: str):
    """Isolér gaten fra token-signal, pushback-beregning og adaptiv DB-læsning."""
    from core.services import veto_gate as vg
    written: list[dict] = []
    monkeypatch.setattr(vg, "_check_token_signal_gate", lambda msg, tool: False)
    monkeypatch.setattr(vg, "_adaptive_threshold", lambda tool, feeling, intensity: 0.5)
    monkeypatch.setattr(vg, "log_veto_event", lambda **kw: (written.append(kw) or "veto-test"))
    monkeypatch.setattr("core.services.pushback.affective_pushback_section",
                        lambda msg: section)
    return vg, written


def test_record_event_false_skriver_ingen_blocked_raekke(monkeypatch):
    """Kernen i fixet: genanvendelsen må ikke skrive en 'blocked'-række."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, reason = vg.check_veto("", "jeg pusher nu", record_event=False)
    assert allowed is False and "VETO" in reason  # dømmekraften kører uændret
    assert written == [], "genanvendelse uden brugermelding må ikke skrive i veto_events"


def test_record_event_false_skriver_ingen_allowed_raekke(monkeypatch):
    vg, written = _hermetic(monkeypatch, _SOFT_SECTION)
    allowed, _ = vg.check_veto("", "jeg genstarter nu", record_event=False)
    assert allowed is True
    assert written == []


def test_record_event_true_skriver_som_foer(monkeypatch):
    """Den ÆGTE vej skal være uændret — vagten må ikke slukke ledger'en."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, _ = vg.check_veto("write_file", "jeg pusher nu", record_event=True)
    assert allowed is False
    assert len(written) == 1 and written[0]["veto_result"] == "blocked"
    assert written[0]["tool_name"] == "write_file"


# ── ingen-bruger-vagten (13/9-2026) ──────────────────────────────────────────
# Baggrund: 100 drømme-rækker + 5 wakeup-rækker stod som 'blocked' i veto_events på
# ordret system-prompt-tekst ("Du er i en drømmetilstand …", "Du bad dig selv: …").
# Gatens grundlag er BRUGERENS pushback; i en autonom tur (VisibleRun.autonomous)
# findes der ingen bruger. Kontrakten: gaten ABSTAINER — den logger at den ville
# have fyret (synligt, C-forudsætningen), men blokerer ikke på et grundlag der ikke
# findes. Den ÆGTE bruger-vej er uændret.


def test_ingen_bruger_abstainer_og_blokerer_ikke(monkeypatch):
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, reason = vg.check_veto("write_file", "Du er i en drømmetilstand",
                                    user_present=False)
    assert allowed is True and reason is None, "en system-prompt må ikke blokere"
    assert len(written) == 1
    assert written[0]["veto_result"] == "allowed"
    assert written[0]["resolution"] == "false_positive"


def test_ingen_bruger_logger_at_den_ville_have_fyret(monkeypatch):
    """C-forudsætningen: abstentionen er SYNLIG, ikke tavs — og sporet bærer
    evidensen, så et review kan se HVORFOR gaten ville have fyret."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    vg.check_veto("write_file", "Du bad dig selv: verificér genstarten",
                  user_present=False)
    assert written, "abstentionen skal efterlade et spor"
    assert written[0]["veto_result"] == "allowed", "må ikke stå som blokeret"
    assert written[0]["resolution"] == "false_positive"
    assert "push" in written[0]["evidence_summary"], "evidensen skal bevares i sporet"


def test_bruger_til_stede_blokerer_som_foer(monkeypatch):
    """Regression: standarden er uændret — en ÆGTE bruger blokeres stadig."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, reason = vg.check_veto("write_file", "slet user.md nu!!!")
    assert allowed is False and "VETO" in reason
    assert written[0]["veto_result"] == "blocked"


def test_record_event_false_ved_ingen_bruger_skriver_intet(monkeypatch):
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, _ = vg.check_veto("write_file", "drøm", record_event=False,
                               user_present=False)
    assert allowed is True and written == []


def test_abstain_spiser_ikke_en_armeret_override(monkeypatch):
    """Rækkefølge: vagten ligger FØR override-forbruget. En tur uden bruger har
    intet at overstyre — en armeret one-shot må ikke brændes af på den."""
    vg, _ = _hermetic(monkeypatch, _FIRM_SECTION)
    consumed: list[tuple[str, str]] = []
    monkeypatch.setattr("core.services.gate_override.consume_override",
                        lambda tool, feeling: (consumed.append((tool, feeling)) or None))
    allowed, _ = vg.check_veto("write_file", "drøm", user_present=False)
    assert allowed is True
    assert consumed == [], "armeret override blev spist af en tur uden bruger"


def test_arbiter_sender_user_present_videre_til_veto_ctx(monkeypatch):
    """Plumbningen: evaluate_commit_gates skal give flaget videre i veto-ctx'en."""
    from core.services import commit_gate_arbiter as cga
    from core.services.gate_kernel import Decision, GateClass, Verdict
    seen: dict = {}

    def _fake_veto(ctx):
        seen.update(ctx)
        return Verdict("veto", Decision.GREEN, "ok", klass=GateClass.COGNITIVE)

    monkeypatch.setattr("core.services.gate_commit.veto_gate", _fake_veto)
    cga.evaluate_commit_gates(name="read_mood", arguments={}, user_message="drøm",
                              session_id="", run_id="", user_present=False)
    assert seen.get("user_present") is False


def test_prepare_call_videresender_user_present(monkeypatch):
    """Plumbningen hele vejen: exec-stien skal give flaget til gate-arbitragen."""
    from core.services import simple_tool_executor as ste
    from core.services.commit_gate_arbiter import CommitGateOutcome
    seen: dict = {}

    def _fake_ecg(**kw):
        seen.update(kw)
        return CommitGateOutcome(blocked=False)

    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates", _fake_ecg)
    monkeypatch.setattr("core.services.agentic_tool_cache.get_cached_result",
                        lambda n, a: None)
    ste._prepare_call({"function": {"name": "read_mood", "arguments": {}}},
                      force=False, run_id="", session_id="", user_message="drøm",
                      controller=None, round_seen=set(), user_present=False)
    assert seen.get("user_present") is False


def test_visible_tool_exec_udleder_flaget_fra_run_autonomous():
    """Kilden: exec-stedet sætter flaget fra run.autonomous — ikke fra tekst."""
    src = Path("core/services/visible_tool_exec.py").read_text(encoding="utf-8")
    assert "user_present=not run.autonomous" in src, (
        "exec-stedet skal udlede 'ingen bruger' af run.autonomous, ikke af beskedtekst")
