"""Turens content-blokke, samlet i den rækkefølge de faktisk opstod.

Udskilt fra ``visible_runs.py`` (7.290 linjer) 2026-09-09 efter Boy Scout-reglen
— og fordi DeepSeek-harness-spec'ens Fase 0 kræver netop dét først:
*«first extract the nearest coherent stream accumulation/settlement unit with
compatibility re-exports before changing its logic»*.

Enheden er naturlig. Fem stykker tilstand og fire lukninger fulgtes altid ad
gennem koden, og de tjener ét formål: at kunne genfortælle turen som den blev
til — fortælling → værktøj → fortælling — frem for den degraderede
«tekst først, så alle værktøjer»-rækkefølge.

**Hvorfor rækkefølgen er hele pointen.** Uden tekst-segmenter har blok-byggeren
kun én samlet blob og kan placere den ét sted; alle mellemsynteser forsvinder
så ind i det afsluttende svar, og værktøjerne står alene i toppen (målt af
Bjørn 2026-09-02). Uden interleave-loggen kender den ikke ordenen overhovedet.

Objektet ændrer INGEN adfærd. Det er de samme fem variabler og de samme fire
funktioner, flyttet ud af en meget lang funktion og gjort testbare uden at køre
et helt run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class TurnAccumulator:
    """Samler tekst-segmenter, værktøjskald og deres rækkefølge for én tur."""

    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    #: 'text' / 'tool' i den orden de kom under streamen.
    interleave: list[str] = field(default_factory=list)
    #: Ét element pr. sammenhængende stykke tekst mellem værktøjskald.
    text_segments: list[str] = field(default_factory=list)
    _segment_open: bool = False

    # ── tekst ────────────────────────────────────────────────────────────
    def add_text(self, chunk: str) -> None:
        """Læg tekst i det ÅBNE segment, eller åbn et nyt.

        Et segment lukkes af et værktøjskald — det er dét der gør at to
        fortællinger omkring et kald ikke smelter sammen til én.
        """
        if not chunk:
            return
        if self._segment_open and self.text_segments:
            self.text_segments[-1] += chunk
        else:
            self.text_segments.append(chunk)
            self._segment_open = True

    def close_segment(self) -> None:
        self._segment_open = False

    # ── rækkefølge ───────────────────────────────────────────────────────
    def note_text(self) -> None:
        self.interleave.append("text")

    def note_tool(self) -> None:
        self.interleave.append("tool")

    # ── værktøjskald ─────────────────────────────────────────────────────
    def add_tools(self, tool_calls: list | None, results: list | None) -> None:
        """Optag et batch af kald og deres resultater. Kaster ALDRIG.

        En fejl i blok-opsamlingen må ikke forplante sig ind i streamet: så
        ville en kosmetisk detalje kunne afbryde et svar der ellers virkede.
        """
        try:
            for tc in (tool_calls or []):
                fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
                self.tool_calls.append({
                    "id": str((tc.get("id") if isinstance(tc, dict) else "") or ""),
                    "name": str(
                        fn.get("name")
                        or (tc.get("name") if isinstance(tc, dict) else None)
                        or "tool"
                    ),
                    "input": coerce_tool_input(
                        fn.get("arguments")
                        if fn.get("arguments") is not None
                        else (tc.get("input") if isinstance(tc, dict) else None)
                    ),
                })
            for r in (results or []):
                self.tool_results.append({
                    "tool_use_id": str(getattr(r, "tool_call_id", "") or ""),
                    "status": "done",
                    "content": str(getattr(r, "content", "") or ""),
                    "is_error": False,
                })
        except Exception:
            pass

    # ── udtag ────────────────────────────────────────────────────────────
    def build_blocks(self, text: str) -> list[dict]:
        """Den kanoniske blok-liste for turen."""
        from core.services.visible_turn_blocks import _build_turn_blocks
        return _build_turn_blocks(
            text=text,
            tool_calls=self.tool_calls,
            tool_results=self.tool_results,
            interleave=self.interleave,
            text_segments=self.text_segments,
        )


def coerce_tool_input(raw: object) -> dict:
    """Normalisér tool-input til et DICT.

    OpenAI-stil ``tool_calls`` bærer ``function.arguments`` som en JSON-STRENG.
    Uden parsing gemmer ``content_json`` en rå streng som klienten renderer
    garbled — og som er en dobbelt-sandhed mod resten, der er dicts.
    Kaster aldrig.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}
