"""Syntetisk samtale-prøve: stil et spørgsmål, afbryd Jarvis midt i svaret, mål.

Kører på CT105 i agentens venv. Tester SERVER-kæden (VAD, whisper, Jarvis,
stemme, afbrydelse). Telefonens ekko-dæmpning kan kun prøves med en rigtig
stemme i en rigtig telefon.

    python proeve.py
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
from livekit import api, rtc

KFG = json.loads((Path.home() / ".jarvis-v2/config/runtime.json").read_text())
RUM = f"proeve-{int(time.time())}"
T0 = time.monotonic()


def t() -> str:
    return f"{time.monotonic() - T0:6.2f}s"


def tale(tekst: str, navn: str) -> np.ndarray:
    mp3, wav = f"/tmp/{navn}.mp3", f"/tmp/{navn}.wav"
    subprocess.run(["/opt/conda/envs/ai/bin/edge-tts", "--voice", "da-DK-JeppeNeural", "--text", tekst,
                    "--write-media", mp3], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "48000", "-ac", "1", wav], check=True)
    with wave.open(wav) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


async def afspil(kilde: rtc.AudioSource, lyd: np.ndarray) -> None:
    ramme = 480  # 10 ms
    for i in range(0, len(lyd) - ramme, ramme):
        f = rtc.AudioFrame(lyd[i:i + ramme].tobytes(), 48000, 1, ramme)
        await kilde.capture_frame(f)


async def stilhed(kilde: rtc.AudioSource, sek: float) -> None:
    await afspil(kilde, np.zeros(int(48000 * sek), dtype=np.int16))


async def main() -> None:
    # Billetten udstedes med Jarvis' egen Python — agentens venv har ikke hans
    # afhængigheder (og skal ikke have dem).
    ejer = "1246415163603816499"
    jarvis = subprocess.check_output([
        "/opt/conda/envs/ai/bin/python", "-c",
        "import sys; sys.path.insert(0, '/media/projects/jarvis-v2'); "
        "from core.runtime.jarvisx_auth import issue_token; "
        f"print(issue_token(user_id='{ejer}', role='owner', ttl_seconds=900, extra_claims={{'voice_room': '{RUM}'}})['token'])",
    ], text=True, stderr=subprocess.DEVNULL).strip().splitlines()[-1]

    lk = api.LiveKitAPI("http://127.0.0.1:7880", KFG["livekit_api_key"], KFG["livekit_api_secret"])
    await lk.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
        room=RUM, agent_name="jarvis-stemme", metadata=json.dumps({"session_id": "", "jarvis_token": jarvis})))
    billet = (api.AccessToken(KFG["livekit_api_key"], KFG["livekit_api_secret"]).with_identity("proeve")
              .with_grants(api.VideoGrants(room_join=True, room=RUM)).to_jwt())

    sporgsmaal = tale("Hej Jarvis. Fortæl mig lidt om hvorfor himlen er blå. Tag dig god tid.", "q1")
    afbryd = tale("Stop. Det er fint. Hvad er to plus to?", "q2")

    rum = rtc.Room()
    tilstande: list[tuple[float, str]] = []
    # Seneste tidspunkt Jarvis' LYD var over støjgrænsen. Tilstanden alene lyver:
    # ved en mulig afbrydelse PAUSES lyden straks, men tilstanden skifter først
    # når afbrydelsen er bekræftet.
    lyd_senest = [0.0]

    async def lyt(spor: rtc.RemoteAudioTrack) -> None:
        async for ev in rtc.AudioStream(spor, sample_rate=16000, num_channels=1):
            data = np.frombuffer(ev.frame.data, dtype=np.int16)
            if len(data) and np.sqrt(np.mean(data.astype(np.float32) ** 2)) > 300:
                lyd_senest[0] = time.monotonic()

    @rum.on("track_subscribed")
    def _spor(spor, pub, deltager) -> None:
        if spor.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.ensure_future(lyt(spor))

    @rum.on("participant_attributes_changed")
    def _attr(aendret, deltager) -> None:
        s = deltager.attributes.get("lk.agent.state")
        if s:
            tilstande.append((time.monotonic(), s))
            print(t(), "jarvis:", s, flush=True)

    await rum.connect("ws://127.0.0.1:7880", billet)
    kilde = rtc.AudioSource(48000, 1)
    spor = rtc.LocalAudioTrack.create_audio_track("mic", kilde)
    await rum.local_participant.publish_track(spor, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
    print(t(), "forbundet, venter på agenten", flush=True)
    await stilhed(kilde, 6)

    print(t(), "spørger", flush=True)
    t_sporgsmaal_slut = None
    await afspil(kilde, sporgsmaal)
    t_sporgsmaal_slut = time.monotonic()

    # Hold stilhed indtil han taler (maks 40 s), og lad ham tale 3 s.
    start = time.monotonic()
    while not (tilstande and tilstande[-1][1] == "speaking") and time.monotonic() - start < 40:
        await stilhed(kilde, 0.1)
    if not (tilstande and tilstande[-1][1] == "speaking"):
        print(t(), "FEJL: han begyndte aldrig at tale", flush=True)
    else:
        t_taler = tilstande[-1][0]
        print(t(), f"svartid fra spørgsmålets slutning til stemme: {t_taler - t_sporgsmaal_slut:.2f}s", flush=True)
        await stilhed(kilde, 3)
        print(t(), "afbryder", flush=True)
        t_afbryd = time.monotonic()
        opgave = asyncio.create_task(afspil(kilde, afbryd))
        # Lyden: første øjeblik efter afbrydelsen hvor der har været stille i 300 ms.
        while time.monotonic() - t_afbryd < 10:
            await asyncio.sleep(0.02)
            if time.monotonic() - max(lyd_senest[0], t_afbryd) > 0.3:
                break
        print(t(), f"LYDEN tav efter: {max(lyd_senest[0], t_afbryd) - t_afbryd:.2f}s", flush=True)
        while tilstande[-1][1] == "speaking" and time.monotonic() - t_afbryd < 10:
            await asyncio.sleep(0.02)
        print(t(), f"tilstanden skiftede efter: {time.monotonic() - t_afbryd:.2f}s ({tilstande[-1][1]})", flush=True)
        await opgave
        t_afbryd_slut = time.monotonic()
        start = time.monotonic()
        while not (tilstande[-1][1] == "speaking" and tilstande[-1][0] > t_afbryd_slut) and time.monotonic() - start < 40:
            await stilhed(kilde, 0.1)
        if tilstande[-1][0] > t_afbryd_slut:
            print(t(), f"svar på afbrydelsen efter {tilstande[-1][0] - t_afbryd_slut:.2f}s", flush=True)
        await stilhed(kilde, 6)

    await rum.disconnect()
    await lk.room.delete_room(api.DeleteRoomRequest(room=RUM))
    await lk.aclose()
    print(t(), "færdig", flush=True)


asyncio.run(main())
