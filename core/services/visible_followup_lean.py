"""Lean agentic-round-prompt transform + kill-switch (split from
``visible_followup.py``).

See the module-level commentary below for the design rationale. Everything here
is re-exported from ``core.services.visible_followup`` for backward
compatibility.
"""

from __future__ import annotations

import os


# ── Lean agentic-round-prompt (spec §4.7, I7) ────────────────────────────────
#
# PROBLEM (kode-bekræftet): hver agentisk followup-runde gen-sender HELE den tunge
# assembly-prompt. ``_build_visible_input`` (visible_model.py) flytter den per-turn-
# dynamiske HALE (inder-liv/somatik/mood/diagnostik/awareness/memory-recall/
# digests/finitude/presence) UD af system-beskeden og NED på den SIDSTE bruger-
# besked. Den hale framer KUN det FØRSTE svar — under opgave-eksekvering (runde ≥2)
# er den ren kontekst-bloat: den fortynder vinduet, øger thinking-modellers fejl og
# kan tippe lange/autonome loops over model-vinduet (Ollama 400 "prompt too long" →
# tavst svar).
#
# LEAN-TRANSFORMEN (runde ≥2): behold den LOAD-BEARING kerne, drop den tunge
# berigelse fra den sidste bruger-besked:
#   BEHOLD:  system-beskeden (identitet-kerne + tool-katalog-linje + tool-output-
#            hygiejne — Jarvis' STEMME), HELE samtale-historikken, den oprindelige
#            bruger-opgave, ALLE tool-exchanges (de ligger i ``exchanges``, røres
#            ALDRIG her), og de 2 load-bearing anti-løgn-rækker.
#   DROP:    den per-turn-dynamiske hale (alt fra det første heavy-marker og frem).
#
# De 2 load-bearing anti-løgn-rækker (spec §4.7) BEVARES eksplicit:
#   1. ``⚖️ FØR DU SVARER`` (behavioral anchor) — extraheres fra halen og re-appendes.
#   2. tool-output-hygiejnen (``🔧 TOOL-OUTPUT``) — ligger i SYSTEM-beskeden, som
#      lean-transformen aldrig rører → den overlever automatisk.
#
# Konservativ ved tvivl: kan vi ikke finde halen, sender vi den FULDE besked (lean
# = byte-identisk full i det tilfælde). At miste stemme/anti-løgn er værre end bloat.

# Det første heavy-enrichment-marker halen kan begynde med (rækkefølge fra
# prompt_contract: inder-liv → diagnostik-header → awareness-buffer → …). Det
# FØRSTE der optræder i den sidste bruger-besked markerer hale-grænsen.
_LEAN_TAIL_START_MARKERS: tuple[str, ...] = (
    "[INDRE LIV]",
    "📊 INTERN DIAGNOSTIK",
    "[SELF-MONITOR]",
    "[VERIFICATION]",
    "[REASONING]",
    "[ROUTING]",
    "[MEMORY-RECALL]",
    "[CALIBRATION]",
    "[OPERATIONAL]",
    "[AWARENESS]",
)

# De 2 load-bearing anti-løgn-rækker — bevares ALTID i lean-prompten.
# Behavioral anchor (anti-fabrikation) ligger i halen → extraheres + re-appendes.
# Match på prefiks (teksten efter kan variere let på tværs af versioner).
_LEAN_KEEP_ROW_PREFIXES: tuple[str, ...] = (
    "⚖️ Before you answer",   # behavioral anchor (audit #3, 2026-07-22; was "⚖️ FØR DU SVARER")
)


def _split_on_double_newline(text: str) -> list[str]:
    """Split en sammensat besked i blokke på ``\\n\\n`` (assembly-join-grænsen)."""
    return text.split("\n\n")


def _lean_strip_user_message(text: str) -> tuple[str, bool, int]:
    """Skær den tunge per-turn-hale af ÉN bruger-besked, men bevar de load-bearing
    anti-løgn-rækker. Returnerer ``(lean_text, changed, dropped_chars)``.

    Konservativ: finder vi intet heavy-marker → ``changed=False`` og teksten
    returneres uændret (lean = full). Aldrig en exception ud (caller er hot-loop)."""
    if not text:
        return text, False, 0
    # Find den TIDLIGSTE hale-grænse blandt alle kendte heavy-markers.
    _cut = -1
    for _m in _LEAN_TAIL_START_MARKERS:
        _i = text.find(_m)
        if _i != -1 and (_cut == -1 or _i < _cut):
            _cut = _i
    if _cut == -1:
        return text, False, 0
    _head = text[:_cut].rstrip()
    _tail = text[_cut:]
    # Bevar de load-bearing anti-løgn-rækker fra halen (behavioral anchor).
    _kept_rows: list[str] = []
    for _block in _split_on_double_newline(_tail):
        _b = _block.strip()
        if not _b:
            continue
        for _pref in _LEAN_KEEP_ROW_PREFIXES:
            if _b.startswith(_pref):
                _kept_rows.append(_b)
                break
    _lean = _head
    if _kept_rows:
        _lean = (_head + "\n\n" + "\n\n".join(_kept_rows)).strip() if _head else "\n\n".join(_kept_rows)
    # POST-BETINGELSE (load-bearing honesty-garanti): hver anti-løgn-række der fandtes
    # i originalen SKAL overleve i lean. Hvis en formaterings-finte (fx række glued til
    # en heavy-blok uden dobbelt-newline) ville droppe den → fail-open til FULD prompt.
    # Bloat er bedre end at tabe anti-fabrikations-ankeret midt i et loop.
    for _pref in _LEAN_KEEP_ROW_PREFIXES:
        if _pref in text and _pref not in _lean:
            return text, False, 0
    _dropped = max(0, len(text) - len(_lean))
    return _lean, True, _dropped


def build_lean_base_messages(
    base_messages: list[dict],
) -> tuple[list[dict], dict]:
    """Producér en LEAN udgave af ``base_messages`` til agentiske runder ≥2.

    Drop den tunge per-turn-hale fra den SIDSTE bruger-besked; behold system-
    beskeden (identitet/tools/stemme), historikken, opgaven og de 2 anti-løgn-rækker.
    ``exchanges`` (tool-resultater) ligger UDENFOR ``base_messages`` og røres ALDRIG.

    Returnerer ``(lean_messages, metrics)``. ``metrics`` bærer char-reduktionen
    (før/efter + estimeret token-besparelse) til observe-nerven. Ren funktion —
    muterer ikke input (kopierer den ene besked vi ændrer). Self-safe: enhver
    overraskelse → original messages + ``changed=False`` (fail-open mod bloat,
    ALDRIG mod tab af stemme/anti-løgn)."""
    _before = sum(len(str(m.get("content") or "")) for m in base_messages)
    try:
        if not base_messages:
            return base_messages, {"changed": False, "before_chars": _before,
                                   "after_chars": _before, "dropped_chars": 0}
        # Find INDEKSET på den sidste user-besked (det er den der bærer halen).
        _last_user_idx = -1
        for _i in range(len(base_messages) - 1, -1, -1):
            if str(base_messages[_i].get("role") or "") == "user":
                _last_user_idx = _i
                break
        if _last_user_idx == -1:
            return base_messages, {"changed": False, "before_chars": _before,
                                   "after_chars": _before, "dropped_chars": 0}
        _orig = str(base_messages[_last_user_idx].get("content") or "")
        _lean_text, _changed, _dropped = _lean_strip_user_message(_orig)
        if not _changed:
            return base_messages, {"changed": False, "before_chars": _before,
                                   "after_chars": _before, "dropped_chars": 0}
        # Kopiér KUN den besked vi ændrer; resten deles by-reference (uændret).
        _out = list(base_messages)
        _new_msg = dict(_out[_last_user_idx])
        _new_msg["content"] = _lean_text
        _out[_last_user_idx] = _new_msg
        _after = _before - _dropped
        return _out, {
            "changed": True,
            "before_chars": _before,
            "after_chars": _after,
            "dropped_chars": _dropped,
            # Grov token-heuristik (char/4) — samme som prompt_contract triage.
            "before_tokens": _before // 4,
            "after_tokens": _after // 4,
            "saved_tokens": _dropped // 4,
        }
    except Exception:
        # Fail-open mod bloat — ALDRIG mod tab af stemme/anti-løgn.
        return base_messages, {"changed": False, "before_chars": _before,
                               "after_chars": _before, "dropped_chars": 0}


# ── Kill-switch: AGENTIC_LEAN_PROMPT (spec §4.7, I7) ─────────────────────────
#
# Den ENE sandhedskilde for om lean agentic-round-prompten (runde ≥2) er aktiv.
# DEFAULT OFF (fail-closed) → byte-identisk med i dag (full prompt hver runde).
# Samme dual-læsnings-mønster som ``agentic_round_retry_enabled()``:
#   1. env ``JARVIS_AGENTIC_LEAN_PROMPT`` vinder når sat til en sandheds-værdi.
#   2. ellers runtime-config ``settings.extra["agentic_lean_prompt_enabled"]``.
# At slå lean FRA må ALDRIG slå terminal-frame (I2) eller nerve (I4) fra — flaget
# styrer KUN om halen trimmes på runde ≥2.

_AGENTIC_LEAN_PROMPT_ENV = "JARVIS_AGENTIC_LEAN_PROMPT"

# Delte truthy/falsy-tokens (samme som kill-switch-familien i facaden).
_TRUTHY = ("1", "true", "yes", "on")
_FALSY = ("0", "false", "no", "off")


def agentic_lean_prompt_enabled() -> bool:
    """Er lean agentic-round-prompt (runde ≥2, spec §4.7) slået til? Default False.

    Env-override (``JARVIS_AGENTIC_LEAN_PROMPT``) vinder over runtime-config.
    Selv-sikker: enhver fejl → False (fail-closed → full prompt hver runde)."""
    env_value = os.environ.get(_AGENTIC_LEAN_PROMPT_ENV)
    if env_value is not None:
        val = env_value.strip().lower()
        if val in _TRUTHY:
            return True
        if val in _FALSY:
            return False
        # Ukendt env-værdi → fald tilbage til config (ignorér uparselbart env).
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("agentic_lean_prompt_enabled", False))
    except Exception:
        return False
