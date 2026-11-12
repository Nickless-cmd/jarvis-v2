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
    from core.services import visible_first_pass_results as FP
    linjer = (inspect.getsource(VR) + "\n" + inspect.getsource(FP)).splitlines()
    steder = [i for i, l in enumerate(linjer) if '"approval_needed"' in l]
    assert len(steder) >= 2, f"forventede mindst to kort-steder, fandt {len(steder)}"

    for i in steder:
        vindue = "\n".join(linjer[i:i + 4])
        assert "run.autonomous" in vindue, (
            f"linje {i + 1}: `approval_needed` uden en autonomous-vagt lige efter")


def test_afvisningen_siger_HVORFOR_til_modellen():
    """Et tavst spring ville faa den til at proeve igen. Beskeden skal sige at
    den ikke KAN godkendes her."""
    from core.services import visible_first_pass_results as FP
    kilde = inspect.getsource(VR) + "\n" + inspect.getsource(FP)
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
    ville de lave kort ingen svarer paa.

    12/11-2026: arkitekturen blev delt i to. Dispatcheren starter intet run —
    den afleverer til indbakken via `wake_gateway`, og `inbox_idle_waker` er
    den der starter et run, naar intet andet koerer. Den gamle test kraevede
    `start_autonomous_stream_run` i dispatcherens KILDE, hvilket bandt testen
    til en startvej der siden blev pensioneret. Den maaler nu de to led der
    faktisk baerer egenskaben: dispatcheren maa ikke bruge den synlige indgang,
    og den usynlige indgang skal vaere den autonome.
    """
    from core.services import inbox_idle_waker as IW
    from core.services import wakeup_dispatcher as WD

    # Den SYNLIGE indgang maa ikke vaere bundet i nogen af de to moduler: den
    # ville lave et kort ingen svarer paa. (Begge moduler importerer deres
    # startere LOKALT inde i funktionerne, saa `hasattr` ser dem ikke — den
    # egenskab der faktisk kan maales her er at den synlige vej ikke er bundet.)
    assert not hasattr(WD, "start_visible_run")
    assert not hasattr(IW, "start_visible_run")

    # At kaeden FAKTISK starter et autonomt run — og at den ikke starter naar en
    # tur er aktiv — maales ende-til-ende gennem den aegte job-koe i
    # tests/e2e/test_wakeup_guard_e2e.py. En streng-grep her ville vaere en
    # attraap: maalt 12/11-2026 bestod den selv da importen blev byttet til den
    # synlige indgang, fordi navnet ogsaa stod i kommentarer og kaldesteder.
    # Se test_e2e_no_active_turn_dispatches_run_through_real_queue.
    assert "anmod_om_vaekning(" in inspect.getsource(WD)


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
