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
    #: Ét element pr. sammenhængende stykke TÆNKNING mellem værktøjskald.
    #: Samme form som text_segments og af samme grund: uden segmenter kan
    #: tænkningen kun placeres ét sted, og alle mellemtanker falder sammen.
    thinking_segments: list[str] = field(default_factory=list)
    #: [start, seneste] pr. tanke-segment. Forskellen ER tænketiden for netop
    #: DEN tanke. `visible_thinking_trace` måler hele turen under ét og kunne
    #: derfor kun beskrive den samlede blok; med segmenter skal hver tanke
    #: bære sin egen tid, ellers står de alle uden.
    thinking_times: list[list[float]] = field(default_factory=list)
    #: Skills runtimen lagde i prompten for turen (skill_relevance_surface.
    #: skill_flade_event). Staar FOERST i blokkene: opslaget skete foer modellen
    #: skrev et ord.
    skill_surface: dict | None = None
    #: Rundernes etiketter som `tool_use_summary`-blokke — Claude Desktops
    #: egen form: `{type, summary, preceding_tool_use_ids}` (19/9-2026). Foer
    #: blev etiketten kun streamet, saa den var vaek efter en genindlaesning.
    round_labels: list[dict] = field(default_factory=list)
    #: Uret. Injicerbart, så en test kan måle uden at vente.
    ur: object = None
    _segment_open: bool = False
    _thinking_open: bool = False

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
        self._luk_tanketid()
        self.interleave.append("text")

    def note_tool(self) -> None:
        self._luk_tanketid()
        self.interleave.append("tool")

    def _luk_tanketid(self) -> None:
        """En tanke varer til det NÆSTE begynder — ikke til dens sidste token.

        17/9-2026: desk målte live fra tanken startede til næste blok (7 s),
        mens den gemte blok kun talte tiden tanke-teksten strømmede (0,4-1,7 s).
        Bjørn så tallet forsvinde når serverens besked overtog efter turen. Nu
        er det samme mål begge steder: modellens tid fra tanken begyndte til
        den gik videre til tekst eller et kald.
        """
        if self._thinking_open and self.thinking_times:
            self.thinking_times[-1][1] = self._nu()
        self._thinking_open = False

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
            # Udfaldet foelger med — med SAMME regel som stroemmen, saa en fejl
            # der stod alene live ogsaa staar alene efter genindlaesning. Her
            # stod «done»/False hardkodet: 4.885 af 4.885 gemte resultater paa
            # CT105 var succeser (maalt 18/9-2026).
            from core.services.visible_followup_events import er_fejlstatus
            for r in (results or []):
                fejl = er_fejlstatus(getattr(r, "status", ""))
                self.tool_results.append({
                    "tool_use_id": str(getattr(r, "tool_call_id", "") or ""),
                    "status": "error" if fejl else "done",
                    "content": str(getattr(r, "content", "") or ""),
                    "is_error": fejl,
                })
        except Exception:
            pass

    # ── tænkning ─────────────────────────────────────────────────────────
    def add_thinking(self, chunk: str) -> None:
        """Læg reasoning i det ÅBNE tanke-segment, eller åbn et nyt.

        Et segment lukkes af tekst eller et værktøjskald — præcis som
        tekst-segmenterne. Derfor bliver «tænk → kald → tænk → svar» til fire
        blokke i den rækkefølge det skete, i stedet for én tanke i toppen.
        """
        if not chunk:
            return
        nu = self._nu()
        if not self._thinking_open:
            self.thinking_segments.append("")
            self.thinking_times.append([nu, nu])
            self.interleave.append("think")
            self._thinking_open = True
            self._segment_open = False
        self.thinking_segments[-1] += chunk
        self.thinking_times[-1][1] = nu

    def close_thinking(self) -> None:
        self._thinking_open = False

    def _nu(self) -> float:
        if callable(self.ur):
            return float(self.ur())
        import time
        return time.monotonic()

    def thinking_seconds(self) -> list[float | None]:
        """Sekunder pr. tanke-segment; None hvor der ikke blev maalt noget.

        `None` og `0` er ikke det samme: `0` ville staa som «Tænkte i 0 s» paa
        en tanke vi bare ikke naaede at tage tid paa.
        """
        ud: list[float | None] = []
        for par in self.thinking_times:
            d = par[1] - par[0]
            ud.append(d if d > 0 else None)
        return ud

    # ── runde-etiketter ─────────────────────────────────────────────────
    def add_round_label(self, etik: dict) -> None:
        """Gem en runde-etiket som den blok Claude Desktop selv gemmer.

        Samme etiket kan komme to gange (streamet ved naeste rundes start, og
        hoestet igen ved turens slutning) — den gemmes én gang. Uden kald-ids
        kan den ikke haefte sig paa sin runde, og saa gemmes den slet ikke.
        """
        try:
            summary = str((etik or {}).get("etiket") or "").strip()
            ids = [str(i) for i in ((etik or {}).get("tool_use_ids") or []) if str(i).strip()]
            if not summary or not ids:
                return
            if any(b["preceding_tool_use_ids"] == ids for b in self.round_labels):
                return
            self.round_labels.append({
                "type": "tool_use_summary",
                "summary": summary,
                "preceding_tool_use_ids": ids,
            })
        except Exception:
            pass

    # ── udtag ────────────────────────────────────────────────────────────
    def build_blocks(self, text: str) -> list[dict]:
        """Den kanoniske blok-liste for turen."""
        from core.services.visible_turn_blocks import _build_turn_blocks
        blokke = _build_turn_blocks(
            text=text,
            tool_calls=self.tool_calls,
            tool_results=self.tool_results,
            interleave=self.interleave,
            text_segments=self.text_segments,
            thinking_segments=self.thinking_segments,
            thinking_seconds=self.thinking_seconds(),
        )
        # Etiketterne til sidst: de hæfter sig på deres kald via ids, ikke på
        # en plads i listen — og midt i blokkene ville de dele en runde op.
        etiketter = [dict(b) for b in self.round_labels]
        if self.skill_surface:
            return [dict(self.skill_surface), *blokke, *etiketter]
        return [*blokke, *etiketter]


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
