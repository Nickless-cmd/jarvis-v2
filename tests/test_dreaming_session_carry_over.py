"""Dream carry-over i prompt-materialet skal prioriteres, ikke skæres råt.

Målt 21/10-2026 02:54Z: `active[:5]` tog rå indeks 0-4 — alle fra 16/10 —
mens de upræsenterede med høj konfidens (0.8 og 0.7) stod på indeks 24-25.
Præcis dem get_presentable_dream() ville vælge først var altså usynlige i
prompten. Prioriteringen fandtes allerede i dream_carry_over.py, men
overfladen returnerer _ACTIVE_DREAMS urørt, så den blev aldrig brugt her.
"""
from __future__ import annotations


def _drøm(navn: str, *, conf: float, presented: bool) -> dict:
    return {
        "content": navn,
        "confidence": conf,
        "presented": presented,
        "session_carry_count": 0,
        "status": "active",
    }


def test_upræsenterede_med_hoej_konfidens_kommer_med(monkeypatch):
    from core.services import dream_carry_over, dreaming_session

    drømme = [_drøm(f"gammel-{i}", conf=0.5, presented=True) for i in range(5)]
    drømme += [
        _drøm("vigtig", conf=0.8, presented=False),
        _drøm("ogsaa-vigtig", conf=0.7, presented=False),
    ]
    monkeypatch.setattr(
        dream_carry_over,
        "build_dream_carry_over_surface",
        lambda **k: {"active_dreams": drømme},
    )

    material = dreaming_session._collect_dream_material()
    indhold = [d["content"] for d in material.get("dream_carry_over", [])]

    assert "vigtig" in indhold, f"upræsenteret drøm (conf 0.8) faldt ud: {indhold}"
    assert "ogsaa-vigtig" in indhold, f"upræsenteret drøm (conf 0.7) faldt ud: {indhold}"
    assert indhold[0] == "vigtig", f"højeste konfidens skal stå først: {indhold}"


def test_streng_confidence_draeber_ikke_hele_droemmen(monkeypatch):
    """Én post med ``"0.8"`` i stedet for ``0.8`` må ikke stoppe hele drømmen.

    Målt 22/10-2026: carry-over-filen bar både float og streng. Strengen fik
    ``_build_dream_prompt`` til at kaste ``ValueError: Unknown format code 'f'
    for object of type 'str'``, som ``fire``-ens brede ``except`` loggede som
    «failed to fire» — drømmen fyrede ALDRIG, så længe posten lå i vinduet på
    fem, og ingen enkelt-post så forkert ud.
    """
    from core.services import dreaming_session

    material = {
        "dream_carry_over": [
            {"content": "float-post", "confidence": 0.8, "presented": False},
            {"content": "streng-post", "confidence": "0.8", "presented": False},
            {"content": "tom-post", "confidence": None, "presented": False},
        ],
        "dream_hypotheses": [
            {"hypothesis": "hypotese-med-streng", "confidence": "0.7"},
        ],
    }

    prompt = dreaming_session._build_dream_prompt(material)

    assert "float-post" in prompt
    assert "streng-post" in prompt, "posten med streng-confidence faldt ud"
    assert "tom-post" in prompt, "posten uden confidence faldt ud"
    assert "hypotese-med-streng" in prompt
    assert "conf=0.8" in prompt
