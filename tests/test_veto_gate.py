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


def test_visible_tool_exec_udleder_flaget_fra_KOERSLEN_ikke_fra_tekst():
    """Kilden: exec-stedet sætter flaget fra kørslen — aldrig fra beskedtekst.

    Vagten hed før `..._fra_run_autonomous` og fastholdt den præcise streng
    `user_present=not run.autonomous`. Hensigten var rigtig; bindingen var for
    stram. Ankeret er siden flyttet til `run.origin` (med `autonomous` som
    faldback), fordi flaget kun virkede ved et sammentræf: enhver
    system-startet tur går I DAG gennem `start_autonomous_run`.

    RETTET 26/10-2026 — tredje gang samme fejlklasse ramte denne fil. Vagten
    greppede efter den BOGSTAVELIGE streng `user_present=_bruger_til_stede(run)`
    og faldt derfor på ren main, da kilden lagde kaldet i en mellemvariabel
    (`_tilstede = _bruger_til_stede(run)` … `user_present=_tilstede`) — selvom
    egenskaben var præcis den samme. En vagt der holder en skrivemåde i stedet
    for egenskaben fælder den næste der skriver koden pænere, og lader den
    eneste ændring der betyder noget passere.

    Vagten parser derfor AST'en og følger værdien tilbage til sin oprindelse:
    `user_present` skal — direkte eller gennem en mellemvariabel — stamme fra
    `_bruger_til_stede(run)`, og ingen gren må røre beskedteksten.
    """
    import ast

    træ = ast.parse(
        Path("core/services/visible_tool_exec.py").read_text(encoding="utf-8"))

    def _fra_koerslen(node: ast.AST) -> bool:
        """Stammer værdien fra `_bruger_til_stede(run)` — direkte eller via navn?"""
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_bruger_til_stede"):
            return True
        if isinstance(node, ast.Name):
            for tildeling in ast.walk(træ):
                if not isinstance(tildeling, (ast.Assign, ast.AnnAssign)):
                    continue
                mål = (tildeling.targets if isinstance(tildeling, ast.Assign)
                       else [tildeling.target])
                if any(isinstance(m, ast.Name) and m.id == node.id for m in mål):
                    if tildeling.value is not None and _fra_koerslen(tildeling.value):
                        return True
        return False

    kald = [
        kw.value
        for node in ast.walk(træ)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "user_present"
    ]
    assert kald, "exec-stedet sender ikke længere user_present — vagten måler intet"

    for værdi in kald:
        assert _fra_koerslen(værdi), (
            "exec-stedet skal udlede 'ingen bruger' af kørslen "
            f"(_bruger_til_stede(run)) — fandt {ast.dump(værdi)}")

    # …og det maa ALDRIG komme fra beskeden. Det var hele kategorifejlen:
    # «Du er i en drømmetilstand…» laest som brugerens frustration.
    for værdi in kald:
        navne = {n.id for n in ast.walk(værdi) if isinstance(n, ast.Name)}
        for forbudt in ("user_message", "user_message_preview", "besked"):
            assert forbudt not in navne, (
                f"flaget udledes af tekst ({forbudt}) — det var netop fejlen")


# ── Gatens egen svarkanal må ikke være gatet (30/9-2026) ──────────────────────
#
# Målt 30/9: gaten blokerede `override_gate`, `pause_and_ask` OG spørgsmålet om
# at genstarte den — tre gange i samme tur på `risk marker: 'merge'`, hvor ordet
# stod i Bjørns videresendte rapport. Så var `bash` den eneste vej ud, og
# ledger'en tabte grunden til at bagdøren blev brugt.
#
# MUTATION der skal fanges:
#   M10 — fjern de tre navne fra `_ALWAYS_ALLOWED_TOOLS` -> denne test falder

def test_gatens_egen_svarkanal_er_aldrig_gatet(monkeypatch):
    """At gate svarkanalen kan ikke beskytte noget — den fjerner kun udvejen.

    `override_gate` fyrer først EFTER at gaten har logget sin blokering, og
    `pause_and_ask` er det modsatte af at handle. En gate der blokerer «spørg
    først» presser mod handling, ikke væk fra den.
    """
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    for navn in ("override_gate", "gate_override_status", "pause_and_ask"):
        allowed, reason = vg.check_veto(navn, "jeg pusher nu", record_event=True)
        assert allowed is True, f"{navn} blev gatet: {reason}"
    assert written == [], "svarkanalen må ikke skrive blocked-rækker"

    # Kontrollen: SAMME sektion blokerer stadig en rigtig handling. Uden den
    # her kunne testen bestå fordi sektionen slet ikke vetoer noget.
    allowed, _ = vg.check_veto("write_file", "jeg pusher nu", record_event=True)
    assert allowed is False, "kontrollen fejler: sektionen vetoer ikke længere"
    assert len(written) == 1 and written[0]["tool_name"] == "write_file"


# ── Forslaget til næste opgave må ikke gates (8/10-2026) ─────────────────────
# Målt 8/10-2026: gaten blokerede `suggest_next_task` FEM gange i samme tur på
# `risk marker: 'merge'` — fordi turen TALTE om en merge. Forslaget blev aldrig
# lagt, og Bjørn stod med et tomt skrivefelt uden at vide hvorfor.
#
# MUTATION der skal fanges:
#   M11 — fjern "suggest_next_task" fra `_ALWAYS_ALLOWED_TOOLS` -> testen falder

def test_forslaget_til_naeste_opgave_er_aldrig_gatet(monkeypatch):
    """Et forslag rører ingen fil og sender intet — at gate det kan intet
    beskytte. Det er hvordan turen slutter med et tilbud, ikke en handling."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, reason = vg.check_veto("suggest_next_task", "jeg pusher nu", record_event=True)
    assert allowed is True, f"suggest_next_task blev gatet: {reason}"
    assert written == [], "et forslag må ikke skrive blocked-rækker"

    # Kontrollen: sektionen vetoer stadig en rigtig handling, så testen ikke
    # består fordi sektionen er blevet harmløs.
    allowed, _ = vg.check_veto("write_file", "jeg pusher nu", record_event=True)
    assert allowed is False, "kontrollen fejler: sektionen vetoer ikke længere"


# ── Værktøjsopdagelsen må ikke være gatet (26/10-2026) ───────────────────────
#
# Målt 26/10: gaten blokerede `load_more_tools` — det værktøj der henter
# skemaet for `override_gate`. Når `override_gate` ikke allerede var i
# værktøjslisten, var der dermed ingen vej til at hente den: gaten blokerede
# adgangen til sin egen frigivelsesmekanisme. Observeret som
# veto-063b9826d64d, i samme tur hvor en MEMORY-rettelse blev afvist.
#
# Samme klasse som svarkanalen ovenfor: at gate adgangen til udvejen fjerner
# ikke behovet for den — den gør bare `bash` til den eneste dør.
#
# MUTATION der skal fanges:
#   M12 — fjern "load_more_tools" fra `_ALWAYS_ALLOWED_TOOLS` -> testen falder

def test_vaerktoejsopdagelsen_er_aldrig_gatet(monkeypatch):
    """`load_more_tools` henter KUN et skema — den udfører intet."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, reason = vg.check_veto("load_more_tools", "jeg pusher nu", record_event=True)
    assert allowed is True, f"load_more_tools blev gatet: {reason}"
    assert written == [], "værktøjsopdagelse må ikke skrive blocked-rækker"

    # Kontrollen: sektionen vetoer stadig en rigtig handling, så testen ikke
    # består fordi sektionen er blevet harmløs.
    allowed, _ = vg.check_veto("write_file", "jeg pusher nu", record_event=True)
    assert allowed is False, "kontrollen fejler: sektionen vetoer ikke længere"


# ── Hele frigivelses-kæden skal være åben (26/10-2026) ───────────────────────
#
# Egenskaben er ikke de enkelte navne, men at der findes en SAMMENHÆNGENDE vej
# ud af en blokering. Mangler ét led, er de øvrige utilstrækkelige — det er
# præcis hvad der skete 26/10, hvor `override_gate` var undtaget men skemaet
# for den ikke kunne hentes.
#
# MUTATION der skal fanges:
#   M13 — fjern ét vilkårligt led af kaeden -> testen falder

def test_frigivelseskaeden_er_komplet(monkeypatch):
    """Se status, hent skemaet, armér — eller spørg. Alle fire led skal virke."""
    from core.services.veto_gate import _ALWAYS_ALLOWED_TOOLS

    kaede = ("gate_override_status", "load_more_tools", "override_gate", "pause_and_ask")
    manglende = [n for n in kaede if n not in _ALWAYS_ALLOWED_TOOLS]
    assert not manglende, f"frigivelseskaeden mangler: {manglende}"

    # Og hvert led skal faktisk slippe igennem — ikke bare stå på listen.
    vg, _ = _hermetic(monkeypatch, _FIRM_SECTION)
    for navn in kaede:
        allowed, reason = vg.check_veto(navn, "jeg pusher nu", record_event=False)
        assert allowed is True, f"{navn} blev gatet: {reason}"
