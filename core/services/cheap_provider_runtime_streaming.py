from __future__ import annotations

# ── cheap_provider_runtime._streaming ────────────────────────────────────────
# SSE streaming iterators + the OpenAI-Codex Responses-protocol adapter, split
# out of cheap_provider_runtime_adapters.py (Boy-Scout rule, behavior-preserving).
# Holds the OpenAI-compatible /chat/completions streamer, the Codex Responses
# streamer + sync adapter, and their tool-shape/model-listing helpers. Depends on
# the core adapter layer for credentials/http/cost/tool-normalize/DSML helpers.
# Re-exported by the public cheap_provider_runtime facade.
import json
import httpx

from core.services.cheap_provider_runtime_adapters import (
    CheapProviderError,
    _DEFAULT_TIMEOUT_SECONDS,
    _OPENAI_CODEX_PROVIDER,
    _estimate_cheap_cost,
    _estimate_tokens,
    _normalize_tools_for_openai_chat,
    _strip_dsml_leak,
)


def _facade():
    # Resolve monkeypatchable primitives (_require_credentials,
    # provider_runtime_defaults) through the public facade so tests that patch
    # cheap_provider_runtime.<name> reach the streaming adapters too — matching
    # the original single-module behaviour.
    import core.services.cheap_provider_runtime as _f
    return _f


def _iter_openai_compatible_chat_events(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
):
    """Stream OpenAI-compatible /chat/completions deltas via SSE.

    Yields dicts:
      {"kind": "delta", "text": "..."}                   — content token
      {"kind": "tool_call", "id":..., "name":..., "arguments":...}
      {"kind": "done",
       "input_tokens": N, "output_tokens": M,
       "cache_hit_tokens": H, "cache_miss_tokens": MS,
       "full_text": "...", "cost_usd": X}

    Tool-call accumulation: Chat Completions streams tool_calls in
    fragments keyed by index. First fragment usually has id+name+start
    of arguments; subsequent fragments append to arguments. We merge
    by index then yield one tool_call event per index when stream ends.

    stream_options.include_usage=true makes the server send a final
    chunk with full usage stats (incl. Deepseek's prompt_cache_*
    fields) before the [DONE] sentinel.
    """
    credentials = _facade()._require_credentials(profile=auth_profile, provider=provider)
    api_key = str(credentials.get("api_key") or "").strip()
    root = str(base_url or _facade().provider_runtime_defaults(provider).get("base_url") or "").rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        # A4: stabiliser flash model med 1-min vindue. Uden max_tokens kan
        # deepseek-v4-flash generere uendeligt via sit 1M context-vindue.
        # 4096 er rigeligt til en enkelt visible-reply uden at brænde tokens.
        "max_tokens": 4096,
    }
    # Lag 10 Phase 1 (2026-05-12): caller may pass modulated values.
    # When None, omit from payload so server-side defaults apply (cheap-lane
    # callers don't pass them; only visible-lane wrappers do).
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if tools:
        payload["tools"] = _normalize_tools_for_openai_chat(tools)

    # 2026-05-22 (Claude): cache-mystery investigation. When the sentinel file
    # /tmp/jarvis-payload-dump exists, dump full payload JSON to
    # /tmp/jarvis-payload-dumps/payload-<ts>.json so two back-to-back live
    # calls can be byte-diffed to find the cache-breaking content. Provider-
    # gated to deepseek so cheap-lane bursts don't flood the dir.
    try:
        import os as _os
        if provider == "deepseek" and _os.path.exists("/tmp/jarvis-payload-dump"):
            from pathlib import Path as _P
            import time as _t
            _dump_dir = _P("/tmp/jarvis-payload-dumps")
            _dump_dir.mkdir(exist_ok=True)
            _dump_path = _dump_dir / f"payload-{int(_t.time()*1000)}-{model}.json"
            _dump_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, default=str)
            )
    except Exception:
        pass

    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    pending_tool_calls: dict[int, dict] = {}
    final_usage: dict = {}
    # DSML-leak filter (Deepseek v4-pro). The thinking-mode model can spill
    # its internal tool-call DSL ("<｜｜DSML｜｜tool_calls>...</｜｜DSML｜｜tool_calls>")
    # into delta.content before firing the proper structured tool_calls.
    # Without filtering, users see raw special-token markup AND any tool
    # arguments embedded there (which has previously included secrets the
    # model planned to use). Strip the entire block from user-visible
    # deltas. The structured tool_calls.tool_calls path is unaffected.
    _dsml_in_block = False
    _dsml_buffer = ""
    # finish_reason-capture (Bjørn 4. jul, conservation-måling #3): provider-side
    # længde-trunkering (finish_reason=="length") blev ALDRIG tjekket i nogen af de
    # to kodebaser (agent-fund). Fanges nu → surface som conservation-nerve.
    _finish_reason = ""

    try:
        with httpx.stream(
            "POST", f"{root}/chat/completions",
            json=payload, headers=headers,
            timeout=httpx.Timeout(connect=15, read=60, write=15, pool=15),
        ) as response:
            if response.status_code == 401:
                raise CheapProviderError(
                    provider=provider, code="auth-failed",
                    message=f"{provider} API key rejected (HTTP 401)",
                    status_code=401,
                )
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", "60") or "60")
                raise CheapProviderError(
                    provider=provider, code="rate-limited",
                    message=f"{provider} rate limited (HTTP 429)",
                    retry_after_seconds=retry_after, status_code=429,
                )
            if response.status_code >= 400:
                body = b""
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > 2000:
                        break
                raise CheapProviderError(
                    provider=provider, code="provider-error",
                    message=f"HTTP {response.status_code}: {body.decode('utf-8', errors='replace')[:500]}",
                    status_code=response.status_code,
                )
            for line in response.iter_lines():
                line = (line or "").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                # Usage-only chunks (stream_options=include_usage) have
                # empty choices but a populated usage block.
                usage_block = event.get("usage") or {}
                if usage_block:
                    final_usage = dict(usage_block)
                choices = event.get("choices") or []
                if not choices:
                    continue
                _fr = (choices[0] or {}).get("finish_reason")
                if isinstance(_fr, str) and _fr.strip():
                    _finish_reason = _fr.strip()
                delta = (choices[0] or {}).get("delta") or {}
                content = delta.get("content")
                if content:
                    _dsml_buffer += str(content)
                    safe_chunk, _dsml_buffer, _dsml_in_block = _strip_dsml_leak(
                        _dsml_buffer, _dsml_in_block
                    )
                    if safe_chunk:
                        text_parts.append(safe_chunk)
                        yield {"kind": "delta", "text": safe_chunk}
                # Deepseek thinking-mode emits reasoning as separate stream
                # field — capture but don't yield as user-visible delta
                # (UI renders it differently, and we need it for followup
                # replay regardless of UI choice).
                reasoning = delta.get("reasoning_content")
                if reasoning:
                    reasoning_parts.append(str(reasoning))
                    yield {"kind": "reasoning_delta", "text": str(reasoning)}
                tc_fragments = delta.get("tool_calls") or []
                for frag in tc_fragments:
                    if not isinstance(frag, dict):
                        continue
                    idx = int(frag.get("index") or 0)
                    slot = pending_tool_calls.setdefault(
                        idx, {"id": "", "name": "", "arguments": ""}
                    )
                    if frag.get("id"):
                        slot["id"] = str(frag.get("id"))
                    fn = frag.get("function") or {}
                    if fn.get("name"):
                        slot["name"] = str(fn.get("name"))
                    args_frag = fn.get("arguments")
                    if args_frag:
                        slot["arguments"] += str(args_frag)
    except CheapProviderError:
        raise
    except Exception as exc:
        raise CheapProviderError(
            provider=provider, code="stream-error",
            message=f"{provider} streaming failed: {exc}",
        ) from exc

    # Emit accumulated tool calls in index order (consumer expects them
    # before the done event so working_step gets surfaced correctly).
    for idx in sorted(pending_tool_calls.keys()):
        slot = pending_tool_calls[idx]
        if slot.get("name"):
            yield {
                "kind": "tool_call",
                "id": slot.get("id") or f"call_{idx}",
                "name": slot["name"],
                "arguments": slot.get("arguments") or "",
            }

    # ── DSML-TAIL-FLUSH (Bjørn 4. jul — cutoff-spøgelset, first-pass gren) ─────
    # _strip_dsml_leak holder en hale tilbage der KUNNE være starten på DSML-openeren
    # (inkl. et bart "<") og flushede den ALDRIG ved stream-slut → svar der ender på
    # "<" (fx "hvis x < y", en tag/kode-stump) mistede halen fra BÅDE stream og
    # persist → completed-men-afkortet, ingen fejl. Flush residualen (delta + full_text)
    # når vi IKKE er i en ægte uafsluttet DSML-blok. Spejler visible_followup.py-fixet.
    if _dsml_buffer and not _dsml_in_block:
        text_parts.append(_dsml_buffer)
        yield {"kind": "delta", "text": _dsml_buffer}
        _dsml_buffer = ""
    elif _dsml_buffer and _dsml_in_block:
        try:
            from core.services.central_core import central as _central_dsml
            _central_dsml().observe({
                "cluster": "stream", "nerve": "dsml_tail_dropped",
                "provider": str(provider or ""), "model": str(model or ""),
                "residual_len": len(_dsml_buffer), "in_block": True,
            })
        except Exception:
            pass
    # CONSERVATION-MÅLING #3: provider skar svaret af pga. længde (finish_reason=="length").
    # Ikke et tab i VORES lag — men det svar brugeren fik ER ufuldstændigt, og ingen af
    # kodebaserne har nogensinde overfladet det. Gør det synligt så det ikke tælles som
    # et rent "completed". Self-safe, egress-fri.
    if _finish_reason == "length":
        try:
            from core.services.central_core import central as _central_len
            _central_len().observe({
                "cluster": "stream", "nerve": "provider_length_truncation",
                "provider": str(provider or ""), "model": str(model or ""),
                "emitted_chars": len("".join(text_parts)),
                "finish_reason": "length",
            })
        except Exception:
            pass
    full_text = "".join(text_parts)
    input_tokens = int(final_usage.get("prompt_tokens") or final_usage.get("input_tokens") or 0)
    output_tokens = int(final_usage.get("completion_tokens") or final_usage.get("output_tokens") or 0)
    cache_hit = int(final_usage.get("prompt_cache_hit_tokens") or 0)
    cache_miss = int(final_usage.get("prompt_cache_miss_tokens") or 0)
    # ── UNIVERSEL per-kald cache-telemetri (2026-06-30) ──────────────────────
    # DETTE er det punkt ALLE deepseek-streaming-kald passerer (first-pass OG
    # agentiske runder, uanset hvilket højere lag der driver dem) — i modsætning
    # til followup-adapteren der viste sig IKKE at være på deepseeks agentiske sti.
    # Logger prefix-hash + cache pr. kald så vi kan se RUNDE FOR RUNDE om
    # [system,tools]-prefixet er stabilt og cachen holder. Gated på visible tool-
    # tunge kald (tools-sæt ≥ 20) så interne cheap-jobs ikke flooder. Self-safe.
    try:
        if provider == "deepseek" and tools and len(tools) >= 20:
            from core.services.cache_telemetry import (
                prefix_signature, record_visible_cache,
            )
            _sys_c = ""
            for _m in (messages or []):
                if _m.get("role") == "system":
                    _sys_c = str(_m.get("content") or "")
                    break
            _psha, _plen = prefix_signature(_sys_c, tools)
            record_visible_cache(
                lane="visible-call", provider=provider, model=model,
                prefix_sha=_psha, prefix_len=_plen,
                cache_hit=cache_hit, cache_miss=cache_miss,
            )
    except Exception:
        pass
    enriched_usage = dict(final_usage)
    if provider == "deepseek":
        enriched_usage.setdefault("model", model)
    cost_usd = float(_estimate_cheap_cost(provider=provider, usage=enriched_usage))
    yield {
        "kind": "done",
        "full_text": full_text,
        "reasoning_content": "".join(reasoning_parts),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_hit_tokens": cache_hit,
        "cache_miss_tokens": cache_miss,
        "cost_usd": cost_usd,
        "finish_reason": _finish_reason,
    }


def _list_openai_codex_models() -> list[dict[str, object]]:
    """Static model list for OpenAI Codex (ChatGPT Plus OAuth).

    The chatgpt.com/backend-api does not expose a /models endpoint.
    Models are discovered through Codex CLI and documentation.
    """
    static_models = _facade().provider_runtime_defaults(_OPENAI_CODEX_PROVIDER).get(
        "static_models", ["gpt-5.3-codex", "gpt-5.4"]
    )
    return [{"id": m, "label": m} for m in static_models]


def _execute_openai_codex_chat(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    """Execute a chat call via OpenAI's Codex Responses API.

    Uses OAuth bearer token obtained via get_openai_bearer_token() (which
    auto-reimports from ~/.codex/auth.json when the refresh token is stale).
    The endpoint is chatgpt.com/backend-api/codex/responses with SSE streaming.
    """
    from core.auth.openai_oauth import get_openai_bearer_token

    root = str(base_url or "https://chatgpt.com/backend-api").rstrip("/")
    bearer_token = get_openai_bearer_token(profile=auth_profile, auto_reimport=True)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload: dict[str, object] = {
        "model": model,
        "instructions": "You are a helpful assistant. Respond concisely.",
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": message}],
            }
        ],
        "store": False,
        "stream": True,
    }
    # Codex Responses API lives under /codex/responses on chatgpt.com.
    # The plain /responses endpoint requires api.responses.write scope
    # which ChatGPT OAuth tokens don't include. The /codex/responses
    # endpoint accepts ChatGPT Plus OAuth bearer tokens (same path the
    # official Codex CLI uses). See OpenClaw issue #64133.
    url = f"{root}/codex/responses"

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
    except httpx.ConnectError as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="connection-error",
            message=f"Cannot connect to {url}: {exc}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="timeout",
            message=f"Request timed out after {_DEFAULT_TIMEOUT_SECONDS}s",
            retry_after_seconds=60,
        ) from exc

    if response.status_code == 401:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="auth-failed",
            message="OAuth bearer token rejected (HTTP 401). Token may be expired.",
        )
    if response.status_code == 403:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="forbidden",
            message="Access denied (HTTP 403). Account may lack codex scope.",
        )
    if response.status_code == 429:
        retry_after = int(response.headers.get("retry-after", "60") or "60")
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="rate-limited",
            message="Rate limited (HTTP 429)",
            retry_after_seconds=retry_after,
            status_code=429,
        )
    if response.status_code >= 400:
        body = response.text[:500]
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="provider-error",
            message=f"HTTP {response.status_code}: {body}",
            status_code=response.status_code,
        )

    # Parse SSE stream to extract text and usage
    text_parts: list[str] = []
    input_tokens = 0
    output_tokens = 0
    model_used = model

    for line in response.text.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        event_type = str(event.get("type") or "")
        if event_type == "response.output_text.delta":
            delta = str(event.get("delta") or "")
            text_parts.append(delta)
        elif event_type == "response.output_text.done":
            # Full text aggregation event — override accumulated deltas
            full_text = str(event.get("text") or "")
            if full_text:
                text_parts = [full_text]
        elif event_type == "response.completed":
            # Final event with usage and model info
            response_obj = event.get("response") or event.get("result") or {}
            usage = response_obj.get("usage") or {}
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            model_from_response = str(response_obj.get("model") or "").strip()
            if model_from_response:
                model_used = model_from_response

    full_text = "".join(text_parts).strip()
    if not full_text and not text_parts:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="empty-response",
            message="Codex Responses API returned no text content",
        )

    # Fall back to estimation if usage wasn't provided
    if not input_tokens:
        input_tokens = _estimate_tokens(message)
    if not output_tokens:
        output_tokens = _estimate_tokens(full_text)

    return {
        "text": full_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": 0.0,  # Codex via ChatGPT Plus has no per-token billing
        "model_used": model_used,
    }


def _convert_tools_to_responses_format(tools: list[dict] | None) -> list[dict] | None:
    """Convert Chat-Completions tool defs to Responses API format.

    Chat Completions:   {"type":"function", "function":{"name", "description", "parameters"}}
    Responses API:      {"type":"function", "name", "description", "parameters"}

    The Responses API flattens the function fields onto the tool object
    instead of nesting them. Both formats use type="function" but the
    location of name/description/parameters differs.
    """
    if not tools:
        return None
    out: list[dict] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        # Already Responses-shaped
        if "name" in t and "function" not in t:
            out.append(t)
            continue
        fn = t.get("function") or {}
        if not fn:
            continue
        out.append({
            "type": "function",
            "name": str(fn.get("name") or ""),
            "description": str(fn.get("description") or ""),
            "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out or None


def _iter_openai_codex_chat_events(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
    tools: list[dict] | None = None,
    input_items: list[dict] | None = None,
):
    """Stream raw SSE events from the OpenAI Codex Responses API.

    Yields dicts with shape:
      {"kind": "delta", "text": "..."}                — text token
      {"kind": "done", "input_tokens": N,
                       "output_tokens": M,
                       "model_used": "...",
                       "full_text": "..."}            — final event

    Uses httpx.stream() so deltas reach the consumer as the server
    emits them — the previous _execute_openai_codex_chat collects
    the entire response body before parsing, which made the visible
    lane look frozen for 5–30s while gpt-5.4 wrote.

    Caller is responsible for handling CheapProviderError; we raise
    the same shape as the sync version.
    """
    from core.auth.openai_oauth import get_openai_bearer_token

    root = str(base_url or "https://chatgpt.com/backend-api").rstrip("/")
    bearer_token = get_openai_bearer_token(profile=auth_profile, auto_reimport=True)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    # input_items (follow-up): færdigbygget Responses API-input med fuld samtale +
    # function_call/function_call_output-items (tool-replay). Ellers: enkelt user-tur.
    _input: list[dict]
    if input_items is not None:
        _input = list(input_items)
    else:
        _input = [{"role": "user", "content": [{"type": "input_text", "text": message}]}]
    payload: dict[str, object] = {
        "model": model,
        "instructions": "You are a helpful assistant. Respond concisely.",
        "input": _input,
        "store": False,
        "stream": True,
    }
    responses_tools = _convert_tools_to_responses_format(tools)
    if responses_tools:
        payload["tools"] = responses_tools
        # tool_choice: 'auto' lets the model decide; we keep it implicit
        # which Responses API treats as auto when tools are present.
    url = f"{root}/codex/responses"

    text_parts: list[str] = []
    input_tokens = 0
    output_tokens = 0
    model_used = model

    # Tool-call accumulation. Responses API streams a function_call as:
    #   1. response.output_item.added with item.type=='function_call'
    #      → records id + name (arguments may be empty initially)
    #   2. zero or more response.function_call_arguments.delta events
    #      → arguments accumulate as a JSON string
    #   3. response.output_item.done with the same item
    #      → final commit; we yield the tool_call event then
    # We key by item_id (Responses uses a stable id per output item).
    pending_tool_calls: dict[str, dict] = {}
    # Track whether the model emitted any tool call. A tool-call-only response
    # (reasoning models routinely answer a turn purely with a function_call and
    # NO output_text) is valid — we must surface it, not raise "no text content".
    tool_calls_emitted = False

    try:
        with httpx.stream(
            "POST", url, json=payload, headers=headers,
            timeout=httpx.Timeout(_DEFAULT_TIMEOUT_SECONDS, read=None),
        ) as response:
            if response.status_code == 401:
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="auth-failed",
                    message="OAuth bearer token rejected (HTTP 401). Token may be expired.",
                )
            if response.status_code == 403:
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="forbidden",
                    message="Access denied (HTTP 403). Account may lack codex scope.",
                )
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", "60") or "60")
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="rate-limited",
                    message="Rate limited (HTTP 429)",
                    retry_after_seconds=retry_after,
                    status_code=429,
                )
            if response.status_code >= 400:
                # Read the body so we can report something useful
                body_bytes = b""
                for chunk in response.iter_bytes():
                    body_bytes += chunk
                    if len(body_bytes) > 2000:
                        break
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="provider-error",
                    message=f"HTTP {response.status_code}: {body_bytes.decode('utf-8', errors='replace')[:500]}",
                    status_code=response.status_code,
                )

            # Iterate SSE lines as they arrive
            for line in response.iter_lines():
                line = (line or "").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                event_type = str(event.get("type") or "")
                if event_type == "response.output_text.delta":
                    delta = str(event.get("delta") or "")
                    if delta:
                        text_parts.append(delta)
                        yield {"kind": "delta", "text": delta}
                elif event_type == "response.output_text.done":
                    full_text = str(event.get("text") or "")
                    if full_text and not text_parts:
                        # Server didn't emit deltas, only a single done
                        text_parts.append(full_text)
                        yield {"kind": "delta", "text": full_text}
                elif event_type == "response.output_item.added":
                    # New output item — could be a function_call. Record
                    # the id+name so subsequent argument deltas can find it.
                    item = event.get("item") or {}
                    if isinstance(item, dict) and str(item.get("type") or "") == "function_call":
                        item_id = str(item.get("id") or item.get("call_id") or "")
                        name = str(item.get("name") or "")
                        call_id = str(item.get("call_id") or item_id)
                        if item_id and name:
                            pending_tool_calls[item_id] = {
                                "id": call_id,
                                "name": name,
                                "arguments": str(item.get("arguments") or ""),
                            }
                            yield {
                                "kind": "tool_call_start",
                                "id": call_id,
                                "name": name,
                            }
                elif event_type == "response.function_call_arguments.delta":
                    item_id = str(event.get("item_id") or "")
                    delta = str(event.get("delta") or "")
                    if item_id in pending_tool_calls and delta:
                        pending_tool_calls[item_id]["arguments"] += delta
                elif event_type == "response.function_call_arguments.done":
                    # Final aggregate — overrides accumulated args if provided
                    item_id = str(event.get("item_id") or "")
                    final_args = str(event.get("arguments") or "")
                    if item_id in pending_tool_calls and final_args:
                        pending_tool_calls[item_id]["arguments"] = final_args
                elif event_type == "response.output_item.done":
                    item = event.get("item") or {}
                    if isinstance(item, dict) and str(item.get("type") or "") == "function_call":
                        item_id = str(item.get("id") or item.get("call_id") or "")
                        if item_id in pending_tool_calls:
                            tc = pending_tool_calls.pop(item_id)
                            # Some servers include the final arguments here too
                            final_args = str(item.get("arguments") or "") or tc["arguments"]
                            tool_calls_emitted = True
                            yield {
                                "kind": "tool_call",
                                "id": tc["id"],
                                "name": tc["name"],
                                "arguments": final_args,
                            }
                elif event_type == "response.completed":
                    response_obj = event.get("response") or event.get("result") or {}
                    usage = response_obj.get("usage") or {}
                    input_tokens = int(usage.get("input_tokens") or 0)
                    output_tokens = int(usage.get("output_tokens") or 0)
                    model_from_response = str(response_obj.get("model") or "").strip()
                    if model_from_response:
                        model_used = model_from_response
    except httpx.ConnectError as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="connection-error",
            message=f"Cannot connect to {url}: {exc}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="timeout",
            message=f"Request timed out after {_DEFAULT_TIMEOUT_SECONDS}s",
            retry_after_seconds=60,
        ) from exc

    full_text = "".join(text_parts).strip()
    # Only a genuinely empty response (no text AND no tool call) is an error.
    # A tool-call-only turn is valid output for reasoning models — surfacing the
    # tool_call above is the answer; we still emit 'done' so the consumer closes.
    if not full_text and not text_parts and not tool_calls_emitted:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="empty-response",
            message="Codex Responses API returned no text content",
        )

    if not input_tokens:
        input_tokens = _estimate_tokens(message)
    if not output_tokens:
        output_tokens = _estimate_tokens(full_text)

    yield {
        "kind": "done",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_used": model_used,
        "full_text": full_text,
    }
