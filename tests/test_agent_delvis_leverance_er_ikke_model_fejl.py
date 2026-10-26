"""En delvis leverance er ikke en model-fejl (26/10-2026).

Maalt paa `asg-4a79ab1ca3094db2`: agenten laeste 6 vaerktoejskald og svarede
KORREKT paa 1 af 3 spoergsmaal. Udfaldet blev alligevel stemplet `AGENT_FAILED`
med `error_phase: "model"` — hvilket paastaar at MODELLEN fejlede, naar den
faktisk arbejdede og leverede.

Fasen er ikke kosmetik: den er det spor den naeste mig soeger i. "model" peger
paa udbyderen, "delivery" peger paa leverancen. Forkert fase = forkert jagt.

Vagten er et PAR: en delvis leverance skal markeres, og en aegte fejl maa ikke
blive sluppet igennem som "delivery" — ellers gør vagten systemet blindt.
"""
from __future__ import annotations

from core.runtime.db_agent_contract import partial_delivery_error

DELVIS = (
    "UFULDSTÆNDIG (3 ubesvarede spørgsmål) — agentens tekst:\n"
    "Confirmed: Task schema has exactly 5 fields: description, prompt, "
    "subagent_type, model, run_in_background."
)


# ── Acceptkriterium 1: delvis leverance markeres som delivery ────────────────
def test_delvis_leverance_faar_delivery_og_incomplete():
    kode, fase = partial_delivery_error(full=DELVIS, registry_status="failed")
    assert kode == "AGENT_INCOMPLETE", f"fik {kode!r}"
    assert fase == "delivery", f"fik {fase!r}"


# ── Acceptkriterium 2: en AEGTE fejl maa ikke blive "delivery" ───────────────
def test_aegte_fejl_uden_tekst_beholder_model_fasen():
    """En agent der fejlede uden at levere noget er stadig en model-fejl."""
    kode, fase = partial_delivery_error(full="", registry_status="failed")
    assert (kode, fase) == ("AGENT_FAILED", "model")


def test_fejl_med_tekst_uden_markering_er_stadig_model():
    """Tekst alene er ikke nok: markeringen skal vaere der, ellers er det en
    almindelig fejl der tilfaeldigt skrev noget."""
    kode, fase = partial_delivery_error(
        full="RuntimeError: udbyderen svarede 500", registry_status="failed")
    assert (kode, fase) == ("AGENT_FAILED", "model")


# ── Acceptkriterium 3: de andre terminale statusser er uberoerte ────────────
def test_cancelled_og_expired_beholder_sine_faser():
    assert partial_delivery_error(full="", registry_status="cancelled") == (
        "CANCELLED", "recovery")
    assert partial_delivery_error(full="", registry_status="expired") == (
        "TIMED_OUT", "budget")


def test_ukendt_status_giver_tomme_felter():
    assert partial_delivery_error(full="", registry_status="weird") == ("", "")


# ── Acceptkriterium 4: hvid rum er ikke en leverance ───────────────────────
def test_kun_hvidrum_taeller_ikke_som_leverance():
    kode, fase = partial_delivery_error(full="   \n\t ", registry_status="failed")
    assert (kode, fase) == ("AGENT_FAILED", "model")
