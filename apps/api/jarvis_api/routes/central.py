"""Real-time Central-vindue til owner (jarvis-desk code mode).

Owner-only: Centralen er kontrol-/observabilitets-planen — kun ejeren følger nervesystemet
live. Tynd route; det blokerende arbejde (DB-læsninger) kører via asyncio.to_thread så
--workers 1-API'et ikke fryser. Snapshot polles af desk-panelet (~1-2s).
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/central", tags=["central"])


def _rec_to_item(r) -> dict:
    """TraceRecord → kompakt feed-item (samme form som snapshot-feed'en)."""
    from core.services.central_catalog import is_security_cluster
    cluster = str(getattr(r, "cluster", "") or "")
    sec = False
    try:
        sec = bool(is_security_cluster(cluster))
    except Exception:
        pass
    return {
        "cluster": cluster, "nerve": str(getattr(r, "nerve", "") or ""),
        "kind": str(getattr(r, "kind", "") or ""),
        "decision": str(getattr(r, "decision", "") or ""),
        "reason": str(getattr(r, "reason", "") or "")[:120],
        "run_id": str(getattr(r, "run_id", "") or ""), "security": sec,
    }


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


# HUD'en poller dette hvert sekund (målt 310 kald/5 min). Snapshottet koster
# 78ms, så ucachet brændte det 24% af al poll-belastning. 2s er stadig "live"
# for et øje, men halverer arbejdet — og cache_age_ms fortæller sandheden om
# hvor gammelt tallet er i stedet for at lade som om.
_REALTIME_TTL_S = 2.0


@router.get("/realtime")
async def central_realtime() -> dict:
    """Ét snapshot af Centralens live-tilstand (puls/feed/flag/læring)."""
    _require_owner()
    from core.services.central_projection_cache import cached
    from core.services.central_realtime import realtime_snapshot

    snap, age_s = await asyncio.to_thread(
        cached, "central:realtime", _REALTIME_TTL_S, realtime_snapshot)
    if isinstance(snap, dict):
        return {**snap, "cache_age_ms": int(age_s * 1000)}
    return snap


@router.get("/timeseries")
async def central_timeseries_merged() -> dict:
    """Per-nerve tidsserie merget PÅ TVÆRS af processer (runtime+api). Lukker cross-proces-
    blindzonen: infra/sensory/shadow/central_meta lever i runtime-processen og var før usynlige
    udefra. Nerve-key → {proces: {latest, count, meta, recent}}. Owner-only, self-safe."""
    _require_owner()
    from core.services.central_xproc import merged_timeseries
    return await asyncio.to_thread(lambda: {"series": merged_timeseries()})


@router.get("/diagnostics")
async def central_diagnostics() -> dict:
    """Fuldt diagnostik-sted til Central-HUD'ens Diagnostik-mode (Bjørn 2026-06-23: 'mangler et
    fuldt diagnostisk sted til at debugge og læse logs'). Samler Centralens grebne fejl-data:
    uløste incidents (fuld besked+ts+run), anomalier (udefinerede fejl), silent-failure-fund,
    rod-årsager + degraderende. Owner-only, billigt (læser DB). Self-safe."""
    _require_owner()

    def _build() -> dict:
        out: dict = {"incidents": [], "anomalies": [], "instrument": [],
                     "root_causes": [], "degrading": []}
        try:
            from core.runtime.db_central_incidents import list_central_incidents
            out["incidents"] = list_central_incidents(unresolved_only=True, limit=40)
        except Exception:
            pass
        try:
            from core.runtime.db_anomalies import list_anomalies
            out["anomalies"] = list_anomalies(limit=25)
        except Exception:
            pass
        try:
            from core.runtime import db_instrument as dbi
            out["instrument"] = dbi.list_findings(status="open", min_score=3, limit=15)
        except Exception:
            pass
        try:
            from core.services import central_learning as cl
            inc = cl._load()
            out["root_causes"] = cl.root_causes(incidents=inc)[:8]
            out["degrading"] = cl.degrading(incidents=inc)[:8]
        except Exception:
            pass
        # Helbreds-fladerne. Hver sin måling: én der fejler må ikke fjerne de
        # andre fra diagnostikken. En None betyder «ikke målt», ikke «alt ok».
        from importlib import import_module

        for noegle, modul, funktion in (
            ("health", "core.services.central_health",
             "build_central_health_surface"),
            ("signal_health", "core.services.central_signal_health",
             "build_central_signal_health_surface"),
            ("coverage", "core.services.central_coverage",
             "build_central_coverage_surface"),
            ("causal_quality", "core.services.central_causal_quality",
             "build_central_causal_quality_surface"),
        ):
            try:
                out[noegle] = getattr(import_module(modul), funktion)()
            except Exception as exc:  # fladen er valgfri; None bevarer ærlighed
                out[noegle] = {"error": f"{type(exc).__name__}: {exc}"}
        return out

    return await asyncio.to_thread(_build)


@router.get("/providers")
async def central_providers() -> dict:
    """Provider-helbred til Central-HUD'en — læser DET GEMTE ping-snapshot (billigt, ingen live
    ping; selve pinget kører på 5-min-cadence). Owner-only."""
    _require_owner()
    from core.services.provider_health_check import build_provider_health_surface
    return await asyncio.to_thread(build_provider_health_surface)


@router.get("/cost")
async def central_cost(window: str = "today", provider: str | None = None) -> dict:
    """Cost-aggregat (WS3): today/7d/30d total $, tokens ind/ud, cache-hit%, fordelt på
    provider/model/lane + DeepSeek-saldo. Owner-only. Blokerende DB-læsning via to_thread."""
    _require_owner()
    from core.services.central_cost_surface import build_cost_surface
    return await asyncio.to_thread(build_cost_surface, window=window, provider=provider)


@router.get("/agents")
async def central_agents(window: str = "today") -> dict:
    """Agent-observabilitet (B3): costs-aggregat (lane in agent/council) + dispatch-
    udfald (status/nerve fra agents-cluster-trace) + recent results. Owner-only.
    Blokerende DB-læsning via to_thread."""
    _require_owner()
    from core.services.central_agents_surface import build_agents_surface
    return await asyncio.to_thread(build_agents_surface, window=window)


@router.get("/agents/work")
async def central_agents_work(limit: int = 20) -> dict:
    """De sidste subagent-kørsler som arbejdskort. Owner-only.

    Modsat /central/agents' dispatches.recent, der bygger på en nerve som ikke
    fyrer, læser denne agent_runs direkte — dér hvor arbejdet faktisk står."""
    _require_owner()
    from core.services.central_agents_surface import build_recent_agent_work
    return await asyncio.to_thread(build_recent_agent_work, limit=limit)


@router.post("/agents/{agent_id}/cancel")
async def central_agent_cancel(agent_id: str, payload: dict | None = None) -> dict:
    """Afbryd (abort) en kørende agent fra Central CLI Agents-fanen. Owner-only.
    Kalder den eksisterende cancel-mekanisme (agent_runtime_spawn.cancel_agent).
    Self-safe: en fejl vælter ikke routen — svarer 200 med status="error"."""
    _require_owner()
    note = str((payload or {}).get("note") or "")

    def _cancel() -> dict:
        from core.services.agent_runtime_spawn import cancel_agent
        try:
            res = cancel_agent(agent_id, note=note) or {}
            out = dict(res)
            out["agent_id"] = agent_id
            out["action"] = "cancel"
            out.setdefault("status", "cancelled")
            return out
        except Exception as exc:
            return {"status": "error", "agent_id": agent_id,
                    "action": "cancel", "detail": str(exc)}

    return await asyncio.to_thread(_cancel)


@router.post("/agents/{agent_id}/pause")
async def central_agent_pause(agent_id: str) -> dict:
    """Pausér en kørende agent fra Central CLI Agents-fanen. Owner-only.

    NOTE: Der findes p.t. ingen mid-run suspend-primitiv, så "pause" mapper til
    cancel_agent(note="paused via central") — agenten afbrydes med en note der
    markerer at det var en pause. Skift kaldet her ud når en ægte suspend/resume-
    primitiv (mid-run) findes. Self-safe: svarer 200 med status="error" ved fejl."""
    _require_owner()

    def _pause() -> dict:
        from core.services.agent_runtime_spawn import cancel_agent
        try:
            res = cancel_agent(agent_id, note="paused via central") or {}
            out = dict(res)
            out["agent_id"] = agent_id
            out["action"] = "pause"
            out.setdefault("status", "cancelled")
            return out
        except Exception as exc:
            return {"status": "error", "agent_id": agent_id,
                    "action": "pause", "detail": str(exc)}

    return await asyncio.to_thread(_pause)


@router.get("/council")
async def central_council(window: str = "today") -> dict:
    """Council-observabilitet (B3): convocations/deadlocks/roller/event-vs-ondemand-
    split (læser agents-cluster council-events). Empty-safe. Owner-only. to_thread."""
    _require_owner()
    from core.services.central_agents_surface import build_council_surface
    return await asyncio.to_thread(build_council_surface, window=window)


@router.get("/shadow-review")
async def central_shadow_review() -> dict:
    """Shadow-eksperiment-register: hvilke shadow-vinduer kører, og hvilke er MODNE
    til review (så vi ikke glemmer at kalibrere/flippe dem). Bygger surface +
    emitter passivt en `central_meta/shadow_review_due`-påmindelse når noget er
    modent. Owner-only. Self-safe. to_thread."""
    _require_owner()
    from core.services.shadow_experiment_registry import build_shadow_review_surface
    return await asyncio.to_thread(build_shadow_review_surface)


@router.post("/command")
async def central_command(payload: dict) -> dict:
    """Live owner-terminal ind i Centralen — skriv+test kommandoer (status/incidents/trace/nerve/
    toggle/scan/providers/…). Owner-only. Genbruger central_query (sikkerheds-gating bevaret).
    Self-safe via central_terminal."""
    _require_owner()
    line = str((payload or {}).get("line") or "")
    from core.services.central_terminal import run_command
    return await asyncio.to_thread(run_command, line)


@router.get("/mind")
async def central_mind(section: str = "", tab: str = "") -> dict:
    """Jarvis Mind-hub: Centralen som ÉT samlingspunkt for alt MC viser. Owner-only.

    Uden `section` → index (alle faner + undertabs + om de er projiceret). Med `section` → den ENE
    sektions projektion (læser den cachede kilde — ingen anden sandhed). `tab` vælger en undertab
    (fx `mind` + `sjael`): hver undertab er sin egen gruppe, så payloaden bliver 2-36 KB i stedet
    for de 110 KB hele surfaces-dicten fylder. Self-safe via central_hub.
    """
    _require_owner()
    from core.services import central_hub
    if section:
        return await asyncio.to_thread(central_hub.mind_section, section, tab)
    return {"index": await asyncio.to_thread(central_hub.mind_index)}


@router.get("/stream")
async def central_stream() -> StreamingResponse:
    """SSE-live-feed af nerve-fyringer (ægte realtid i stedet for 2s-poll). Owner-only.
    Hver fyring → 'data: {feed-item}\\n\\n'. Keepalive-ping hvert 15s. Self-safe."""
    _require_owner()
    from core.services import central_trace

    async def _gen():
        q = central_trace.sink().subscribe()
        try:
            # send de seneste 12 med det samme (panelet har kontekst fra start)
            for r in central_trace.sink().recent(limit=12):
                yield f"data: {json.dumps(_rec_to_item(r))}\n\n"
            while True:
                try:
                    # Kortere blok (5s, var 15s): en disconnect-et klient holder kun en
                    # thread-pool-tråd i ≤5s → mindre kontention på single-worker'en når flere
                    # streams (Central-felt + Jarvis Mind) skifter (Bjørn 2026-06-23).
                    rec = await asyncio.to_thread(q.get, True, 5)
                except Exception:
                    yield ": ping\n\n"  # timeout → keepalive
                    continue
                yield f"data: {json.dumps(_rec_to_item(rec))}\n\n"
        finally:
            central_trace.sink().unsubscribe(q)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.get("/nerve/{nerve}")
async def central_nerve_detail(nerve: str) -> dict:
    """Lag 5: én nerves spor + kode-lokation + cluster + live tænd/sluk-tilstand."""
    _require_owner()

    def _detail() -> dict:
        from core.services import central_trace
        from core.services.central_catalog import nerve_location, nerve_cluster, is_security_cluster
        from core.services import central_switches
        recs = [_rec_to_item(r) for r in central_trace.sink().recent(limit=400)
                if str(getattr(r, "nerve", "")) == str(nerve)]
        cluster = ""
        try:
            cluster = nerve_cluster(str(nerve)) or ""
        except Exception:
            pass
        enabled = True
        try:
            enabled = central_switches.is_enabled("nerve", str(nerve))
        except Exception:
            pass
        location = ""
        try:
            location = nerve_location(str(nerve)) or ""
        except Exception:
            pass
        return {
            "nerve": str(nerve), "cluster": cluster,
            "security": bool(is_security_cluster(cluster)) if cluster else False,
            "location": location,
            "enabled": bool(enabled),
            "recent": list(reversed(recs))[:20],   # nyeste først
        }

    return await asyncio.to_thread(_detail)


@router.post("/nerve/{nerve}/toggle")
async def central_nerve_toggle(nerve: str, enabled: bool = True) -> dict:
    """Owner kill-switch: tænd/sluk en nerve LIVE (Lag 5). Sikkerheds-nerver kan IKKE
    slås fra (central_switches håndhæver det) — så returneres den uændrede tilstand."""
    _require_owner()

    def _toggle() -> dict:
        try:
            from core.services import central_switches
            res = central_switches.set_enabled("nerve", str(nerve), bool(enabled))
            return {"ok": True, "nerve": str(nerve), "result": res}
        except Exception as exc:
            return {"ok": False, "nerve": str(nerve), "error": f"{type(exc).__name__}: {exc}"}

    return await asyncio.to_thread(_toggle)


@router.get("/tool-infra")
async def central_tool_infra() -> dict:
    """De 12 værktøjs-lag der ellers er usynlige — hver med sine egne signaler.

    Målt 7/11-2026: lagene havde en ``build_*_surface`` men ingen rute kaldte dem,
    så Cartographer'en talte dem som dækkede mens ingen kunne se tallene. Owner-only,
    read-only, blokerende fil-/DB-læsning via to_thread."""
    _require_owner()
    from core.services.central_tool_infra_surface import build_tool_infra_surface
    return await asyncio.to_thread(build_tool_infra_surface)


@router.get("/memory-state")
async def central_memory_state() -> dict:
    """Hukommelses-lagene der ellers er usynlige — hver med sine egne signaler.

    Målt 7/11-2026: 19 hukommelses-flader havde en ``build_*_surface`` men ingen
    læser i apps/. Owner-only, read-only, blokerende fil-/DB-læsning via to_thread."""
    _require_owner()
    from core.services.memory_state_surface import build_memory_state_surface
    return await asyncio.to_thread(build_memory_state_surface)


@router.get("/infra-state")
async def central_infra_state() -> dict:
    """Drifts- og infrastruktur-lagene der ellers er usynlige — hver med sine signaler.

    Målt 7/11-2026 på tværs af HELE repoet (ikke kun apps/): 24 flader blev
    refereret fra ingen anden fil end deres egen. De 23 her er maskinrummet —
    DB-helbred, cache, ressource-signaler, mail, vision, selv-reparation. Netop
    den slags der kører forkert i månedsvis uden at nogen opdager det, fordi
    ingen ser den. Owner-only, read-only, blokerende læsning via to_thread."""
    _require_owner()
    from core.services.infra_state_surface import build_infra_state_surface
    return await asyncio.to_thread(build_infra_state_surface)


@router.get("/inner-state")
async def central_inner_state() -> dict:
    """De indre tilstands-lag der ellers er usynlige — grupperet efter hvem der ejer dem.

    Målt 7/11-2026: efter de tre første aggregatorer (hukommelse, godkendelse,
    drift) stod 31 flader tilbage med nul reference uden for deres egen fil.
    Det er ikke maskinrummet — det er drev-arbitrering, emotions-tagging,
    identitets-komposition, metakognitiv integration, selektiv opmærksomhed,
    subjektiv tid, resonans-henfald, og de beslutnings-lag der afgør hvordan et
    svar bliver til. Grupperet som indre/beslutning/verden, ikke efter mappenavn:
    en fil i core/services/ siger hvor koden bor, ikke hvad den tilhører.

    ``active=False`` med en grund tælles ikke som tavs — en flade der ærligt
    melder at der intet er, er ikke død. Owner-only, read-only, via to_thread."""
    _require_owner()
    from core.services.inner_state_surface import build_inner_state_surface
    return await asyncio.to_thread(build_inner_state_surface)


@router.get("/relation-state")
async def central_relation_state() -> dict:
    """Relation, bruger-model, drev, kreativitet og temporal tilstand — grupperet.

    Målt 7/11-2026: 315 af 462 flader var usynlige for operatøren. De 35 her er
    dem der beskriver HVEM JEG TALER MED og HVAD DER BEVÆGER MIG: relationen til
    brugeren, min model af ham, mine drev og følelser, det kreative og det
    tidslige. Alle kaldt før de blev skrevet ind.

    ``relation_dynamics`` er udeladt med grund: den kaster ``NoUserContextError``
    når ``workspace_dir()`` kaldes uden ``user_id`` — samme fejlform som
    ``memory_write_policy``. At tvinge den ind ville gøre hele fladen tavs i
    stedet for at isolere den ene.

    ``active=False`` med en grund tælles ikke som tavs — en flade der ærligt
    melder at der intet er, er ikke død. Owner-only, read-only, via to_thread."""
    _require_owner()
    from core.services.relation_creative_state_surface import (
        build_relation_creative_state_surface,
    )
    return await asyncio.to_thread(build_relation_creative_state_surface)


@router.get("/self-state")
async def central_self_state() -> dict:
    """Selv- og drømme-tilstand: 34 flader der ellers var usynlige for operatøren.

    Målt 7/11-2026: moduler med præfiks self/dream, hver kaldt før de blev
    registreret. dreaming_session, dream_action_executor og self_model_predictive
    udeladt — de er allerede i inner-state/infra-state. Grupperet selv/drom.
    Owner-only, read-only, via to_thread."""
    _require_owner()
    from core.services.self_dream_state_surface import build_self_dream_state_surface
    return await asyncio.to_thread(build_self_dream_state_surface)


@router.get("/daemon-state")
async def central_daemon_state() -> dict:
    """Daemon- og runtime-lagene: 105 flader der ellers var usynlige for operatøren.

    Målt 7/11-2026: efter de seks første indgange stod 283 af 464 flader uden
    nogen indgang. De 105 her er resten efter central/selv/drøm/privat-bunken —
    det der KOERER: daemoner, rytmer, signal-tracking, refleksions-cyklusser,
    vane- og maal-maskineri, værktøjs-routing, sansning. Grupperet efter hvad
    laget gør, ikke efter mappenavn. relational_warmth udeladt — den kræver
    bruger-kontekst og kaster uden. Owner-only, read-only, via to_thread."""
    _require_owner()
    from core.services.daemon_state_surface import build_daemon_state_surface
    return await asyncio.to_thread(build_daemon_state_surface)


@router.get("/central-state")
async def central_central_state() -> dict:
    """Centralens egne 72 tilstands-lag: sjael, kognition, rytme, drom, relation, maskinrum.

    Maalt 7/11-2026: `central_hub._SURFACE_GROUPS` peger paa navne i
    `cognitive_architecture_surface`, og den funktion kalder IKKE
    `build_*_surface`-funktionerne. Navnene findes derfor to steder der ikke
    taler sammen — de 72 flader saa synlige ud i een maaling og moerke i den
    naeste. Her kaldes hver producent og resultatet taelles.
    `build_layer_surface` er udeladt: den kraever et argument og er maskineri,
    ikke tilstand. Owner-only, read-only, via to_thread."""
    _require_owner()
    from core.services.central_state_surface import build_central_state_surface
    return await asyncio.to_thread(build_central_state_surface)
