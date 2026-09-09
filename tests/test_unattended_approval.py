"""En uovervaaget koersel maa ikke kunne godkende sig selv — Fase 4.

«unattended child approval is pinned to rejection; wider authority requires a
new parent-owned invocation and decision.»

Kriteriet HOLDT allerede da det blev maalt 9/9-2026 — men det hviler paa to
ting der begge kan drive:

  1. To steder i `visible_runs` afviser `approval_needed` naar `run.autonomous`.
     To kopier af en sikkerhedsregel er to steder den kan forsvinde ét.
  2. HVER uovervaaget indgang skal saette `autonomous=True`. Glemmer en ny det,
     laver den kort ingen kan svare paa — og de bliver liggende. Der laa 26
     saadanne paa produktionen (fra synlige sessioner, men samme skaebne).
"""
from __future__ import annotations

import inspect

import core.services.visible_runs as VR


# ── 1. begge afvisnings-steder findes ────────────────────────────────────

def test_BEGGE_steder_afviser_en_uovervaaget_godkendelse():
    """Struktur-test, og den er noteret som saadan: reglen ligger dybt i en
    generator hvor et adfaerds-kald ville kraeve hele run-maskineriet.

    Faelden ved struktur-tests er set i dag: de kan bestaa mens en tidlig
    return goer dem ligegyldige. Derfor tjekkes AFSTANDEN — vagten skal ligge
    i samme aandedrag som `approval_needed`, ikke 200 linjer senere.
    """
    linjer = inspect.getsource(VR).splitlines()
    steder = [i for i, l in enumerate(linjer) if '"approval_needed"' in l]
    assert len(steder) >= 2, f"forventede mindst to kort-steder, fandt {len(steder)}"

    for i in steder:
        vindue = "\n".join(linjer[i:i + 4])
        assert "run.autonomous" in vindue, (
            f"linje {i + 1}: `approval_needed` uden en autonomous-vagt lige efter")


def test_afvisningen_siger_HVORFOR_til_modellen():
    """Et tavst spring ville faa den til at proeve igen. Beskeden skal sige at
    den ikke KAN godkendes her."""
    kilde = inspect.getsource(VR)
    assert "Autonomous run cannot approve tool calls" in kilde
    assert "skipped (autonomous)" in kilde


# ── 2. hver uovervaaget indgang markerer sig ─────────────────────────────

def test_start_autonomous_run_markerer_koerslen_som_uovervaaget():
    kilde = inspect.getsource(VR.start_autonomous_run)
    assert "autonomous=True" in kilde


def test_stream_varianten_ogsaa():
    from core.services import autonomous_stream_run as ASR
    assert "autonomous=True" in inspect.getsource(ASR)


def test_wakeup_gaar_gennem_en_uovervaaget_indgang():
    """Wakeups fyrer uden nogen til stede. Gik de gennem den SYNLIGE indgang,
    ville de lave kort ingen svarer paa."""
    from core.services import wakeup_dispatcher as WD
    kilde = inspect.getsource(WD)
    assert "start_autonomous_stream_run" in kilde
    assert "start_visible_run(" not in kilde


def test_droemme_ogsaa():
    from core.services import dreaming_session as DS
    assert "start_autonomous_run" in inspect.getsource(DS)


# ── og at trust-tilstanden ikke er en bagvej ─────────────────────────────

def test_trust_mode_kraever_stadig_godkendelse_for_DESTRUKTIVT():
    """«wider authority requires a new parent-owned invocation and decision».
    Selv i trust-tilstand maa en destruktiv kommando ikke auto-godkendes."""
    kilde = inspect.getsource(VR)
    assert kilde.count('_classification == "destructive"') >= 1
    assert kilde.count('_a_classification == "destructive"') >= 1


def test_trust_er_et_EKSPLICIT_valg_ikke_en_standard():
    import inspect as I
    sig = I.signature(VR.start_visible_run)
    assert sig.parameters["approval_mode"].default == "ask"
