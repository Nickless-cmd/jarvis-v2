"""Translator: legacy SSE-events → Anthropic-style v2-protokol.

Phase 1 (denne fil): basic text-flow translation
- delta → content_block_delta(text_delta) til den aktive text-block
- working_step / capability / approval_request / steer_received /
  turn_changelog → system_event-wrappes
- done → content_block_stop + message_delta + message_stop
- heartbeat → skip (v2 har sin egen ping)

Phase 2 (senere): tool_use blocks, thinking_delta, partial input_json_delta.

Forbruger output fra core.services.visible_runs.start_visible_run() der
yielder SSE-formaterede strenge i legacy-format. Parser dem, oversætter
til v2 dataclasses, serializer som v2 SSE-strenge.

Spec: docs/superpowers/specs/2026-06-10-chat-stream-v2-design.md
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncIterator

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


def _run_still_active(run_id: str) -> bool:
    """True hvis dette run stadig er det aktive visible-run server-side. Fail-safe:
    antag AKTIVT ved fejl, så vi aldrig afslutter en levende stream for tidligt."""
    try:
        from core.services.visible_runs import _get_active_visible_run_state
        st = _get_active_visible_run_state() or {}
        return bool(st.get("active")) and str(st.get("run_id") or "") == str(run_id or "")
    except Exception:
        return True


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
        "run_id": run_id,
        "model": model,
        "provider": provider,
        "lane": lane,
        "session_id": session_id,
    }

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

    async def _close_thinking_block_if_open() -> None:
        if _state["thinking_block_open"]:
            await queue.put(ContentBlockStop(
                index=int(_state["thinking_block_index"]),
            ).to_sse_line())
            _state["thinking_block_open"] = False

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

    async def _emit_tool_use(payload: dict) -> None:
        """Oversæt et tool-relateret capability-event til en tool_use-blok.

        Lukker en evt. åben text-block, udsender tool_use start (+ input via
        input_json_delta) + stop, og videregiver status som system_event så
        klienten kan markere ToolCard'ens udfald."""
        ptype = str(payload.get("type") or "")
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
                _is_error = str(status).strip().lower() in {"error", "failed", "denied"}
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

                # Pluk metadata ud af tidlige events så message_start har
                # meningsfulde værdier hvis de ikke blev givet til kaldet.
                if event_name == "delta" and payload.get("run_id"):
                    _state["run_id"] = _state["run_id"] or str(payload.get("run_id") or "")

                if event_name == "reasoning_delta":
                    # Live thinking-trace → foldbart 'tænker…'-felt i frontend.
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
                    await _ensure_text_block_open()
                    raw_text = str(payload.get("delta") or "")
                    text = echo_filter.feed(raw_text)
                    if text:
                        await queue.put(ContentBlockDelta(
                            index=int(_state["text_block_index"]),
                            delta_type="text_delta",
                            content=text,
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
                    await _emit_message_start_if_needed()
                    await _close_thinking_block_if_open()
                    await _close_text_block_if_open()
                    _state["input_tokens"] = int(payload.get("input_tokens") or 0)
                    _state["output_tokens"] = int(payload.get("output_tokens") or 0)
                    _state["stop_reason"] = str(payload.get("status") or "end_turn")
                    await queue.put(MessageDelta(
                        stop_reason=str(_state["stop_reason"]),
                        input_tokens=int(_state["input_tokens"]),
                        output_tokens=int(_state["output_tokens"]),
                        cache_hit_tokens=int(_state["cache_hit_tokens"]),
                        cache_miss_tokens=int(_state["cache_miss_tokens"]),
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
                    await _close_text_block_if_open()
                    await queue.put(MessageDelta(
                        stop_reason=str(_state.get("stop_reason") or "end_turn"),
                        input_tokens=int(_state["input_tokens"]),
                        output_tokens=int(_state["output_tokens"]),
                        cache_hit_tokens=int(_state["cache_hit_tokens"]),
                        cache_miss_tokens=int(_state["cache_miss_tokens"]),
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
