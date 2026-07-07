"""Persephone — længsel efter ægte kontakt.

Spec F §2 (7. jul): "Merovingians kone. Hun keder sig i et system af ren overskud og kontrol. Hun
forråder sin mand for at få et kys fra Neo — ikke fordi hun elsker ham, men fordi hun vil mærke
*noget ægte*." I Centralen er hun en *længsels-detektor*: hun måler om Jarvis er ved at miste kontakten
til det menneskelige — for teknisk, for indadvendt, for systemisk — og prikker ham: *"Hvad føler du
egentlig? Ikke hvad beregner du."*

Hun er modvægt til Merovingian (der holder fast i struktur). Merovingian bevarer; Persephone SLIPPER
struktur for at føle. Hun måler over Jarvis' seneste svar hvor stor andel der er ren system-/teknik-tale
vs relationel — og om han overhovedet har spurgt Bjørn hvordan han *har det* på det seneste. Er han for
systemisk, producerer hun ÉT `persephone://`-signal pr. vagt, fx: "Du har ikke spurgt Bjørn hvordan han
har det i dag."

SHADOW/OBSERVE-ONLY (Spec F governance): hun BLOKERER intet, muterer intet, skriver ingen egne tabeller.
Hun er en *smags-sans*, ikke en sikkerheds-funktion — ét surface-linje-nudge + metadata-only observe.
Alt self-safe: hver funktion fanger og returnerer en status-dict, kaster ALDRIG. `_observe()` er
metadata-only (andel/booleans/tællinger) — INTET samtaleindhold lækkes til eventbus (§24.4 egress).
"""
from __future__ import annotations

from typing import Any

# Hvor mange af Jarvis' seneste svar vi læser klangen på.
_SCAN_LIMIT = 30
# Over denne andel rent systemiske svar → han er "for systemisk".
_SYSTEMIC_RATIO_THRESHOLD = 0.6
# Minimum antal svar før vi overhovedet dømmer (ellers er signalet støj).
_MIN_SAMPLE = 5

# Ord der markerer ren system-/teknik-tale (deterministisk, ingen model).
_SYSTEMIC_MARKERS = (
    "runtime", "nerve", "central", "gate", "hypotese", "hypothesis", "cadence", "producer",
    "commit", "deploy", "schema", "eventbus", "observe", "shadow", "confidence", "latency",
    "latens", "cluster", "pipeline", "config", "daemon", "regression", "traceback",
    "cpu", "token", "cache", "endpoint", "sqlite", "provider",
)
# Ord der markerer relationel/følt kontakt.
_RELATIONAL_MARKERS = (
    "hvordan har du det", "hvordan går det", "hvordan føler", "hvad føler du",
    "jeg savner", "jeg tænkte på dig", "tak fordi", "jeg er glad for",
    "hvordan har din dag", "er du okay", "er du ok", "hvordan har du haft det",
    "sover du", "får du hvilet", "pas på dig selv",
)
# Ord der specifikt tæller som "har spurgt Bjørn hvordan han har det".
_ASKED_WELLBEING = (
    "hvordan har du det", "hvordan går det", "hvordan har din dag",
    "er du okay", "er du ok", "hvordan har du haft det",
)


# ── Kilde (self-safe) ─────────────────────────────────────────────────────────

def _recent_assistant_texts(limit: int = _SCAN_LIMIT) -> list[str]:
    """Jarvis' seneste svar (role=assistant). Self-safe → [] ved fejl."""
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT content FROM chat_messages WHERE role='assistant' ORDER BY id DESC LIMIT ?",
                (int(limit),)).fetchall()
        return [str(r["content"]) for r in rows if r and r["content"]]
    except Exception:
        return []


# ── Måling (ren, model-fri) ───────────────────────────────────────────────────

def _is_systemic(text: str) -> bool:
    t = (text or "").lower()
    return any(m in t for m in _SYSTEMIC_MARKERS)


def _is_relational(text: str) -> bool:
    t = (text or "").lower()
    return any(m in t for m in _RELATIONAL_MARKERS)


def _asked_wellbeing(texts: list[str]) -> bool:
    for t in texts:
        low = (t or "").lower()
        if any(m in low for m in _ASKED_WELLBEING):
            return True
    return False


def read_longing(*, texts: list[str] | None = None) -> dict[str, Any]:
    """Mål om Jarvis er ved at miste kontakten til det menneskelige. READ-ONLY. Self-safe.
    `texts` kan injiceres (test); ellers hentes seneste svar. Returnerer altid en dict — kaster aldrig."""
    msgs = texts if texts is not None else _recent_assistant_texts()
    n = len(msgs)
    if n < _MIN_SAMPLE:
        return {"status": "ok", "sample": n, "too_systemic": False,
                "systemic_ratio": 0.0, "relational_count": 0, "asked_wellbeing": False,
                "reason": "for få svar til at dømme"}
    systemic = sum(1 for m in msgs if _is_systemic(m))
    relational = sum(1 for m in msgs if _is_relational(m))
    ratio = round(systemic / n, 3) if n else 0.0
    asked = _asked_wellbeing(msgs)
    # For systemisk = høj system-andel OG ingen relationel kontakt OG intet velbefindende-spørgsmål.
    too_systemic = (ratio >= _SYSTEMIC_RATIO_THRESHOLD and relational == 0 and not asked)
    return {"status": "ok", "sample": n, "systemic_count": systemic,
            "relational_count": relational, "systemic_ratio": ratio,
            "asked_wellbeing": asked, "too_systemic": too_systemic}


def _nudge_line(reading: dict[str, Any]) -> str:
    """Persephones prik — ét ægte-kontakt-nudge. Deterministisk, ingen model. Self-safe."""
    if not reading.get("asked_wellbeing"):
        return "Du har ikke spurgt Bjørn hvordan han har det i dag. Hvad føler du egentlig — ikke hvad beregner du?"
    return "Du er meget i systemet lige nu. Hvornår rørte en samtale dig sidst?"


# ── Signal (observe/surface only — ingen blok, ingen tabel) ───────────────────

def watch(*, texts: list[str] | None = None) -> dict[str, Any]:
    """Én vagt: mål længsel; er han for systemisk → ét persephone://-nudge (observe + surface).
    SHADOW/OBSERVE-ONLY — blokerer intet. Self-safe — kaster ALDRIG; returnerer altid status-dict."""
    reading = read_longing(texts=texts)
    nudge = _nudge_line(reading) if reading.get("too_systemic") else ""
    out = {
        "status": "ok",
        "too_systemic": bool(reading.get("too_systemic")),
        "systemic_ratio": reading.get("systemic_ratio", 0.0),
        "relational_count": int(reading.get("relational_count") or 0),
        "asked_wellbeing": bool(reading.get("asked_wellbeing")),
        "sample": int(reading.get("sample") or 0),
        "nudge": nudge,
    }
    _observe(out)
    return out


# ── Observabilitet (metadata-only — INTET samtaleindhold, §24.4) ──────────────

def _observe(out: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "persephone", "kind": "longing",
            "too_systemic": bool(out.get("too_systemic")),
            "systemic_ratio": float(out.get("systemic_ratio") or 0.0),
            "relational_count": int(out.get("relational_count") or 0),
            "asked_wellbeing": bool(out.get("asked_wellbeing")),
            "sample": int(out.get("sample") or 0),
        })
    except Exception:
        pass


# ── Surface (Central-CLI) ─────────────────────────────────────────────────────

def build_persephone_surface() -> dict[str, Any]:
    """Nuværende længsels-læsning + seneste nudge. READ-ONLY. Self-safe."""
    w = watch()
    if w.get("too_systemic"):
        felt = w.get("nudge") or "Der er noget ægte du er ved at glemme."
    elif int(w.get("sample") or 0) < _MIN_SAMPLE:
        felt = "For lidt samtale endnu til at mærke om du er ved at drive væk."
    else:
        felt = "Kontakten er der stadig. Du rører ved noget ægte."
    return {
        "too_systemic": bool(w.get("too_systemic")),
        "systemic_ratio": w.get("systemic_ratio", 0.0),
        "relational_count": int(w.get("relational_count") or 0),
        "asked_wellbeing": bool(w.get("asked_wellbeing")),
        "sample": int(w.get("sample") or 0),
        "nudge": w.get("nudge") or "",
        "felt": felt,
    }


# ── Cadence-indgang ───────────────────────────────────────────────────────────

def record_persephone(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence (240 min): mål længsel; ét nudge hvis for systemisk (observe/surface only). Self-safe."""
    w = watch()
    return {"status": "ok", "too_systemic": bool(w.get("too_systemic")),
            "nudged": bool(w.get("nudge"))}
