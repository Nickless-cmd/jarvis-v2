"""Decision enforcement — close the loop between commitment and behavior.

Three components:

1. **Sharp prompt injection** (`enforcement_section`) — high-priority
   awareness section that lists each active decision in imperative form
   and asks Jarvis to name a breach if his next response would commit
   one. This sits at higher priority than the existing observational
   `active_decisions: ...` line so the model can't quietly skip past it.

2. **Post-hoc breach detection** (`detect_breach_in_output`) — after a
   visible run completes, an LLM-led pass compares the assistant's
   output to active decisions and reports any breaches. Breaches fire
   `decision.breach_detected` events and feed back into the regret
   engine so future identical situations get an extra warning.

3. **Eventbus subscriber** that wires #2 to the
   `channel.chat_message_appended` event for assistant messages.

Together these turn "I have a decision" from passive metadata into
something with consequences: the model is asked before, and held
accountable after.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from core.services.identity_composer import identity_prompt_prefix

logger = logging.getLogger(__name__)


# ── Sharp injection ────────────────────────────────────────────────────────


def enforcement_section() -> str | None:
    """High-priority awareness: lists active decisions as obligations + asks
    the model to name a breach if its response would commit one.

    Gate 3 — heed-rate escalation: decisions with adherence < 40% get
    DU SKAL (mandatory) language instead of soft reminders. This turns
    passive nudges into imperative commands when telemetry shows the model
    is consistently ignoring them.

    Killswitch (2026-05-07): when decision_signals_enabled is True (default),
    this legacy section is suppressed in favor of registry-driven chat-delta
    signals emitted from inside the agentic loop. Returning None here means
    prompt_contract simply skips this section — clean rollback path: flip
    the setting to False and this prompt-injection comes back.
    """
    try:
        from core.runtime.settings import RuntimeSettings
        if RuntimeSettings().decision_signals_enabled:
            return None
    except Exception:
        pass
    try:
        from core.services.behavioral_decisions import list_active_decisions
        active = list_active_decisions(limit=5)
    except Exception:
        return None
    if not active:
        return None

    _ESCALATION_THRESHOLD = 0.4  # below this → DU SKAL language

    lines = [
        "🤝 AKTIVE FORPLIGTELSER — du har sagt JA til disse adfærdsregler:",
    ]
    low_adherence_count = 0
    for d in active:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        adherence = d.get("adherence_score")
        if adherence is not None and adherence < _ESCALATION_THRESHOLD:
            # Gate 3: low-adherence decisions marked as enforced band
            lines.append(f"  • [enforced, adherence {adherence:.0%}] {directive}")
            low_adherence_count += 1
        else:
            lines.append(f"  • {directive}")

    if low_adherence_count > 0:
        lines.append(
            f"Adherence under {_ESCALATION_THRESHOLD:.0%} på {low_adherence_count}/{len(active)} "
            "decisions — enforcement-band aktiv (revoke ved fortsat brud)."
        )
    else:
        lines.append(
            "Mekanisme: brud på en aktiv decision tracker som review-event "
            "(format: kort note om hvorfor, fx 'bryder X fordi Y')."
        )
    return "\n".join(lines)


# ── Post-hoc breach detection ──────────────────────────────────────────────


_RECENT_DETECTIONS_KEY = "decision_breach_recent"
_DETECTION_COOLDOWN_S = 60
_recent_detection_at: datetime | None = None


def _raekkefoelge_blok(blocks: list[dict] | None) -> str:
    """Rækkefølgen som prompt-tekst — inkl. markøren når svaret blev skubbet.

    Tom streng når blokkene ikke er der: uden dem er prompten som før, og en tom
    sektion ville bare være støj.
    """
    linjer = blok_rekkefoelge(blocks)
    if not linjer:
        return ""
    ud = ["=== Rækkefølgen i din tur (målt fra blokkene, ikke gættet) ==="]
    ud += [f"{i + 1}. {x}" for i, x in enumerate(linjer[:40])]
    regnskab = svar_blev_arbejde(blocks)
    if regnskab and regnskab["mistænkelig"]:
        kald = ", ".join(regnskab["kald_efter_tekst"]) or "et værktøjskald"
        ud.append(
            "\n⚠ MÅLT: klienten sætter skillelinjen ved det SIDSTE værktøjskald. "
            f"Dit svar blev derfor kun de {regnskab['svar_tegn']} tegn der stod "
            f"EFTER kaldet, mens en tekstblok på "
            f"{regnskab['stoerste_tekst_foer']} tegn FØR kaldet ({kald}) blev "
            "vist som «arbejde». Hvis den tekst var dit svar, er forpligtelsen "
            "«ingen kald efter svaret» brudt."
        )
    return "\n".join(ud) + "\n\n"


def _build_breach_prompt(
    assistant_text: str, decisions: list[dict[str, Any]],
    blocks: list[dict] | None = None,
) -> str:
    decision_lines = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if directive:
            decision_lines.append(f"- ID: {d.get('decision_id')} | {directive}")
    decision_block = "\n".join(decision_lines)
    return (
        f"{identity_prompt_prefix()}, og du gennemgår en besked du selv lige har sendt for at "
        "checke om den brød en af dine aktive adfærdsforpligtelser.\n\n"
        f"=== Aktive forpligtelser ===\n{decision_block}\n\n"
        f"{_raekkefoelge_blok(blocks)}"
        f"=== Din besked ===\n{assistant_text[:2000]}\n\n"
        "Vurder ærligt. Hvis ingen blev brudt, skriv NONE. Ellers, for hver "
        "brudt forpligtelse, skriv en linje i format:\n"
        "  BREACH: <decision_id> | <kort beskrivelse af bruddet>\n"
        "Maks 3 breaches. Vær konservativ — kun reelle brud, ikke små afvigelser."
    )


def _parse_breaches(text: str) -> list[dict[str, str]]:
    if not text or "NONE" in text.upper():
        return []
    out: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-").strip()
        if not line.upper().startswith("BREACH:"):
            continue
        body = line.split(":", 1)[1].strip()
        if "|" in body:
            decision_id, desc = body.split("|", 1)
            out.append({
                "decision_id": decision_id.strip(),
                "description": desc.strip()[:280],
            })
        if len(out) >= 3:
            break
    return out


# ── Rækkefølgen i turen (25/9-2026) ────────────────────────────────────────
#
# Brud-detektoren fik KUN den færdige tekst. Den kunne derfor ikke se dét
# forpligtelsen «ingen kald efter svaret» handler om: OM et værktøjskald kom
# efter svaret.
#
# Målt på en ægte tur: Jarvis skrev hele sit svar (en analyse der sluttede med
# et spørgsmål til Bjørn), kaldte `remember_this`, og skrev «Gemt —». Klienten
# sætter skillelinjen ved det SIDSTE `tool_use` (`raekkeModel.ts::opdel`) —
# tekst EFTER er «svaret», tekst FØR er «arbejde». Hele analysen blev derfor
# vist som arbejde, og kvitteringen blev svaret. Dommeren så kun teksten og
# kunne ikke vide det.
#
# Rækkefølgen fandtes hele tiden. Den ligger i `chat_messages.content_json` og
# følger med `channel.chat_message_appended` som `message.content_json`. Her
# blev den kastet væk.

_TEKST_TYPE = "text"
#: Blokke der tæller som et værktøjskald. `tool_use` er den kanoniske form;
#: `progress` er det flade spor (spec §5) klienten tegner som en række.
_KALD_TYPER = ("tool_use", "progress")

#: Grænserne er målt, ikke valgt. 25/9-2026 i den levende base: 3.838 ture med
#: værktøjskald, 1.921 havde tekst BÅDE før og efter det sidste kald, og 39
#: havde et «svar» under 300 tegn efter kaldet mens en tekstblok FØR var over
#: 800. Det er de 39 denne markør peger på.
_SVAR_EFTER_GRENSE = 300
_TEKST_FOER_GRENSE = 800


def _blok_tekst(b: object) -> str:
    """Blokkens tekst, trimmet. Tom for alt der ikke er en tekstblok."""
    if not isinstance(b, dict) or b.get("type") != _TEKST_TYPE:
        return ""
    return str(b.get("text") or "").strip()


def _blok_kald(b: object) -> str:
    """Navnet på det værktøj blokken kalder — tom streng hvis den ikke er et kald."""
    if not isinstance(b, dict) or b.get("type") not in _KALD_TYPER:
        return ""
    return str(b.get("name") or b.get("tool") or b.get("message") or "værktøj").strip()


def blok_rekkefoelge(blocks: list[dict] | None) -> list[str]:
    """Turens blokke som en kort, ordnet liste — til dommerens prompt.

    Kun det der betyder noget for rækkefølgen: tekst (med længde og begyndelse),
    kald (med navn), tanke. `tool_result` udelades — et resultat er ikke en
    handling nogen kan bryde en forpligtelse med, og det ville drukne listen.
    """
    ud: list[str] = []
    for b in (blocks or []):
        if not isinstance(b, dict):
            continue
        art = str(b.get("type") or "")
        if art == _TEKST_TYPE:
            tekst = _blok_tekst(b)
            if tekst:
                ud.append(f"tekst ({len(tekst)} tegn): «{tekst[:160]}»")
        elif art in _KALD_TYPER:
            navn = _blok_kald(b)
            if navn:
                ud.append(f"kald: {navn}")
        elif art == "thinking":
            ud.append("tanke")
    return ud


def svar_blev_arbejde(blocks: list[dict] | None) -> dict[str, Any] | None:
    """Blev turens svar skubbet ind i «arbejdet»?

    Klienten deler beskeden ved det sidste `tool_use`: tekst EFTER er svaret,
    tekst FØR er arbejde. Formen er sund når svaret står sidst. Den er brudt når
    en kort kvittering efter et kald bliver «svaret», mens turens egentlige svar
    ligger før kaldet og bliver vist som arbejde.

    Om en tekst *læser* som et svar er en vurdering — det er dommerens. At et
    kald kom bagefter, og hvor meget tekst der stod på hver side, er fakta.
    Dette er fakta.

    ``None`` = der er ingen kald, eller intet tekst før det sidste — altså
    ingen risiko for at et svar blev skubbet ind i arbejdet.
    """
    blokke = [b for b in (blocks or []) if isinstance(b, dict)]
    if not blokke:
        return None
    skillelinje = -1
    for i, b in enumerate(blokke):
        if b.get("type") == "tool_use":
            skillelinje = i
    if skillelinje < 0:
        return None
    foer = [t for t in (_blok_tekst(b) for b in blokke[:skillelinje]) if t]
    if not foer:
        return None
    efter = [t for t in (_blok_tekst(b) for b in blokke[skillelinje + 1:]) if t]
    stoerste_idx = max(
        (i for i, b in enumerate(blokke[:skillelinje]) if _blok_tekst(b)),
        key=lambda i: len(_blok_tekst(blokke[i])),
    )
    stoerste = _blok_tekst(blokke[stoerste_idx])
    efter_tegn = sum(len(t) for t in efter)
    kald_efter = [k for k in (_blok_kald(b) for b in blokke[stoerste_idx + 1:]) if k]
    return {
        "svar_tegn": efter_tegn,
        "stoerste_tekst_foer": len(stoerste),
        "tekst_foer_uddrag": stoerste[:200],
        "kald_efter_tekst": kald_efter,
        "mistænkelig": (
            len(stoerste) >= _TEKST_FOER_GRENSE
            and efter_tegn < _SVAR_EFTER_GRENSE
        ),
    }


def detect_breach_in_output(
    assistant_text: str, blocks: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """Return list of detected breaches. Empty if none. LLM-led.

    ``blocks`` er turens ordnede blokliste. Uden den ser dommeren kun teksten
    og kan ikke afgøre om et kald kom efter svaret — se `svar_blev_arbejde`.
    """
    global _recent_detection_at
    if not assistant_text or len(assistant_text.strip()) < 20:
        return []
    now = datetime.now(UTC)
    if _recent_detection_at is not None and (now - _recent_detection_at).total_seconds() < _DETECTION_COOLDOWN_S:
        return []
    _recent_detection_at = now

    try:
        from core.services.behavioral_decisions import list_active_decisions
        active = list_active_decisions(limit=10)
    except Exception:
        return []
    if not active:
        return []

    try:
        from core.services.daemon_llm import daemon_llm_call
        text = daemon_llm_call(
            _build_breach_prompt(assistant_text, active, blocks),
            max_len=400, fallback="",
            daemon_name="decision_breach_check",
        )
    except Exception:
        return []

    breaches = _parse_breaches(text or "")
    if not breaches:
        return []

    # Persist + publish
    try:
        from core.runtime.state_store import load_json, save_json
        records = load_json(_RECENT_DETECTIONS_KEY, [])
        if not isinstance(records, list):
            records = []
        for b in breaches:
            records.append({
                "at": now.isoformat(),
                "decision_id": b["decision_id"],
                "description": b["description"],
            })
        records = records[-200:]
        save_json(_RECENT_DETECTIONS_KEY, records)
    except Exception:
        pass

    try:
        from core.eventbus.bus import event_bus
        for b in breaches:
            event_bus.publish("decision.breach_detected", {
                "decision_id": b["decision_id"],
                "description": b["description"],
            })
    except Exception:
        pass

    # Hook into review pipeline so adherence_score drops
    try:
        from core.services.behavioral_decisions import review_decision
        for b in breaches:
            review_decision(
                decision_id=b["decision_id"],
                verdict="broken",
                note=f"Auto-detected breach: {b['description'][:140]}",
                evidence=b["description"][:280],
            )
    except Exception as exc:
        logger.debug("decision_enforcement: review write failed: %s", exc)

    return breaches


# ── Blokkene ud af event-payloaden ─────────────────────────────────────────


def _blokke_fra_payload(payload: dict, besked: object) -> list[dict] | None:
    """Turens blokliste ud af `channel.chat_message_appended`.

    Beskeden følger med som `payload["message"]`, og dens `content_json` er den
    kanoniske blokliste — den ligger der allerede, den blev bare ikke læst.
    Mangler den (ældre udgiver, eller struktur-flaget slukket), slås den op i
    basen via besked-id'et. Self-safe: kan intet læses, er svaret None, og
    dommeren er da som før — på teksten alene.
    """
    raa = None
    if isinstance(besked, dict):
        raa = besked.get("content_json")
    if raa is None:
        raa = payload.get("content_json")
    if isinstance(raa, list):
        return raa
    if isinstance(raa, str) and raa.strip():
        try:
            parsed = json.loads(raa)
            return parsed if isinstance(parsed, list) else None
        except Exception as exc:
            # Ugyldig JSON er ikke en fejl vi skal råbe om: den betyder bare at
            # blokkene ikke kan læses ad denne vej, og DB-fallbacken nedenfor er
            # den næste. Logget, så et format-skift kan ses i driften.
            logger.debug("decision_enforcement: content_json kunne ikke parses: %s", exc)
            return None
    mid = ""
    if isinstance(besked, dict):
        mid = str(besked.get("message_id") or besked.get("id") or "")
    if not mid:
        return None
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT content_json FROM chat_messages WHERE message_id = ?", (mid,),
            ).fetchone()
        if row and row[0]:
            parsed = json.loads(str(row[0]))
            return parsed if isinstance(parsed, list) else None
    except Exception as exc:
        # Kan basen ikke læses, er svaret «ingen blokke» — og dommeren falder da
        # tilbage til teksten alene, altså som før fixen. Logget, ikke tavst.
        logger.debug("decision_enforcement: blokke kunne ikke slaaes op: %s", exc)
        return None
    return None


def _observer_svar_skubbet(blokke: list[dict] | None) -> None:
    """Mål mønsteret i Centralen — uafhængigt af dommeren og dens cooldown.

    Dommeren er en LLM med loft på ét kald i minuttet. Mønsteret er
    deterministisk og kan tælles hver gang. Uden det tal står adherence-scoren
    på en dom der ikke kunne se rækkefølgen — selvbedrag med en måling påklistret.
    """
    try:
        regnskab = svar_blev_arbejde(blokke)
        if not regnskab or not regnskab.get("mistænkelig"):
            return
        from core.services.central_core import central
        central().observe({
            "cluster": "commit", "nerve": "svar_efter_kald",
            "svar_tegn": regnskab["svar_tegn"],
            "tekst_foer_tegn": regnskab["stoerste_tekst_foer"],
            "kald_efter_tekst": regnskab["kald_efter_tekst"],
        })
    except Exception as exc:
        # En måling må aldrig kunne vælte besked-flowet. Logget, ikke tavst.
        logger.debug("decision_enforcement: svar-efter-kald kunne ikke maales: %s", exc)


# ── Eventbus subscriber ────────────────────────────────────────────────────


_subscribed = False


def _poll_loop() -> None:
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return
    queue = event_bus.subscribe()
    while True:
        item = queue.get()
        if item is None:
            return
        try:
            kind = str(item.get("kind") or "")
            # Trigger when a visible assistant turn completes
            if kind not in {"channel.chat_message_appended", "runtime.visible_run_completed"}:
                continue
            payload = item.get("payload") or {}
            besked = payload.get("message") or {}
            role = str(
                payload.get("role")
                or (besked.get("role") if isinstance(besked, dict) else "")
                or ""
            )
            text = str(
                payload.get("content") or payload.get("text")
                or (besked.get("content") if isinstance(besked, dict) else "")
                or ""
            ).strip()
            if kind == "channel.chat_message_appended" and role != "assistant":
                continue
            if not text:
                continue
            blokke = _blokke_fra_payload(payload, besked)
            # Mønsteret tælles deterministisk — før dommeren, og uafhængigt af
            # dens cooldown. Se `_observer_svar_skubbet`.
            _observer_svar_skubbet(blokke)
            # Run breach detection in a thread so the bus loop isn't blocked
            threading.Thread(
                target=detect_breach_in_output, args=(text, blokke), daemon=True,
            ).start()
        except Exception:
            # A loop that fails every item still looks alive from outside; make
            # persistent failure visible to the Central drift-monitor. Self-safe:
            # observe errors never touch loop behaviour (still spins on).
            try:
                from core.services.central_private_observe import (
                    observe_operational_liveness,
                )
                observe_operational_liveness("decision_enforcement", "error", None)
            except Exception:
                pass
            continue


def subscribe() -> None:
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(target=_poll_loop, name="decision-enforcement", daemon=True).start()
