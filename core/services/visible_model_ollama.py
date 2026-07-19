"""Ollama visible-lane adapter (execute + native NDJSON streaming).

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07). Contains
the Ollama-specific execute/stream adapters, the thinking-mode + sampling-option
appliers, the Ollama target probe and the flat-prompt builder. Re-exported
verbatim from ``core.services.visible_model``.

Imports the two prompt-input builders from ``visible_model`` at top; that module
imports this one at the BOTTOM of its body, after those builders are defined, so
there is no import cycle.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)
from datetime import UTC, datetime
from typing import Iterator

from urllib import error as urllib_error
from urllib import request as urllib_request

from core.services.stream_failure_kind import (
    MalformedStreamPayload,
    safe_decode_line,
    try_parse_json_line,
)
from core.services.ollama_visible_prompt import serialize_ollama_visible_prompt

from core.services.visible_model_types import (
    VisibleModelDelta,
    VisibleModelResult,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)
from core.services.visible_model_observe import (
    _observe_content_empty_thinking_fallback,
    _observe_malformed_stream_payload,
    _observe_visible_prefill,
    _observe_visible_provider_error,
    _strip_thinking_delimiters,
)
from core.services.visible_model_sse import _estimate_tokens
from core.services.visible_model import _build_visible_input


def _vm():
    """Return the ``visible_model`` facade module.

    Boy-scout split seam (2026-07-07): ``_build_visible_input`` /
    ``urllib_request`` / the ``_OLLAMA_*_BUDGET_S`` deadlines are re-exported
    from the facade, and tests monkeypatch the facade binding. Resolving them
    through the facade at call time keeps ``monkeypatch.setattr(visible_model,
    ...)`` effective across the module boundary — same behaviour as before the
    split. Pure seam plumbing: no behaviour change.
    """
    from core.services import visible_model as _vm_mod

    return _vm_mod


def _execute_ollama_model(
    *, message: str, model: str, session_id: str | None = None
) -> VisibleModelResult:
    from core.services.ollama_visible_prompt import (
        serialize_ollama_chat_messages,
    )
    from core.tools.simple_tools import get_tool_definitions

    # 2026-06-13: resolve OLLAMA-providerens base_url — IKKE visible-lanen (som
    # peger på deepseek-API). Ellers POST'er vi ollama-format til deepseek → 401.
    from core.runtime.provider_router import (
        load_provider_router_registry as _lprr,
        _provider_base_url as _pburl,
    )
    base_url = (
        _pburl(provider="ollama", registry=_lprr()) or "http://127.0.0.1:11434"
    ).rstrip("/")

    visible_input = _vm()._build_visible_input(message, session_id=session_id)
    messages = serialize_ollama_chat_messages(visible_input)
    from core.tools.copilot_tool_pruning import select_tools_for_visible
    tools = select_tools_for_visible(
        get_tool_definitions(), user_message=message, session_id=session_id,
    )

    # Model-bevidst sikkerhedsnet: trim ældste historik så den samlede prompt
    # passer i modellens vindue. Uden dette overløber små-vindue-modeller (fx GLM
    # 200k) på lange samtaler → Ollama HTTP 400 "prompt is too long" → tavst svar.
    try:
        from core.services.model_context import fit_messages_to_window
        from core.runtime.settings import load_settings as _ls
        _s = _ls()
        _np = int(_s.visible_ollama_num_predict or 0) or 16_000
        # + headroom (Bjørn 2026-06-23): hold ekstra plads fri ud over output, så
        # transcripten ikke fylder hele vinduet → undgår loop/cut-off på lange sessioner.
        _budget = _np + int(getattr(_s, "visible_context_headroom_tokens", 0) or 0)
        messages, _dropped = fit_messages_to_window(
            messages, provider="ollama", model=model, output_budget=_budget,
        )
        if _dropped:
            logger.warning(
                "visible ollama: trimmede %d ældste beskeder så prompten passer i "
                "%s's kontekstvindue", _dropped, model,
            )
    except Exception:
        pass  # fail-open — hellere et forsøg end ingen

    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    _apply_visible_ollama_options(payload)
    if tools:
        payload["tools"] = tools

    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as _http_exc:
        try:
            _d = _http_exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            _d = ""
        _observe_visible_provider_error("ollama", model, int(_http_exc.code),
                                        f"Ollama HTTP {_http_exc.code}: {_d or _http_exc.reason}")
        raise RuntimeError(f"Ollama HTTP {_http_exc.code}: {_d or _http_exc.reason}") from _http_exc

    msg = data.get("message") or {}
    text = str(msg.get("content") or "").strip()
    if not text:
        # I1-heal (spec §11.5): SAMME thinking-felt-parse-hul som streaming-stien.
        # En resend (re-sample) helbreder IKKE et thinking-only svar af sig selv —
        # content er stadig tom. Surface thinking som svaret hvis det har indhold,
        # i stedet for at raise empty. FALLBACK: når content er til stede er adfærden
        # uændret. Fyr nerve så hyppigheden er målbar.
        think = _strip_thinking_delimiters(str(msg.get("thinking") or ""))
        if think:
            _observe_content_empty_thinking_fallback(
                "ollama", model, "resend", len(str(msg.get("thinking") or "")),
            )
            text = think
        else:
            # Tomt svar = "spinner→stop→intet". Gør det SYNLIGT i Centralen (var tavst).
            _observe_visible_provider_error("ollama", model, 0, "Ollama returnerede tomt svar")
            raise RuntimeError("Ollama visible execution returned no response")

    prompt_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
    prompt_eval_count = int(data.get("prompt_eval_count") or prompt_estimate)
    eval_count = int(data.get("eval_count") or _estimate_tokens(text))
    return VisibleModelResult(
        text=text,
        input_tokens=prompt_eval_count,
        output_tokens=eval_count,
        cost_usd=0.0,
    )


def _apply_thinking_mode(payload: dict, thinking_mode: str) -> None:
    """Translate UI thinking-mode label to ollama-chat payload keys.

    Models like deepseek-v4-flash expose 3 reasoning modes via the chat API:
      - 'fast' → think=False (intuitive, no <thinking> output)
      - 'think' → default (omitted; model decides) — balanced
      - 'deep' → reasoning_effort='high' (max reasoning effort)

    For models that ignore these keys (older Llama, Qwen non-reasoning)
    Ollama silently drops them, so it's safe to always send.
    """
    mode = (thinking_mode or "think").strip().lower()
    if mode == "fast":
        payload["think"] = False
    elif mode == "deep":
        payload["reasoning_effort"] = "high"
    # 'think' (default) → don't add anything; let model use its own default


# Visible-lane num_ctx for ollama. deepseek-v4-flash:cloud supports 1M tokens.
# Now configurable via runtime.json (visible_ollama_num_ctx). The hardcoded
# default here is the fallback when settings aren't loaded yet — it should
# match the default in core.runtime.settings.JarvisSettings.
# Bumped from 256k → 512k on 2026-06-14: doubles the effective context
# window, reduces premature compaction, still well within 1M model capacity.
_VISIBLE_OLLAMA_NUM_CTX = 524_288  # 512k fallback — settings override this

# Visible-lane num_predict (max output tokens). Ollama's default for cloud
# models is restrictive — DeepSeek-v4 (and other reasoners) get cut off
# mid-sentence at ~128–256 tokens. 8192 lets a full coherent answer through
# without wasting anything: the model still stops at its natural EOS, this
# is just a ceiling. Bump if we ever see legitimate truncation again.
# Visible-lane num_predict (max output tokens). Configurable via runtime.json
# (visible_ollama_num_predict). The hardcoded default here is the fallback.
_VISIBLE_OLLAMA_NUM_PREDICT = 16_384


def _apply_visible_ollama_options(payload: dict) -> None:
    """Set ollama generation options for the visible lane.

    num_ctx — input context window. Larger costs more attention memory.
    num_predict — output token cap. Without this, Ollama's defaults can
                  cut DeepSeek/Qwen reasoners off mid-thought.

    Both are now configurable via runtime.json (visible_ollama_num_ctx /
    visible_ollama_num_predict). The module-level constants serve as
    fallback defaults when settings aren't loaded yet.
    """
    from core.runtime.settings import load_settings
    settings = load_settings()
    num_ctx = settings.visible_ollama_num_ctx or _VISIBLE_OLLAMA_NUM_CTX
    num_predict = settings.visible_ollama_num_predict or _VISIBLE_OLLAMA_NUM_PREDICT
    # Model-bevidst loft (Bjørn 2026-06-23): send ALDRIG et num_ctx større end modellens
    # reelle vindue. glm-5.2 er 200k men num_ctx-defaulten var 512k → 2.5× modellens kapacitet
    # (vildledende + spildt attention-allokering). Cap til vinduet; større-vindue-modeller
    # (deepseek-v4-flash 1M) påvirkes ikke. 0/ukendt vindue → behold konfigureret værdi.
    try:
        from core.services.model_context import model_context_window
        _win = int(model_context_window("ollama", str(payload.get("model") or "")) or 0)
        if _win > 0:
            num_ctx = min(int(num_ctx), _win)
    except Exception:
        pass
    options = dict(payload.get("options") or {})
    options.setdefault("num_ctx", num_ctx)
    options.setdefault("num_predict", num_predict)
    payload["options"] = options


# H3 (spec §2): two-stage ollama stream-deadline. Module-level så de er
# overskrivbare i tests (det re-armende inter-byte-watchdog er ellers svært at
# verificere hermetisk uden at vente 30s). FIRST_BYTE = warmup+first-token,
# INTER_BYTE = max-idle MELLEM to linjer når streamen først er i live.
_OLLAMA_FIRST_BYTE_BUDGET_S = 90
_OLLAMA_INTER_BYTE_BUDGET_S = 30


def _stream_ollama_model(
    *,
    message: str,
    model: str,
    session_id: str | None = None,
    controller=None,
    thinking_mode: str = "think",
) -> Iterator[VisibleModelDelta | VisibleModelToolCalls | VisibleModelStreamDone]:
    from core.services.ollama_visible_prompt import (
        serialize_ollama_chat_messages,
    )
    from core.tools.simple_tools import get_tool_definitions

    # 2026-06-13: resolve OLLAMA-providerens base_url — IKKE visible-lanen (som
    # peger på deepseek-API). Ellers POST'er vi ollama-format til deepseek → 401.
    from core.runtime.provider_router import (
        load_provider_router_registry as _lprr,
        _provider_base_url as _pburl,
    )
    base_url = (
        _pburl(provider="ollama", registry=_lprr()) or "http://127.0.0.1:11434"
    ).rstrip("/")

    visible_input = _vm()._build_visible_input(message, session_id=session_id)
    messages = serialize_ollama_chat_messages(visible_input)
    from core.tools.copilot_tool_pruning import select_tools_for_visible
    tools = select_tools_for_visible(
        get_tool_definitions(), user_message=message, session_id=session_id,
    )

    # Model-bevidst sikkerhedsnet: trim ældste historik så den samlede prompt
    # passer i modellens vindue. Uden dette overløber små-vindue-modeller (fx GLM
    # 200k) på lange samtaler → Ollama HTTP 400 "prompt is too long" → tavst svar.
    try:
        from core.services.model_context import fit_messages_to_window
        from core.runtime.settings import load_settings as _ls
        _s = _ls()
        _np = int(_s.visible_ollama_num_predict or 0) or 16_000
        # + headroom (Bjørn 2026-06-23): hold ekstra plads fri ud over output, så
        # transcripten ikke fylder hele vinduet → undgår loop/cut-off på lange sessioner.
        _budget = _np + int(getattr(_s, "visible_context_headroom_tokens", 0) or 0)
        messages, _dropped = fit_messages_to_window(
            messages, provider="ollama", model=model, output_budget=_budget,
        )
        if _dropped:
            logger.warning(
                "visible ollama: trimmede %d ældste beskeder så prompten passer i "
                "%s's kontekstvindue", _dropped, model,
            )
    except Exception:
        pass  # fail-open — hellere et forsøg end ingen

    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    _apply_thinking_mode(payload, thinking_mode)
    _apply_visible_ollama_options(payload)
    if tools:
        payload["tools"] = tools

    prompt_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4

    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    parts: list[str] = []
    reasoning_parts: list[str] = []  # ollama `message.thinking` (thinking-modeller)
    terminal_response = ""
    prompt_eval_count = prompt_estimate
    eval_count = 0
    collected_tool_calls: list[dict] = []

    # Two-stage deadline (same pattern as visible_followup.py):
    #   FIRST_BYTE_BUDGET (90s):  warmup + first-token. Big prompts
    #     legitimately need this. Watchdog thread force-closes the
    #     socket if exceeded → URLError → caller handles.
    #   INTER_BYTE_BUDGET (30s):  per-read deadline once stream is
    #     alive. Mid-stream freeze fails fast instead of waiting full
    #     180s like the previous single-stage timeout did.
    #
    # H3 (spec §2, 2026-06-29): FØR disarmede watchdog'en PERMANENT efter byte 1
    # (``got_first_byte`` blev sat → ``wait`` returnerede → tråden døde). En FRYS
    # MIDT i streamen (mellem to tokens) var derfor UBUNDET — kun en ydre ~180s
    # timeout fangede den til sidst. Nu RE-ARMER watchdog'en på HVER modtaget linje:
    # den tracker ``last_activity`` (monotonic) og force-lukker socketen hvis der går
    # mere end INTER_BYTE_BUDGET_S uden ny linje. Samme force-close-mekanisme som
    # før (r.close() → URLError) → classify_failure ser en transient → komponerer med
    # rund-retry. Ren tilføjelse: control-flow på happy-path er uændret.
    import threading as _threading
    import time as _wd_time
    _facade_vm = _vm()
    FIRST_BYTE_BUDGET_S = _facade_vm._OLLAMA_FIRST_BYTE_BUDGET_S
    INTER_BYTE_BUDGET_S = _facade_vm._OLLAMA_INTER_BYTE_BUDGET_S
    got_first_byte = _threading.Event()
    stream_finished = _threading.Event()  # sættes når loopet er HELT færdigt
    watchdog_response: dict[str, object] = {"resp": None}
    # Monotonic tidsstempel for seneste aktivitet (sat ved hver linje). Læses kun
    # af watchdog-tråden; CPython-attribut-write er atomisk nok til dette formål.
    last_activity: dict[str, float] = {"ts": _wd_time.monotonic()}
    watchdog_fired: dict[str, bool] = {"inter_byte": False}

    def _force_close_stream() -> None:
        r = watchdog_response.get("resp")
        if r is not None:
            try:
                r.close()  # type: ignore[attr-defined]
            except Exception:
                pass

    def _stream_watchdog() -> None:
        # Fase 1: vent på første byte inden FIRST_BYTE_BUDGET_S.
        if not got_first_byte.wait(timeout=FIRST_BYTE_BUDGET_S):
            _force_close_stream()  # første-byte-timeout (uændret adfærd)
            return
        # Fase 2: re-armende inter-byte-deadline. Poll med kort interval; hvis der
        # ikke er kommet en ny linje inden INTER_BYTE_BUDGET_S → force-close.
        poll = min(1.0, float(INTER_BYTE_BUDGET_S))
        while not stream_finished.wait(timeout=poll):
            idle = _wd_time.monotonic() - float(last_activity.get("ts") or 0.0)
            if idle >= INTER_BYTE_BUDGET_S:
                watchdog_fired["inter_byte"] = True
                # H3: gør den ellers-tavse mid-stream-frys MÅLBAR i Centralen FØR
                # vi river socketen ned (den resulterende URLError klassificeres
                # som transient af det højere lag). Self-safe.
                _observe_visible_provider_error(
                    "ollama", model, 0,
                    f"ollama_inter_byte_stall: ingen ny linje i {INTER_BYTE_BUDGET_S}s "
                    f"midt i streamen (idle={idle:.0f}s)")
                _force_close_stream()
                return

    watchdog = _threading.Thread(
        target=_stream_watchdog,
        name="ollama-stream-watchdog",
        daemon=True,
    )
    watchdog.start()

    # Prefill-cache-observabilitet (blind-spot-luk): mål tid fra request→første
    # content-token. Hurtig prefill på en stor prompt ⇒ upstream KV-prefix-cache.
    _t_prefill_start = _wd_time.monotonic()
    _t_first_content: dict[str, float] = {}

    try:
        try:
            response_cm = _facade_vm.urllib_request.urlopen(req, timeout=INTER_BYTE_BUDGET_S)
        except urllib_error.HTTPError as http_exc:
            # urllib's HTTPError-str er bare "HTTP Error 400: Bad Request" — den
            # TABER body'en, hvor Ollama forklarer hvorfor (fx "prompt is too long:
            # 208863, model maximum context length: 202752" for et model-vindue der
            # er mindre end den samlede prompt). Læs body'en + re-raise med den, så
            # friendly_provider_error_message kan give en handlingsanvisende besked.
            try:
                detail = http_exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                detail = ""
            # Stream-cluster (2026-06-23, HUL fundet via Centralen): ollama-lanens HTTP-fejl
            # (særligt 400 "prompt is too long" → ELLERS TAVST svar = "spinner→stop→intet")
            # gik gennem en generisk RuntimeError der IKKE ramte nogen nerve. GLM/deepseek-
            # via-ollama er DEFAULT visible-lane → cut-offs var usynlige for Centralen. Observe nu.
            _observe_visible_provider_error(
                "ollama", model, int(http_exc.code),
                f"Ollama HTTP {http_exc.code}: {detail or http_exc.reason}")
            raise RuntimeError(
                f"Ollama HTTP {http_exc.code}: {detail or http_exc.reason}"
            ) from http_exc
        # A11 (spec §11.1): hærdet NDJSON-parse. saw_done = streamen nåede et
        # terminalt event; saw_malformed = vi sprang ≥1 dårlig chunk over. Hvis
        # streamen slutter uden done EFTER et skip → typed retryable malformed.
        saw_done = False
        saw_malformed = False
        with response_cm as response:
            watchdog_response["resp"] = response
            if controller is not None:
                controller.attach_stream(response)
            for raw_line in response:
                # H3: re-arm inter-byte-deadlinen — hver modtaget linje nulstiller
                # idle-uret, så watchdog'en kun fyrer ved en ÆGTE mid-stream-frys.
                last_activity["ts"] = _wd_time.monotonic()
                if not got_first_byte.is_set():
                    got_first_byte.set()
                # A11 pkt. 1: decode UDEN at rejse (split æøå/emoji → U+FFFD,
                # ikke et dødt stream).
                line = safe_decode_line(raw_line).strip()
                if not line:
                    continue
                # A11 pkt. 2: én malformet NDJSON-linje må IKKE dræbe streamen.
                event, _ok = try_parse_json_line(line)
                if not _ok:
                    # Lone bad chunk på en ellers sund stream → skip + let observe.
                    saw_malformed = True
                    _observe_malformed_stream_payload(
                        "ollama", model, "stream_first_pass",
                        ended_malformed=False, detail=line[:120])
                    continue
                if event is None:
                    continue
                msg = event.get("message") or {}

                delta = str(msg.get("content") or "")
                if delta:
                    if "ts" not in _t_first_content:
                        _t_first_content["ts"] = _wd_time.monotonic()
                    terminal_response = delta
                    parts.append(delta)
                    yield VisibleModelDelta(delta=delta)

                # Thinking-modeller (deepseek-v4/GLM/...) via ollama lægger
                # ræsonneringen i `message.thinking`. Fang den så den FØRSTE
                # rundes reasoning_content kan replayes på followup-runder
                # (ellers mister modellen kontinuitet → tool-spam → tabt svar).
                think = str(msg.get("thinking") or "")
                if think:
                    if "ts" not in _t_first_content:
                        # reasoning-modeller streamer thinking FØR content — det er
                        # stadig efter prefill, så det er et gyldigt første-token-mål.
                        _t_first_content["ts"] = _wd_time.monotonic()
                    reasoning_parts.append(think)

                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    collected_tool_calls.extend(tool_calls)

                if event.get("done"):
                    saw_done = True
                    if not parts and delta:
                        terminal_response = delta
                    prompt_eval_count = int(
                        event.get("prompt_eval_count") or prompt_eval_count
                    )
                    eval_count = int(event.get("eval_count") or eval_count)
                    break
        got_first_byte.set()  # let watchdog exit on early-break
        stream_finished.set()  # H3: stop den re-armende inter-byte-poll
        # A11: streamen sluttede UDEN terminal/done EFTER vi sprang malformet(e)
        # chunk(s) over → trunkeret final-JSON. Bær op som typed retryable, så
        # 4.1's rund-retry kan fange den (i stedet for det generiske "no streamed
        # response" der så ud som en fatal/tom-completion).
        if not saw_done and saw_malformed:
            _observe_malformed_stream_payload(
                "ollama", model, "stream_first_pass", ended_malformed=True,
                detail="stream ended without done after malformed chunk")
            raise MalformedStreamPayload(
                "Ollama stream ended malformed (truncated final JSON)")
    except Exception:
        got_first_byte.set()  # always release watchdog
        stream_finished.set()  # H3: stop den re-armende inter-byte-poll
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise
    finally:
        # H3: garantér at watchdog-tråden ALTID slipper (også ved early return/
        # GeneratorExit), så den ikke kan force-lukke en socket efter vi er færdige.
        got_first_byte.set()
        stream_finished.set()
        if controller is not None:
            controller.clear_stream()

    # Prefill-cache-signal (inferred, ollama-only) → Centralen. Self-safe.
    if "ts" in _t_first_content:
        _observe_visible_prefill(
            "ollama", model,
            prompt_tokens=int(prompt_eval_count or 0),
            prefill_ms=int((_t_first_content["ts"] - _t_prefill_start) * 1000),
        )

    text = "".join(parts).strip()
    if not text:
        text = terminal_response.strip()

    reasoning_text = "".join(reasoning_parts)

    # I1-heal (thinking-felt-parse-hul, spec §11.5): reasoning-modeller (glm-5.2:cloud,
    # deepseek thinking, ...) lægger NOGLE GANGE hele svaret i `message.thinking` mens
    # `message.content` er TOM. FØR raiste vi "returned no streamed response" → empty_
    # completion → brugeren fik fallback i stedet for et svar. Nu: HVIS content-text er
    # tom OG ingen tool_calls MEN thinking har indhold → surface thinking som svaret.
    # FALLBACK, ikke default: når content er til stede, er adfærden UÆNDRET (thinking
    # forbliver reasoning-only til replay, præcis som før). Vi kan ikke altid skelne
    # (a) svar-i-thinking-by-design fra (b) trunkeret stream — begge surfaces (bedre end
    # blankt), men vi fyrer et nerve så det højere lag kan måle/retrye.
    if not text and not collected_tool_calls and reasoning_text.strip():
        text = _strip_thinking_delimiters(reasoning_text)
        _observe_content_empty_thinking_fallback(
            "ollama", model, "stream_first_pass", len(reasoning_text),
        )

    if collected_tool_calls:
        yield VisibleModelToolCalls(tool_calls=collected_tool_calls)

    if not text and not collected_tool_calls:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise RuntimeError("Ollama visible execution returned no streamed response")

    yield VisibleModelStreamDone(
        result=VisibleModelResult(
            text=text or "[tool calls only]",
            input_tokens=prompt_eval_count,
            output_tokens=eval_count or _estimate_tokens(text),
            cost_usd=0.0,
            reasoning_content=reasoning_text,
        )
    )


def _probe_ollama_visible_target(*, model: str, base_url: str) -> dict[str, str | bool]:
    checked_at = datetime.now(UTC).isoformat()
    root = (base_url or "http://127.0.0.1:11434").rstrip("/")
    req = urllib_request.Request(f"{root}/api/tags", method="GET")
    try:
        with urllib_request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        names = {
            str(item.get("name") or "").strip()
            for item in data.get("models", [])
            if isinstance(item, dict)
        }
        if model and model not in names:
            return {
                "provider_reachable": True,
                "live_verified": False,
                "provider_status": "model-not-found",
                "checked_at": checked_at,
            }
        return {
            "provider_reachable": True,
            "live_verified": True,
            "provider_status": "ready",
            "checked_at": checked_at,
        }
    except urllib_error.HTTPError as exc:
        return {
            "provider_reachable": False,
            "live_verified": False,
            "provider_status": f"http-{exc.code}",
            "checked_at": checked_at,
        }
    except urllib_error.URLError:
        return {
            "provider_reachable": False,
            "live_verified": False,
            "provider_status": "unreachable",
            "checked_at": checked_at,
        }


def _build_ollama_prompt(message: str, *, model: str, session_id: str | None) -> str:
    return serialize_ollama_visible_prompt(
        _vm()._build_visible_input(message, session_id=session_id)
    )
