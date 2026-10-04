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
import re
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

# SSE-format regex til at parse legacy events:
#   event: <name>
#   data: <json>
#   (blank line)
_SSE_BLOCK_RE = re.compile(
    r"event:\s*(?P<event>[^\n]+)\n"
    r"data:\s*(?P<data>[^\n]+)\n\n",
)


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
    # Skills runtimen lagde i prompten (skill_relevance_surface.skill_flade_event).
    "skill_surface",
    # Unified fejl-system (2026-06-23): konsistent bruger-vendt fejl-event
    # (central_error_envelope.to_client_event). Alle klienter renderer samme form.
    "error",
}


# Echo-mønstre for tool-leak backstop (Del A2 i Phase 2-spec):
#  - _ECHO_BUILDING: en partiel linje der STADIG kan blive til "[tool]:"
#    (vi holder den tilbage indtil den enten fuldføres eller diverger).
#  - _ECHO_FULL: en bekræftet "[tool]:"-præfiks — droppes hvis <tool> er et
#    kendt registreret toolnavn.
_ECHO_BUILDING_RE = re.compile(r"^\s*\[[a-z0-9_]*\]?\s*:?\s*$")
_ECHO_FULL_RE = re.compile(r"^\s*\[([a-z0-9_]+)\]\s*:")


class ToolEchoFilter:
    """Streaming-backstop mod at modellen ekkoer rå tool-output i sit svar.

    Dropper hele linjer der starter med ``[<kendt_tool>]:`` (fx
    ``[read_file]: <fil-dump>``) men lader al anden tekst flyde igennem
    token-for-token (minimal latency — vi holder kun tilbage når en linje
    ved line-start *kunne* blive til en tool-echo).

    Brug: ``feed(text)`` pr. delta, ``flush()`` ved stream-slut.
    """

    def __init__(self, tool_names=None) -> None:
        if tool_names is None:
            try:
                from core.tools.simple_tools import _TOOL_HANDLERS
                tool_names = list(_TOOL_HANDLERS.keys())
            except Exception:
                tool_names = []
        self._names = {str(n).lower() for n in tool_names}
        self._held = ""             # holdt partiel linje (mulig echo)
        self._at_line_start = True  # er vi ved starten af en ny linje?
        self._dropping = False      # dropper vi resten af en bekræftet echo-linje?

    def _is_echo_line(self, line: str) -> bool:
        m = _ECHO_FULL_RE.match(line)
        return bool(m and m.group(1).lower() in self._names)

    def feed(self, text: str) -> str:
        if not text:
            return ""
        out: list[str] = []
        buf = self._held + text
        self._held = ""
        while buf:
            if self._dropping:
                nl = buf.find("\n")
                if nl == -1:
                    buf = ""
                else:
                    buf = buf[nl + 1:]
                    self._dropping = False
                    self._at_line_start = True
                continue
            if not self._at_line_start:
                nl = buf.find("\n")
                if nl == -1:
                    out.append(buf)
                    buf = ""
                else:
                    out.append(buf[:nl + 1])
                    buf = buf[nl + 1:]
                    self._at_line_start = True
                continue
            # Ved line-start.
            nl = buf.find("\n")
            if nl != -1:
                line = buf[:nl + 1]
                buf = buf[nl + 1:]
                if not self._is_echo_line(line):
                    out.append(line)
                # echo-linje droppes
                self._at_line_start = True
                continue
            # Partiel linje uden newline endnu.
            line = buf
            buf = ""
            if _ECHO_BUILDING_RE.match(line):
                self._held = line          # endnu uafklaret — hold tilbage
            elif self._is_echo_line(line):
                self._dropping = True      # bekræftet echo, drop resten af linjen
            else:
                out.append(line)
                self._at_line_start = False
            break
        return "".join(out)

    def flush(self) -> str:
        held = self._held
        self._held = ""
        if not held:
            return ""
        if self._is_echo_line(held):
            return ""
        return held


def _parse_legacy_sse(chunk: str) -> tuple[str, dict] | None:
    """Parse en legacy SSE event-blok til (event_name, payload_dict).

    Returnerer None hvis chunk ikke er en fuldstændig event-blok eller
    payload ikke er valid JSON.
    """
    m = _SSE_BLOCK_RE.search(chunk)
    if not m:
        return None
    event_name = m.group("event").strip()
    data_str = m.group("data")
    try:
        payload = json.loads(data_str)
    except (ValueError, TypeError):
        return None
    return event_name, payload


# D2-leak hang-fix (16. jun 2026): legacy-strømmen kan BLOKERE uden at sende 'done'
# (presentation-invariant-leak afslutter runnet server-side, men kilde-generatoren
# hænger), så `async for raw in legacy_iter` venter evigt og når aldrig finally-
# terminal-garantien → desk hænger i 'working'. Vi venter derfor med en idle-timeout:
# hvis ingen legacy-event i _IDLE_TICK_S OG runnet ikke længere er aktivt server-side
# → bryd ud så message_stop fyrer. Hård loft (_MAX_IDLE_TICKS) som sidste værn.
_IDLE_TICK_S = 20.0          # sekunder uden legacy-event før vi tjekker active-state
_MAX_IDLE_TICKS = 9          # ~180s total stilhed → kilden er død uanset


#: De tre værktøjer der producerer et billede. `openrouter_image_edit` er et
#: tyndt lag over `generate_image` og deler hele kæden efter kaldet, så den er
#: lige så ramt af et manglende live-billede som genereringen.
_BILLEDVAERKTOEJER = frozenset({
    "openrouter_image", "openrouter_image_edit", "pollinations_image",
})


def _live_billedblokke(tool_use_id: str, allerede_sendt: set[str]) -> list[dict[str, Any]]:
    """Billedblokke for turen der endnu ikke er sendt, klar til den levende stream.

    Noterne kommer fra `published_files` — dem værktøjet lagde fra sig under
    turen — og læses med `peek`, ikke `take`: den der persisterer svaret
    bagefter skal stadig kunne finde dem.

    ## Hvorfor der IKKE filtreres på `tool_use_id`

    Første udgave gjorde det, og den virkede i test og ikke i drift. Grunden
    stod i udsenderen: `visible_runs` har TO steder der sender
    `capability/tool_result`, og det ene (linje ~4706, den godkendte vej)
    sender kun `{"type", "tool", "status"}` — **uden `capability_id`**. Så
    faldt `tool_id` tilbage til selve værktøjsNAVNET, filteret ledte efter en
    note med `tool_use_id = "openrouter_image"`, og der var ingen. Testen
    gav eventet et `capability_id` og kunne derfor ikke se det.

    I stedet holdes der styr på hvad der ER sendt. Enhver endnu usendt
    billed-note går ud ved næste billedværktøjs-resultat. Det virker uanset om
    udsenderen har et id med, uanset om ét kald producerede flere billeder
    (`n > 1`), og uanset hvor mange billedkald turen indeholder.

    En LIVE-blok bærer `src` (en data-URL) så klienten kan tegne den med det
    samme. Er billedet for stort til en data-URL, sendes blokken alligevel med
    sin `attachment_id`: den er allerede registreret, så
    `/attachments/image/{id}` virker med det samme, og klienten henter den
    med token. Bedre et billede der kommer et øjeblik senere end intet.
    """
    if not tool_use_id:
        return []
    from core.services.published_files import as_blocks, peek_efter_tool_use
    poster = peek_efter_tool_use(tool_use_id)
    blokke = []
    for b in as_blocks(poster):
        if b.get("type") != "image":
            continue
        noegle = str(b.get("attachment_id") or b.get("url") or b.get("filename") or "")
        if not noegle or noegle in allerede_sendt:
            continue
        allerede_sendt.add(noegle)
        blokke.append(b)
    if not blokke:
        return []
    from core.services.attachment_service import image_data_url
    for blok in blokke:
        aid = str(blok.get("attachment_id") or "")
        if not aid:
            continue
        try:
            url = image_data_url(aid)
        except Exception as exc:
            logger.debug("sse_v2: data-URL for %s fejlede: %s", aid, exc)
            url = None
        if url:
            blok["src"] = url
    return blokke


def _run_still_active(run_id: str) -> bool:
    """True hvis dette run stadig kører server-side. Fail-safe: antag AKTIVT ved fejl,
    så vi aldrig afslutter en levende stream for tidligt.

    ROD-FIX (Bjørn 4. aug): FØR tjekkede den KUN den globale active-visible-run-slot
    (_get_active_visible_run_state). Men ALLE runs er nu detached (server-autoritative),
    og detached-stien vedligeholder den slot UPÅLIDELIGT (detached_run.py:86-96) → den
    returnerede False for LEVENDE runs → idle-timeouten (20s uden legacy-event) brød
    _translation_loop → gen.aclose() rev det stadig-kørende run ned midt i tool-exec →
    CancelledError/vis_len=0 i ALLE sessioner på tværs af klienter. run_event_log er den
    PÅLIDELIGE autoritet (detached_run.py:144): is_open = registreret OG ikke done.
    Frame-friskhed er kun et UI-signal og må aldrig være dødsbevis for et blokerende
    provider/tool-kald. _MAX_IDLE_TICKS≈180s er sidste hæng-værn; rammes det, bogføres
    et recovery-udfald. Slot beholdes som fallback for legacy-runs."""
    try:
        from core.services import run_event_log as _rel
        if _rel.is_open(run_id):
            return True
    except Exception:
        return True
    try:
        from core.services.visible_runs import _get_active_visible_run_state
        st = _get_active_visible_run_state() or {}
        return bool(st.get("active")) and str(st.get("run_id") or "") == str(run_id or "")
    except Exception:
        return True


def _laes_tempo(run_id: str, output_tokens: int) -> dict[str, float | None]:
    """TTFT og tok/s for dette run. Tomt dict ved enhver fejl.

    Egen funktion fordi `MessageDelta` bygges to steder (normal afslutning og
    gendannelse), og en try/except kopieret begge steder ville vaere to
    definitioner af «hvad goer vi naar maalingen fejler».
    """
    try:
        from core.services import svar_tempo
        return svar_tempo.afslut(run_id, output_tokens=output_tokens)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sse_v2: kunne ikke aflaese svar-tempoet: %s", exc)
        return {}


async def translate_to_v2(
    legacy_iter: AsyncIterator[str],
    *,
    run_id: str = "",
    model: str = "",
    provider: str = "",
    lane: str = "",
    session_id: str | None = None,
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
        "has_tool": False,
    }

    # Efter et værktøj kan tekst være både en mellemsyntese og slutsvaret.
    # Hold kun den uafklarede tekst tilbage; et nyt værktøj/en ny runde gør
    # den til arbejde, mens terminal done gør den til et bekræftet svar.
    _pending_text: list[str] = []

    #: Kald hvis linje allerede er født af annonceringen (før kørslen). Uden
    #: den ville resultat-eventet føde en linje MERE om samme kald.
    _annonceret: set[str] = set()

    def _alloc_index() -> int:
        idx = int(_state["next_index"])
        _state["next_index"] = idx + 1
        return idx

    async def _open_text_block() -> None:
        idx = _alloc_index()
        _state["text_block_index"] = idx
        await queue.put(ContentBlockStart(
            index=idx, block_type="text",
        ).to_sse_line())
        _state["text_block_open"] = True

    async def _emit_message_start_if_needed() -> None:
        if _state["message_started"]:
            return
        _state["message_started"] = True
        await queue.put(MessageStart(
            run_id=str(_state["run_id"] or ""),
            model=str(_state["model"] or ""),
            provider=str(_state["provider"] or ""),
            lane=str(_state["lane"] or ""),
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

    async def _ensure_text_block_open() -> None:
        if not _state["text_block_open"]:
            await _open_text_block()

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
                await queue.put(ContentBlockDelta(
                    index=int(_state["text_block_index"]),
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
        if final:
            await queue.put(SystemEvent(
                kind="final_answer_start",
                payload={"run_id": str(_state["run_id"] or "")},
            ).to_sse_line())
        await _ensure_text_block_open()
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
        chunk_size = max(16, (len(text) + 29) // 30)
        for offset in range(0, len(text), chunk_size):
            await queue.put(ContentBlockDelta(
                index=int(_state["text_block_index"]),
                delta_type="text_delta",
                content=text[offset:offset + chunk_size],
            ).to_sse_line())
            if offset + chunk_size < len(text):
                await asyncio.sleep(0.03)
        if not final:
            await queue.put(SystemEvent(
                kind="provisional_text_commit",
                payload={"run_id": str(_state["run_id"] or "")},
            ).to_sse_line())

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
        tool_input = payload.get("arguments")
        await _flush_pending_text()
        _state["has_tool"] = True
        await _close_thinking_block_if_open()
        await _close_text_block_if_open()
        idx = _alloc_index()
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
            if name in _BILLEDVAERKTOEJER:
                for _blok in _live_billedblokke(tool_id, _sendte_billeder):
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

                if event_name == "reasoning_delta":
                    # Live thinking-trace → foldbart 'tænker…'-felt i frontend.
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

                elif event_name == "delta":
                    await _emit_message_start_if_needed()
                    await _close_thinking_block_if_open()  # tanke færdig → nu svaret
                    raw_text = str(payload.get("delta") or "")
                    text = echo_filter.feed(raw_text)
                    if text:
                        if _state["has_tool"]:
                            _pending_text.append(text)
                            await queue.put(SystemEvent(
                                kind="provisional_text_delta",
                                payload={"run_id": str(_state["run_id"] or ""), "delta": text},
                            ).to_sse_line())
                        else:
                            await _ensure_text_block_open()
                            await queue.put(ContentBlockDelta(
                                index=int(_state["text_block_index"]),
                                delta_type="text_delta",
                                content=text,
                            ).to_sse_line())

                elif event_name == "working_step" and payload.get("action") == "thinking" and not payload.get("tool_id"):
                    # En ny modelrunde bekræfter, at forrige tekst var syntese.
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
                    _state["saw_done"] = True
                    await _emit_message_start_if_needed()
                    await _close_thinking_block_if_open()
                    await _flush_pending_text(final=str(payload.get("status") or "") == "completed")
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
                    kind = event_name
                    if kind not in _KNOWN_SYSTEM_EVENT_KINDS:
                        # Ukendt legacy event-type: stadig pass through
                        # som system_event så klienten kan ignorere det
                        # eller logge til debug.
                        pass
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
