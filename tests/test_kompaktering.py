"""Én komprimerings-sti, med de garantier specen kraever (18/9-2026).

Plan og maalinger: docs/superpowers/plans/2026-09-18-kompaktering-en-sti.md.
Reglerne fra den slettede `compaction_runtime.py` (fremdrift, terminal ved
manglende fremdrift, beskyttet hale) er bragt hertil — nu paa den sti der
faktisk koerer.
"""
from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest

from core.context import kompaktering as kp
from core.context import session_compact as sc

_REPO = Path(__file__).resolve().parents[1]


def _session(titel: str = "t") -> str:
    from core.services.chat_sessions import create_chat_session
    return str(create_chat_session(title=titel)["id"])


def _besked(sid: str, rolle: str, tekst: str) -> None:
    from core.services.chat_sessions import append_chat_message
    append_chat_message(session_id=sid, role=rolle, content=tekst)


def _markoer(sid: str, tekst: str) -> None:
    from core.services.chat_sessions import store_compact_marker
    store_compact_marker(sid, tekst)


# ── 1. Den rullende opsummering ──────────────────────────────────────────
#
# Foer: de seneste 500 raekker, uden den forrige markoer. Den nye markoer
# afloeste den gamle, og alt aeldre gik tabt. CT105: 8.344 raekker/29 markoerer.

def test_komprimeringen_ser_det_jarvis_ser(isolated_runtime) -> None:
    sid = _session()
    _besked(sid, "user", "meget gammel besked foer markoeren")
    _markoer(sid, "RESUMÉ AF ALT FOER")
    _besked(sid, "user", "ny besked")
    _besked(sid, "assistant", "nyt svar")

    msgs = sc._get_all_session_messages(sid)

    assert msgs[0] == {"role": kp.TIDLIGERE_RESUME, "content": "RESUMÉ AF ALT FOER"}
    indhold = [m["content"] for m in msgs[1:]]
    assert indhold == ["ny besked", "nyt svar"]
    # Det der ligger FOER markoeren er allerede i resuméet — ikke igen.
    assert "meget gammel besked foer markoeren" not in indhold


def test_uden_markoer_er_det_bare_beskederne(isolated_runtime) -> None:
    sid = _session()
    _besked(sid, "user", "a")
    assert [m["role"] for m in sc._get_all_session_messages(sid)] == ["user"]


def test_det_forrige_resumé_naar_opsummereren(isolated_runtime) -> None:
    """Hele pointen: den forrige opsummering er INPUT til den naeste."""
    sid = _session()
    _markoer(sid, "RESUMÉ AF ALT FOER")
    for i in range(6):
        _besked(sid, "user", f"spoergsmaal {i} " + "x" * 400)
        _besked(sid, "assistant", f"svar {i} " + "y" * 400)

    set_input: list[list[dict]] = []

    def opsummer(msgs: list[dict]) -> str:
        set_input.append(msgs)
        return "kort nyt resumé"

    res = sc.compact_session_history(sid, keep_recent_tokens=200, summarise_fn=opsummer)

    assert res is not None
    assert set_input[0][0]["role"] == kp.TIDLIGERE_RESUME
    assert "RESUMÉ AF ALT FOER" in set_input[0][0]["content"]


def test_rendereren_navngiver_det_forrige_resumé() -> None:
    from core.context.compaction_policy import render_transcript_for_summary
    ud = render_transcript_for_summary([{"role": kp.TIDLIGERE_RESUME, "content": "X"}])
    assert ud.startswith("[Tidligere resumé")


# ── 2. Fremdrift eller intet ─────────────────────────────────────────────

def _lang_session() -> str:
    # Stoerre end halens gulv (4.000 tokens) — ellers beholdes alt og der er
    # intet at komprimere, hvilket er rigtig opfoersel, men ikke det vi tester.
    sid = _session()
    for i in range(6):
        _besked(sid, "user", f"q{i} " + "x" * 8000)
        _besked(sid, "assistant", f"a{i} " + "y" * 8000)
    return sid


def test_uden_fremdrift_gemmes_INTET(isolated_runtime, monkeypatch) -> None:
    sid = _lang_session()
    gemt: list[str] = []
    monkeypatch.setattr(sc, "_store_marker", lambda s, t, git_sha="": gemt.append(t) or "m")

    # En «opsummering» der er stoerre end det den skulle erstatte.
    with pytest.raises(kp.NotAdvancing):
        sc.compact_session_history(sid, keep_recent_tokens=200, kraev_fremdrift=True,
                                   summarise_fn=lambda m: "z" * 200_000)
    assert gemt == []


def test_manglende_fremdrift_er_terminal_indtil_overfladen_flytter_sig(isolated_runtime, monkeypatch) -> None:
    sid = _lang_session()
    monkeypatch.setattr(kp.StruktureretOpsummering, "__call__", lambda self, m: "z" * 200_000)
    monkeypatch.setattr(kp, "_ground_truth_for", lambda s: "")

    assert kp.komprimer_session(sid, udloeser="test") is None
    log = kp.seneste_log(sid)
    assert log is not None and log["fremdrift"] == 0

    # Samme overflade: et nyt forsoeg er samme kald med samme udfald.
    assert kp.staar_fast(sid) is True

    # Overfladen flytter sig — en ny besked — og saa maa der proeves igen.
    _besked(sid, "user", "noget nyt")
    assert kp.staar_fast(sid) is False


def test_kun_det_forrige_resumé_er_ikke_noget_at_komprimere(isolated_runtime) -> None:
    """At opsummere en opsummering igen ville skrumpe den hver gang og ikke
    flytte noget andet — en loekke der langsomt sletter historikken."""
    sid = _session()
    _markoer(sid, "R" * 20_000)
    _besked(sid, "user", "kort")
    _besked(sid, "assistant", "kort")

    with pytest.raises(kp.NotAdvancing):
        sc.compact_session_history(sid, keep_recent_tokens=50, kraev_fremdrift=True,
                                   summarise_fn=lambda m: "kort")


def test_vellykket_komprimering_logger_spor_og_tal(isolated_runtime, monkeypatch) -> None:
    sid = _lang_session()
    monkeypatch.setattr(kp, "_ground_truth_for", lambda s: "")
    monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                        lambda *a, **k: "<summary>" + "Et rigtigt resumé af samtalen. " * 5 + "</summary>")

    res = kp.komprimer_session(sid, udloeser="test")

    assert res is not None
    assert res.vej == "llm"
    assert res.tokens_efter < res.tokens_foer
    log = kp.seneste_log(sid)
    assert log["vej"] == "llm" and log["fremdrift"] == 1 and log["udloeser"] == "test"
    assert log["marker_id"] == res.marker_id


# ── 3. Opsummeringen: struktureret, tabstolerant, ærlig ─────────────────

def test_ubrugeligt_svar_giver_mekanisk_vej_og_aldrig_tom(monkeypatch) -> None:
    monkeypatch.setattr(kp, "_ground_truth_for", lambda s: "")
    monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                        lambda *a, **k: "[Kontekst komprimeret — detaljer ikke tilgængelige]")
    op = kp.StruktureretOpsummering(session_id="s")
    ud = op([{"role": "user", "content": "hej"}])
    assert op.vej == "mekanisk"
    assert ud.strip() and "[user] hej" in ud


def test_mekanisk_opsummering_er_aldrig_tom() -> None:
    assert kp.mekanisk_opsummering([]).strip()
    assert kp.mekanisk_opsummering([{"role": "user", "content": ""}]).strip()


def test_mekanisk_opsummering_baerer_det_forrige_resumé_i_fuld_laengde() -> None:
    # Klippet som en almindelig besked (400 tegn) ville en fejlende udbyder
    # slette alt aeldre.
    ud = kp.mekanisk_opsummering([{"role": kp.TIDLIGERE_RESUME, "content": "R" * 5000}])
    assert ud.count("R") >= 5000


def test_timeouten_afbryder_FAKTISK_ventetiden(monkeypatch) -> None:
    """`with ThreadPoolExecutor(...)` ventede ved exit paa det haengende kald.
    Maalt 18/9: timeout 1 s, kalderen blokeret 4,0 s."""
    monkeypatch.setattr(kp, "_TIMEOUT_SEK", 1)
    t = time.monotonic()
    ud = kp._kald_med_timeout(lambda: time.sleep(4) or "for sent")
    assert ud == ""
    assert time.monotonic() - t < 2.0


def test_opsummeringen_maa_bruge_primaer_modellen(monkeypatch) -> None:
    """Bjoerns valg 19/8: et compact-resumé ER hans hukommelse. Den koerende
    komprimering manglede opt-in'et fra 14/9 til 18/9."""
    set_kw: list[dict] = []
    monkeypatch.setattr(kp, "_ground_truth_for", lambda s: "")
    monkeypatch.setattr("core.context.compact_llm.call_compact_llm",
                        lambda *a, **k: set_kw.append(k) or "")
    kp.StruktureretOpsummering(session_id="s")([{"role": "user", "content": "x"}])
    assert set_kw and set_kw[0].get("tillad_betalt") is True


# ── 4. Én komprimator ────────────────────────────────────────────────────

def test_kun_den_faelles_indgang_kalder_compact_session_history() -> None:
    """AST, ikke tekst-grep: en streng i en kommentar maa ikke taelle, og et
    kald maa ikke kunne gemme sig bag en omformattering."""
    kaldere: set[str] = set()
    for rod in ("core", "apps"):
        for p in (_REPO / rod).rglob("*.py"):
            if "__pycache__" in p.parts or "node_modules" in p.parts:
                continue
            try:
                trae = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for n in ast.walk(trae):
                if isinstance(n, ast.Call):
                    f = n.func
                    navn = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
                    if navn == "compact_session_history":
                        kaldere.add(str(p.relative_to(_REPO)))
    assert kaldere == {"core/context/kompaktering.py"}


def test_de_doede_komprimatorer_er_vaek() -> None:
    assert not (_REPO / "core/context/auto_compact.py").exists()


# ── Overflow er terminalt ────────────────────────────────────────────────

def test_context_overflow_er_ikke_retrybar() -> None:
    """Der findes ingen retry efter overflow, og det er med vilje: uden en
    komprimering der flytter overfladen ville et retry vaere samme kald."""
    from core.services.stream_failure_kind import classify_failure, is_retryable_kind
    kind, retryable = classify_failure(http_status=400, error_text="maximum context length exceeded")
    assert kind == "http_400_overflow"
    assert retryable is False
    assert is_retryable_kind(kind) is False


def test_komprimatoren_er_naabar_fra_de_konfigurerede_indgange() -> None:
    """Acceptkriteriet: den ene komprimator skal vaere REACHABLE.

    `docs/capability_matrix.md` har kun raekker for core/services/, og
    komprimatoren bor i core/context/. Testen bruger derfor auditens EGEN
    import-graf og naabarheds-soegning — samme maal som matricen, uden at
    bøje dens scope. `compaction_runtime` stod dér som 🔴 SUSPICIOUS: «not
    reachable from configured entry points».
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("capability_audit", _REPO / "scripts/capability_audit.py")
    audit = importlib.util.module_from_spec(spec)
    import sys
    # Scriptet har dataclasses; de slaar deres modul op i sys.modules.
    sys.modules["capability_audit"] = audit
    try:
        spec.loader.exec_module(audit)  # type: ignore[union-attr]
    finally:
        sys.modules.pop("capability_audit", None)

    filer = audit.find_python_files(_REPO)
    moduler = {audit.module_name_from_path(p): p for p in filer}
    kendte = set(moduler)
    graf = {navn: audit.parse_imports(p, current_module=navn, known_modules=kendte)
            for navn, p in moduler.items()}
    naabare, foraeldre = audit.compute_reachability(graf, audit.entry_modules())

    assert "core.context.kompaktering" in naabare
    assert "core.context.session_compact" in naabare
