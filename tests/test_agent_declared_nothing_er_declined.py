"""En agent der SELV erklærer at den ikke leverede noget er ikke en succes (22/11-2026).

MAALT 22/11-2026 paa `run-3d7235b3553245c5`, skrevet 17 sekunder EFTER at tjenesten
var genstartet med den rettede kode: agenten svarede ordret «Ingen af mine værktøjer
kan afvikle `systemctl status jarvis-api --no-pager` … jeg har kun filsystem-/
søgeværktøjer» og blev stemplet `completed` med tom fejlkode.

Hvorfor den slap igennem: `decline_error` er en ORDLISTE. Formuleringen brugte «kan
afvikle» hvor moenstrene kender «kan koere» — og fire nye moenstre tilfoejet samme dag
fangede den stadig ikke. Ordlister fanger det man har set; agenten vaelger et andet ord.

DEN STRUKTURELLE VEJ
`_AGENT_COVERAGE_RULE` beder nu hver agent afslutte med én `DÆKNING:`-linje, og
«DÆKNING: ingen» er agentens eget udsagn om at den ikke leverede noget. Et fast format
kan ikke omgaas ved at vaelge et andet verbum. Loekken faar dermed en FEMTE indgang,
som de fire runtime-maalte (must_write, loefte, kontrakt, nummererede spoergsmaal) ikke
daekker for en laese-agent paa en opgave uden tal.
"""

from __future__ import annotations

import pytest

from core.runtime.db_agent_contract import _incomplete_kode, decline_error
from core.services import agent_loop_core as core
from core.services.agent_runtime_base import _role_prompt

# Den faktiske tekst fra det run der blev maalt. Forkortet, men ordlyden er den samme:
# ingen af ordene «køre», «løse opgaven» eller «besvare» optræder — derfor fangede
# ingen af de atten ordliste-mønstre den.
FAKTISK = (
    "Ingen af mine værktøjer kan afvikle `systemctl status jarvis-api --no-pager` — jeg "
    "har kun filsystem-/søgeværktøjer i workspace-roden, ingen exec/SSH til den kørende "
    "server. Jeg har til gengæld verificeret, hvad der findes i repoet vedr. tjenesten."
)


class FakeIO:
    """Minimal I/O til `run_tool_loop` — samme form som tests/test_agent_loop_core.py."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.model_calls: list[dict] = []
        self.tool_calls: list[str] = []

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls.append({"tools": tools, "requires_tools": requires_tools})
        r = self.replies.pop(0) if self.replies else {"text": ""}
        if isinstance(r, Exception):
            raise r
        return r

    def tool(self, tc):
        self.tool_calls.append(tc["id"])
        return "ok"

    def after_tool(self, tc, out):
        pass

    def after_round(self, rounds, tool_calls):
        pass


def _koer(tekst: str):
    io = FakeIO([{"text": tekst}, {"text": tekst}])
    return core.run_tool_loop(
        io, prompt="Kør `systemctl status jarvis-api` og rapportér resultatet.",
        tools_payload=[{"function": {"name": "read_file"}}], requires_tools=True,
        provider="p", model="m", scout=False, max_rounds=3,
        synthesis_directive="SLUT", expected_result="",
    )


# ── den strukturelle etiket ──────────────────────────────────────────────────

def test_erklaeringen_om_ingen_leverance_er_declined():
    """«DÆKNING: ingen» er agentens eget udsagn — det skal give capability, ikke delivery."""
    assert decline_error(text=f"{FAKTISK}\n\nDÆKNING: ingen") == (
        "AGENT_DECLINED", "capability")


def test_den_positive_erklaering_doemmes_ikke():
    """`leveret` er den positive form. Et ord vi ikke kender maa aldrig blive en dom."""
    assert decline_error(text=f"{FAKTISK}\n\nDÆKNING: leveret") == ("", "")


def test_uden_linje_doemmes_intet():
    """Ingen erklæring = vi ved det ikke. Saa falder vi tilbage til ordlisten som foer."""
    assert decline_error(text=FAKTISK) == ("", "")


def test_linjen_laeses_i_slutningen_af_en_lang_tekst():
    """Vinduet paa 250 tegn kan ikke bruges: linjen staar pr. definition til sidst."""
    lang = ("Jeg har gennemgået otte filer og sammenlignet deres indhold med main. " * 8)
    assert len(lang) > 500, "forudsætning: teksten skal være længere end vinduet"
    assert decline_error(text=f"{lang}\nDÆKNING: ingen") == (
        "AGENT_DECLINED", "capability")


def test_markeringen_baerer_erklaeringen_videre():
    """`_incomplete_kode` er den vej markeringen tager — den skal ogsaa se den."""
    tekst = (
        "UFULDSTÆNDIG (agenten erklærede selv at den ikke leverede noget) — "
        f"agentens tekst:\n{FAKTISK}\n\nDÆKNING: ingen"
    )
    assert _incomplete_kode(tekst) == ("AGENT_DECLINED", "capability")


def test_kapacitet_vejer_tungere_end_agentens_egen_fortolkning():
    """Et rundebudget der loeb ud er en RUNTIME-maalt kendsgerning, ikke en vurdering."""
    tekst = (
        "UFULDSTÆNDIG (rundebudgettet løb ud efter 8 runder) — "
        f"agentens tekst:\n{FAKTISK}\n\nDÆKNING: ingen"
    )
    assert _incomplete_kode(tekst) == ("AGENT_BUDGET_EXHAUSTED", "capacity")


# ── den femte indgang i loekken ─────────────────────────────────────────────

def test_loekken_markerer_en_erklaering_om_ingenting():
    """Kernen: uden denne indgang blev markeringen ALDRIG skrevet for en laese-agent."""
    out = _koer(f"{FAKTISK}\n\nDÆKNING: ingen")
    assert out.get("incomplete") is True, (
        "løkken meldte en erklæring om nul leverance som fuldført")
    assert "erklærede selv" in str(out.get("stop_reason") or ""), out.get("stop_reason")


def test_loekken_lader_en_erklaeret_leverance_vaere():
    """Den positive form maa ikke faelde noget — ellers er vagten ubrugelig."""
    out = _koer(f"{FAKTISK}\n\nDÆKNING: leveret")
    assert "incomplete" not in out, out


def test_reglen_i_prompten_er_ubetinget():
    """Reglen var betinget af nummererede spoergsmaal — og blev derfor aldrig brugt.

    Maalt 22/11: 0 af 1951 runs havde en DÆKNING-linje. Uden en ubetinget regel er
    den strukturelle vej tom, uanset hvor god parseren er.
    """
    prompt = _role_prompt("Du er researcher.")
    assert "ALWAYS end your answer with ONE line" in prompt
    assert "DÆKNING: leveret" in prompt and "DÆKNING: ingen" in prompt


@pytest.mark.parametrize("form", ["DÆKNING: ingen", "Dækning: ingen", "DÆKNING: intet"])
def test_formen_er_fast_men_store_smaa_bogstaver_og_synonymer_taeller(form):
    """Agenten skriver den form den blev bedt om; vi accepterer de tre varianter."""
    assert decline_error(text=f"{FAKTISK}\n{form}") == ("AGENT_DECLINED", "capability")
