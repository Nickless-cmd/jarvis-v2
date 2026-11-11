"""To grænser der begge var teater (11/11-2026).

MAALT FOER AENDRINGEN:

1. ``AGENT_INCOMPLETE``/``delivery`` blev sat for ENHVER tekst med ordet
   ``UFULDSTÆNDIG`` i. Markeringen baerer allerede den aegte grund i parentesen
   (``agent_runtime_base._loop_result`` skriver ``stop_reason`` derind), men den
   blev kastet vaek. Resultat: et kapacitetsstop ("rundebudgettet loeb ud") blev
   rapporteret som en mangelfuld leverance, og den naeste jagt gik efter den
   forkerte aarsag.

2. ``deadline_at`` blev skrevet ind i kontrakten af ``agent_task_facade`` (nu + 45
   min for skrivende, + 30 for laesende), gemt i ``agent_assignments``, projiceret
   til Desk — og **aldrig laest i loopet**. Den var dekoration. Det eneste loft der
   faktisk stoppede en agent var et rundetal paa 60, og maalt paa 133
   completed-koersler er median-rundetiden 3,5 s: 60 runder = ~3,5 minut, mens
   kontrakten gav 45. Rundetallet ramte altsaa foerst og klippede et arbejde der
   stadig havde tid.

Vagterne er PAR: hver aendring skal baade virke og ikke goere noget andet galt.
"""
from __future__ import annotations

import types
from datetime import UTC, datetime, timedelta

import pytest

from core.runtime.db_agent_contract import partial_delivery_error
from core.services import agent_loop_core as core


class FakeIO:
    def __init__(self, replies, tool_out="ok"):
        self.replies = list(replies)
        self.tool_out = tool_out
        self.model_calls = []

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls.append([dict(m) for m in messages])
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def tool(self, tc):
        return self.tool_out

    def after_tool(self, tc, out):
        pass

    def after_round(self, rounds, tool_calls):
        pass


def _tc(i):
    return {"id": f"c{i}", "function": {"name": "t", "arguments": "{}"}}


def _run(io, **kw):
    base = dict(prompt="P", tools_payload=[{"function": {"name": "t"}}], requires_tools=True,
                provider="p", model="m", scout=False, max_rounds=3, synthesis_directive="SLUT")
    base.update(kw)
    return core.run_tool_loop(io, **base)


#: Et svar der ikke er et loefte og ikke for kort, saa kun den graense vi maaler
#: kan goere det incomplete.
_FAERDIG = ("Undersoegelsen er afsluttet. Feltet hedder description og er en streng. "
            "Feltet prompt er en streng, subagent_type er en streng, og model er en streng. "
            "run_in_background er en boolean. Det er de fem felter, alle verificeret i koden.")


# ── 1. Klassifikationen: grunden i markeringen afgoer koden ──────────────────
@pytest.mark.parametrize("grund,kode,fase", [
    # Kapacitet: agenten blev STOPPET, dens leverance var ikke mangelfuld.
    ("rundebudgettet løb ud efter 60 runder", "AGENT_BUDGET_EXHAUSTED", "capacity"),
    ("deadline nået efter 12 runder", "AGENT_BUDGET_EXHAUSTED", "capacity"),
    # Leverance: agenten kunne arbejde men gjorde det ikke.
    ("agenten kunne skrive men skrev intet", "AGENT_NO_WRITE", "delivery"),
    ("3 værktøjskald, men svaret er et løfte om næste skridt — ikke et resultat",
     "AGENT_PROMISED_NOT_DONE", "delivery"),
    ("et løfte den ikke udførte", "AGENT_PROMISED_NOT_DONE", "delivery"),
    # Ukendt grund: den gamle kode bevares, saa eksisterende laesere ikke braekker.
    ("2 ubesvarede spørgsmål", "AGENT_INCOMPLETE", "delivery"),
    ("", "AGENT_INCOMPLETE", "delivery"),
])
def test_markeringens_grund_afgoer_koden(grund, kode, fase):
    tekst = f"UFULDSTÆNDIG ({grund}) — agentens tekst:\n" + _FAERDIG
    assert partial_delivery_error(full=tekst, registry_status="failed") == (kode, fase)


def test_en_aegte_fejl_er_stadig_model_og_ikke_kapacitet():
    """Vagten skal ikke goere alt til kapacitet — saa bliver systemet blindt."""
    assert partial_delivery_error(full="Connection reset by peer",
                                  registry_status="failed") == ("AGENT_FAILED", "model")


def test_tekst_med_parentes_uden_markering_falder_tilbage_paa_status():
    assert partial_delivery_error(
        full="RuntimeError (500) — udbyderen svarede",
        registry_status="failed") == ("AGENT_FAILED", "model")


# ── 2. Deadline: tiden er graensen ─────────────────────────────────────────
def _fast_tid(monkeypatch, nu: datetime) -> None:
    """Erstat `time` KUN inde i loop-kernen, saa den globale ur ikke roeres."""
    monkeypatch.setattr(core, "time", types.SimpleNamespace(
        time=lambda: nu.timestamp(), monotonic=lambda: nu.timestamp(),
        sleep=lambda _s: None))


def test_deadline_i_fortiden_stopper_foer_et_eneste_modelkald(monkeypatch):
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([{"text": _FAERDIG}])
    out = _run(io, deadline_at=(nu - timedelta(seconds=1)).isoformat())
    assert io.model_calls == [], "et modelkald blev brugt efter deadlinen"
    assert out.get("incomplete") is True
    assert "deadline" in str(out.get("stop_reason") or "")


def test_rundetallet_klipper_ikke_naar_der_findes_en_deadline(monkeypatch):
    """Det maalte problem: 60 runder = ~3,5 minut mod en deadline paa 45 minutter.

    Med en deadline langt ude skal et lavt `max_rounds` derfor IKKE klippe forloebet.
    """
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": "", "tool_calls": [_tc(2)]},
        {"text": "", "tool_calls": [_tc(3)]},
        {"text": _FAERDIG},
    ])
    out = _run(io, max_rounds=2, deadline_at=(nu + timedelta(minutes=40)).isoformat())
    assert out["rounds"] == 4, f"blev klippet ved {out['rounds']} runder"
    assert out["total_tool_calls"] == 3


def test_uden_deadline_gaelder_rundetallet_stadig(monkeypatch):
    """Regression: kaldes loekken uden deadline, er det gamle loft uaendret."""
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": "", "tool_calls": [_tc(2)]},
        {"text": "", "tool_calls": [_tc(3)]},
        {"text": _FAERDIG},
    ])
    out = _run(io, max_rounds=2)
    assert out["rounds"] == 2, f"loftet bandt ikke: {out['rounds']} runder"


def test_tidsnoten_naevner_den_mindste_taerskel_og_ikke_en_stoerre(monkeypatch):
    """Er der 2 minutter tilbage, er "10 minutter tilbage" en loegn."""
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([
        {"text": "", "tool_calls": [_tc(1)]},
        {"text": _FAERDIG},
    ])
    _run(io, max_rounds=10, deadline_at=(nu + timedelta(seconds=120)).isoformat())
    noter = [m["content"] for m in io.model_calls[1]
             if m["role"] == "user" and "Tidsgrænse" in str(m.get("content"))]
    assert noter, "tidsnoten blev aldrig injiceret"
    assert "3 minutter" in noter[-1], f"fik {noter[-1]!r}"
    assert "10 minutter" not in noter[-1]


def test_ugyldig_deadline_handhaeves_ikke_men_kaster_ikke(monkeypatch):
    nu = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    _fast_tid(monkeypatch, nu)
    io = FakeIO([{"text": "", "tool_calls": [_tc(1)]},
                 {"text": _FAERDIG}])
    out = _run(io, max_rounds=5, deadline_at="ikke-en-dato")
    assert out["rounds"] == 2
