from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, UTC

@dataclass(slots=True)
class Event:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=lambda: datetime.now(UTC))
