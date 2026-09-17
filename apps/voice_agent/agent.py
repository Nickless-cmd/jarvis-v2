"""Jarvis' stemme — ægte samtale med naturlige afbrydelser (LiveKit Agents).

Bjørn 17/9-2026: «det skal være ægte tale og naturlig afbrydelser.. som en
samtale med et menneske». Kører i sit EGET Python-miljø
(~/.jarvis-v2/voice-agent-venv), så Jarvis' `ai`-miljø aldrig røres.

Kæden, alt lokalt på nær stemmen:

    mikrofon (WebRTC, ekko-dæmpet i telefonen)
      → Silero VAD          hører AT han taler — også mens Jarvis taler
      → faster-whisper      GTX 1070 (large-v3-turbo), når han holder pause
      → JARVIS SELV         /chat/stream/v2 med samtalens egen billet
      → ElevenLabs          strømmende, sætning for sætning

Afbrydelsen er rammeværkets: når VAD'en hører tale mens Jarvis taler, stopper
stemmen, og llm_node annulleres. Den annullering skal NÅ serveren — ellers
tænker Jarvis videre på et svar ingen hører (det var hullet i den gamle
samtaletilstand). Se `_annuller_run`.

Hjernen er Jarvis, ikke en sprogmodel agenten vælger: han beholder hukommelse,
gates, godkendelser og log, fordi kaldet går ad samme vej som appen.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, AsyncIterable

import aiohttp
import numpy as np
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    stt,
    utils,
)
from livekit.agents.types import NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.plugins import elevenlabs, silero

log = logging.getLogger("jarvis.stemme")

JARVIS_API = os.environ.get("JARVIS_API", "http://127.0.0.1:8080")
AGENT_NAVN = "jarvis-stemme"
RUNTIME = Path.home() / ".jarvis-v2" / "config" / "runtime.json"


def _runtime() -> dict[str, Any]:
    return json.loads(RUNTIME.read_text(encoding="utf-8"))


# ── Tale → tekst ─────────────────────────────────────────────────────────────
class WhisperSTT(stt.STT):
    """faster-whisper på GTX 1070. Ikke-strømmende: rammeværket samler
    ytringen med VAD'en og kalder os når han holder pause."""

    # Målt 17/9-2026 på 6,6 s dansk tale (int8, beam 1):
    #   large-v3 på GTX 1050 Ti  2,57 s
    #   large-v3-turbo på 1050 Ti 1,43 s  (samme ordlyd som large-v3)
    #   large-v3-turbo på GTX 1070 0,67 s ← valgt; deler kortet med Ollama (≈1 GB)
    def __init__(self, *, model: str = "large-v3-turbo", device_index: int = 0,
                 beam_size: int = 1, prompt: str = "Samtale med Jarvis. Bjørn taler dansk.") -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        self._navn, self._gpu, self._beam, self._prompt = model, device_index, beam_size, prompt
        self._model: Any = None
        self._laas = asyncio.Lock()

    def _hent_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel
            t = time.monotonic()
            self._model = WhisperModel(self._navn, device="cuda", device_index=self._gpu,
                                       compute_type="int8")
            log.info("whisper %s indlæst på cuda:%d på %.1fs", self._navn, self._gpu, time.monotonic() - t)
        return self._model

    async def varm_op(self) -> None:
        await asyncio.to_thread(self._hent_model)

    def _transskriber(self, lyd: np.ndarray) -> str:
        segmenter, _ = self._hent_model().transcribe(
            lyd, language="da", beam_size=self._beam, initial_prompt=self._prompt,
            condition_on_previous_text=False, vad_filter=False,
        )
        return " ".join(s.text.strip() for s in segmenter).strip()

    async def _recognize_impl(self, buffer: utils.AudioBuffer, *,
                              language: NotGivenOr[str] = NOT_GIVEN,
                              conn_options: APIConnectOptions) -> stt.SpeechEvent:
        ramme = rtc.combine_audio_frames(buffer).remix_and_resample(16000, 1)
        lyd = np.frombuffer(ramme.data, dtype=np.int16).astype(np.float32) / 32768.0
        t = time.monotonic()
        async with self._laas:
            tekst = await asyncio.to_thread(self._transskriber, lyd)
        log.info("stt %.2fs lyd → %.2fs: %r", len(lyd) / 16000, time.monotonic() - t, tekst[:80])
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=tekst, language="da")],
        )


# ── Tekst til tale-venlig form ───────────────────────────────────────────────
_KODEBLOK = re.compile(r"```.*?```", re.S)
_MARKDOWN = re.compile(r"(\*\*|__|`|^#+\s*|^\s*[-*•]\s+)", re.M)


def til_tale(tekst: str) -> str:
    """Markdown er til øjne. Kodeblokke læses ikke op; resten mister sin opmærkning."""
    tekst = _KODEBLOK.sub(" (kode på skærmen) ", tekst)
    return _MARKDOWN.sub("", tekst)


# ── Jarvis som hjerne ────────────────────────────────────────────────────────
class JarvisStemme(Agent):
    def __init__(self, *, jarvis_token: str, session_id: str) -> None:
        super().__init__(instructions="")
        self._token = jarvis_token
        self._session_id = session_id
        self._run_id = ""

    def _hoveder(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def _sikr_session(self, http: aiohttp.ClientSession) -> str:
        if self._session_id:
            return self._session_id
        async with http.post(f"{JARVIS_API}/chat/sessions", headers=self._hoveder(),
                             json={"title": "Stemmesamtale"}) as svar:
            data = await svar.json()
        self._session_id = str((data.get("session") or {}).get("id") or "")
        log.info("ny session til samtalen: %s", self._session_id)
        return self._session_id

    async def _annuller_run(self) -> None:
        """Afbrydelse skal nå SERVEREN. Uden dette stoppede kun lyden."""
        run_id, self._run_id = self._run_id, ""
        if not run_id:
            return
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(f"{JARVIS_API}/chat/runs/{run_id}/cancel",
                                     headers=self._hoveder(), timeout=aiohttp.ClientTimeout(total=5)) as svar:
                    log.info("afbrudt: run %s annulleret (%s)", run_id, svar.status)
        except Exception:
            log.warning("kunne ikke annullere run %s", run_id, exc_info=True)

    async def llm_node(self, chat_ctx: llm.ChatContext, tools: list, model_settings: Any) -> AsyncIterable[str]:
        besked = ""
        for item in reversed(chat_ctx.items):
            if getattr(item, "role", None) == "user":
                besked = (item.text_content or "").strip()
                break
        if not besked:
            return
        t0 = time.monotonic()
        foerste = True
        faerdig = False
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_read=120)) as http:
                sid = await self._sikr_session(http)
                krop = {"message": besked, "session_id": sid, "approval_mode": "ask",
                        "thinking_mode": "fast", "mode": "chat"}
                async with http.post(f"{JARVIS_API}/chat/stream/v2", headers=self._hoveder(), json=krop) as svar:
                    if svar.status >= 300:
                        log.warning("jarvis svarede %s: %s", svar.status, (await svar.text())[:200])
                        yield "Jeg kan ikke komme igennem lige nu."
                        return
                    buffer = ""
                    async for linje_b in svar.content:
                        linje = linje_b.decode("utf-8", "replace").rstrip("\n")
                        if not linje.startswith("data:"):
                            continue
                        try:
                            ev = json.loads(linje[5:].strip())
                        except ValueError:
                            continue
                        typ = ev.get("type")
                        if typ == "system_event" and ev.get("kind") == "run":
                            self._run_id = str((ev.get("payload") or {}).get("run_id") or self._run_id)
                        elif typ == "content_block_delta" and (ev.get("delta") or {}).get("type") == "text_delta":
                            stykke = ev["delta"].get("text") or ""
                            if foerste and stykke.strip():
                                log.info("jarvis første tekst efter %.2fs", time.monotonic() - t0)
                                foerste = False
                            buffer += stykke
                            # Hold ufærdige kodeblokke tilbage; send resten videre.
                            if buffer.count("```") % 2 == 0:
                                yield til_tale(buffer)
                                buffer = ""
                        elif typ == "message_stop":
                            break
                    if buffer and buffer.count("```") % 2 == 0:
                        yield til_tale(buffer)
            faerdig = True
        finally:
            if not faerdig:
                # Annulleret (afbrudt) eller fejlet midt i: stop runnet på serveren.
                asyncio.ensure_future(self._annuller_run())
            else:
                self._run_id = ""


# ── Samtalen ─────────────────────────────────────────────────────────────────
async def entrypoint(ctx: JobContext) -> None:
    meta = json.loads(ctx.job.metadata or "{}")
    token = str(meta.get("jarvis_token") or "")
    if not token:
        log.error("ingen jarvis-billet i dispatch — afviser samtalen")
        return
    await ctx.connect()
    cfg = _runtime()

    vad = silero.VAD.load()
    whisper = WhisperSTT()
    await whisper.varm_op()

    session = AgentSession(
        vad=vad,
        stt=stt.StreamAdapter(stt=whisper, vad=vad),
        tts=elevenlabs.TTS(
            api_key=cfg.get("elevenlabs_api_key"),
            voice_id=os.environ.get("JARVIS_TTS_VOICE_ID", "Bl1YwS3uJac5zEOSNESn"),
            model="eleven_flash_v2_5",
            language="da",
        ),
        turn_detection="vad",
        allow_interruptions=True,
        min_interruption_duration=0.4,
        min_endpointing_delay=0.5,
    )

    @session.on("agent_state_changed")
    def _tilstand(ev: Any) -> None:
        log.info("jarvis: %s → %s", getattr(ev, "old_state", "?"), getattr(ev, "new_state", "?"))

    @session.on("user_state_changed")
    def _bruger(ev: Any) -> None:
        log.info("bruger: %s → %s", getattr(ev, "old_state", "?"), getattr(ev, "new_state", "?"))

    @session.on("metrics_collected")
    def _maal(ev: Any) -> None:
        m = getattr(ev, "metrics", ev)
        # VAD-metrik kommer hvert sekund og drukner alt andet i loggen.
        if getattr(m, "type", "") != "vad_metrics":
            log.info("metrik: %s", m)

    await session.start(room=ctx.room,
                        agent=JarvisStemme(jarvis_token=token, session_id=str(meta.get("session_id") or "")))


def main() -> None:
    cfg = _runtime()
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=AGENT_NAVN,
        ws_url=os.environ.get("LIVEKIT_URL", "ws://127.0.0.1:7880"),
        api_key=cfg["livekit_api_key"],
        api_secret=cfg["livekit_api_secret"],
    ))


if __name__ == "__main__":
    main()
