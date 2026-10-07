"""Wire-protokollen mellem serverens broker og en sandboxet agent-worker (C6b).

Linjebaseret JSON over en unix-socketpair (den ene ende arves af workeren som en fd; der er
INTET netvaerk i sandboxen). Kun standardbiblioteket: modulet bindes ind i sandboxen som en
enkelt fil. Rammestoerrelsen er begraenset i begge retninger, og en misdannet ramme er en
``ProtocolError`` - aldrig en tavs fortolkning.
"""
from __future__ import annotations

import json
import select
import socket
from typing import Any

#: Stoerste ramme (bytes). Et modelsvar eller et vaerktoejsresultat er sjaeldent over et par hundrede KB.
MAX_FRAME = 8 * 1024 * 1024


class ProtocolError(Exception):
    """Misdannet eller for stor ramme."""


class FrameTooLarge(ProtocolError):
    pass


def send(sock: socket.socket, obj: dict[str, Any]) -> None:
    data = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8") + b"\n"
    if len(data) > MAX_FRAME:
        raise FrameTooLarge(f"ramme paa {len(data)} bytes over graensen {MAX_FRAME}")
    sock.sendall(data)


class FrameReader:
    """Laeser rammer ét ad gangen. ``read(timeout)`` giver ``None`` ved timeout, hæver ``EOFError``
    naar den anden ende er lukket, og ``ProtocolError`` ved en ugyldig eller for stor ramme."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._buf = bytearray()

    def read(self, timeout: float | None = None) -> dict[str, Any] | None:
        while True:
            nl = self._buf.find(b"\n")
            if nl >= 0:
                line = bytes(self._buf[:nl])
                del self._buf[:nl + 1]
                try:
                    obj = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, ValueError) as exc:
                    raise ProtocolError(f"ugyldig ramme: {exc}") from exc
                if not isinstance(obj, dict):
                    raise ProtocolError("rammen er ikke et objekt")
                return obj
            if len(self._buf) > MAX_FRAME:
                raise FrameTooLarge("ramme over graensen uden linjeskift")
            ready, _, _ = select.select([self._sock], [], [], timeout)
            if not ready:
                return None
            chunk = self._sock.recv(65536)
            if not chunk:
                raise EOFError("forbindelsen er lukket")
            self._buf += chunk
