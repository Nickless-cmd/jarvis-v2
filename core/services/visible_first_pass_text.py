"""Akkumuleret first-pass-tekst med indbygget degenerations-vagt.

Udskilt fra ``visible_runs.py`` (7.078 linjer) 2026-09-01 efter Boy Scout-reglen,
før reasoning-streaming blev tilføjet samme sted.

Enheden er naturlig: den samme streng tjener TO formål i første pas, og de har
altid fulgt hinanden gennem koden —

1. **Vagt.** Provider-agnostisk drab af model-repetitionsløkker ved kilden.
   Indført 2026-06-23 efter at 147 KB «probe_ollama»-skrald blev både streamet
   og persisteret. Tjekket er ikke gratis, så det køres i spring frem for pr.
   delta.
2. **Kilde til det persisterede svar.** Teksten brugeren FAKTISK så, samlet af
   de live-streamede deltas — ikke providerens ``full_text``, som kan afvige.

At holde de to i ét objekt fjerner to løse variabler (``_fp_deg_accum``,
``_fp_deg_since``) fra en i forvejen meget lang funktion, og gør tærsklen
testbar uden at skulle køre et helt run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Tegn mellem hvert degenerations-tjek. Lavt nok til at fange en løkke længe
# før den fylder skærmen; højt nok til at tjekket ikke koster pr. token.
CHECK_INTERVAL_CHARS = 1500


@dataclass
class FirstPassText:
    """Samler first-pass-tekst og siger til når den degenererer."""

    _text: str = ""
    _since_check: int = 0
    _interval: int = field(default=CHECK_INTERVAL_CHARS)

    @property
    def text(self) -> str:
        return self._text

    def __len__(self) -> int:
        return len(self._text)

    def __bool__(self) -> bool:
        return bool(self._text)

    def feed(self, delta: str) -> tuple[bool, str]:
        """Tilføj en delta. Returnér (degenereret, årsag).

        Årsagen er tom når svaret er sundt. Tjekket kører kun hver
        ``CHECK_INTERVAL_CHARS`` tegn — mellem spring er svaret altid (False, "").
        """
        piece = str(delta or "")
        if not piece:
            return False, ""
        self._text += piece
        self._since_check += len(piece)
        if self._since_check < self._interval:
            return False, ""
        self._since_check = 0
        try:
            from core.services.stream_degeneration import check_degeneration
        except Exception:
            # Vagten må aldrig tage svaret med sig i faldet.
            return False, ""
        try:
            is_degenerate, why = check_degeneration(self._text)
        except Exception:
            return False, ""
        return bool(is_degenerate), str(why or "")
