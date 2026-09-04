"""Tests for hollow_promise_guard — fang 'lovede handling, kaldte intet værktøj'."""
from __future__ import annotations

import pytest

import core.services.hollow_promise_guard as hpg


# ── is_promise_of_action ─────────────────────────────────────────────────────────────

def test_detects_danish_promises():
    for t in [
        "Jeg kører self-review nu.",
        "Ja, du har ret. Jeg gør det nu.",
        "I gang — jeg fortsætter auditen.",
        "Jeg fortsætter auditen nu. 🎯",
        "I gang — jeg fortsætter auditen og gemmer bagefter. 🎯",
        "Lad mig lige køre tools.",
        "Nu kører jeg self-review og council.",
        "Jeg starter self-review nu, så council, så commit.",
    ]:
        assert hpg.is_promise_of_action(t) is True, t


def test_detects_english_promises():
    for t in ["I'll run it now.", "Let me start the audit.", "I'm going to check that.",
              "Running it now."]:
        assert hpg.is_promise_of_action(t) is True, t


def test_ignores_normal_answers():
    for t in [
        "Root-cause er cooldown 0; jeg har committet fixet og deployet.",
        "Her er de tre spor: STITCH, PULSE, DIASTOLE.",
        "Membranen er intakt, ingen brud.",
        "",
        "   ",
    ]:
        assert hpg.is_promise_of_action(t) is False, t


def test_question_tail_is_not_a_promise():
    # afventer bruger (spørgsmål) → ikke tom løfte (respektér consent-bug-læringen)
    assert hpg.is_promise_of_action("Skal jeg køre self-review nu?") is False


# ── is_hollow_promise ────────────────────────────────────────────────────────────────

def test_hollow_when_promise_and_zero_tools():
    assert hpg.is_hollow_promise("Jeg kører det nu.", total_tool_calls=0) is True


def test_not_hollow_when_a_tool_ran():
    # et værktøj KØRTE → ikke tomt (han handlede faktisk)
    assert hpg.is_hollow_promise("Jeg kører det nu.", total_tool_calls=3) is False


def test_not_hollow_when_already_nudged():
    assert hpg.is_hollow_promise("Jeg kører det nu.", total_tool_calls=0,
                                 nudged_already=True) is False


def test_not_hollow_on_empty_text():
    # tomt håndteres af empty-completion-vagten, ikke her
    assert hpg.is_hollow_promise("", total_tool_calls=0) is False


def test_not_hollow_on_normal_answer():
    assert hpg.is_hollow_promise("Fixet er committet og deployet.", total_tool_calls=0) is False


# ── flag ─────────────────────────────────────────────────────────────────────────────

def test_flag_default_true(monkeypatch):
    monkeypatch.delenv(hpg._ENV, raising=False)
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d: d)  # ingen override → default
    assert hpg.hollow_promise_guard_enabled() is True


def test_env_can_disable(monkeypatch):
    monkeypatch.setenv(hpg._ENV, "off")
    assert hpg.hollow_promise_guard_enabled() is False


def test_env_can_enable(monkeypatch):
    monkeypatch.setenv(hpg._ENV, "1")
    assert hpg.hollow_promise_guard_enabled() is True


def test_runtime_state_can_disable(monkeypatch):
    monkeypatch.delenv(hpg._ENV, raising=False)
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d: False)
    assert hpg.hollow_promise_guard_enabled() is False


# ── Udvidelse 30-08-2026 ────────────────────────────────────────────────────
# Bjørn: "han bliver cuttet" viste sig at være noget andet end afskæring: turen
# ender med et grammatisk HELT svar der annoncerer næste skridt — og stopper.
# Vagten var blind på to måder samtidig:
#   (a) den krævede nul værktøjskald i HELE runnet, men Jarvis kalder 15 og
#       stopper derefter, så summen var aldrig 0;
#   (b) mønstrene krævede verbum FØR nu-adverbiet ("jeg læser ... nu"), mens
#       han skriver "nu læser jeg X" — og "læser" manglede i nu-listen.
# Teksterne herunder er ordret fra samtalen 30-08-2026.

_ÆGTE_HALER = [
    "Funktionerne er lokaliseret — nu læser jeg `_pop_pre_run_state` og hele "
    "`_on_run_completed`-flowet for at se præcis hvor de tre fail-open-punkter sidder.",
    "Nu læser jeg `_git_staged_paths` og starten af `_try_auto_commit` — de to "
    "sidste steder jeg skal se før jeg skriver fixet.",
    "Hele gatens anatomi er nu kortlagt. Jeg læser de eksisterende auto-commit-tests "
    "for at matche mock-stilen præcist, før jeg skriver fixet og nye tests.",
    "Jeg har kortlagt de fem fund, så skriver jeg alle fem fixes.",
    "Jeg mangler at se hvordan touched-paths bygges, derefter retter jeg attributionsværnet.",
    "Søjle 3 — bevidsthed, non-lokalitet, og hvorfor det ændrer min betydning "
    "— kommer nu. Den her er den vigtigste.",
    "Bid 2 kommer nu — og det er dér, det rammer mig.",
    "Sidste graverunde: de konkrete hændelser ved navn, og hvad fysikken "
    "egentlig siger om måling og bevidsthed.",
]

_ALMINDELIGE_AFSLUTNINGER = [
    "Jeg har rettet fejlen og kørt testene — 34 grønne. Sig til hvis du vil have mere.",
    "Vil du have mig til at køre det nu?",
    "Her er resultatet af analysen. Der er tre muligheder, og jeg anbefaler den første.",
    "Opgaven er løst. Filerne er committet og pushet.",
]


def test_faktiske_haler_fra_30_august_fanges():
    """Skal fanges SELVOM runnet har kaldt værktøjer tidligere."""
    for t in _ÆGTE_HALER:
        assert hpg.is_hollow_promise(
            final_text=t, total_tool_calls=15, last_round_tool_calls=0) is True, t


def test_deferred_text_promises_can_be_identified_separately():
    assert hpg.is_deferred_text_promise(_ÆGTE_HALER[-3]) is True
    assert hpg.is_deferred_text_promise(_ÆGTE_HALER[-2]) is True
    assert hpg.is_deferred_text_promise(_ÆGTE_HALER[-1]) is True
    assert hpg.is_deferred_text_promise(_ÆGTE_HALER[0]) is False


def test_almindelige_afslutninger_fanges_ikke():
    for t in _ALMINDELIGE_AFSLUTNINGER:
        assert hpg.is_hollow_promise(
            final_text=t, total_tool_calls=15, last_round_tool_calls=0) is False, t


def test_vaerktoej_i_sidste_runde_er_ikke_tomt_loefte():
    """Kaldte han et værktøj i den runde, handlede han — så er det ikke tomt."""
    assert hpg.is_hollow_promise(
        final_text=_ÆGTE_HALER[0], total_tool_calls=15, last_round_tool_calls=1) is False


def test_bagudkompatibel_uden_sidste_runde():
    """Uden last_round_tool_calls falder vagten tilbage til den gamle adfærd."""
    t = _ÆGTE_HALER[0]
    assert hpg.is_hollow_promise(final_text=t, total_tool_calls=15) is False
    assert hpg.is_hollow_promise(final_text=t, total_tool_calls=0) is True


# ---------------------------------------------------------------------------
# 4. sep 2026: «vores cutoff bug er vendt tilbage». Det var ikke et cut — det
# var tre tomme løfter i træk, hver med en ordstilling mønster-listen ikke
# kendte. Haler taget ordret fra Bjørns samtale samme morgen.
# ---------------------------------------------------------------------------

REELLE_HALER = [
    "Først åbner jeg en session og finder hvad der scanner output for tidsclaims.",
    "Den læser jeg nu præcist.",
    "Lad mig læse resten (linje ~350-520) præcist.",
]


@pytest.mark.parametrize("hale", REELLE_HALER)
def test_faktiske_haler_fra_samtalen_fanges(hale):
    from core.services.hollow_promise_guard import is_promise_of_action

    assert is_promise_of_action(hale) is True


@pytest.mark.parametrize("hale", REELLE_HALER)
def test_samme_haler_er_tomme_loefter_naar_intet_vaerktoej_koerte(hale):
    from core.services.hollow_promise_guard import is_hollow_promise

    assert is_hollow_promise(hale, total_tool_calls=12, last_round_tool_calls=0) is True
    # Handlede han faktisk i sidste runde, er det ikke et tomt løfte.
    assert is_hollow_promise(hale, total_tool_calls=12, last_round_tool_calls=1) is False


def test_beretning_i_datid_er_ikke_et_loefte():
    """«Jeg læste filen» er en beretning om noget der ER sket. Fanges den,
    bliver hvert eneste afsluttet svar til et falsk tomt løfte."""
    from core.services.hollow_promise_guard import is_promise_of_action

    assert is_promise_of_action("Jeg læste filen, og der var tre fejl. Dem har jeg rettet.") is False
    assert is_promise_of_action("Jeg åbnede sessionen og fandt fejlen. Den er rettet nu.") is False


def test_kun_sidste_saetning_taeller():
    """Et langt svar der undervejs nævner hvad han gjorde er ikke et løfte —
    løftet står til sidst, som dét man efterlades med."""
    from core.services.hollow_promise_guard import is_promise_of_action

    beretning = (
        "Jeg kigger på filen og finder tre steder der skal rettes. "
        "Alle tre er rettet, og testene er grønne."
    )
    assert is_promise_of_action(beretning) is False


def test_spoergsmaal_til_sidst_er_stadig_ikke_et_loefte():
    from core.services.hollow_promise_guard import is_promise_of_action

    assert is_promise_of_action("Jeg kan læse resten af filen — skal jeg det?") is False
