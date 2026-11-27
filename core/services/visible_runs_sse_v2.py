"""Translator: legacy SSE-events → Anthropic-style v2-protokol.

Phase 1 (denne fil): basic text-flow translation
- delta → content_block_delta(text_delta) til den aktive text-block
- working_step / capability / approval_request / steer_received /
  turn_changelog → system_event-wrappes
- done → content_block_stop + message_delta + message_stop
- heartbeat → skip (v2 har sin egen ping)

Phase 2 er LEVERET: tool_use-blokke, thinking_delta (se `thinking_delta`
nedenfor) og partial input_json_delta oversættes alle. Linjen her sagde
«senere» indtil 21/9-2026, hvor den blev efterprøvet mod koden.

Forbruger output fra core.services.visible_runs.start_visible_run() der
yielder SSE-formaterede strenge i legacy-format. Parser dem, oversætter
til v2 dataclasses, serializer som v2 SSE-strenge.

Spec: docs/superpowers/specs/2026-06-10-chat-stream-v2-design.md
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from apps.api.jarvis_api.sse_v2_events import (
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageDelta,
    MessageStart,
    MessageStop,
    Ping,
    SystemEvent,
    _sse_format,
)
from core.services.structured_content_flag import structured_content_v2_enabled

logger = logging.getLogger(__name__)

# System-event kinds vi proxy'er fra legacy event-types.
# Hvis et legacy event-name ikke er kendt, wrappes det også som
# system_event med kind = legacy-navnet (safe fallback).
_KNOWN_SYSTEM_EVENT_KINDS = {
    "working_step",
    "capability",
    "approval_request",
    "steer_received",
    "turn_changelog",
    "app_action_request",
    "tool_output_delta",
    # Skills runtimen lagde i prompten (skill_relevance_surface.skill_flade_event).
    "skill_surface",
    # Unified fejl-system (2026-06-23): konsistent bruger-vendt fejl-event
    # (central_error_envelope.to_client_event). Alle klienter renderer samme form.
    "error",
}


from core.services.visible_tool_echo import ToolEchoFilter  # compatibility re-export


from core.services.visible_sse_observations import _parse_legacy_sse  # compatibility re-export


# D2-leak hang-fix (16. jun 2026): legacy-strømmen kan BLOKERE uden at sende 'done'
# (presentation-invariant-leak afslutter runnet server-side, men kilde-generatoren
# hænger), så `async for raw in legacy_iter` venter evigt og når aldrig finally-
# terminal-garantien → desk hænger i 'working'. Vi venter derfor med en idle-timeout:
# hvis ingen legacy-event i _IDLE_TICK_S OG runnet ikke længere er aktivt server-side
# → bryd ud så message_stop fyrer. Hård loft (_MAX_IDLE_TICKS) som sidste værn.
_IDLE_TICK_S = 20.0          # sekunder uden legacy-event før vi tjekker active-state
_MAX_IDLE_TICKS = 9          # ~180s total stilhed → kilden er død uanset


#: (Fjernet 7/10-2026.) Konstanten `_BILLEDVAERKTOEJER` gatede den levende
#: udgivelses-blok til billedværktøjerne alene. En widget udgives af
#: `vis_widget`, som ikke er et billedværktøj — så fladen blev aldrig sendt.
#: Udsenderen kalder nu `_live_udgivne_blokke` for ETHVERT værktøj;
#: `peek_efter_tool_use` giver tom liste for alle andre, så det koster intet.


from core.services.visible_sse_observations import (  # compatibility re-exports
    _live_udgivne_blokke, _run_still_active, _laes_tempo,
)


async def translate_to_v2(
    legacy_iter: AsyncIterator[str],
    *,
    run_id: str = "",
    model: str = "",
    provider: str = "",
    lane: str = "",
    session_id: str | None = None,
    origin: str = "",
    ping_interval_s: float = 5.0,
) -> AsyncIterator[str]:
    """Konverter legacy SSE-stream til Anthropic-style v2 protokol.

    Yielder Anthropic-formaterede SSE-strenge.

    Translation-state:
      - message_started: True efter message_start er sendt
      - text_block_open: True hvis en text content-block er aktiv
      - text_block_index: index på den aktive text-block (starter 0)
      - last_run_id/model/etc: synkroniseres fra legacy events (overrider
        de tomme defaults vi blev kaldt med)

    Bemærk: ping-loop kører i en separat task der yielder ind i en kø,
    så vi har konkurrence-fri yielding fra både den primære oversættelse
    og ping-eventene.
    """
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    from core.services.code_answer_boundary import AnswerMarkerStream

    answer_marker = AnswerMarkerStream()
    echo_filter = ToolEchoFilter()

    _state = {
        "message_started": False,
        "message_stopped": False,
        "text_block_open": False,
        "text_block_index": 0,
        "thinking_block_open": False,
        "thinking_block_index": 0,
        "next_index": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_hit_tokens": 0,
        "cache_miss_tokens": 0,
        "stop_reason": "end_turn",
        "saw_done": False,
        "recovery_reason": "",
        "run_id": run_id,
        "model": model,
        "provider": provider,
        "lane": lane,
        "session_id": session_id,
        "origin": origin,
        "has_tool": False,
        "code_answer_started": False,
        "code_answer_pending": False,
        "code_answer_active": False,
        #: Indeks for det sidste værktøjskald der udførte ARBEJDE. Et
        #: afsluttende kald (`suggest_next_task`) flytter den ikke.
        "last_real_tool_index": -1,
        # Er fold-signalet sendt? Det maa ikke afhaenge af, om der
        # tilfaeldigt laa tekst i koen (se done-grenen).
        "final_answer_started": False,
        # Stroemmer slutsvaret allerede? Sat naar tærsklen nedenfor har
        # promoveret den ventende tekst til `final_answer`. Fra da af skrives
        # ny tekst DIREKTE i den aabne blok — ellers ville den gaa i
        # `_pending_text` og blive en ny `commentary`-blok midt i svaret.
        "svar_stroemmer": False,
        # Legacy chat threshold only; code mode uses the explicit marker.
        "svar_kandidat_len": 0,
    }

    # Efter et værktøj kan tekst være både en mellemsyntese og slutsvaret.
    # Hold kun den uafklarede tekst tilbage; et nyt værktøj/en ny runde gør
    # den til arbejde, mens terminal done gør den til et bekræftet svar.
    _pending_text: list[str] = []
    # Tekst kan komme FØR modellen afslører om runden kalder et værktøj. Den
    # må derfor ikke stemples final ved første token: det var præcis dét der
    # klappede Chat-hovedet sammen i PWA'en, når et tool fulgte bagefter.
    # Indeksene afgøres ved første tool (commentary) eller terminal done
    # (final_answer for en ren teksttur).
    _unresolved_text_indexes: set[int] = set()

    #: Fase pr. tekstblok, i åbningsrækkefølge. Bruges ved `done` til at
    #: afgøre om turen overhovedet HAR en slutblok — og hvis ikke, hvilken
    #: blok der er turens svar (se `_promote_last_text_block_to_answer`).
    _text_block_phases: dict[int, str | None] = {}

    #: Værktøjer der AFLUTTER turen frem for at udføre arbejde. Tekst efter
    #: dem er en hale, ikke svaret — se `_promote_earlier_answer_block`.
    _afsluttende_vaerktoejer = frozenset({"suggest_next_task", "pause_and_ask"})

    #: Antal tegn sendt pr. tekstblok. Uden det kan `done` ikke afgøre hvilken
    #: blok der er turens svar — kun hvilken der kom sidst.
    _text_block_lengths: dict[int, int] = {}

    # Legacy chat heuristic. Code-mode consumers require explicit metadata.
    from core.services.code_answer_boundary import ANSWER_START_CHARS

    _svar_taerskel = ANSWER_START_CHARS

    #: Kald hvis linje allerede er født af annonceringen (før kørslen). Uden
    #: den ville resultat-eventet føde en linje MERE om samme kald.
    _annonceret: set[str] = set()

    def _alloc_index() -> int:
        idx = int(_state["next_index"])
        _state["next_index"] = idx + 1
        return idx

    async def _open_text_block(*, phase: str | None) -> None:
        idx = _alloc_index()
        _state["text_block_index"] = idx
        await queue.put(ContentBlockStart(
            index=idx, block_type="text", phase=phase,
            code_answer_protocol=1,
            code_answer_start=bool(_state["code_answer_pending"]),
        ).to_sse_line())
        _state["code_answer_pending"] = False
        _text_block_phases[idx] = phase
        _text_block_lengths[idx] = 0
        if phase is None:
            _unresolved_text_indexes.add(idx)
        _state["text_block_open"] = True

    async def _emit_model_text(raw_text: str) -> None:
        text = echo_filter.feed(raw_text)
        if text:
            if _state["svar_stroemmer"] or _state["code_answer_active"]:
                await _ensure_text_block_open(phase="final_answer")
                _blok = int(_state["text_block_index"])
                _text_block_lengths[_blok] = _text_block_lengths.get(_blok, 0) + len(text)
                await queue.put(ContentBlockDelta(
                    index=_blok,
                    delta_type="text_delta",
                    content=text,
                ).to_sse_line())
            elif _state["has_tool"]:
                _pending_text.append(text)
                _state["svar_kandidat_len"] += len(text)
                await queue.put(SystemEvent(
                    kind="provisional_text_delta",
                    payload={"run_id": str(_state["run_id"] or ""), "delta": text},
                ).to_sse_line())
                if (
                    not _state["final_answer_started"]
                    and _state["svar_kandidat_len"] >= _svar_taerskel
                ):
                    logger.info(
                        "fold-signal: TAERSKEL (%d tegn >= %d, koe=%d)",
                        _state["svar_kandidat_len"],
                        _svar_taerskel,
                        len(_pending_text),
                    )
                    if _pending_text:
                        await _flush_pending_text(final=True)
                    else:
                        _state["final_answer_started"] = True
                        await queue.put(SystemEvent(
                            kind="final_answer_start",
                            payload={"run_id": str(_state["run_id"] or "")},
                        ).to_sse_line())
                        await _ensure_text_block_open(phase="final_answer")
                    _state["svar_stroemmer"] = True
            else:
                await _ensure_text_block_open(phase=None)
                _blok = int(_state["text_block_index"])
                _text_block_lengths[_blok] = _text_block_lengths.get(_blok, 0) + len(text)
                await queue.put(ContentBlockDelta(
                    index=_blok,
                    delta_type="text_delta",
                    content=text,
                ).to_sse_line())


    async def _emit_message_start_if_needed() -> None:
        if _state["message_started"]:
            return
        _state["message_started"] = True
        await queue.put(MessageStart(
            run_id=str(_state["run_id"] or ""),
            model=str(_state["model"] or ""),
            provider=str(_state["provider"] or ""),
            lane=str(_state["lane"] or ""),
            origin=str(_state["origin"] or ""),
            session_id=(
                str(_state["session_id"]) if _state["session_id"] is not None else None
            ),
        ).to_sse_line())
        # Stream-cluster: lanen synlig i Centralen (self-safe, kaster aldrig).
        try:
            from core.services import stream_sentinel
            stream_sentinel.note_start(
                str(_state["run_id"] or ""),
                str(_state["session_id"] or ""),
                model=str(_state["model"] or ""), lane=str(_state["lane"] or ""))
        except Exception:
            pass
        # Text-block åbnes lazily ved første delta (_ensure_text_block_open) —
        # så en evt. reasoning/thinking-block kan komme FØR svar-teksten.

    async def _ensure_text_block_open(*, phase: str | None) -> None:
        if not _state["text_block_open"]:
            await _open_text_block(phase=phase)

    async def _resolve_unresolved_text(*, phase: str) -> None:
        """Afgør tidlig tekst uden at gensende eller flytte dens indhold."""
        if not _unresolved_text_indexes:
            return
        if phase == "final_answer":
            # Gammel klient-kontrakt bevares; nye klienter bruger blokfasen.
            _state["final_answer_started"] = True
            await queue.put(SystemEvent(
                kind="final_answer_start",
                payload={"run_id": str(_state["run_id"] or "")},
            ).to_sse_line())
        for index in sorted(_unresolved_text_indexes):
            _text_block_phases[index] = phase
            await queue.put(SystemEvent(
                kind="text_phase_update",
                payload={
                    "run_id": str(_state["run_id"] or ""),
                    "index": index,
                    "phase": phase,
                },
            ).to_sse_line())
        _unresolved_text_indexes.clear()

    async def _promote_earlier_answer_block() -> int | None:
        """Vælg svarets blok FØR fold-signalet — ikke efter.

        Målt 26/11-2026 over 3.000 persisterede assistent-svar: 52 havde en
        `final_answer`-blok der var mere end halvandet gang kortere end den
        tekst der stod før den. I det groveste tilfælde var svaret 36 tegn
        («Forslaget ligger klar i komponisten.») mens 2.533 tegn med hele
        besvarelsen lå inde i folden som arbejde.

        Årsagen er ikke folden: `_promote_last_text_block_to_answer` vælger
        den allersidste tekstblok, og efter et afsluttende kald
        (`suggest_next_task`, `pause_and_ask`) skriver Jarvis en kort hale.
        Halen blev svaret, besvarelsen blev arbejde.

        Reglen her: svaret er den LÆNGSTE tekst efter det sidste RIGTIGE
        værktøjskald. Afsluttende kald tæller ikke som arbejde, så teksten før
        dem hører med. Halen efter svaret åbnes bagefter som `commentary` og
        bliver stående synligt uden for foldet — se `_flush_pending_text`.

        Længde er en præsentationsheuristik, ikke semantik: den kan pege på en
        lang mellemsyntese. Fejlretningen er valgt bevidst — den skjuler aldrig
        tekst. Alt efter den valgte blok er svar, uanset hvad den bærer.
        """
        if not _text_block_lengths:
            return None
        # Har serveren allerede stemplet et svar — fx en ren teksttur — rører
        # vi den ikke. Klienten læser den FØRSTE `final_answer`, så et sent
        # stemplet ville flytte grænsen bagud efter foldet.
        if "final_answer" in _text_block_phases.values():
            return None
        ventende = sum(len(t) for t in _pending_text)
        gulv = int(_state.get("last_real_tool_index") or -1)
        kandidat: int | None = None
        laengst = ventende
        for i in sorted(_text_block_lengths):
            if i <= gulv:
                continue
            if _text_block_lengths[i] > laengst:
                kandidat, laengst = i, _text_block_lengths[i]
        if kandidat is None:
            return None
        _text_block_phases[kandidat] = "final_answer"
        await queue.put(SystemEvent(
            kind="text_phase_update",
            payload={
                "run_id": str(_state["run_id"] or ""),
                "index": kandidat,
                "phase": "final_answer",
            },
        ).to_sse_line())
        _state["final_answer_started"] = True
        await queue.put(SystemEvent(
            kind="final_answer_start",
            payload={"run_id": str(_state["run_id"] or "")},
        ).to_sse_line())
        return kandidat

    async def _promote_last_text_block_to_answer() -> None:
        """En AFLUTTET tur har altid en slutblok.

        Bjørn 29/10-2026: «alt der sker efter slut svaret gør hoved holdes
        lukkes, og svaret først paces ind i det lukket hoved». Målt i 395
        persisterede assistent-svar: 11 (2,8 %) havde mønstret
        `text → tool_use → progress` — og svaret lå inde i folden.

        Mekanikken: teksten blev sendt ud FØR det sidste værktøjskald. Kaldet
        tømte `_pending_text` og stemplede blokken `commentary`, så der lå
        intet tilbage ved `done`. `_flush_pending_text(final=True)` returnerer
        tidligt på en tom kø, og der blev derfor aldrig åbnet en blok med
        `phase=final_answer`.

        Konsekvensen er ikke kosmetisk: `deriveChatFlow` flytter blokken ind i
        folden, `finalBlocks` bliver tom — og paceren har intet at rulle ud.
        Skærmen er tom indtil den persisterede række overtager.

        Turens SIDSTE tekstblok ER svaret: det er den brugeren læser. Er der
        slet ingen tekst, gør vi intet — en tur der kun kørte værktøjer skal
        ikke opfinde et svar.
        """
        if not _text_block_phases:
            return
        # Er der allerede stemplet et svar, er det valgt med vilje — se
        # `_promote_earlier_answer_block`. Kun naar ingen blok er svar endnu,
        # er den sidste tekstblok det bedste bud.
        if "final_answer" in _text_block_phases.values():
            return
        index = max(_text_block_phases)
        _text_block_phases[index] = "final_answer"
        _state["final_answer_started"] = True
        await queue.put(SystemEvent(
            kind="text_phase_update",
            payload={
                "run_id": str(_state["run_id"] or ""),
                "index": index,
                "phase": "final_answer",
            },
        ).to_sse_line())

    # ── Thinking/reasoning-block (live deepseek-reasoning) ──
    async def _open_thinking_block() -> None:
        idx = _alloc_index()
        _state["thinking_block_index"] = idx
        await queue.put(ContentBlockStart(index=idx, block_type="thinking").to_sse_line())
        _state["thinking_block_open"] = True
        # Varigheden måles HER, hvor tænkningen faktisk begynder, og læses ved
        # persistering. Ræsonneringens tekst blev allerede gemt; tallet manglede,
        # og uden det kan klienten ikke vise «Tænkte i 14 s ›». Self-safe: en
        # måling må aldrig kunne vælte en stream.
        try:
            from core.services import visible_thinking_trace
            visible_thinking_trace.mark_start(str(_state.get("run_id") or ""))
        except Exception:
            pass

    async def _close_thinking_block_if_open() -> None:
        if _state["thinking_block_open"]:
            await queue.put(ContentBlockStop(
                index=int(_state["thinking_block_index"]),
            ).to_sse_line())
            _state["thinking_block_open"] = False
            try:
                from core.services import visible_thinking_trace
                visible_thinking_trace.mark_end(str(_state.get("run_id") or ""))
            except Exception:
                pass

    async def _close_text_block_if_open() -> None:
        if _state["text_block_open"]:
            # Tøm echo-filterets evt. holdte hale ind i den aktive text-block,
            # før vi lukker den (fx ved et tool-kald der afbryder teksten).
            tail = echo_filter.flush()
            if tail:
                _blok = int(_state["text_block_index"])
                _text_block_lengths[_blok] = _text_block_lengths.get(_blok, 0) + len(tail)
                await queue.put(ContentBlockDelta(
                    index=_blok,
                    delta_type="text_delta",
                    content=tail,
                ).to_sse_line())
            await queue.put(ContentBlockStop(
                index=int(_state["text_block_index"]),
            ).to_sse_line())
            _state["text_block_open"] = False

    async def _flush_pending_text(*, final: bool = False) -> None:
        tail = echo_filter.flush()
        if tail:
            _pending_text.append(tail)
            if _state["has_tool"]:
                await queue.put(SystemEvent(
                    kind="provisional_text_delta",
                    payload={"run_id": str(_state["run_id"] or ""), "delta": tail},
                ).to_sse_line())
        if not _pending_text:
            return
        text = "".join(_pending_text)
        _pending_text.clear()
        # Folden sendes KUN én gang. Er den allerede sendt — fordi
        # `_promote_earlier_answer_block` valgte en blok der stod på skærmen
        # før halen — så er den ventende tekst noget der kom EFTER svaret. Den
        # skal åbnes som `commentary`, så den bliver stående synligt uden for
        # foldet i stedet for at blive svaret.
        _fold_allerede = bool(_state["final_answer_started"])
        if final and not _fold_allerede:
            _state["final_answer_started"] = True
            await queue.put(SystemEvent(
                kind="final_answer_start",
                payload={"run_id": str(_state["run_id"] or "")},
            ).to_sse_line())
        await _ensure_text_block_open(
            phase="final_answer" if (final and not _fold_allerede) else "commentary",
        )
        # Replay teksten i ~30 små dele — BÅDE slutsvaret og den mellemliggende
        # syntese.
        #
        # MÅLT 3/10-2026 (Bjørn: «det første du skriver før første runde
        # streamer korrekt og efter første runde dumper det ind»). Forklaringen
        # stod i `delta`-grenen ovenfor: teksten FØR første værktøj går ud som
        # `content_block_delta` token-for-token og glider. Teksten EFTER første
        # værktøj lægges i `_pending_text` og bliver først sendt her — og med
        # `chunk_size = len(text)` når `final=False` landede HELE syntesen som
        # ÉT delta. Blokken åbnes først lige her, så den var tom indtil da:
        # den sprang fra tom til fuld, og den synlige strøm blev et dump.
        #
        # Delingen gør de to veje ens. Det er samme tekst, uden et nyt
        # modelkald — og `provisional_text_commit` sendes stadig til sidst, så
        # klienternes foreløbige visning og den bekræftede blok følges ad.
        if final:
            # SLUTSVARET er det Bjørn faktisk LÆSER — det skal rulle, ikke
            # vælte ind. MÅLT 17/10-2026 («det er når hoved folder sammen den
            # dumper»): den gamle form delte i 30 bidder med 30 ms mellemrum,
            # altså 0,87 s UANSET svarets længde — 3000 tegn landede med
            # ~3400 tegn/sekund, hvilket læses som et dump, ikke som strøm.
            #
            # Nu er hastigheden tidsbaseret og læsbar (~900 tegn/s), og den
            # samlede tid har et loft, så et meget langt svar ikke hænger i
            # mange sekunder. Kun `final`: en MELLEMLIGGENDE syntese awaiter
            # også her, og dér må replayen ikke forsinke det værktøjskald der
            # kommer lige efter.
            _REPLAY_MIN_CHARS_PER_SECOND = 900.0
            _REPLAY_MAX_SECONDS = 6.0
            _REPLAY_TICK_S = 0.03
            _rate = max(_REPLAY_MIN_CHARS_PER_SECOND, len(text) / _REPLAY_MAX_SECONDS)
            # Loftet `len//4` sikrer at selv et KORT svar deles i mindst fire
            # bidder: ellers ville en 19-tegns-slutbemærkning komme som ÉT
            # delta (chunken er 27), og så er der intet at rulle.
            chunk_size = max(2, min(int(round(_rate * _REPLAY_TICK_S)), max(2, len(text) // 4)))
        else:
            chunk_size = max(16, (len(text) + 29) // 30)
        _blok = int(_state["text_block_index"])
        for offset in range(0, len(text), chunk_size):
            _bid = text[offset:offset + chunk_size]
            _text_block_lengths[_blok] = _text_block_lengths.get(_blok, 0) + len(_bid)
            await queue.put(ContentBlockDelta(
                index=_blok,
                delta_type="text_delta",
                content=_bid,
            ).to_sse_line())
            if offset + chunk_size < len(text):
                await asyncio.sleep(0.03)
        if not final:
            await queue.put(SystemEvent(
                kind="provisional_text_commit",
                payload={"run_id": str(_state["run_id"] or "")},
            ).to_sse_line())
            # En commentary-blok er en afsluttet arbejdsrunde. Luk den her,
            # så næste rundes terminale tekst kan åbne sin egen blok med
            # ``phase=final_answer`` i stedet for at arve commentary-fasen.
            await _close_text_block_if_open()

    #: Hvilke billeder streamen allerede har sendt — nøgle er `attachment_id`.
    #: Uden den ville hvert efterfølgende billedværktøjs-resultat sende turens
    #: tidligere billeder igen.
    _sendte_billeder: set[str] = set()

    async def _emit_tool_use_start(payload: dict) -> None:
        """Vis værktøjslinjen NÅR kaldet starter — ikke når det er færdigt.

        Bjørn 17/9-2026: «ved tung eller længerevarende kommandoer vises tool
        result linje først efter kommandoen er færdig og den burde vises med
        det samme». Årsagen var at blokken KUN blev født af resultat-eventet;
        annonceringen før kørslen bar hverken id eller argumenter, så klienten
        havde intet at vise. En `bash` der kører i to minutter stod derfor som
        ingenting i to minutter.

        Blokken skrives åben-og-lukket her; status og resultat foldes på af
        `tool_result`-eventet bagefter, som klienten allerede er idempotent
        over for.
        """
        tool_id = str(payload.get("tool_id") or "")
        name = str(payload.get("action") or "")
        if not tool_id or not name or tool_id in _annonceret:
            return
        _annonceret.add(tool_id)
        for kind, value in answer_marker.flush():
            await _emit_model_text(value)
        answer_marker.line_start = True
        answer_marker.line_prefix = ""
        answer_marker.fence = ""
        _state["code_answer_active"] = False
        tool_input = payload.get("arguments")
        await _flush_pending_text()
        await _resolve_unresolved_text(phase="commentary")
        _state["has_tool"] = True
        # Et nyt værktøjskald beviser at teksten FØR det var en mellemsyntese.
        # `final_answer_started` bliver staaende (klienten har allerede foldet,
        # og det maa ikke fortrydes), men teksten EFTER dette kald er hale —
        # ikke en fortsættelse af svaret — saa den skal igen gennem
        # `_pending_text` og blive `commentary`.
        _state["svar_stroemmer"] = False
        # Taelleren hoerer til teksten MELLEM to vaerktoejskald. Et nyt kald
        # afslutter den periode, saa naeste tekst skal maales forfra — ellers
        # ville en lang tur akkumulere sig til 600 over mange runder og
        # promovere en mellemsyntese til svar.
        _state["svar_kandidat_len"] = 0
        await _close_thinking_block_if_open()
        await _close_text_block_if_open()
        idx = _alloc_index()
        if name not in _afsluttende_vaerktoejer:
            _state["last_real_tool_index"] = idx
        await queue.put(ContentBlockStart(
            index=idx, block_type="tool_use", tool_id=tool_id, tool_name=name,
        ).to_sse_line())
        if isinstance(tool_input, dict) and tool_input:
            await queue.put(ContentBlockDelta(
                index=idx,
                delta_type="input_json_delta",
                content=json.dumps(tool_input, ensure_ascii=False),
            ).to_sse_line())
        await queue.put(ContentBlockStop(index=idx).to_sse_line())

    async def _emit_tool_use(payload: dict) -> None:
        """Oversæt et tool-relateret capability-event til en tool_use-blok.

        Lukker en evt. åben text-block, udsender tool_use start (+ input via
        input_json_delta) + stop, og videregiver status som system_event så
        klienten kan markere ToolCard'ens udfald."""
        ptype = str(payload.get("type") or "")
        await _flush_pending_text()
        await _resolve_unresolved_text(phase="commentary")
        _state["has_tool"] = True
        name = str(
            payload.get("capability_name")
            or payload.get("tool")
            or payload.get("capability_id")
            or ""
        )
        tool_id = str(payload.get("capability_id") or payload.get("id") or name or "tool")
        status = str(payload.get("status") or "")
        tool_input: dict = {}
        _args = payload.get("arguments")
        if isinstance(_args, dict):
            tool_input.update(_args)
        for k in ("target_path", "command_text", "write_content"):
            v = payload.get(k)
            if v:
                tool_input[k] = v

        # Blev linjen allerede født da kaldet startede, skal den ikke fødes
        # igen — så ville samme kald stå to gange i tråden. Resultatet foldes
        # på den eksisterende blok via `tool_use_id` nedenfor.
        if tool_id not in _annonceret:
            await _close_thinking_block_if_open()
            await _close_text_block_if_open()
            idx = _alloc_index()
            if name not in _afsluttende_vaerktoejer:
                _state["last_real_tool_index"] = idx
            await queue.put(ContentBlockStart(
                index=idx, block_type="tool_use", tool_id=tool_id, tool_name=name,
            ).to_sse_line())
            if tool_input:
                await queue.put(ContentBlockDelta(
                    index=idx,
                    delta_type="input_json_delta",
                    content=json.dumps(tool_input, ensure_ascii=False),
                ).to_sse_line())
            await queue.put(ContentBlockStop(index=idx).to_sse_line())
        _result_text = str(payload.get("result_text") or "")
        # Status/udfald som system_event bundet til tool_use_id.
        # BEHOLDES ALTID (dual-read på klienten tolererer den) — også når
        # structured_content_v2 er ON. Folding på klienten er idempotent.
        await queue.put(SystemEvent(
            kind="tool_result",
            payload={"tool_use_id": tool_id, "tool": name, "status": status, "type": ptype,
                     "result": _result_text},
        ).to_sse_line())
        # Flag ON → ALSO emit et første-klasses tool_result content-block på nyt
        # index (kanonisk wire-form, jf. AnthropicSSEEmitter.tool_result_block).
        # Klientens reducer folder content_block_start m. content_block.type ==
        # "tool_result" på det matchende tool_use (idempotent). Fejl → intet
        # ekstra event, system_event bærer stadig udfaldet (aldrig break stream).
        try:
            if structured_content_v2_enabled():
                # Samme regel som den gemte tur — se er_fejlstatus.
                from core.services.visible_followup_events import er_fejlstatus
                _is_error = er_fejlstatus(status)
                _tr_idx = _alloc_index()
                await queue.put(_sse_format("content_block_start", {
                    "type": "content_block_start",
                    "index": _tr_idx,
                    "content_block": {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "status": status,
                        "content": _result_text,
                        "is_error": _is_error,
                    },
                }))
                await queue.put(_sse_format("content_block_stop", {
                    "type": "content_block_stop",
                    "index": _tr_idx,
                }))
        except Exception:
            pass

        # BILLEDET I DEN LEVENDE STREAM (27/9-2026).
        #
        # Indtil nu lagde billedværktøjet en note fra sig under turen, og
        # blokken blev først bygget når svaret blev PERSISTERET. Under kørslen
        # var der bogstaveligt talt intet at tegne: animationen vistes, fordi
        # den er sin egen komponent, men billedet havde ingen blok at bo i før
        # turen var slut. Begge klienter havde grenen klar — desk skriver det
        # selv i `sseProtocol.ts`: «LIVE bærer det en `src`, PERSISTERET bærer
        # det en REFERENCE» — den havde bare aldrig fået noget at tage imod.
        #
        # Det er IKKE en ændring af stream-formatet. `content_block_start`
        # bærer allerede vilkårlige blokke; det er præcis sådan `tool_result`
        # ovenfor blev en førsteklasses blok. Her bruges samme konvolut.
        #
        # ALLE TRE billedværktøjer. `openrouter_image_edit` er et tyndt lag
        # over `generate_image` og deler hele resten af kæden — samme
        # `_save_images`, samme `register_generated_image`, samme note. En
        # betingelse på `openrouter_image` alene ville glemme redigeringen OG
        # `pollinations_image`, og det ville ingen opdage, fordi man tester med
        # det værktøj man selv bruger.
        try:
            # 7/10-2026: kaldt for ETHVERT værktøj, ikke kun billedværktøjerne.
            # En widget udgives af `vis_widget`, som ikke er et billedværktøj —
            # så den levende blok blev aldrig sendt. `peek_efter_tool_use` giver
            # tom liste for alle andre værktøjer, så kaldet koster intet.
            for _blok in _live_udgivne_blokke(tool_id, _sendte_billeder):
                _img_idx = _alloc_index()
                await queue.put(_sse_format("content_block_start", {
                    "type": "content_block_start",
                    "index": _img_idx,
                    "content_block": _blok,
                }))
                await queue.put(_sse_format("content_block_stop", {
                    "type": "content_block_stop",
                    "index": _img_idx,
                }))
        except Exception as _img_exc:
            # Et billede der ikke kan sendes live må aldrig brække streamen —
            # den persisterede blok bygges stadig når svaret gemmes, så
            # billedet er der efter turen uanset hvad der sker her.
            logger.warning("sse_v2: kunne ikke sende billedet live: %r", _img_exc)

    async def _ping_loop() -> None:
        try:
            while True:
                await asyncio.sleep(ping_interval_s)
                await queue.put(Ping().to_sse_line())
        except asyncio.CancelledError:
            pass

    async def _translation_loop() -> None:
        _aiter = legacy_iter.__aiter__()
        _idle_ticks = 0
        # ── IDLE-CANCEL-ROD-FIX (Bjørn 4. jul) ──────────────────────────────────
        # FØR: `await asyncio.wait_for(_aiter.__anext__(), timeout=_IDLE_TICK_S)`.
        # wait_for CANCELLERER DESTRUKTIVT den awaitede coroutine ved timeout → hver
        # 20s tavshed kastede CancelledError IND i den LEVENDE run-generator på dens
        # aktuelle await (langt tool-kald, model-runde med lav TTFT som glm-5.2 44-102s,
        # _build_visible_input 6-33s) → generatoren revet ned midt-flugt → run forladt
        # → 'interrupted'/survival. Rammer enhver run med ét tavst vindue >20s (varieret
        # varighed 27-112s, provider-agnostisk). Bevist: keepalive lukkede KUN
        # native_tool_exec-vinduet; alle andre >20s-gaps overlevede stadig ikke.
        # NU: driv __anext__ som en BEVARET task via asyncio.wait (som IKKE cancellerer
        # ved timeout). En tavs-men-levende generator får lov at fortsætte sit lange
        # await; vi bryder KUN når runnet er ægte dødt server-side (_run_still_active
        # False) eller det hårde loft (_MAX_IDLE_TICKS × _IDLE_TICK_S ≈ 180s) — præcis
        # den oprindelige hængende-kilde-sikkerhed, uden at dræbe levende runs.
        _anext_task: "asyncio.Future | None" = None
        try:
            while True:
                if _anext_task is None:
                    _anext_task = asyncio.ensure_future(_aiter.__anext__())
                _done, _pending = await asyncio.wait(
                    {_anext_task}, timeout=_IDLE_TICK_S,
                )
                if not _done:
                    # Timeout — tasken kører VIDERE (ikke cancelleret). Tjek liveness.
                    _idle_ticks += 1
                    _rid = str(_state.get("run_id") or "")
                    if (_rid and not _run_still_active(_rid)) or _idle_ticks >= _MAX_IDLE_TICKS:
                        _state["recovery_reason"] = (
                            "relay_source_closed" if _rid and not _run_still_active(_rid)
                            else "relay_source_idle_timeout"
                        )
                        _anext_task.cancel()  # ægte død kilde → nu må vi rydde op
                        break
                    continue
                try:
                    raw = _anext_task.result()
                except StopAsyncIteration:
                    break  # kilden sluttede rent → finally fyrer terminal-garantien
                finally:
                    _anext_task = None
                _idle_ticks = 0
                parsed = _parse_legacy_sse(raw)
                if parsed is None:
                    continue
                event_name, payload = parsed

                # TTFT maales HER og kun her (4/10-2026). Det er den ene soem
                # hvor hver opstroems-haendelse passerer praecis én gang,
                # allerede parset — en markering ved hvert `queue.put` ville
                # vaere fire kopier af samme regel, og kopier driver fra
                # hinanden.
                #
                # `reasoning_delta` taeller MED som indhold: taenke-tokens er
                # det foerste man ser, og en TTFT der sprang dem over ville
                # sige 14 s om noget der foeltes som 2.
                if event_name in ("delta", "reasoning_delta"):
                    try:
                        from core.services import svar_tempo
                        svar_tempo.foerste_token(str(_state.get("run_id") or ""))
                    except Exception as _tempo_exc:  # noqa: BLE001
                        # Et maaleinstrument maa aldrig vaelte det det maaler.
                        logger.warning("sse_v2: TTFT-markering fejlede: %s", _tempo_exc)

                # Pluk metadata ud af tidlige events så message_start har
                # meningsfulde værdier hvis de ikke blev givet til kaldet.
                #
                # ROD-FIX (12. sep): her stod der `event_name == "delta"`, og
                # det gjorde tænke-varigheden umulig at måle. Kalderen sender
                # run_id="" (chat_stream_v2.py:566 — «plukkes fra første legacy
                # event»), og tænkningen kommer FØR svaret: den første
                # reasoning_delta ramte derfor _open_thinking_block() med en tom
                # run_id, og visible_thinking_trace.mark_start("") returnerede
                # tavst. Målingen fandtes aldrig, take_seconds(run.run_id) gav
                # None ved persistering, og «Tænkte i …»-linjen blev aldrig
                # skrevet — 787 ture med en tænke-blok, 0 med et tal.
                #
                # Ethvert legacy-event må bidrage med run_id, ikke kun "delta".
                # reasoning_delta bærer det selv (visible_runs.py:1727).
                if payload.get("run_id"):
                    _state["run_id"] = _state["run_id"] or str(payload.get("run_id") or "")
                if payload.get("origin"):
                    _state["origin"] = _state["origin"] or str(payload.get("origin") or "")

                if event_name == "reasoning_delta":
                    # Live thinking-trace → foldbart 'tænker…'-felt i frontend.
                    #
                    # Ligger der allerede ventende tekst, ER det rundens egen tekst:
                    # hvert værktøjskald og hvert `working_step: thinking`
                    # flusher den, så ventende tekst kan kun være kommet efter
                    # rundens start. Reasoningen er så BLANDET ind i svaret
                    # (ollama/GLM sender begge felter i samme strøm) og er ikke en
                    # rundegrænse. Flushede vi her, blev svaret skåret over og hver
                    # del en egen afsluttet blok: «V» → Think → «idnet skal …»
                    # (målt i desk på en vækning 12/11-2026). DeepSeek sender
                    # reasoning FØR teksten, så dér var der aldrig noget at skære.
                    if not _pending_text:
                        await _flush_pending_text()
                    await _emit_message_start_if_needed()
                    if not _state["thinking_block_open"]:
                        await _open_thinking_block()
                    chunk = str(payload.get("delta") or "")
                    if chunk:
                        await queue.put(ContentBlockDelta(
                            index=int(_state["thinking_block_index"]),
                            delta_type="thinking_delta",
                            content=chunk,
                        ).to_sse_line())

                elif event_name == "answer_start":
                    await _emit_message_start_if_needed()
                    if not _state["code_answer_started"]:
                        await _flush_pending_text()
                        await _close_text_block_if_open()
                        _state["code_answer_started"] = True
                        _state["code_answer_pending"] = True
                        _state["code_answer_active"] = True
                        logger.info("code-answer-start: EXPLICIT run=%s", _state["run_id"])

                elif event_name == "delta":
                    await _emit_message_start_if_needed()
                    await _close_thinking_block_if_open()  # tanke færdig → nu svaret
                    for kind, value in answer_marker.feed(str(payload.get("delta") or "")):
                        if kind == "text":
                            await _emit_model_text(value)
                        elif not _state["code_answer_started"]:
                            await _flush_pending_text()
                            await _close_text_block_if_open()
                            _state["code_answer_started"] = True
                            _state["code_answer_pending"] = True
                            _state["code_answer_active"] = True
                            logger.info("code-answer-start: EXPLICIT run=%s", _state["run_id"])

                elif event_name == "working_step" and payload.get("action") == "thinking" and not payload.get("tool_id"):
                    # Round boundary: flush commentary without changing code-answer intent.
                    await _flush_pending_text()
                    await _emit_message_start_if_needed()
                    await queue.put(SystemEvent(kind="working_step", payload=payload).to_sse_line())

                elif (
                    event_name == "working_step"
                    and payload.get("er_vaerktoej")
                    and str(payload.get("status") or "") == "running"
                    and payload.get("tool_id")
                ):
                    # Kaldet er annonceret men ikke kørt endnu → linjen fødes
                    # HER, så en tung kommando er synlig mens den kører.
                    # Eventet sendes stadig videre som system_event nedenfor
                    # (liveness-linjen lever af det), derfor ingen `continue`.
                    await _emit_message_start_if_needed()
                    await _emit_tool_use_start(payload)
                    await queue.put(SystemEvent(
                        kind="working_step", payload=payload,
                    ).to_sse_line())

                elif (
                    event_name == "capability"
                    and str(payload.get("type") or "") in ("tool_denied", "gate_blocked")
                    and payload.get("capability_id") in _annonceret
                ):
                    # Et kald der blev afvist har ingen resultat-event. Før
                    # 17/9-2026 betød det bare at linjen aldrig blev født; nu
                    # fødes den ved annonceringen, så uden dette ville den stå
                    # og «køre» resten af turen. Udfaldet lukker den.
                    await _flush_pending_text()
                    await _emit_message_start_if_needed()
                    await queue.put(SystemEvent(
                        kind="tool_result",
                        payload={"tool_use_id": str(payload.get("capability_id") or ""),
                                 "tool": str(payload.get("tool") or ""),
                                 "status": "denied",
                                 "type": str(payload.get("type") or ""),
                                 "result": str(payload.get("message")
                                               or "Afvist.")},
                    ).to_sse_line())

                elif event_name == "capability" and str(payload.get("type") or "") in (
                    "tool_result", "capability"
                ):
                    # Phase 2: ægte tool-eksekvering → struktureret tool_use-blok.
                    # Andre capability-typer (tool_approved, gate_blocked, …)
                    # falder igennem til system_event nedenfor.
                    await _emit_message_start_if_needed()
                    await _emit_tool_use(payload)

                elif event_name == "done":
                    for kind, value in answer_marker.flush():
                        await _emit_model_text(value)
                    _state["saw_done"] = True
                    await _emit_message_start_if_needed()
                    await _close_thinking_block_if_open()
                    _completed = str(payload.get("status") or "") == "completed"
                    await _resolve_unresolved_text(
                        phase="final_answer" if _completed and not _state["has_tool"] else "commentary",
                    )
                    # Svar-blokken vælges FØR fold-signalet. Bagefter ville
                    # grænsen flytte sig mens brugeren ser på den — og det er
                    # præcis det «blink» der er blevet jagtet på visningen.
                    if _completed:
                        await _promote_earlier_answer_block()
                    await _flush_pending_text(final=_completed)
                    # Bjoern 20/10-2026: «en runde linje der hang saa hoved ikk
                    # foldet og da runden forsvandt glippede foldet».
                    #
                    # Efter et vaerktoejskald gaar teksten gennem
                    # `_pending_text`, og en runde-linje EFTER slutsvaret
                    # toemmer den. Ved `done` var koen derfor tom, og begge
                    # emissionssteder sprang over — derfor kom fold-signalet
                    # aldrig, og hovedet stod stille indtil `message_stop` rev
                    # det ned i EET glip.
                    #
                    # Signatet er ikke en transportdetalje: det er beskeden
                    # «svaret er faerdigt». Det skal ud, uanset koen.
                    if _completed and not _state["final_answer_started"]:
                        logger.info(
                            "fold-signal: DONE (taersklen aldrig naaet, %d tegn, has_tool=%s)",
                            _state["svar_kandidat_len"],
                            _state["has_tool"],
                        )
                        _state["final_answer_started"] = True
                        await queue.put(SystemEvent(
                            kind="final_answer_start",
                            payload={"run_id": str(_state["run_id"] or "")},
                        ).to_sse_line())
                    # En afsluttet tur skal ALTID have en slutblok. Har
                    # værktøjskaldet efter svaret tømt køen, blev der aldrig
                    # åbnet en — og så ligger svaret i folden mens skærmen er
                    # tom. Se `_promote_last_text_block_to_answer`.
                    #
                    # Rækkefølgen er ikke ligegyldig: promoveringen sætter
                    # `final_answer_started`, så kørte den FØR blokken ovenfor,
                    # ville den kvalt fold-signalet. Den eksisterende test
                    # `test_runde_linje_efter_svaret_maa_ikke_fjerne_fold_signalet`
                    # fangede præcis det.
                    if _completed:
                        await _promote_last_text_block_to_answer()
                    if _completed and not _state["code_answer_started"] and _text_block_phases:
                        code_index = max(_text_block_phases)
                        logger.info("code-answer-start: TERMINAL_FALLBACK run=%s index=%d", _state["run_id"], code_index)
                        await queue.put(SystemEvent(kind="code_answer_boundary", payload={
                            "run_id": str(_state["run_id"] or ""), "index": code_index,
                        }).to_sse_line())
                    await _close_text_block_if_open()
                    _state["input_tokens"] = int(payload.get("input_tokens") or 0)
                    _state["output_tokens"] = int(payload.get("output_tokens") or 0)
                    _state["stop_reason"] = str(payload.get("status") or "end_turn")
                    _tempo = _laes_tempo(str(_state.get("run_id") or ""),
                                         int(_state["output_tokens"]))
                    await queue.put(MessageDelta(
                        stop_reason=str(_state["stop_reason"]),
                        input_tokens=int(_state["input_tokens"]),
                        output_tokens=int(_state["output_tokens"]),
                        cache_hit_tokens=int(_state["cache_hit_tokens"]),
                        cache_miss_tokens=int(_state["cache_miss_tokens"]),
                        ttft_ms=_tempo.get("ttft_ms"),
                        tok_per_sek=_tempo.get("tok_per_sek"),
                    ).to_sse_line())
                    await queue.put(MessageStop().to_sse_line())
                    _state["message_stopped"] = True
                    try:
                        from core.services import stream_sentinel
                        stream_sentinel.note_stop(str(_state["run_id"] or ""), reason="done")
                    except Exception:
                        pass
                    break

                elif event_name == "tool_output_delta":
                    await _emit_message_start_if_needed()
                    await queue.put(SystemEvent(
                        kind="tool_output_delta", payload=payload,
                    ).to_sse_line())

                elif event_name == "heartbeat":
                    # v2 har sin egen ping — skip legacy heartbeats
                    continue

                elif event_name == "tool_call":
                    # Path B (local_tool_exec): serveren ejer transcript'et men
                    # eksekverer IKKE tool'et — den registrerer kaldet hos brokeren
                    # og sender det som et FØRSTE-KLASSES tool_call-event til klienten
                    # (jarvis-code), som kører det lokalt og POSTer resultatet tilbage
                    # til /chat/tool_results. Payload bærer allerede den fulde form
                    # {type, run_id, session_id, call_id, name, arguments}.
                    await _flush_pending_text()
                    _state["has_tool"] = True
                    await _emit_message_start_if_needed()
                    await queue.put(_sse_format("tool_call", payload))

                else:
                    # working_step, capability, approval_request,
                    # steer_received, turn_changelog, eller ukendt →
                    # wrap som system_event med kind = event_name
                    await _emit_message_start_if_needed()
                    # 25/10-2026: her stod en gren der gjorde ingenting —
                    # ``if kind not in _KNOWN_SYSTEM_EVENT_KINDS: pass``. Den
                    # lignede en beslutning om at ukendte kinds blev behandlet
                    # særskilt, men både den kendte og den ukendte vej endte i
                    # det samme ``queue.put``. Fjernet, så der ikke står en
                    # forgrening der ser ud som om den vælger noget.
                    #
                    # ``_KNOWN_SYSTEM_EVENT_KINDS`` bliver stående som
                    # dokumentation af hvilke legacy-navne vi kender — den
                    # beskriver navnene, den styrer ikke længere et valg.
                    kind = event_name
                    await queue.put(SystemEvent(
                        kind=kind, payload=payload,
                    ).to_sse_line())
        except asyncio.CancelledError:
            # Stream-cluster: lanen blev afbrudt (klient-disconnect / outer cancel).
            # Ryd den bevarede __anext__-task så den ikke bliver en orphaned pending
            # task ("Task was destroyed but it is pending"-anomalien).
            try:
                if _anext_task is not None and not _anext_task.done():
                    _anext_task.cancel()
            except Exception:
                pass
            try:
                from core.services import stream_sentinel
                if _state["message_started"] and not _state["message_stopped"]:
                    stream_sentinel.note_event(
                        str(_state["run_id"] or ""), "cancel",
                        str(_state["session_id"] or ""),
                        message_stopped=bool(_state["message_stopped"]))
            except Exception:
                pass
            raise
        except Exception as _loop_exc:
            # Stream-cluster: ÆGTE fejl i translations-loopet. Før forsvandt den
            # tavst (kun finally-garantien kørte, ingen kunne pege på hvad der
            # gik galt). Nu synlig i Centralen — finally lukker stadig rent.
            try:
                from core.services import stream_sentinel
                stream_sentinel.note_event(
                    str(_state["run_id"] or ""), "error",
                    str(_state["session_id"] or ""),
                    error=f"{type(_loop_exc).__name__}: {_loop_exc}"[:200],
                    message_started=bool(_state["message_started"]))
            except Exception:
                pass
        finally:
            if not _state["saw_done"]:
                _reason = str(
                    _state.get("recovery_reason")
                    or "legacy_stream_ended_without_done"
                )
                try:
                    from core.services.auto_continuation import noter_udfald
                    noter_udfald(
                        str(_state.get("run_id") or ""),
                        f"interrupted:{_reason}",
                        str(_state.get("session_id") or ""),
                    )
                except Exception:
                    pass
            # TERMINAL-GARANTI (Bjørn 2026-06-13: "random hangs"): klientens
            # status forlader kun 'working' når den ser message_stop. Hvis
            # runnet sluttede UDEN et 'done'-event (error, exception, cancel,
            # eller legacy-strømmen bare endte) ville message_stop aldrig blive
            # sendt → liveness/thinking hænger på 'working' for evigt. Emit den
            # her hvis et message_start blev sendt men intet message_stop endnu,
            # så turen ALTID afsluttes rent uanset hvordan den endte.
            if _state["message_started"] and not _state["message_stopped"]:
                try:
                    await _close_thinking_block_if_open()
                    await _flush_pending_text()
                    await _close_text_block_if_open()
                    # Samme kontrakt paa GENDANNELSES-vejen (maalt 20/10-2026):
                    # et run der slutter uden `done` (fejl, cancel, legacy-stream
                    # der bare ender) sendte `message_stop` uden at have sendt
                    # fold-signalet — klienten faldt fra «arbejde koerer» til
                    # «faerdig» i EET glip, praecis som den tomme tekstkoe gav.
                    # Kommer `message_stop`, skal fold-signalet altid vaere sendt
                    # foerst; ellers er der intet at folde til.
                    if not _state["final_answer_started"]:
                        _state["final_answer_started"] = True
                        await queue.put(SystemEvent(
                            kind="final_answer_start",
                            payload={"run_id": str(_state["run_id"] or "")},
                        ).to_sse_line())
                    if not _state["saw_done"]:
                        from core.services.visible_terminal_policy import recovery_notice
                        _reason = str(
                            _state.get("recovery_reason")
                            or "legacy_stream_ended_without_done"
                        )
                        await queue.put(SystemEvent(
                            kind="run_recovery",
                            payload=recovery_notice(_reason),
                        ).to_sse_line())
                        _state["stop_reason"] = "recovering"
                    # Ogsaa paa GENDANNELSES-vejen. Et run der endte uden
                    # `done` har stadig haft en TTFT, og udelod vi den her,
                    # ville tallet forsvinde praecis i de ture hvor noget gik
                    # galt — altsaa dem man helst vil kunne maale.
                    _tempo = _laes_tempo(str(_state.get("run_id") or ""),
                                         int(_state["output_tokens"]))
                    await queue.put(MessageDelta(
                        stop_reason=str(_state.get("stop_reason") or "end_turn"),
                        input_tokens=int(_state["input_tokens"]),
                        output_tokens=int(_state["output_tokens"]),
                        cache_hit_tokens=int(_state["cache_hit_tokens"]),
                        cache_miss_tokens=int(_state["cache_miss_tokens"]),
                        ttft_ms=_tempo.get("ttft_ms"),
                        tok_per_sek=_tempo.get("tok_per_sek"),
                    ).to_sse_line())
                    await queue.put(MessageStop().to_sse_line())
                    _state["message_stopped"] = True
                except Exception:
                    pass  # best-effort — sentinel nedenfor lukker uanset hvad
            # Stream-cluster: terminal-garanti-stop (run sluttede uden 'done'-event).
            try:
                from core.services import stream_sentinel
                if _state["message_started"]:
                    stream_sentinel.note_stop(
                        str(_state["run_id"] or ""),
                        reason="fallback" if _state["message_stopped"] else "no_stop")
            except Exception:
                pass
            # ── KRITISK (2026-06-21): luk den underliggende legacy-generator ──
            # _translation_loop BRYDER ud ved 'done' (break) uden at udtømme
            # legacy_iter. `async for ... break` aclose'r IKKE automatisk → så
            # _stream_visible_run's finally — der spawner _post_process (fact_gate,
            # diagnosis, claim-scanner, memory-postprocess, auto-continuation) —
            # kørte ALDRIG for follow-runs (desk/mobil). aclose() raiser
            # GeneratorExit ved den suspenderede 'done'-yield → finally kører →
            # post-process spawnes. Det er roden til "truth-gates fyrer aldrig".
            try:
                _aclose = getattr(legacy_iter, "aclose", None)
                if _aclose is not None:
                    await _aclose()
            except Exception:
                pass
            # Signaler at translation er færdig — ping-loop stoppes via
            # outer cancel, og hovedløkken nedenfor breaker når den ser
            # sentinel.
            await queue.put(None)

    ping_task = asyncio.create_task(_ping_loop())
    translation_task = asyncio.create_task(_translation_loop())

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        ping_task.cancel()
        translation_task.cancel()
        # Drain eventuelle restevents i kø så ressourcer frigives ordentligt.
        try:
            await asyncio.gather(ping_task, translation_task, return_exceptions=True)
        except Exception:
            pass
