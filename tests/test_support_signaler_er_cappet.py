"""Én langsom support-bygger må ikke fryse hele turen.

24/9-2026, målt på en kold promptopbygning på Jarvis-maskinen:

    i alt                          30,8 s
      supportsignaler              27,4 s
        opslag efter oplevelser    27,1 s
          synkront embedding-kald  26,0 s

`_visible_support_signal_sections` var en almindelig for-løkke over 17 byggere
uden deadline. `_experience_substrate_section` er den SIDSTE i listen og laver
et synkront embedding-kald mod ollama. Når ollama er optaget — af Jarvis' eget
svar, af inner-voice-skyggen, af cheap-lane — venter hele promptopbygningen.

Hang-fixet 18/7-2026 indførte `_HOT_RESOLVE_CAP_S` mod nøjagtig dette symptom
(«embed batch +28306ms») og cappede tre andre resolves. Denne sti var et
almindeligt synkront kald og gik udenom. To måneder senere kom den samme fejl
tilbage med næsten samme tal.
"""
from __future__ import annotations

import time

from core.services import prompt_contract as pc


def test_en_haengende_bygger_koster_kun_sin_egen_sektion(monkeypatch) -> None:
    """Akkumulatoren er hele pointen.

    Uden den ville en deadline koste alle 17 sektioner — også de 16 der var
    færdige på millisekunder. Med den mister vi kun den der hænger.
    """
    kaldt: list[str] = []

    def _hurtig(navn):
        def _b():
            kaldt.append(navn)
            return f"[{navn}]"
        return _b

    def _haenger():
        kaldt.append("langsom")
        time.sleep(30)
        return "[naar aldrig frem]"

    monkeypatch.setattr(pc, "_private_support_signal_instruction", _hurtig("a"))
    monkeypatch.setattr(pc, "_growth_support_signal_instruction", _hurtig("b"))
    monkeypatch.setattr(pc, "_experience_substrate_section",
                        lambda **kw: _haenger())

    acc: list[str] = []
    import threading
    t = threading.Thread(
        target=lambda: pc._visible_support_signal_sections(
            compact=False, include=True, user_message="hej",
            session_id="s", acc=acc),
        daemon=True)
    start = time.time()
    t.start()
    t.join(timeout=2.0)          # samme rolle som `_timed_result`s deadline

    # Traaden koerer stadig — men det vi NAAEDE er laesbart.
    assert t.is_alive(), "testen maalte ikke det den tror (byggeren haengte ikke)"
    assert time.time() - start < 5.0, "kalderen ventede paa den haengende bygger"
    assert "[a]" in acc and "[b]" in acc, (
        f"de hurtige sektioner gik tabt sammen med den langsomme: {acc}"
    )
    assert "[naar aldrig frem]" not in acc


def test_kaldstedet_bruger_hot_resolve_cap() -> None:
    """Blokken skal resolves med den SAMME spærre som de øvrige hot-resolves.

    Et eget tal her ville drive fra hinanden. `_HOT_RESOLVE_CAP_S` er
    beslutningen, og den blev truffet 18/7 med målinger bag sig.
    """
    import inspect

    kilde = inspect.getsource(pc.build_visible_prompt_contract) if hasattr(
        pc, "build_visible_prompt_contract") else inspect.getsource(pc)
    i = kilde.index('"support_signals", _visible_support_signal_sections')
    naerved = kilde[i:i + 600]
    assert "_HOT_RESOLVE_CAP_S" in naerved, (
        "supportblokken resolves uden den fælles spærre — så kan den fryse "
        "turen igen næste gang ollama er optaget"
    )
    assert "_support_acc" in naerved, (
        "ingen akkumulator — en deadline ville koste alle 17 sektioner"
    )


def test_akkumulatoren_er_valgfri() -> None:
    """Uden `acc` skal funktionen opføre sig præcis som før.

    Den kaldes også andre steder; en påkrævet parameter ville brække dem.
    """
    r = pc._visible_support_signal_sections(compact=True, include=True)
    assert r == []
    r2 = pc._visible_support_signal_sections(compact=False, include=False)
    assert r2 == []


def test_sektionerne_havner_i_den_liste_kalderen_holder(monkeypatch) -> None:
    """`acc` skal være DEN liste der fyldes — ikke en kopi."""
    monkeypatch.setattr(pc, "_private_support_signal_instruction", lambda: "[x]")
    for navn in ("_growth_support_signal_instruction",
                 "_self_model_support_signal_instruction",
                 "_self_model_signal_tracking_section",
                 "_runtime_resource_signal_section",
                 "_world_model_support_signal_instruction",
                 "_goal_support_signal_instruction",
                 "_runtime_awareness_support_signal_instruction",
                 "_development_focus_support_signal_instruction",
                 "_reflection_support_signal_instruction",
                 "_retained_memory_support_signal_instruction",
                 "_temporal_support_signal_instruction",
                 "_emotion_concept_tone_section",
                 "_emotion_signal_section",
                 "_agreement_streak_section",
                 "_proactive_outbound_section"):
        monkeypatch.setattr(pc, navn, lambda: "")
    monkeypatch.setattr(pc, "_experience_substrate_section", lambda **kw: "")

    acc: list[str] = []
    ud = pc._visible_support_signal_sections(
        compact=False, include=True, acc=acc)
    assert ud is acc, "returværdien er ikke den samme liste som kalderen holder"
    assert acc == ["[x]"]
