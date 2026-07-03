"""core/services/central_brain_link.py

Tråd 5 (Intelligent Central-spec §7): jarvis-brain DYBT koblet — fra "ser hukommelsen" til "bruger den".

To retninger, begge scope-bundne:
  (M2) Centralen SKRIVER sine egne resolverede hypoteser+udfald tilbage i Jarvis' egen hjerne
       (jarvis_brain, source=brain_memory) → læringen akkumulerer i langtidshukommelsen.
  (M1) Centralen LÆSER relevant kontekst for en formodning — men KUN fra selv-scopede kilder
       (workspace + chronicle). ALDRIG private_brain i cadence (tom scope_uid = rådets hårde grænse).

⚠️ SCOPE-SIKKERHED (rådet, exit-gate):
  * M1-recall rører ALDRIG private_brain uden eksplicit owner-uid (test_m1_scope_bounded).
  * M2-write sker KUN med resolveret owner-attribution (test_m2_write_scoped) — cross-user-skrivning
    er værre end -læsning.
  * Circular-grænse (§7): Fase 1 fodrer IKKE brain-minder tilbage som sampler-evidens (det er hvor
    selv-bekræftelse bider). Brain→sampler-loopet er BEVIDST udeladt; skrives med source-markør så en
    fremtidig sampler kan sætte triggered_by=hyp_id. OBSERVE-ONLY. Kaster ALDRIG.
"""
from __future__ import annotations

import json
from typing import Any

_KIND = "indsigt"                                # gyldig brain-kind; central-læring = en indsigt
_DOMAIN = "central"
_VISIBILITY = "personal"                          # Jarvis' egen viden om sig selv (ikke public_safe)
_RECALL_SOURCES = ("workspace", "chronicle")     # SELV-scopet — ALDRIG private_brain i cadence
_MARK_TAG = "source:brain_memory"
_CENTRAL_TAG = "central"                          # markerer central-læringer (surface tæller på denne)


def _owner_uid() -> str:
    """Resolvér owner-attribution. "" hvis ukendt → M2 skriver IKKE (scope-gate). Self-safe."""
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return (get_owner_discord_id() or "").strip()
    except Exception:
        return ""


def recall_context(query: str, *, limit: int = 3) -> list[dict[str, Any]]:
    """M1: scope-BUNDET selv-recall for en formodning — workspace + chronicle KUN. private_brain
    røres ALDRIG her. Recall sker inde i EKSPLICIT owner-kontekst (så workspace_dir resolver til
    ejerens EGNE kuraterede filer, ikke ambient/ukendt scope — rådets 'privat-lag kun med eksplicit
    owner-uid'). Ingen owner → intet recall (scope-gate). Read-only, self-safe."""
    q = (query or "").strip()
    owner = _owner_uid()
    if not q or not owner:
        return []                                 # SCOPE-GATE: aldrig recall i ambient/ukendt kontekst
    try:
        from core.identity.workspace_context import user_context
        from core.services.memory_recall_engine import multi_signal_recall
        with user_context(discord_id=owner):      # eksplicit owner-attribution
            res = multi_signal_recall(query=q, sources=list(_RECALL_SOURCES),
                                      total_limit=int(limit), with_mood=False)
        out = []
        for r in (res.get("results") or [])[:int(limit)]:
            src = str(r.get("source") or "")
            if src == "private_brain":            # forsvars-i-dybden: dobbelt-værn mod scope-læk
                continue
            out.append({"source": src, "snippet": str(r.get("text") or r.get("title") or "")[:200]})
        return out
    except Exception:
        return []


def _hyp_tag(hyp_id: str) -> str:
    return f"central_hyp:{hyp_id}"


def already_remembered(hyp_id: str) -> bool:
    """Har Centralen allerede skrevet denne hypotese til hjernen? (idempotens via tag). Self-safe."""
    try:
        from core.services.jarvis_brain import connect_index
        tag = _hyp_tag(hyp_id)
        conn = connect_index()
        try:
            row = conn.execute(
                "SELECT 1 FROM brain_index WHERE tags LIKE ? LIMIT 1", (f"%{tag}%",)).fetchone()
        finally:
            conn.close()
        return bool(row)
    except Exception:
        return False


def remember_resolved_hypothesis(hyp: dict[str, Any]) -> str | None:
    """M2: skriv Centralens LÆRING (en resolveret/død hypotese) til jarvis_brain (source=brain_memory).
    Owner-scopet write — skriver ALDRIG uden resolveret owner-attribution. Idempotent. Self-safe."""
    owner = _owner_uid()
    if not owner:
        return None                               # SCOPE-GATE: ingen owner → ingen skrivning
    hyp_id = str(hyp.get("hyp_id") or hyp.get("id") or "").strip()
    if not hyp_id or already_remembered(hyp_id):
        return None
    outcome = str(hyp.get("outcome") or hyp.get("status") or "resolved")
    statement = str(hyp.get("statement") or "").strip()
    notation = str(hyp.get("notation_il") or "").strip()
    source = str(hyp.get("source") or "?")
    verb = {"supported": "BEKRÆFTEDE", "contradicted": "AFKRÆFTEDE",
            "falsified": "FALSIFICEREDE", "dead": "FORKASTEDE"}.get(outcome, "afsluttede")
    content = (f"Centralen {verb} en formodning ({source}): {statement}\n\n"
               f"Udfald: {outcome}." + (f"\nNotation: {notation}" if notation else ""))
    try:
        from core.services.jarvis_brain import write_entry
        new_id = write_entry(
            kind=_KIND, title=f"Central-læring: {statement[:60]}", content=content,
            visibility=_VISIBILITY, domain=_DOMAIN, trigger="reflection_slot",
            tags=[_CENTRAL_TAG, _hyp_tag(hyp_id), _MARK_TAG, f"outcome:{outcome}"],
            importance=0.55)
        return new_id
    except Exception:
        return None


def _recently_resolved(limit: int = 25) -> list[dict[str, Any]]:
    """Resolverede/døde central-hypoteser (kandidater til at blive husket). Self-safe."""
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, source, statement, status, outcome, notation_il "
                "FROM central_hypotheses WHERE status IN ('resolved','dead') "
                "ORDER BY resolved_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def run_brain_link_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: skriv nyligt resolverede central-læringer til hjernen (M2, owner-scopet).
    OBSERVE-ONLY. Egress-fri observe. Self-safe.

    M1-recall (recall_context) er UDSKUDT ud af hot-path'en (3. jul): den er count-only /
    fremtidig-fase (beriger provenance SENERE, forbruges ingen steder nu), MEN multi_signal_recall
    tager ~31s/kald → 25 hyps × 31s ≈ 277s sprængte cadencens 75s-timeout HVER tick → nerven blev
    fejl-flagget uafbrudt. M2-write (idempotent + billig) er det faktisk nyttige arbejde og beholdes.
    Genindfør M1 når (a) en fase faktisk FORBRUGER provenance-konteksten OG (b) multi_signal_recall-
    latensen er fikset (31s er selvstændigt patologisk — separat opgave). recall_context() består +
    er stadig scope-testet (test_m1_scope_bounded)."""
    remembered = 0
    for hyp in _recently_resolved():
        # M2: owner-scopet skrivning tilbage til Jarvis' egen hjerne. Idempotent (already_remembered
        # = indekseret opslag) → allerede-huskede springes billigt over; kun nye resolutioner skrives.
        if remember_resolved_hypothesis(hyp):
            remembered += 1
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "brain_link", value=float(remembered),
                       meta={"remembered": remembered, "owner_scoped": bool(_owner_uid())})
    except Exception:
        pass
    return {"status": "ok", "remembered": remembered}


def register_brain_link_producer() -> None:
    """Registrér Tråd 5 som cadence-producer (~hvert 60 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_brain_link",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=run_brain_link_tick,
        priority=6,
    ))


def build_brain_link_surface() -> dict[str, object]:
    """Mission Control surface — read-only: hvor mange central-læringer bor i hjernen."""
    n = 0
    try:
        from core.services.jarvis_brain import connect_index
        conn = connect_index()
        try:
            # tæl KUN central-læringer (tag), ikke alle 'indsigt'-entries
            row = conn.execute("SELECT COUNT(*) FROM brain_index WHERE tags LIKE ?",
                               (f"%{_MARK_TAG}%",)).fetchone()
            n = int(row[0] or 0) if row else 0
        finally:
            conn.close()
    except Exception:
        pass
    return {"active": True, "central_learnings_in_brain": n, "owner_scoped": bool(_owner_uid())}
