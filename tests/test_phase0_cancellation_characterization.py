"""Karakterisering: hvad sker der FAKTISK ved afbrud og frakobling.

Fase 0 i DeepSeek-harness-spec'en kræver karakteriseringstests for bl.a.
«cancellation before/after deltas» og «local-tool disconnect». Karakterisering
betyder at pinne den adfærd der ER — ikke den man ønsker sig — så en senere
refaktor ikke kan ændre den ved et uheld.

To af testene her dokumenterer en KONFLIKT mellem spec'ens målbillede og en
bevidst beslutning i koden. Konflikten skal løses med vilje, ikke opdages som en
regression.
"""
from __future__ import annotations

from core.services.interruption_notice import (
    INTERRUPTION_NOTICE,
    is_interruption_notice,
    strip_interruption_notices,
)
import core.services.local_tool_broker as broker


# ── Afbrud FØR første delta ───────────────────────────────────────────────

def test_afbrud_uden_leveret_tekst_giver_en_note_til_mennesket():
    """SPEC-KONFLIKT, bevidst.

    Spec'ens Fase 2 siger: «cancellation before text does not create a surface
    message». Vi gør det MODSATTE — og med god grund, som er målt:
    uden noten ser Bjørn tavshed ved genindlæsning og ved ikke hvorfor.

    Noten er en besked til MENNESKET. Den løsning skal ikke rulles tilbage af
    en refaktor der følger spec'en bogstaveligt; den skal drøftes.
    """
    assert is_interruption_notice(INTERRUPTION_NOTICE)
    assert "afbrudt" in INTERRUPTION_NOTICE.lower()


def test_noten_naar_ALDRIG_modellens_historik():
    """Dét er hele grunden til at noten er forsvarlig.

    Målt 5/9-2026: 45 stubs, klumpet 16/8/7/4/2 i enkelte sessioner. Da tre lå
    i træk, gentog DeepSeek sætningen ord for ord — modellen efterlignede sin
    egen historik, og ét ægte cut avlede uendeligt mange falske.
    """
    historik = [
        {"role": "user", "content": "hej"},
        {"role": "assistant", "content": INTERRUPTION_NOTICE},
        {"role": "assistant", "content": "et ægte svar"},
    ]
    ud = strip_interruption_notices(historik)
    assert [m["content"] for m in ud] == ["hej", "et ægte svar"]


def test_brugerens_EGNE_ord_om_afbrydelse_bliver_staaende():
    """Kun assistent-beskeder filtreres. Skriver Bjørn selv «du blev afbrudt
    midt i det», er det en ægte ytring og må ikke forsvinde."""
    historik = [{"role": "user", "content": "du blev afbrudt midt i det, prøv igen"}]
    assert strip_interruption_notices(historik) == historik


def test_et_aegte_svar_forveksles_ikke_med_noten():
    assert not is_interruption_notice("Jeg har rettet filen og pushet ændringen.")
    assert not is_interruption_notice("")


def test_en_LANG_tekst_er_aldrig_noten():
    """Kendetegnet er snævert med vilje: over 400 tegn kan det ikke være noten,
    uanset hvad der står i den."""
    assert not is_interruption_notice("blev afbrudt midt i det " + "x" * 500)


# ── Afbrud EFTER leveret tekst ────────────────────────────────────────────

def test_der_findes_INGEN_prefix_ankring_i_dag():
    """SPEC-HUL, bekræftet.

    Spec'ens Fase 2 kræver: «cancellation after delivered text records an
    interrupted surface anchor with the exact prefix». Det gør vi ikke. Vi
    springer blot noten over når sidste rolle allerede er assistant
    (`visible_runs.py`, ~5733) — der er ingen ankring af den nøjagtige leverede
    tekst.

    Testen pinner fraværet, så den dagen ankringen bygges, fejler her og bliver
    skrevet om bevidst.
    """
    import core.services.interruption_notice as mod
    assert not hasattr(mod, "anchor_interrupted_prefix")


# ── Lokal-tool-frakobling ─────────────────────────────────────────────────

def test_frakobling_faejler_ventende_kald_i_stedet_for_at_haenge():
    """Det broker'en gør RIGTIGT: en frakoblet klient efterlader ikke et run
    hængende — de ventende kald fejles med en typet fejl, så løkken kommer
    videre i stedet for at vente sin timeout ud."""
    sid = "sess-karakterisering"
    p = broker.register("kald-1", session_id=sid, name="operator_bash")
    assert broker.pending_call_ids(sid) == ["kald-1"]

    assert broker.cancel_session(sid) == 1

    assert p.event.is_set()
    assert p.is_error is True
    assert "disconnected" in str(p.result)
    assert broker.pending_call_ids(sid) == []


def test_frakobling_roerer_ikke_ANDRE_sessioners_kald():
    """Oprydningen er pr. session. Ville den ramme bredt, ville én klients
    netværks-blip dræbe alle andres værktøjskald."""
    broker.register("kald-a", session_id="sess-a", name="x")
    broker.register("kald-b", session_id="sess-b", name="x")
    assert broker.cancel_session("sess-a") == 1
    assert broker.pending_call_ids("sess-b") == ["kald-b"]
    broker.cancel_session("sess-b")


def test_frakobling_kan_IKKE_skelne_afbrudt_foer_afsendelse_fra_ukendt_udfald():
    """SPEC-HUL, bekræftet — og det farligste af dem.

    `cancel_session` sætter ÉN besked på alle ventende kald:
    «[local tool aborted: client disconnected]». Den siger ikke om værktøjet
    NÅEDE at køre.

    Spec'ens Fase 3 kræver netop den skelnen: `aborted_before_dispatch` (intet
    skete, sikkert at prøve igen) mod `outcome_unknown` (kan have haft en
    sideeffekt, må ALDRIG prøves igen automatisk for ikke-idempotente kald).

    Ingen af de 97 subprocess-kaldsteder i repoet bærer den forskel i dag.
    """
    import inspect
    kilde = inspect.getsource(broker.cancel_session)
    assert "client disconnected" in kilde
    assert "aborted_before_dispatch" not in kilde
    assert "outcome_unknown" not in kilde
