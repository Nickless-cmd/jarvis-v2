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
    #: Kald-id'er fra runder som hollow-promise-værnet TVANG frem
    #: (``tool_choice="required"``). Et fremtvunget kald er ikke arbejde
    #: Jarvis valgte — det er konsekvensen af at han lovede en handling uden
    #: at udføre den. Uden dette står kaldet efter hans afsluttende besked,
    #: og klientens skillerum flytter sig ned under det (målt 9/10-2026:
    #: 339 af 369 fyringer tvang et kald, overvejende ``bash``/``edit_file``).
    forced_tool_ids: set[str] = field(default_factory=set)
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
    def add_tools(
        self, tool_calls: list | None, results: list | None, *,
        forced: bool = False,
    ) -> None:
        """Optag et batch af kald og deres resultater. Kaster ALDRIG.

        En fejl i blok-opsamlingen må ikke forplante sig ind i streamet: så
        ville en kosmetisk detalje kunne afbryde et svar der ellers virkede.

        ``forced=True`` markerer at runden blev TVUNGET frem af
        hollow-promise-værnet (``tool_choice="required"``). Kaldet er ægte
        nok — det kørte — men det er ikke arbejde Jarvis valgte, og det må
        derfor flyttes op før hans afsluttende besked (se
        ``_med_interne_kald_foer_svaret``).
        """
        try:
            for tc in (tool_calls or []):
                fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
                _tid = str((tc.get("id") if isinstance(tc, dict) else "") or "")
                self.tool_calls.append({
                    "id": _tid,
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
                if forced and _tid:
                    self.forced_tool_ids.add(_tid)
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
            # Tænke-resuméet (visningstilstanden «Tænkning») rider med på samme
            # blok — det hører til samme værktøjsgruppe. Kan stå alene, fx når
            # Jarvis selv skrev linjen og der derfor ingen etiket blev lavet.
            resume = str((etik or {}).get("tanke_resume") or "").strip()
            ids = [str(i) for i in ((etik or {}).get("tool_use_ids") or []) if str(i).strip()]
            if not ids or (not summary and not resume):
                return
            if any(b["preceding_tool_use_ids"] == ids for b in self.round_labels):
                return
            blok = {
                "type": "tool_use_summary",
                "summary": summary,
                "preceding_tool_use_ids": ids,
            }
            if resume:
                blok["thinking_summary"] = resume
            self.round_labels.append(blok)
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
        # Etiketterne SIDST blandt arbejdet, men FØR det sidste svar.
        #
        # De hæfter sig på deres kald via `preceding_tool_use_ids`, ikke på en
        # plads i listen, så opslaget er ligeglad med hvor de står. Men
        # klienten TEGNER i rækkefølge, og desks rækkemodel lægger alt efter
        # sidste værktøjskald i svar-sektionen. Lå etiketterne bagest, havnede
        # de præcis dér hvor det endelige svar skulle stå.
        #
        # Målt 28/9-2026: 4.027 `tool_use_summary`-blokke lå efter svaret på
        # syv dage — i 791 beskeder, altså ~5 pr. besked — og andelen af
        # beskeder der ikke slutter i tekst sprang fra 2 % til 76 % den 19/9,
        # da etiketterne begyndte at blive gemt. Bjørn så det som «et
        # værktøjskald og en syntese i stedet for den endelige besked», og
        # læste det som om Jarvis arbejdede videre efter at have svaret. Det
        # gjorde han ikke: 913 af hans 919 gemninger ligger FØR svaret.
        #
        # Midt i blokkene ville stadig dele en runde op — derfor ikke dér.
        # Lige før den sidste tekstblok er både efter alt arbejdet og før
        # svaret.
        etiketter = [dict(b) for b in self.round_labels]
        krop = _med_etiketter_foer_svaret(blokke, etiketter)
        # Og halen efter svaret flyttes op, så turens sidste tekstblok ER den
        # sidste blok. Klienten sætter skillerummet ved det sidste
        # værktøjskald; uden dette bliver et internt kald EFTER beskeden til
        # «svaret», og beskeden selv til et mellemsvar (målt 8/10-2026).
        krop = _med_interne_kald_foer_svaret(krop, forced_ids=self.forced_tool_ids)
        if self.skill_surface:
            return [dict(self.skill_surface), *krop]
        return krop


def _med_etiketter_foer_svaret(
    blokke: list[dict], etiketter: list[dict],
) -> list[dict]:
    """Læg etiketterne ind lige før den sidste tekstblok.

    Uden en tekstblok er der intet svar at beskytte, og så står de bagest som
    før — det er tilfældet hvor turen kun er arbejde.
    """
    if not etiketter:
        return list(blokke)
    sidste_tekst = -1
    for i, b in enumerate(blokke):
        if isinstance(b, dict) and b.get("type") == "text" and str(b.get("text") or "").strip():
            sidste_tekst = i
    if sidste_tekst < 0:
        return [*blokke, *etiketter]
    return [*blokke[:sidste_tekst], *etiketter, *blokke[sidste_tekst:]]


def _med_interne_kald_foer_svaret(
    blokke: list[dict], *, forced_ids: set[str] | None = None,
) -> list[dict]:
    """Flyt INTERNE bogførings-kald op FØR svaret, så svaret står sidst.

    Klienten sætter skillerummet ved det sidste værktøjskald
    (``raekkeModel.ts``): tekst FØR det bliver «mellemsvar», og alt efter
    læses som arbejde. Lægger Jarvis et internt kald efter sin afsluttende
    besked, flytter skillerummet sig ned under kaldet — og så står
    kvitteringen som det egentlige svar, mens beskeden bliver et mellemsvar.

    Målt 8/10-2026: i vejr-tråden lå et ``decision_create`` efter den
    afsluttende tekst, og kvitteringen landede efter svaret. Bjørn rettede
    det: «vi skal have lært dit ikk at lave extra kald efter din endelig
    besked». Reglen stod allerede i VISIBLE_CHAT_RULES.md og blev brudt
    gentagne gange — derfor flyttes halen mekanisk i stedet for at blive
    bedt om.

    **Kun interne kald — og fremtvungne kald.** Et rigtigt værktøj efter
    teksten er arbejde der faktisk skete i den rækkefølge, og rækkefølgen må
    ikke omskrives (kontrakten fra 2026-09-02: blokkene fortæller turen som
    den blev til). To ting flyttes derfor:

    * kald der står på listen over bogførings-værktøjer, og
    * kald hvis id står i ``forced_ids`` — runder som hollow-promise-værnet
      TVANG frem med ``tool_choice="required"``.

    Det andet er ikke en omskrivning af historien: et fremtvunget kald er
    ikke arbejde Jarvis valgte, det er konsekvensen af at han lovede en
    handling uden at udføre den. Målt 9/10-2026: 339 af 369 fyringer tvang
    et kald — overvejende ``bash`` og ``edit_file``, altså rigtige værktøjer
    som listen over bogførings-kald aldrig fangede. Det var præcis dem Bjørn
    så ligge efter svaret.

    **Ankeret er det sidste kald Jarvis selv valgte — ikke den sidste
    tekstblok.** Den første udgave ankrede på teksten og ramte derfor kun
    kald der lå allersidst. Målt 9/10-2026 var den dominerende form et kald
    i MIDTEN: et 2.413-tegns svar, så ``suggest_next_task``, så en kort
    afrunding. Ankret på den sidste tekstblok (afrundingen) fandt ingen hale
    og flyttede intet — så det rigtige svar blev liggende i «arbejde» mens
    afrundingen blev «svaret». 9 af 13 fyrede runs havde netop denne form.
    Flytningen sker derfor i hele halen efter det sidste rigtige kald: alt
    ikke-tekst op foran halens tekst, så turen slutter i tekst.
    """
    # Progress-sporet er en FLAD liste uden fortælling, lagt bagest af
    # ``_build_turn_blocks`` (ét element pr. kald, i kald-rækkefølge). Det er
    # ikke turens historie og holdes udenfor — ellers skubbede en flytning
    # 54 sporblokke rundt i hver gemt besked.
    skel = len(blokke)
    while skel and str((blokke[skel - 1] or {}).get("type") or "") == "progress":
        skel -= 1
    kerne, progress = blokke[:skel], blokke[skel:]
    if not kerne:
        return list(blokke)

    _tvungne = forced_ids or set()

    def _flytbar(b: dict) -> bool:
        if str(b.get("name") or "") in _INTERNE_HALE_VAERKTOEJER:
            return True
        return str(b.get("id") or "") in _tvungne

    anker = -1
    for i, b in enumerate(kerne):
        if b.get("type") == "tool_use" and not _flytbar(b):
            anker = i
    if anker >= 0:
        hale = kerne[anker + 1:]
        if not hale:
            return list(blokke)
        if not all(_flytbar(b) for b in hale if b.get("type") == "tool_use"):
            return list(blokke)
        flyt = [b for b in hale if b.get("type") != "text"]
        tekst = [b for b in hale if b.get("type") == "text"]
        # Kun når der både er en tekst at beskytte og noget at flytte.
        if not flyt or not tekst:
            return list(blokke)
        # Indbyrdes rækkefølge bevares — kun placeringen flyttes.
        return [*kerne[:anker + 1], *flyt, *tekst, *progress]

    # Ingen rigtige kald i turen: svaret er den sidste tekstblok, og halen
    # efter den flyttes op foran den (reglen fra 8/10-2026, uændret).
    sidste_tekst = -1
    for i, b in enumerate(kerne):
        if b.get("type") == "text" and str(b.get("text") or "").strip():
            sidste_tekst = i
    if sidste_tekst < 0:
        return list(blokke)
    hale = kerne[sidste_tekst + 1:]
    if not hale:
        return list(blokke)
    if not all(_flytbar(b) for b in hale if b.get("type") == "tool_use"):
        return list(blokke)
    return [*kerne[:sidste_tekst], *hale, kerne[sidste_tekst], *progress]


#: Værktøjer der er AFSLUTNING, ikke arbejde — de bogfører, husker eller
#: tilbyder det næste skridt. Ligger de efter den sidste tekstblok, er det
#: ikke fordi arbejdet fortsatte; det er fordi beskeden blev skrevet først.
#: Sideopgaven 8/10-2026 navngav de fire første; resten er samme form.
_INTERNE_HALE_VAERKTOEJER = frozenset({
    "decision_create",
    "remember_this",
    "flag_side_task",
    "suggest_next_task",
    "activate_side_task",
    "dismiss_side_task",
    "write_handover",
    "note_add",
    "set_flag",
    "clear_flag",
    "memory_upsert_section",
})


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
