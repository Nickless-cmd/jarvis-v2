"""Pris-værn for autonome runs — Ollamas myldretid og pris-loftet (10/10-2026).

Baggrund (målt 10/10-2026): den LÆRTE routing-præference stod på
``ollama/glm-5.2:cloud`` ($1,40/M input) og sendte 788 autonome kald dertil —
9× den konfigurerede base. Ingen af de eksisterende guards fangede den, fordi de
dømmer på udbyder-navn ('deepseek') og kode-suffiks ('-code:'), ikke på pris.
Efter 31/8-2026 er ollama-cloud ikke længere «gratis» (kvote-planen er afløst af
usage-credits), så et dyrt lært valg brænder rigtige penge — tavst, fordi
``costs``-tabellen bogfører $0 for udbydere uden priser.

To ting testes her, og de hører sammen:
  1. **Vinduet.** Ollamas myldretid er 12–18 UTC på hverdage. DeepSeeks er
     01–04 og 06–10. De er IKKE ens, og et svar fra den forkerte tabel
     klassificerede 262 af vores egne kald forkert.
  2. **Loftet.** Ingen autonom kørsel må ende over $0,35/M input — og ukendt
     pris klemmer også (fail-closed), mens en LOKAL model slipper (gratis).
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock

import pytest

from core.services import central_router_adapt as cra
from core.services import llm_pricing as lp

# Mandag 12/10-2026 — en hverdag. Lørdag 10/10-2026 — en weekenddag.
_MAN = datetime(2026, 10, 12, tzinfo=timezone.utc)
_LØR = datetime(2026, 10, 10, tzinfo=timezone.utc)


def _paa(dag: datetime, time: int) -> datetime:
    return dag.replace(hour=time)


# ── 1. Vinduet ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("time, forventet", [
    (11, False),   # 13 dansk — lige før
    (12, True),    # 14 dansk — åbner
    (17, True),    # 19 dansk — sidste hele time
    (18, False),   # 20 dansk — lukker
    (3, False),    # 05 dansk — DeepSeeks vindue, IKKE Ollamas
    (8, False),    # 10 dansk — DeepSeeks vindue, IKKE Ollamas
])
def test_ollama_vinduet_er_12_til_18_utc(time: int, forventet: bool) -> None:
    assert lp.er_ollama_myldretid(_paa(_MAN, time)) is forventet


def test_weekend_er_aldrig_ollama_myldretid() -> None:
    assert lp.er_ollama_myldretid(_paa(_LØR, 14)) is False


def test_ugyldigt_tidspunkt_prises_som_myldretid() -> None:
    """Fail-closed: kan vinduet ikke afgøres, vælges det dyre — ikke det billige."""
    assert lp.er_ollama_myldretid("ikke-en-dato") is True


def test_de_to_vinduer_er_forskellige() -> None:
    """Kernen i hele sagen: 03 UTC er DeepSeeks myldretid men Ollamas off-peak,
    og 13 UTC er det omvendte. Deler man tabel, klassificerer man forkert."""
    nat, eftermiddag = _paa(_MAN, 3), _paa(_MAN, 13)
    assert lp.er_myldretid(nat) is True and lp.er_ollama_myldretid(nat) is False
    assert lp.er_myldretid(eftermiddag) is False and lp.er_ollama_myldretid(eftermiddag) is True


# ── 2. Pris-opslaget ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("model, off_peak, peak", [
    ("deepseek-v4.1-flash:cloud", 0.15, 0.30),
    ("glm-5.3-flash:cloud", 0.15, 0.15),
    ("glm-5.2:cloud", 1.40, 1.40),
    ("gemma4:31b-cloud", 0.14, 0.14),   # '-cloud'-suffiks, ikke ':cloud'
])
def test_pris_pr_million_med_enheden_i_navnet(model: str, off_peak: float, peak: float) -> None:
    assert lp.ollama_input_pris_per_m(model, _paa(_MAN, 20)) == pytest.approx(off_peak)
    assert lp.ollama_input_pris_per_m(model, _paa(_MAN, 13)) == pytest.approx(peak)


def test_ukendt_model_giver_none_ikke_nul() -> None:
    """None, ikke 0.0: et loft der læste «ukendt» som «gratis» ville slippe
    præcis den model igennem det skulle fange."""
    assert lp.ollama_input_pris_per_m("helt-ny-model:cloud", _paa(_MAN, 13)) is None


# ── 3. Loftet ─────────────────────────────────────────────────────────────────

def test_loftet_klemmer_den_model_der_braendte_credits() -> None:
    """glm-5.2 er den konkrete synder — 788 autonome kald til $1,40/M."""
    assert cra._input_pris("glm-5.2:cloud") > cra._AUTONOMOUS_MAX_INPUT_USD_PER_M


@pytest.mark.parametrize("model", ["glm-5.3-flash:cloud", "deepseek-v4.1-flash:cloud", "gpt-oss:20b-cloud"])
def test_billige_cloud_modeller_slipper_igennem(model: str) -> None:
    pris = cra._input_pris(model)
    assert pris is not None and pris <= cra._AUTONOMOUS_MAX_INPUT_USD_PER_M


@pytest.mark.parametrize("model", ["qwen3:4b-instruct-2507-q4_K_M", "llama3.1:8b"])
def test_lokale_modeller_er_gratis_og_klemmes_ikke(model: str) -> None:
    """En lokal model kører på vores egen GPU. Blev den læst som «ukendt», ville
    loftet klemme den til en BETALT sky — den modsatte fejl af den tilsigtede."""
    assert cra._input_pris(model) == 0.0


def test_ukendt_cloud_model_klemmes_fail_closed() -> None:
    pris = cra._input_pris("helt-ny-model:cloud")
    assert pris is None or pris > cra._AUTONOMOUS_MAX_INPUT_USD_PER_M


# ── 4. Den pris-bevidste base ─────────────────────────────────────────────────

def test_basen_skifter_til_den_faste_billige_i_myldretiden() -> None:
    with mock.patch("core.services.llm_pricing.er_ollama_myldretid", return_value=True):
        assert cra._pris_bevidst_base("ollama", "deepseek-v4.1-flash:cloud") == (
            "ollama", "glm-5.3-flash:cloud")


def test_basen_staar_urørt_uden_for_myldretiden() -> None:
    with mock.patch("core.services.llm_pricing.er_ollama_myldretid", return_value=False):
        assert cra._pris_bevidst_base("ollama", "deepseek-v4.1-flash:cloud") == (
            "ollama", "deepseek-v4.1-flash:cloud")


def test_den_betalte_deepseek_base_roeres_ikke() -> None:
    """deepseek.com har sit eget, smallere vindue — den må ikke skiftes her."""
    with mock.patch("core.services.llm_pricing.er_ollama_myldretid", return_value=True):
        assert cra._pris_bevidst_base("deepseek", "deepseek-flash") == ("deepseek", "deepseek-flash")


# ── 5. End-to-end gennem den ægte vælger ──────────────────────────────────────

@pytest.mark.parametrize("peak, forventet_model", [
    (True, "glm-5.3-flash:cloud"),      # 14 dansk — deepseek koster dobbelt
    (False, "deepseek-v4.1-flash:cloud"),  # off-peak — begge er $0,15, behold konsistensen
])
def test_laert_glm52_praefence_klemmes_i_begge_vinduer(peak: bool, forventet_model: str) -> None:
    """Den lærte præference pegede på glm-5.2. Den skal klemmes uanset vindue,
    og lande på den rigtige billige model for det vindue vi står i."""
    with mock.patch.object(cra, "resolve_visible_model", return_value=("ollama", "glm-5.2:cloud")), \
         mock.patch("core.services.llm_pricing.er_ollama_myldretid", return_value=peak):
        assert cra.resolve_autonomous_model() == ("ollama", forventet_model)


def test_billig_laert_praefence_slipper_igennem() -> None:
    """Loftet skal ikke dræbe den adaptive læring inden for det billige segment."""
    with mock.patch.object(cra, "resolve_visible_model", return_value=("ollama", "glm-5.3-flash:cloud")), \
         mock.patch("core.services.llm_pricing.er_ollama_myldretid", return_value=False):
        assert cra.resolve_autonomous_model() == ("ollama", "glm-5.3-flash:cloud")


# ── 6. Lærerens pris-gate (10/10-2026) ────────────────────────────────────────
# Uden denne gate nulstiller en manuel oprydning sig selv: læreren rangerer på
# ALL-TIME model_meta og skriver sin vinder til live-præferencen hvert 45. min.

@pytest.mark.parametrize("model_key, forventet", [
    ("ollama/glm-5.2:cloud", False),                 # $1,40/M — den vi ryddede væk
    ("ollama/glm-5.3:cloud", False),                 # $1,40/M
    ("ollama/glm-5.3-flash:cloud", True),            # $0,15/M
    ("ollama/deepseek-v4.1-flash:cloud", True),      # $0,15 off-peak / $0,30 peak
    ("ollama/gemma4:31b-cloud", True),               # vision, $0,14/M
    ("ollama/qwen3:4b-instruct-2507-q4_K_M", True),  # lokal GPU — intet pr. token
    ("ollama/helt-ny-model:cloud", False),           # ukendt pris → fail-closed
    ("", False),                                     # tom → nej
])
def test_laererens_prisgate(model_key: str, forventet: bool) -> None:
    assert cra._pref_pris_ok(model_key) is forventet


def test_laereren_skriver_ikke_en_dyr_praefence_til_live() -> None:
    """Selv om læreren FORESLÅR glm-5.2, må den ikke lande i live-præferencen.
    Shadow'en skal stadig skrives, så forslaget er synligt i Mission Control."""
    skrevet: dict = {}
    with mock.patch.object(cra, "compute_preference",
                           return_value={"enough": True, "preferred": "ollama/glm-5.2:cloud",
                                         "strength": 0.5, "support": 9}), \
         mock.patch.object(cra, "is_live_enabled", return_value=True), \
         mock.patch.object(cra, "_kv_set", side_effect=lambda k, v: skrevet.__setitem__(k, v)), \
         mock.patch.object(cra.gov, "gate_self_mutation",
                           return_value=mock.Mock(action="apply")):
        cra.run_router_adapt_tick()
    assert cra._PREF_KEY not in skrevet, "den dyre præference blev skrevet til LIVE"
    assert cra._SHADOW_KEY in skrevet, "shadow-diff'en skal stadig være synlig"


def test_laereren_skriver_en_billig_praefence_til_live() -> None:
    """Gaten må ikke dræbe den adaptive læring inden for det billige segment."""
    skrevet: dict = {}
    with mock.patch.object(cra, "compute_preference",
                           return_value={"enough": True, "preferred": "ollama/glm-5.3-flash:cloud",
                                         "strength": 0.5, "support": 9}), \
         mock.patch.object(cra, "is_live_enabled", return_value=True), \
         mock.patch.object(cra, "_kv_set", side_effect=lambda k, v: skrevet.__setitem__(k, v)), \
         mock.patch.object(cra.gov, "gate_self_mutation",
                           return_value=mock.Mock(action="apply")):
        cra.run_router_adapt_tick()
    assert cra._PREF_KEY in skrevet
    assert skrevet[cra._PREF_KEY]["visible"]["model"] == "ollama/glm-5.3-flash:cloud"
